"""Davomat qatori uchun talaba qarzi va KPI (CLAUDE.md 8.1–8.3) hamda qayta hisoblash (8.5).

Dars narxi oy darslariga so'm aniqligida bo'lib beriladi — oy yig'indisi kurs narxiga aniq teng (`lesson_share`); KPI so'mgacha
ROUND_HALF_UP bilan yaxlitlanadi (docs/decisions.md). Narx, dars soni va stavka bir hisob davomida
keshlanadi — bir oy qatorlarini qayta hisoblash bir necha so'rov bilan bajariladi.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.payroll.models import KPIRate
from apps.references.models import CoursePrice, DayPattern, LessonFrequency

from .models import Attendance, Contract

KELDI, SABABLI, BESABAB, NOFAOL = "1", "0", "X", "-"
NOTE_NO_FREQ = "Dars soni tasdiqlanmagan"
NOTE_NO_PRICE = "Kurs narxi kiritilmagan"
NOTE_NO_RATE = "KPI stavkasi belgilanmagan"
CALC_FIELDS = ["student_debt", "teacher_kpi", "supporter_kpi", "calc_note"]


# Mayda qoldiq (oy o'rtasidan boshlash, «–» dars, eski yozuvlar): shundan kichigi qarz hisoblanmaydi (buyurtmachi qarori 2026-11-09)
DEBT_MIN = Decimal(10)


def rnd(x):
    return Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP)


def lesson_share(price, freq, n):
    """Oy narxining n-darsga to'g'ri keladigan ulushi, so'mda (buyurtmachi qarori 2026-11-26). Ulushlar 1 so'mgacha farq qiladi va
    `freq` ta darsning yig'indisi narxga aniq teng: 500 000 ÷ 12 → 41 666, 41 667, 41 667, …  Kalendarda dars `freq` dan ko'p
    bo'lsa, ortiqchasi boshidan takrorlanadi."""
    price, i = int(price), (n - 1) % freq + 1
    return Decimal(price * i // freq - price * (i - 1) // freq)


def age_of(age_group):
    """Lidning yosh guruhidan («25-27») eng kichik yoshni oladi → 25; bo'sh yoki noma'lum bo'lsa None."""
    try:
        return int(str(age_group).split("-")[0])
    except (TypeError, ValueError):
        return None


def month_of(d):
    return d.replace(day=1)


class Calculator:
    """Bitta hisob davomida narx, dars soni va stavkalarni keshlaydi."""

    def __init__(self):
        self._price, self._freq, self._rate, self._age, self._days = {}, {}, {}, {}, {}

    def tiers(self, branch_id, course_id, month):
        """{min_age: narx} — har bir yosh pog'onasi uchun shu oyda amalda bo'lgan oxirgi narx (0 — hamma uchun)."""
        key = (branch_id, course_id, month)
        if key not in self._price:
            out = {}
            for age, price in (CoursePrice.objects.filter(branch_id=branch_id, course_id=course_id, effective_from__lte=month)
                               .order_by("-effective_from").values_list("min_age", "price")):
                out.setdefault(age, price)
            self._price[key] = out
        return self._price[key]

    def age(self, branch_id, student_id):
        """Talabaning yoshi — shu filialdagi lidning yosh guruhidan (bo'lmasa None)."""
        from apps.crm.models import Lead

        key = (branch_id, student_id)
        if key not in self._age:
            g = Lead.objects.filter(branch_id=branch_id, student_id=student_id).values_list("age_group", flat=True).first()
            self._age[key] = age_of(g)
        return self._age[key]

    def price(self, branch_id, course_id, month, student_id=None):
        """Oy narxi. Kursda yosh bo'yicha alohida narx bo'lsa va talabaning yoshi (lid yosh guruhi) ma'lum bo'lsa — mos pog'ona narxi,
        aks holda hamma uchun oddiy narx (min_age=0)."""
        tiers = self.tiers(branch_id, course_id, month)
        if student_id and len(tiers) > 1:
            age = self.age(branch_id, student_id)
            if age is not None:
                fit = [m for m in tiers if m and m <= age]
                if fit:
                    return tiers[max(fit)]
        return tiers.get(0)

    def frequency(self, branch_id, pattern_id, course_id, month):
        """8.1: faqat «Tasdiqlangan» yozuv — aynan shu filial + dars kunlari + kurs + oy."""
        key = (branch_id, pattern_id, course_id, month)
        if key not in self._freq:
            f = (LessonFrequency.objects.filter(branch_id=branch_id, day_pattern_id=pattern_id, courses=course_id, year=month.year, month=month.month,
                                                status=LessonFrequency.FreqStatus.APPROVED).values_list("frequency", flat=True).first())
            self._freq[key] = f
        return self._freq[key]

    def lesson_no(self, pattern_id, d):
        """Sananing oy ichidagi dars tartib raqami (1 dan): shu oyda undan oldingi dars kunlari soni + 1."""
        if pattern_id not in self._days:
            self._days[pattern_id] = set(DayPattern.all_objects.filter(pk=pattern_id).values_list("weekdays", flat=True).first() or [])
        return 1 + sum(d.replace(day=k).isoweekday() in self._days[pattern_id] for k in range(1, d.day))

    def rate(self, branch_id, user_id, role_type, course_id, month):
        key = (branch_id, user_id, role_type, course_id, month)
        if key not in self._rate:
            self._rate[key] = (KPIRate.objects.filter(branch_id=branch_id, user_id=user_id, role_type=role_type, course_id=course_id, effective_from__lte=month)
                               .order_by("-effective_from").first())
        return self._rate[key]

    def apply(self, a, contract_type, student_id=None):
        """Qatorning hisoblangan maydonlarini to'ldiradi (saqlamaydi). student_id — yosh bo'yicha narx uchun."""
        month = month_of(a.date)
        grant = contract_type == Contract.Type.GRANT
        price = self.price(a.branch_id, a.course_id, month, student_id)
        freq = self.frequency(a.branch_id, a.day_pattern_id, a.course_id, month)
        notes = []
        # 8.2 — dars bo'ldimi, qarz yoziladi (talaba kelmagan bo'lsa ham)
        if a.status == NOFAOL or grant:
            a.student_debt = Decimal(0)
        elif not freq:
            a.student_debt = None
            notes.append(NOTE_NO_FREQ)
        elif price is None:
            a.student_debt = None
            notes.append(NOTE_NO_PRICE)
        else:
            a.student_debt = lesson_share(price, freq, self.lesson_no(a.day_pattern_id, a.date))
        # 8.3 — KPI faqat Keldi va Sababli uchun
        no_kpi = grant or a.status in (BESABAB, NOFAOL)

        def kpi(user_id, role_type):
            if not user_id or no_kpi:
                return Decimal(0)
            if not freq:
                if NOTE_NO_FREQ not in notes:
                    notes.append(NOTE_NO_FREQ)
                return None
            r = self.rate(a.branch_id, user_id, role_type, a.course_id, month)
            if r is None:
                if NOTE_NO_RATE not in notes:
                    notes.append(NOTE_NO_RATE)
                return Decimal(0)
            if r.type == KPIRate.Kind.PERCENT:
                if price is None:
                    if NOTE_NO_PRICE not in notes:
                        notes.append(NOTE_NO_PRICE)
                    return None
                return rnd(Decimal(r.percent) / 100 * Decimal(price) / freq)
            return rnd(Decimal(r.fixed_amount) / freq)

        a.teacher_kpi = kpi(a.teacher_id, KPIRate.RoleType.TEACHER)
        a.supporter_kpi = kpi(a.supporter_id, KPIRate.RoleType.SUPPORTER)
        a.calc_note = "; ".join(notes)
        return a


def calculate(a, calc=None):
    """Bitta qator (contract yuklangan bo'lsa qo'shimcha so'rovsiz)."""
    return (calc or Calculator()).apply(a, a.contract.type, a.contract.student_id)


@transaction.atomic
def recalculate(qs, batch=500):
    """Berilgan davomat qatorlarini qayta hisoblaydi. Qaytaradi: o'zgargan qatorlar soni."""
    calc = Calculator()
    changed = []
    for a in qs.select_related("contract").only(
        "id", "branch_id", "course_id", "day_pattern_id", "date", "status", "teacher_id", "supporter_id", *CALC_FIELDS, "contract__type", "contract__student_id",
    ).iterator(chunk_size=batch):
        before = tuple(getattr(a, f) for f in CALC_FIELDS)
        calc.apply(a, a.contract.type, a.contract.student_id)
        if tuple(getattr(a, f) for f in CALC_FIELDS) != before:
            changed.append(a)
    Attendance.objects.bulk_update(changed, CALC_FIELDS, batch_size=batch)
    return len(changed)


def month_range(month):
    nxt = (month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return month, nxt


def recalc_month(year, month, **filters):
    start, end = month_range(datetime.date(year, month, 1))
    return recalculate(Attendance.objects.filter(date__gte=start, date__lt=end, **filters))


def recalc_from(month, **filters):
    """Narx yoki stavka o'zgarganda: shu oydan boshlab."""
    return recalculate(Attendance.objects.filter(date__gte=month, **filters))

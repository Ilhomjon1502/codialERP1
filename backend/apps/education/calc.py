"""Davomat qatori uchun talaba qarzi va KPI (CLAUDE.md 8.1–8.3) hamda qayta hisoblash (8.5).

Bo'lish so'mgacha ROUND_HALF_UP bilan yaxlitlanadi (docs/decisions.md). Narx, dars soni va stavka bir hisob davomida
keshlanadi — bir oy qatorlarini qayta hisoblash bir necha so'rov bilan bajariladi.
"""

import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.payroll.models import KPIRate
from apps.references.models import CoursePrice, LessonFrequency

from .models import Attendance, Contract

KELDI, SABABLI, BESABAB, NOFAOL = "1", "0", "X", "-"
NOTE_NO_FREQ = "Dars soni tasdiqlanmagan"
NOTE_NO_PRICE = "Kurs narxi kiritilmagan"
NOTE_NO_RATE = "KPI stavkasi belgilanmagan"
CALC_FIELDS = ["student_debt", "teacher_kpi", "supporter_kpi", "calc_note"]


def rnd(x):
    return Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP)


def month_of(d):
    return d.replace(day=1)


class Calculator:
    """Bitta hisob davomida narx, dars soni va stavkalarni keshlaydi."""

    def __init__(self):
        self._price, self._freq, self._rate = {}, {}, {}

    def price(self, branch_id, course_id, month):
        key = (branch_id, course_id, month)
        if key not in self._price:
            p = (CoursePrice.objects.filter(branch_id=branch_id, course_id=course_id, effective_from__lte=month)
                 .order_by("-effective_from").values_list("price", flat=True).first())
            self._price[key] = p
        return self._price[key]

    def frequency(self, branch_id, pattern_id, course_id, month):
        """8.1: faqat «Tasdiqlangan» yozuv — aynan shu filial + dars kunlari + kurs + oy."""
        key = (branch_id, pattern_id, course_id, month)
        if key not in self._freq:
            f = (LessonFrequency.objects.filter(branch_id=branch_id, day_pattern_id=pattern_id, courses=course_id, year=month.year, month=month.month,
                                                status=LessonFrequency.FreqStatus.APPROVED).values_list("frequency", flat=True).first())
            self._freq[key] = f
        return self._freq[key]

    def rate(self, branch_id, user_id, role_type, course_id, month):
        key = (branch_id, user_id, role_type, course_id, month)
        if key not in self._rate:
            self._rate[key] = (KPIRate.objects.filter(branch_id=branch_id, user_id=user_id, role_type=role_type, course_id=course_id, effective_from__lte=month)
                               .order_by("-effective_from").first())
        return self._rate[key]

    def apply(self, a, contract_type):
        """Qatorning hisoblangan maydonlarini to'ldiradi (saqlamaydi)."""
        month = month_of(a.date)
        grant = contract_type == Contract.Type.GRANT
        price = self.price(a.branch_id, a.course_id, month)
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
            a.student_debt = rnd(Decimal(price) / freq)
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
    return (calc or Calculator()).apply(a, a.contract.type)


@transaction.atomic
def recalculate(qs, batch=500):
    """Berilgan davomat qatorlarini qayta hisoblaydi. Qaytaradi: o'zgargan qatorlar soni."""
    calc = Calculator()
    changed = []
    for a in qs.select_related("contract").only(
        "id", "branch_id", "course_id", "day_pattern_id", "date", "status", "teacher_id", "supporter_id", *CALC_FIELDS, "contract__type",
    ).iterator(chunk_size=batch):
        before = tuple(getattr(a, f) for f in CALC_FIELDS)
        calc.apply(a, a.contract.type)
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

"""«Shu oy to'lovi» — oyning kurs narxi bo'yicha kutilayotgan to'lov (davomatga bog'liq emas).

Markazda to'lov oldindan (oyning 10-sanasigacha) olinadi, davomat esa kech olinishi mumkin. Shuning uchun:

    oy boshidagi balans = opening_balance + oy boshigacha yozilgan qarz − oy boshigacha to'lov va chegirma
    shu oy narxi        = kurs narxi × (shartnoma amal qilgan dars kunlari ÷ oydagi barcha dars kunlari)   # pro-rata
    to'lashi kerak      = max(0, oy boshidagi balans + shu oy narxi − shu oydagi to'lov va chegirma)

Oldindan to'lagan (balansi minusda) o'quvchi uchun kredit shu oyni yopadi; eski qarz «to'lashi kerak»ga qo'shiladi.
"""

import calendar
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum

from apps.core.permissions import today as today_fn

from .calc import Calculator, rnd
from .models import Attendance, Contract


def _lessons(weekdays, start, end):
    """[start, end] oralig'idagi dars kunlari soni."""
    if end < start:
        return 0
    return sum(1 for i in range((end - start).days + 1) if (start + datetime.timedelta(days=i)).isoweekday() in weekdays)


def month_dues(contracts_qs, month=None, on=None):
    """`contracts_qs` — ko'rinish doirasidagi shartnomalar (filial doirasi qo'llangan). Qaytaradi: {contract_id: {...}}
    faqat shu oy uchun to'lashi kerak bo'lganlar (to_pay > 0) va ularning hisobi. Ro'yxat to'lashi kerak bo'yicha kamayish tartibida emas —
    tartiblash chaqiruvchida."""
    from apps.finance.models import Payment

    on = on or today_fn()
    month = (month or on).replace(day=1)
    last = calendar.monthrange(month.year, month.month)[1]
    month_end = month.replace(day=last)

    cs = list(
        contracts_qs.filter(type=Contract.Type.PAID, start_date__lte=month_end)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=max(month, min(on, month_end))))
        .select_related("group__day_pattern", "branch")
    )
    if not cs:
        return {}
    ids = [c.pk for c in cs]

    def per_contract(qs, **ann):
        return {r["contract"]: r for r in qs.filter(contract__in=ids, is_deleted=False).order_by().values("contract").annotate(**ann)}

    charged_before = per_contract(Attendance.objects.filter(date__lt=month), s=Sum("student_debt"))
    pay_before = per_contract(Payment.objects.filter(date__lt=month), a=Sum("amount"), d=Sum("discount"))
    pay_month = per_contract(Payment.objects.filter(date__gte=month, date__lte=month_end), a=Sum("amount"), d=Sum("discount"))

    calc = Calculator()
    zero = Decimal(0)
    out = {}
    for c in cs:
        g = c.group
        weekdays = g.day_pattern.weekdays
        total_lessons = _lessons(weekdays, month, month_end)
        frm = max(month, c.start_date, g.start_date)
        to = min(month_end, c.end_date or month_end, g.end_date or month_end)
        mine = min(_lessons(weekdays, frm, to), total_lessons)
        price = calc.price(c.branch_id, c.course_id, month)
        no_price = price is None
        price = Decimal(price or 0)
        month_price = rnd(price * mine / total_lessons) if total_lessons else zero
        before = (c.opening_balance or zero) + (charged_before.get(c.pk, {}).get("s") or zero) \
            - (pay_before.get(c.pk, {}).get("a") or zero) - (pay_before.get(c.pk, {}).get("d") or zero)
        paid_m = (pay_month.get(c.pk, {}).get("a") or zero) + (pay_month.get(c.pk, {}).get("d") or zero)
        to_pay = max(zero, before + month_price - paid_m)
        if to_pay <= 0:
            continue
        due_day = min(c.branch.payment_due_day or 10, last)
        deadline = month.replace(day=due_day)
        out[c.pk] = {
            "price": price,
            "month_price": month_price,
            "lessons": mine,
            "lessons_total": total_lessons,
            "prev_balance": before,
            "paid_month": paid_m,
            "to_pay": to_pay,
            "deadline": deadline,
            "overdue": on > deadline,
            "days_over": max(0, (on - deadline).days),
            "no_price": no_price,
        }
    return out


def due_map_by_group(contracts_qs, on=None):
    """Telegram uchun: {group_id: [(contract, info)]} — to'lashi kerak bo'yicha kamayish tartibida."""
    dues = month_dues(contracts_qs, on=on)
    cs = {c.pk: c for c in contracts_qs.filter(pk__in=dues.keys()).select_related("student")}
    by_group = defaultdict(list)
    for pk, info in sorted(dues.items(), key=lambda kv: -kv[1]["to_pay"]):
        by_group[cs[pk].group_id].append((cs[pk], info))
    return by_group

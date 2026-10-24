"""Mijozlar boti kabineti (B3): o'quvchi va vasiy o'z to'lovlari, davomati, dars jadvali va to'lov muddatini ko'radi — faqat o'qish.

Ko'rinadigan ma'lumot botga ulangan talabaniki (`BotLink`); vasiy ham, o'quvchining o'zi ham bir xil narsani ko'radi (buyurtmachi qarori).
KPI, o'qituvchi izohlari va ichki hisoblar ko'rsatilmaydi. Hisob serverning mavjud servislaridan olinadi (`with_balance`, `month_dues`).
"""

import datetime
from decimal import Decimal
from html import escape

from django.utils import timezone

from apps.calls.sms import MONTHS, money
from apps.education.dues import month_dues
from apps.education.models import Attendance, Contract
from apps.education.services import NOFAOL, REJADA, period_status, with_balance
from apps.finance.models import Confirm, Payment

ACTIONS = {"pay": "💳 To'lovlar", "att": "📋 Davomat", "sch": "📅 Dars jadvali", "due": "💰 To'lov muddati"}
MENU_TEXTS = {label: key for key, label in ACTIONS.items()}
WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
SHORT = ["Dush", "Sesh", "Chor", "Pay", "Jum", "Shan", "Yak"]
STATUS = {"1": "✅ Keldi", "0": "🟡 Sababli", "X": "❌ Sababsiz"}
CASH = {"CASH": "naqd", "CARD": "karta", "BANK": "bank"}
PAYMENTS_SHOWN = 10
ATTENDANCE_SHOWN = 12


def menu_markup():
    keys = list(ACTIONS.values())
    return {"keyboard": [[{"text": keys[0]}, {"text": keys[1]}], [{"text": keys[2]}, {"text": keys[3]}]], "resize_keyboard": True, "is_persistent": True}


def _fmt(d):
    return f"{d:%d.%m.%Y}"


def _group(group):
    return f"{group.course.name} / #{group.number}"


def _contracts(student):
    return list(Contract.objects.filter(student=student, is_deleted=False).select_related("course", "group__course", "group__day_pattern", "group__time",
                                                                                          "group__room", "group__teacher").order_by("-start_date"))


def _active(contracts, today):
    return [c for c in contracts if period_status(c.start_date, c.end_date, today) != NOFAOL]


def _head(title, student):
    return f"<b>{title}</b>\n{escape(student.first_name)} {escape(student.last_name)}\n"


def payments_text(student, today=None):
    contracts = _contracts(student)
    if not contracts:
        return _head("💳 To'lovlar", student) + "\nShartnoma topilmadi."
    ids = [c.pk for c in contracts]
    pays = list(Payment.objects.filter(contract__in=ids, is_deleted=False).select_related("contract__course", "discount_type").order_by("-date", "-created_at")[:PAYMENTS_SHOWN])
    total = sum((p.amount for p in Payment.objects.filter(contract__in=ids, is_deleted=False)), Decimal(0))
    lines = [_head("💳 To'lovlar", student)]
    if pays:
        for p in pays:
            if not p.amount and p.discount:  # faqat chegirma yozuvi (masalan tavsiya bonusi)
                lines.append(f"{_fmt(p.date)} — 🎁 chegirma <b>{money(p.discount)}</b> so'm" + (f" ({escape(p.discount_type.name)})" if p.discount_type_id else ""))
                continue
            extra = f" + chegirma {money(p.discount)}" if p.discount else ""
            wait = " ⏳ tasdiqlanmoqda" if Confirm.PENDING in (p.noncash_status, p.discount_status) else ""
            lines.append(f"{_fmt(p.date)} — <b>{money(p.amount)}</b> so'm ({CASH.get(p.cash_type, p.cash_type or '—')}){extra}{wait}")
        lines.append(f"\nJami to'langan: <b>{money(total)}</b> so'm")
    else:
        lines.append("\nHali to'lov kiritilmagan.")
    for c in with_balance(Contract.objects.filter(pk__in=[c.pk for c in _active(contracts, today or timezone.localdate())])).select_related("course"):
        bal = c.balance or Decimal(0)
        state = f"qarz <b>{money(bal)}</b> so'm" if bal > 0 else f"oldindan to'langan <b>{money(-bal)}</b> so'm" if bal < 0 else "qarz yo'q"
        lines.append(f"{escape(c.course.name)}: {state}")
    return "\n".join(lines)


def attendance_text(student, today=None):
    today = today or timezone.localdate()
    contracts = _contracts(student)
    if not contracts:
        return _head("📋 Davomat", student) + "\nShartnoma topilmadi."
    qs = Attendance.objects.filter(contract__in=[c.pk for c in contracts], is_deleted=False, status__in=list(STATUS))
    rows = list(qs.select_related("course").order_by("-date")[:ATTENDANCE_SHOWN])
    month = qs.filter(date__gte=today.replace(day=1), date__lte=today)
    counts = {s: month.filter(status=s).count() for s in STATUS}
    lines = [_head("📋 Davomat", student)]
    if not rows:
        return "\n".join(lines) + "\nHali davomat belgilanmagan."
    lines.append(f"{MONTHS[today.month - 1].capitalize()} oyida: ✅ {counts['1']} · 🟡 {counts['0']} · ❌ {counts['X']} (jami {sum(counts.values())} dars)\n")
    for a in rows:
        lines.append(f"{a.date:%d.%m} ({SHORT[a.date.weekday()]}) — {STATUS[a.status]}")
    return "\n".join(lines)


def next_lesson(group, now=None):
    """Guruhning keyingi dars kuni (bugun — dars hali tugamagan bo'lsa); guruh tugagan bo'lsa None."""
    now = now or timezone.localtime()
    weekdays = set(group.day_pattern.weekdays)
    for i in range(0, 15):
        d = now.date() + datetime.timedelta(days=i)
        if d.isoweekday() not in weekdays or d < group.start_date or (group.end_date and d > group.end_date):
            continue
        if i == 0 and now.time() > group.time.end_time:
            continue
        return d
    return None


def schedule_text(student, today=None):
    now = timezone.localtime()
    today = today or now.date()
    mine = [c for c in _active(_contracts(student), today) if c.group_id]
    lines = [_head("📅 Dars jadvali", student)]
    if not mine:
        return "\n".join(lines) + "\nHozir faol shartnoma yo'q."
    for c in mine:
        g = c.group
        lines.append(f"\n<b>{escape(_group(g))}</b>" + (" (boshlanmagan)" if period_status(c.start_date, c.end_date, today) == REJADA else ""))
        lines.append(f"🗓 {escape(', '.join(x.strip() for x in g.day_pattern.name.split(',')))} · {g.time.start_time:%H:%M}–{g.time.end_time:%H:%M}")
        lines.append(f"🏫 Xona: {escape(g.room.name)} · 👨‍🏫 Ustoz: {escape(g.teacher.full_name)}")
        if c.start_date > today:
            lines.append(f"Boshlanishi: {_fmt(max(c.start_date, g.start_date))}")
        elif (nl := next_lesson(g, now)):
            lines.append(f"Keyingi dars: {'bugun' if nl == today else WEEKDAYS[nl.weekday()]}, {_fmt(nl)}")
    return "\n".join(lines)


def due_text(student, today=None):
    today = today or timezone.localdate()
    mine = _active(_contracts(student), today)
    lines = [_head("💰 To'lov muddati", student)]
    if not mine:
        return "\n".join(lines) + "\nHozir faol shartnoma yo'q."
    month = today.replace(day=1)
    qs = Contract.objects.filter(pk__in=[c.pk for c in mine])
    dues = month_dues(qs, month, today)
    balances = {c.pk: c.balance or Decimal(0) for c in with_balance(qs)}
    for c in mine:
        lines.append(f"\n<b>{escape(c.course.name)}</b>")
        if c.type == Contract.Type.GRANT:
            lines.append("Grant — to'lov talab qilinmaydi.")
            continue
        info = dues.get(c.pk)
        if info and info["no_price"]:
            lines.append("Bu oy narxi hali belgilanmagan — administratorga murojaat qiling.")
        elif info:
            lines.append(f"{MONTHS[month.month - 1].capitalize()} oyi uchun to'lash kerak: <b>{money(info['to_pay'])}</b> so'm")
            lines.append(f"Muddat: {_fmt(info['deadline'])}" + (f" ⚠️ {info['days_over']} kun o'tdi" if info["overdue"] else ""))
            if info["prev_balance"] > 0:
                lines.append(f"Shundan avvalgi oylardan qarz: {money(info['prev_balance'])} so'm")
        else:
            lines.append(f"✅ {MONTHS[month.month - 1].capitalize()} oyi uchun to'lov qilingan.")
        bal = balances.get(c.pk, Decimal(0))
        if bal < 0:
            lines.append(f"Oldindan to'langan: {money(-bal)} so'm")
    return "\n".join(lines)


TEXTS = {"pay": payments_text, "att": attendance_text, "sch": schedule_text, "due": due_text}

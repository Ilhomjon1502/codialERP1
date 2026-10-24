"""Hozirgi (faol shartnomali) talabalarni mijozlar botiga ulash: administrator bir marta «Mavjud talabalarni taklif qilish»ni bosadi →
server hisobi (nechta talaba/raqam/SMS) → tasdiq → har ulanmagan raqamga SMS (oxirida shu raqamga xos bot havolasi va kodi).

Avtomatik emas — faqat administrator tasdig'i bilan. Takror yuborilmaydi (kalit: taklif); ulangan raqamga yuborilmaydi.
Yuborilgan SMS shu taklifning birinchi eslatmasi hisoblanadi: keyingi eslatmalar «Botga ulanish eslatmasi» qoidasi bo'yicha (har `reminder_days` kunda).
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.calls import sms
from apps.calls.models import SmsMessage
from apps.core.scoping import scope_branch
from apps.crm.models import Student

from . import services as bot
from .models import BotInvite

DEFAULT_TEXT = "Codial o'quv markazining Telegram boti ishga tushdi: to'lov, davomat va dars jadvalingizni shu yerda ko'rasiz. Ulaning:"
PLACEHOLDERS = ["ism", "talaba"]


def active_students(user, today=None):
    """Faol yoki boshlanmagan shartnomasi bor talabalar (foydalanuvchi filiallari doirasida)."""
    today = today or timezone.localdate()
    qs = scope_branch(Student.objects.filter(is_deleted=False), user, "branch")
    return qs.filter(Q(contracts__is_deleted=False, contracts__end_date__isnull=True)
                     | Q(contracts__is_deleted=False, contracts__end_date__gte=today)).distinct()


def _check(text):
    text = sms.plain(text or "")
    if not text:
        raise ValidationError({"text": ["Matn kiriting"]})
    bad = sorted({t for t in sms._TOKEN.findall(text) if t not in PLACEHOLDERS})
    if bad:
        raise ValidationError({"text": [f"Noma'lum o'rinbosar: {', '.join('{' + b + '}' for b in bad)}. Mavjud: {{ism}}, {{talaba}}"]})
    return text


def _plan(user, text):
    if not bot.configured():
        raise ValidationError({"detail": "Mijozlar boti hali ulanmagan (serverda deploy/set-clientbot.sh)"})
    text = _check(text)
    out = {"students": 0, "numbers": 0, "messages": 0, "parts": 0, "skipped_linked": 0, "skipped_sent": 0, "no_phone": 0, "no_device": [], "sample": "",
           "sample_parts": 0}
    rows, devices, no_device = [], {}, set()
    students = active_students(user).select_related("parent", "branch")
    for st in students:
        phones = sms.recipients(st)
        if not phones:
            out["no_phone"] += 1
            continue
        out["students"] += 1
        msg = sms.render(text, {"ism": st.first_name, "talaba": f"{st.first_name} {st.last_name}".strip()})
        for phone, who in phones:
            out["numbers"] += 1
            if bot.is_linked(st, phone):
                out["skipped_linked"] += 1
                continue
            inv = BotInvite.objects.filter(student=st, phone=phone).first()
            if inv and SmsMessage.all_objects.filter(key=f"botinv:{inv.pk}").exists():
                out["skipped_sent"] += 1
                continue
            if st.branch_id not in devices:
                devices[st.branch_id] = sms.branch_device(st.branch_id)
            if not devices[st.branch_id]:
                no_device.add(st.branch.name)
                continue
            rows.append((st, phone, who, msg))
            out["sample"] = out["sample"] or msg + " Telegram bot: t.me/" + settings.CLIENT_BOT_USERNAME + "?start=XXXXXXXX"
    out["messages"] = len(rows)
    out["no_device"] = sorted(no_device)
    out["sample"] = sms.plain(out["sample"])
    out["sample_parts"] = sms.segments(out["sample"]) if out["sample"] else 0
    return out, rows, devices


def preview(user, text):
    out, rows, _ = _plan(user, text)
    # taxminiy bo'laklar: namuna bo'yicha (haqiqiy kod uzunligi bir xil)
    out["parts"] = out["messages"] * out["sample_parts"]
    return out


@transaction.atomic
def send(user, text):
    out, rows, devices = _plan(user, text)
    msgs = []
    for st, phone, who, msg in rows:
        inv = bot.invite_for(st, phone)
        full = msg + sms.plain(bot.invite_suffix(st, phone, st.branch) or "")
        if "t.me/" not in full:  # sozlamada havola o'chirilgan bo'lsa ham taklif SMS'ida havola kerak
            full += f" Telegram bot: {bot.link_url(inv.code)}"
        BotInvite.objects.filter(pk=inv.pk).update(reminders=inv.reminders + 1, last_reminded_at=timezone.now())
        msgs.append(SmsMessage(branch_id=st.branch_id, device=devices[st.branch_id], student=st, kind=SmsMessage.Kind.BOT, phone=phone, recipient=who,
                               text=full, parts=sms.segments(full), key=f"botinv:{inv.pk}", created_by=user, updated_by=user))
    SmsMessage.objects.bulk_create(msgs, ignore_conflicts=True)
    out["messages"] = len(msgs)
    out["parts"] = sum(m.parts for m in msgs)
    return out

"""Xabarlar: kimga, nima (CLAUDE.md 12). Hamma funksiyalar xatoga chidamli — xabar yuborilmasa ham asosiy amal buzilmaydi.

Kim oladi (buyurtmachi qarori 2026-10-13): xodim «Telegram» oynasida o'zi belgilagan xabar turlari keladi, lekin faqat
tizimda **ko'rish huquqi** bor narsa haqida (EVENT_PERM) va o'z filiali doirasida. Xodim hali tanlamagan bo'lsa — rol bo'yicha
standart (DEFAULT_ROLES) yoki hodisaga bevosita aloqador bo'lsa (g'azna mas'uli, guruh ustozi).
"""

import json
import logging
import urllib.parse
import urllib.request
from html import escape

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.permissions import can, is_top, role_code
from apps.core.roles import TEACHER_ROLES, RoleCode

from .models import EVENTS, ExtraRecipient, Outbox, TelegramLink, new_code

log = logging.getLogger(__name__)
R = RoleCode

# Xabar turini olish uchun kerakli ko'rish huquqi (bo'lim, amal)
EVENT_PERM = {
    "new_lead": ("leads", "v"),
    "lead_change": ("leads", "v"),
    "contract_change": ("contracts", "v"),
    "approval": ("payments", "v"),
    "transfer": ("transfers", "v"),
    "makeup": ("attendance", "p"),
    "attendance_missing": ("attendance", "v"),
    "daily_report": ("audit", "v"),  # hisobotda audit (kim nima qildi) bor — faqat Admin va Bosh menejer
    "lesson_start": ("attendance", "a"),
    "morning_plan": ("payments", "v"),  # qarzdorlar ro'yxati bor
    "task": ("staffTasks", "v"),
    "debt_lesson": ("debtors", "v"),
    "demo_soon": ("leads", "v"),
    "lead_callback": ("leads", "e"),  # tugmalar lidni o'zgartiradi
    "sms_problem": ("sms", "v"),
    "survey": ("clientbot", "v"),
    "referral": ("clientbot", "v"),
    "founder_report": ("founderReport", "v"),
}
# Xodim hali tanlamagan bo'lsa — kimga standart holda boradi
DEFAULT_ROLES = {
    "new_lead": {R.ADMINISTRATOR, R.ADMINISTRATOR_HISOBCHI, R.BOSH_MENEJER, R.FILIAL_MENEJERI, R.MARKETOLOG},
    "lead_change": {R.MARKETOLOG},
    "contract_change": {R.MARKETOLOG},
    "approval": {R.ADMIN, R.BOSH_MENEJER, R.FILIAL_MENEJERI},
    "transfer": set(),  # standart — faqat qabul qiluvchi g'azna mas'ullari (default_users)
    "makeup": {R.BOSH_MENEJER, R.FILIAL_MENEJERI, R.ADMINISTRATOR, R.ADMINISTRATOR_HISOBCHI},
    "attendance_missing": {R.ADMINISTRATOR, R.ADMINISTRATOR_HISOBCHI},  # + guruh ustozi (default_users)
    "daily_report": {R.BOSH_MENEJER},
    "lesson_start": set(),  # standart — faqat guruh ustozi (default_users)
    "morning_plan": {R.ADMINISTRATOR_HISOBCHI},
    "task": set(),  # faqat topshiriq ishtirokchilari (default_users)
    "debt_lesson": {R.ADMINISTRATOR_HISOBCHI},
    "demo_soon": {R.ADMINISTRATOR_HISOBCHI},  # + guruh ustozi (default_users)
    "lead_callback": {R.ADMINISTRATOR_HISOBCHI},  # buyurtmachi qarori 2026-10-21: hamma Administrator+Hisobchiga
    "sms_problem": {R.BOSH_MENEJER},  # buyurtmachi qarori 2026-10-23: SMS bormasa Bosh menejerga
    "survey": {R.BOSH_MENEJER},  # tamomlash so'rovnomasi javobi (B4)
    "referral": {R.BOSH_MENEJER},  # tavsiya bonusi (B5)
    "founder_report": {R.ASOSCHI},  # asoschiga faqat shu xabar boradi (2026-10-25)
}


def allowed(user, event):
    if role_code(user) == R.ASOSCHI:  # asoschi saytda hamma narsani ko'radi, botga esa faqat kunlik hisobot keladi (operatsion xabarlar yo'q)
        return event == "founder_report"
    sec, op = EVENT_PERM[event]
    return can(user, sec, op)


LOCKED = {"demo_soon"}  # o'chirib bo'lmaydigan xabarlar (buyurtmachi qarori 2026-10-19): standart oluvchilarga har doim boradi


def wants(link, event, default=False):
    """Xodimning tanlovi; tanlamagan bo'lsa — standart. Qulflangan xabarlar — standart oluvchilarga (rol yoki hodisaga aloqador) har doim."""
    if event in LOCKED:
        return default or role_code(link.user) in DEFAULT_ROLES[event]
    v = link.prefs.get(event)
    return v if v is not None else (default or role_code(link.user) in DEFAULT_ROLES[event])


def events_for(user, link):
    """«Telegram» oynasi uchun: xodimga ruxsat etilgan xabar turlari va hozirgi holati."""
    return [{"key": k, "label": label, "on": wants(link, k)} for k, label in EVENTS if allowed(user, k) and k not in LOCKED]


def in_branch(user, branch):
    return branch is None or is_top(user) or user.branches.filter(pk=branch.pk).exists()


def notify(event, text, branch=None, default_users=(), key="", only=None, markup=None, exclude=None, force=False):
    """Bog'langan, huquqi bor, filial doirasidagi va shu xabarni tanlagan xodimlarga navbatga qo'yadi (tranzaksiya tugagach).
    default_users — hodisaga bevosita aloqador xodimlar (standart holda oladi); only(user) — qo'shimcha cheklov (masalan ustoz faqat o'z guruhi);
    key — takrorlanmaslik uchun; force — xodimning «o'chirilgan» tanlovini hisobga olmaydi (huquq va filial baribir tekshiriladi)."""
    default_ids = {u.pk for u in default_users if u}

    def enqueue():
        try:
            links = TelegramLink.objects.filter(chat_id__isnull=False, user__employment_status=User.Employment.ACTIVE).select_related("user__role")
            done = set(Outbox.objects.filter(key=key).values_list("user_id", flat=True)) if key else set()
            rows = []
            for lk in links:
                u = lk.user
                if u.pk in done or (exclude and u.pk == exclude.pk) or not allowed(u, event) or not in_branch(u, branch) or (only and not only(u)):
                    continue
                if force or wants(lk, event, default=u.pk in default_ids):
                    rows.append(Outbox(user=u, chat_id=lk.chat_id, event=event, key=key, text=text, markup=markup or {}))
            # Qo'shimcha qabul qiluvchilar (masalan umumiy @codial_admin): (1) xabar tanlangan rollarga standart keladigan turdan bo'lsa yoki
            # (2) xabar aynan shu rollardagi xodimga mo'ljallangan bo'lsa (masalan topshiriq) — nusxa; (2) da «Kimga» yoziladi. Bitta chatga bir marta.
            sent_to = {x.chat_id for x in rows}
            for er in ExtraRecipient.objects.filter(active=True):
                by_role = any(role in DEFAULT_ROLES.get(event, ()) for role in er.roles)
                targets = [u for u in default_users if u and role_code(u) in er.roles]
                if er.chat_id in sent_to or not (by_role or targets):
                    continue
                if key and Outbox.objects.filter(chat_id=er.chat_id, key=key).exists():
                    continue
                names = ", ".join(escape(str(u)) for u in targets)
                body = text if by_role else f"👤 <b>Kimga:</b> {names}\n{text}"
                rows.append(Outbox(user=None, chat_id=er.chat_id, event=event, key=key, text=body, markup=markup or {}))
            Outbox.objects.bulk_create(rows)
        except Exception:  # noqa: BLE001 — xabar asosiy amalni buzmasin
            log.exception("Telegram navbatiga yozilmadi")

    transaction.on_commit(enqueue)


def money(n):
    return f"{int(n or 0):,}".replace(",", " ") + " so'm"


# ------------------------------------------------------------------ hodisalar

def lead_created(lead):
    st = lead.student
    notify("new_lead", f"🆕 <b>Yangi lid</b>\n{escape(st.full_name)} · +998{st.phone1}\nKurs: {escape(str(lead.course))} · manba: {escape(str(lead.source))}",
           branch=lead.branch)


def _lead_status(code):
    """«3» → «3. Sinov darsga yozildi» — xabarni o'qigan odam raqamni yodlab yurmasin."""
    from apps.crm.models import Lead

    label = dict(Lead.LeadStatus.choices).get(code)
    return f"{code}. {label}" if label else str(code or "—")


def lead_changed(lead, old_status, user):
    from apps.calls import auto_sms

    auto_sms.lead_status_changed(lead, old_status)  # «Sinov darsga qatnashdi» SMS/bot xabari (qoida yoqilgan bo'lsa)
    st = lead.student
    notify("lead_change", f"🔄 <b>Lid o'zgardi</b>\n{escape(st.full_name)} · {escape(str(lead.course))}\n"
                          f"{escape(_lead_status(old_status))}\n➡️ <b>{escape(_lead_status(lead.status))}</b>\n✍️ {escape(str(user))}",
           branch=lead.branch, exclude=user)


def contract_saved(c, user, created, note=""):
    head = "📄 <b>Yangi shartnoma</b>" if created else "📄 <b>Shartnoma o'zgardi</b>"
    extra = f"\n{escape(note)}" if note else ""
    notify("contract_change", f"{head}\n{escape(c.name)} · {escape(str(c.course))}{extra}\n✍️ {escape(str(user))}", branch=c.branch, exclude=user)


def _buttons(*pairs):
    """Xabar ostidagi tugmalar: [(matn, callback_data)] — har biri alohida qatorda."""
    return {"inline_keyboard": [[{"text": t, "callback_data": d}] for t, d in pairs]}


def _comment(text):
    text = (text or "").strip()
    return f"\n💬 {escape(text[:500])}" if text else ""


def payment_pending(p):
    parts, buttons = [], []
    if p.discount_status == "Tasdiqlashga":
        parts.append(f"chegirma {money(p.discount)} ({escape(str(p.discount_type))})")
        buttons.append(("✅ Chegirmani tasdiqlash", f"ap:d:{p.pk}"))
    if p.noncash_status == "Tasdiqlashga":
        parts.append(f"naqdsiz to'lov {money(p.amount)} ({p.get_cash_type_display()})")
        buttons.append(("✅ Naqdsiz to'lovni tasdiqlash", f"ap:n:{p.pk}"))
    if parts:
        who = f"\n✍️ {escape(str(p.created_by))}" if p.created_by_id else ""
        notify("approval", f"⏳ <b>Tasdiq kutilmoqda</b>: {', '.join(parts)}\n{escape(p.contract.name)}{_comment(p.comment)}{who}",
               branch=p.branch, markup=_buttons(*buttons))


def transfer_created(t):
    from apps.finance.services import scoped_account_ids

    def sees(u):
        ids = scoped_account_ids(u)
        return ids is None or t.sender_account_id in ids or t.receiver_account_id in ids

    notify("transfer", f"🔁 <b>O'tkazma kutilmoqda</b>: {money(t.amount)}\n{escape(str(t.sender_account))} → {escape(str(t.receiver_account))}{_comment(t.comment)}",
           default_users=list(t.receiver_account.responsible.all()), only=sees, markup=_buttons(("✅ Qabul qildim", f"ap:t:{t.pk}")))


def transfer_changed(t, what, user):
    """Tasdiqlanmagan o'tkazma o'zgardi yoki bekor qilindi — qabul qiluvchiga xabar (tugmasiz: eski tugma ishlamaydi yoki yangilangan summani tasdiqlaydi)."""
    from apps.finance.services import scoped_account_ids

    def sees(u):
        ids = scoped_account_ids(u)
        return ids is None or t.sender_account_id in ids or t.receiver_account_id in ids

    markup = None if what != "o'zgardi" else _buttons(("✅ Qabul qildim", f"ap:t:{t.pk}"))
    notify("transfer", f"✏️ <b>O'tkazma {what}</b>: {money(t.amount)}\n{escape(str(t.sender_account))} → {escape(str(t.receiver_account))}{_comment(t.comment)}\n✍️ {escape(str(user))}",
           default_users=list(t.receiver_account.responsible.all()), only=sees, markup=markup, exclude=user)


def makeup_requested(m):
    a = m.attendance
    notify("makeup", f"📚 <b>Dars yetkazildi — so'rov</b>\n{escape(str(m.teacher))}: {escape(a.contract.student.full_name)}, {a.date:%d.%m.%Y} "
                     f"(yetkazildi {m.makeup_date:%d.%m.%Y}){_comment(m.comment)}", branch=a.branch, markup=_buttons(("✅ Tasdiqlash", f"ap:m:{m.pk}")))


def lead_callback_from_telegram(chat_id, data):
    """Botdagi qayta bog'lanish tugmalari (callback `lc:<amal>:<lid_id>`): done / h1 / tm. Qaytaradi: qisqa javob (✅ bilan boshlansa — tugmalar olib tashlanadi)."""
    from rest_framework.exceptions import PermissionDenied, ValidationError

    from apps.crm import services as crm
    from apps.crm.models import Lead

    link = TelegramLink.objects.filter(chat_id=chat_id, user__employment_status=User.Employment.ACTIVE).select_related("user").first()
    try:
        _, action, pk = data.split(":", 2)
    except ValueError:
        return "Noma'lum amal"
    if not link:
        return "Siz botga ulanmagansiz"
    lead = Lead.objects.select_related("branch", "student").filter(pk=pk).first()
    if not lead or not in_branch(link.user, lead.branch):
        return "Lid topilmadi (o'chirilgan bo'lishi mumkin)"
    try:
        return crm.callback_action(link.user, lead, action)
    except (ValidationError, PermissionDenied) as e:
        detail = e.detail.get("detail") if isinstance(e.detail, dict) else e.detail
        if isinstance(detail, list):
            detail = detail[0]
        return str(detail)[:190]


def approve_from_telegram(chat_id, data):
    """Botdagi «✅ Tasdiqlash» tugmalari (callback `ap:<tur>:<id>`): d — chegirma, n — naqdsiz to'lov, t — o'tkazma, m — qoldirilgan dars.
    Tasdiqlovchi — chat_id bo'yicha topilgan xodim; huquq va muddatlar saytdagi bilan bir xil (servislar tekshiradi). Qaytaradi: qisqa javob."""
    from rest_framework.exceptions import PermissionDenied, ValidationError

    from apps.education import services as edu
    from apps.education.models import MakeupRequest
    from apps.finance import services as fin
    from apps.finance.models import Payment, Transfer

    link = TelegramLink.objects.filter(chat_id=chat_id, user__employment_status=User.Employment.ACTIVE).select_related("user").first()
    try:
        _, kind, pk = data.split(":", 2)
    except ValueError:
        return "Noma'lum amal"
    if not link:
        return "Siz botga ulanmagansiz"
    user = link.user
    try:
        if kind in ("d", "n"):
            p = Payment.objects.select_related("contract", "branch").filter(pk=pk).first()
            if not p:
                return "To'lov topilmadi (o'chirilgan bo'lishi mumkin)"
            (fin.approve_discount if kind == "d" else fin.approve_noncash)(user, p)
            return "✅ Chegirma tasdiqlandi" if kind == "d" else "✅ Naqdsiz to'lov tasdiqlandi"
        if kind == "t":
            t = Transfer.objects.select_related("sender_account", "receiver_account").filter(pk=pk).first()
            if not t:
                return "O'tkazma topilmadi (bekor qilingan bo'lishi mumkin)"
            fin.confirm_transfer(user, t)
            return "✅ O'tkazma qabul qilindi"
        if kind == "m":
            m = MakeupRequest.objects.select_related("attendance").filter(pk=pk).first()
            if not m:
                return "So'rov topilmadi"
            edu.approve_makeup(user, m)
            return "✅ Dars yetkazilgani tasdiqlandi"
    except (ValidationError, PermissionDenied) as e:
        detail = e.detail.get("detail") if isinstance(e.detail, dict) else e.detail
        if isinstance(detail, list):
            detail = detail[0]
        return f"⚠️ {detail}"[:190]
    return "Noma'lum amal"


def attendance_missing(group, text, key):
    """Ustoz va yordamchilar — faqat o'z guruhi haqida; boshqalar — filial doirasida."""
    mine = {group.teacher_id, group.supporter_id}

    def only(u):
        return role_code(u) not in TEACHER_ROLES or u.pk in mine

    notify("attendance_missing", text, branch=group.branch, default_users=[group.teacher], key=key, only=only)


def lesson_started(group, text, key):
    """Dars boshlandi — guruh ustoziga (standart); ustoz va yordamchilar faqat o'z guruhi haqida oladi.
    Xabar ostida «Davomat olish» tugmasi — davomat sahifasi Telegram ichida ochiladi (Mini App, parolsiz)."""
    from . import webapp

    mine = {group.teacher_id, group.supporter_id}
    markup = webapp.button("📋 Davomat olish", group=group.pk) if webapp.enabled() else None
    notify("lesson_start", text, branch=group.branch, default_users=[group.teacher], key=key,
           only=lambda u: role_code(u) not in TEACHER_ROLES or u.pk in mine, markup=markup)


def chunks(text, limit=3900):
    """Telegram xabari 4096 belgigacha — uzun matn qatorlar bo'yicha bo'linadi."""
    parts, cur = [], ""
    for line in text.split("\n"):
        if cur and len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line[:limit]
    return [*parts, cur] if cur else parts


def notify_chunks(event, text, branch=None, key=""):
    parts = chunks(text)
    for i, part in enumerate(parts, 1):
        suffix = f"\n<i>({i}/{len(parts)})</i>" if len(parts) > 1 else ""
        notify(event, part + suffix, branch=branch, key=f"{key}:{i}" if key else "")


def daily_report(text, key):
    notify("daily_report", text, key=key)


# ------------------------------------------------------------------ Telegram API

def api(method, **params):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN berilmagan")
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=params.get("timeout", 0) + 15) as r:
        res = json.loads(r.read().decode())
    if not res.get("ok"):
        raise RuntimeError(res.get("description", "Telegram xatosi"))
    return res["result"]


def download_file(file_id, max_bytes=20 * 1024 * 1024):
    """Botga yuborilgan fayl (masalan ovozli xabar) — baytlar. Bot API 20 MB gacha beradi."""
    path = api("getFile", file_id=file_id)["file_path"]
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{path}", timeout=60) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError("Fayl juda katta")
    return data


def send_pending(limit=30, sender=None):
    """Navbatdagi xabarlarni yuboradi. sender(chat_id, text) — testlar uchun almashtiriladi. Qaytaradi: yuborilganlar soni."""
    def default_sender(chat, text, markup=None):
        extra = {"reply_markup": json.dumps(markup)} if markup else {}
        return api("sendMessage", chat_id=chat, text=text, parse_mode="HTML", disable_web_page_preview="true", **extra)

    sender = sender or default_sender
    n = 0
    for m in Outbox.objects.filter(status=Outbox.Status.PENDING).order_by("created_at")[:limit]:
        try:
            if m.markup:
                sender(m.chat_id, m.text, m.markup)
            else:
                sender(m.chat_id, m.text)
            m.status, m.sent_at = Outbox.Status.SENT, timezone.now()
            n += 1
        except Exception as e:  # noqa: BLE001
            m.attempts += 1
            m.error = str(e)[:255]
            if m.attempts >= 5:
                m.status = Outbox.Status.FAILED
        m.save(update_fields=["status", "sent_at", "attempts", "error"])
    return n


HELP = ("Codial ERP boti. Akkauntingizni bog'lash uchun tizimda o'ng yuqoridagi ismingiz → «Telegram» bo'limidagi kodni shu yerga yuboring "
        "(yoki havolani bosing). /stop — bog'lanishni uzish.")


def handle_message(chat_id, text, username=""):
    """Botga kelgan xabar: «/start KOD», «KOD» yoki «/stop». Qaytaradi: javob matni."""
    text = (text or "").strip()
    if text.startswith("/stop"):
        n = TelegramLink.objects.filter(chat_id=chat_id).update(chat_id=None, linked_at=None)
        return "Bog'lanish uzildi. Xabarlar endi kelmaydi." if n else "Bu chat hech qaysi akkauntga bog'lanmagan."
    code = text.split(maxsplit=1)[1] if text.startswith("/start") and " " in text else ("" if text.startswith("/") else text)
    code = code.strip().upper()
    if not code:
        existing = TelegramLink.objects.filter(chat_id=chat_id).select_related("user").first()
        return f"Siz {existing.user.full_name} sifatida bog'langansiz. /stop — uzish." if existing else HELP
    link = TelegramLink.objects.filter(code=code).select_related("user").first()
    if link is None or link.user.employment_status != User.Employment.ACTIVE:
        return "Kod topilmadi yoki eskirgan. Tizimdagi «Telegram» bo'limidan yangi kod oling."
    with transaction.atomic():
        TelegramLink.objects.filter(chat_id=chat_id).exclude(pk=link.pk).update(chat_id=None, linked_at=None)
        link.chat_id, link.username, link.linked_at = chat_id, (username or "")[:64], timezone.now()
        link.code = new_code()  # kod bir martalik
        link.save()
    return f"✅ Bog'landi: {link.user.full_name}. Endi tizim xabarlari shu yerga keladi. Qaysi xabarlarni olishni tizimda sozlashingiz mumkin."

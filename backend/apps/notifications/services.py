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
}


def allowed(user, event):
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


def lead_changed(lead, old_status, user):
    st = lead.student
    notify("lead_change", f"🔄 <b>Lid o'zgardi</b>\n{escape(st.full_name)} · {escape(str(lead.course))}\n"
                          f"{escape(old_status)} → <b>{escape(lead.status)}</b>\n✍️ {escape(str(user))}", branch=lead.branch, exclude=user)


def contract_saved(c, user, created, note=""):
    head = "📄 <b>Yangi shartnoma</b>" if created else "📄 <b>Shartnoma o'zgardi</b>"
    extra = f"\n{escape(note)}" if note else ""
    notify("contract_change", f"{head}\n{escape(c.name)} · {escape(str(c.course))}{extra}\n✍️ {escape(str(user))}", branch=c.branch, exclude=user)


def payment_pending(p):
    parts = []
    if p.discount_status == "Tasdiqlashga":
        parts.append(f"chegirma {money(p.discount)} ({escape(str(p.discount_type))})")
    if p.noncash_status == "Tasdiqlashga":
        parts.append(f"naqdsiz to'lov {money(p.amount)} ({p.get_cash_type_display()})")
    if parts:
        notify("approval", f"⏳ <b>Tasdiq kutilmoqda</b>: {', '.join(parts)}\n{escape(p.contract.name)}", branch=p.branch)


def transfer_created(t):
    from apps.finance.services import scoped_account_ids

    def sees(u):
        ids = scoped_account_ids(u)
        return ids is None or t.sender_account_id in ids or t.receiver_account_id in ids

    notify("transfer", f"🔁 <b>O'tkazma kutilmoqda</b>: {money(t.amount)}\n{escape(str(t.sender_account))} → {escape(str(t.receiver_account))}",
           default_users=list(t.receiver_account.responsible.all()), only=sees)


def makeup_requested(m):
    a = m.attendance
    notify("makeup", f"📚 <b>Dars yetkazildi — so'rov</b>\n{escape(str(m.teacher))}: {escape(a.contract.student.full_name)}, {a.date:%d.%m.%Y} "
                     f"(yetkazildi {m.makeup_date:%d.%m.%Y})\n{escape(m.comment)}", branch=a.branch)


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

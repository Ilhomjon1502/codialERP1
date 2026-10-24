"""Mijozlar boti xizmatlari: taklif kodlari, ulash, manba so'rovi, tavsiya (tanish). Telegram bilan ishlash `run_clientbot` da."""

import datetime
import json
import logging
import re
import urllib.parse
import urllib.request
from html import escape

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.calls.services import normalize
from apps.crm.models import Lead, Student
from apps.references.models import LeadSource

from .models import BotAccount, BotConfig, BotInvite, BotLink, ClientOutbox, LeadSurvey, Referral

log = logging.getLogger(__name__)
Role = BotInvite.Role

MAX_ACCOUNTS_PER_INVITE = 3  # bir raqam: o'quvchi, ota, ona — uchtagacha Telegram akkaunt
MAX_FAILS = 8  # soatiga noto'g'ri kod urinishi
CODE_RE = re.compile(r"^[A-Z0-9]{8}$")
REFERRAL_WORDS = ("tanish", "tavsiya")  # manba nomida shu so'z bo'lsa — «kim tavsiya qildi?» deb so'raladi
APOSTROPHES = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'"})


# ---------- sozlama va havola ----------


def configured():
    return bool(settings.CLIENT_BOT_TOKEN and settings.CLIENT_BOT_USERNAME)


def link_url(code):
    return f"t.me/{settings.CLIENT_BOT_USERNAME}?start={code}"


def get_config(branch):
    cfg = BotConfig.objects.filter(branch=branch).first()
    return cfg or BotConfig.objects.create(branch=branch)


# ---------- taklif (SMS'dagi kod) ----------


def _role_for(student, phone):
    """Raqam vasiyniki bo'lsa — vasiy, talabaning 1-telefoni bo'lsa — talaba; 2-telefon va boshqalar — bot ulanganda so'raydi."""
    if student.parent_id and normalize(student.parent.phone) == phone:
        return Role.GUARDIAN
    if normalize(student.phone1) == phone and normalize(student.phone2) != phone:
        return Role.STUDENT
    return ""


def invite_for(student, phone, branch=None):
    """Talaba + raqam uchun taklif (bo'lmasa yaratadi). Qaytaradi: BotInvite."""
    phone = normalize(phone)
    inv = BotInvite.objects.filter(student=student, phone=phone).first()
    if inv:
        return inv
    for _ in range(5):
        try:
            with transaction.atomic():
                return BotInvite.objects.create(branch=branch or student.branch, student=student, parent=student.parent, phone=phone,
                                                role=_role_for(student, phone))
        except IntegrityError:  # kod to'qnashdi yoki parallel yaratildi
            inv = BotInvite.objects.filter(student=student, phone=phone).first()
            if inv:
                return inv
    raise RuntimeError("Bot taklifi yaratilmadi")


def is_linked(student, phone):
    """Shu raqam bo'yicha botga ulangan faol akkaunt bormi (taklif orqali)."""
    return BotLink.objects.filter(student=student, phone=normalize(phone), is_active=True).exists()


def invite_suffix(student, phone, branch):
    """SMS oxiriga qo'shiladigan bot havolasi (bo'sh — bot sozlanmagan, o'chirilgan yoki raqam allaqachon ulangan).
    Havola ketgan vaqt taklifga yoziladi — start eslatmasi shundan `reminder_days` kun o'tgach."""
    if not configured() or not get_config(branch).invite_in_sms or is_linked(student, phone):
        return ""
    inv = invite_for(student, phone, branch)
    BotInvite.objects.filter(pk=inv.pk).update(last_reminded_at=timezone.now())
    return f" Telegram bot: {link_url(inv.code)}"


def sample_suffix():
    return f" Telegram bot: {link_url('XXXXXXXX')}" if configured() else ""


# ---------- yetkazish: bot yoki SMS ----------


def accounts_for(student, phone):
    """Shu talaba + raqam bo'yicha botga ulangan faol akkauntlar (botni bloklaganlarsiz). Bot sozlanmagan bo'lsa — bo'sh."""
    if not configured():
        return []
    return list(BotAccount.objects.filter(links__student=student, links__phone=normalize(phone), links__is_active=True, blocked=False).distinct())


def deliver(accounts, text, *, kind, key, student=None, contract=None, lead=None, month=None, phone="", recipient=""):
    """SMS o'rniga botga: har akkauntga bitta xabar (`key` bo'yicha takrorlanmaydi). Qaytaradi: yaratilgan xabarlar soni."""
    n = 0
    for acc in accounts:
        if ClientOutbox.objects.filter(account=acc, key=key).exists():
            continue
        ClientOutbox.objects.create(account=acc, kind=kind, key=key, text=escape(text), student=student, contract=contract, lead=lead, month=month,
                                    phone=normalize(phone), recipient=recipient)
        n += 1
    return n


def sent_pairs(contract_ids, month, kinds):
    """Botga ketgan (shartnoma, raqam) juftlari — «shu oy eslatma olgan» tekshiruvi SMS bilan birga hisoblaydi."""
    q = ClientOutbox.objects.filter(contract__in=contract_ids, month=month, kind__in=kinds, status__in=[ClientOutbox.Status.PENDING, ClientOutbox.Status.SENT])
    return set(q.values_list("contract_id", "phone"))


# ---------- Telegram API va navbat ----------


def api(method, **params):
    token = settings.CLIENT_BOT_TOKEN
    if not token:
        raise RuntimeError("CLIENT_BOT_TOKEN berilmagan")
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=params.get("timeout", 0) + 15) as r:
        res = json.loads(r.read().decode())
    if not res.get("ok"):
        raise RuntimeError(res.get("description", "Telegram xatosi"))
    return res["result"]


def queue(account, text, kind="", key="", markup=None):
    """Akkauntga xabar navbatga. `key` takrorlanmaslik uchun. Qaytaradi: yaratilgan yozuv yoki None."""
    if key and ClientOutbox.objects.filter(account=account, key=key).exists():
        return None
    return ClientOutbox.objects.create(account=account, kind=kind, key=key, text=text, markup=markup or {})


def send_pending(limit=30, sender=None):
    """Navbatdagi xabarlarni yuboradi. sender(chat_id, text, markup) — testlar uchun almashtiriladi."""
    def default_sender(chat, text, markup=None):
        extra = {"reply_markup": json.dumps(markup)} if markup else {}
        return api("sendMessage", chat_id=chat, text=text, parse_mode="HTML", disable_web_page_preview="true", **extra)

    sender = sender or default_sender
    n = 0
    for m in ClientOutbox.objects.filter(status=ClientOutbox.Status.PENDING).select_related("account").order_by("created_at")[:limit]:
        try:
            sender(m.account.chat_id, m.text, m.markup or None)
            m.status, m.sent_at = ClientOutbox.Status.SENT, timezone.now()
            n += 1
        except Exception as e:  # noqa: BLE001
            m.attempts += 1
            m.error = str(e)[:255]
            if "blocked" in m.error.lower() or "deactivated" in m.error.lower():  # foydalanuvchi botni bloklagan — qayta urinmaymiz
                m.status = ClientOutbox.Status.FAILED
                BotAccount.objects.filter(pk=m.account_id).update(blocked=True)
            elif m.attempts >= 5:
                m.status = ClientOutbox.Status.FAILED
        m.save(update_fields=["status", "sent_at", "attempts", "error"])
    return n


# ---------- suhbat ----------


class Reply:
    """Bot javobi: matn, tugmalar; `done` — bosilgan tugmalar olib tashlansin."""

    def __init__(self, text, markup=None, done=False):
        self.text, self.markup, self.done = text, markup, done


def buttons(*pairs, per_row=1):
    rows, row = [], []
    for t, d in pairs:
        row.append({"text": t, "callback_data": d})
        if len(row) >= per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


HELP = ("Assalomu alaykum! Bu <b>Codial</b> o'quv markazining rasmiy boti.\n"
        "Ulanish uchun SMS'dagi havolani bosing yoki SMS'dagi <b>8 belgili kodni</b> shu yerga yuboring.")


def account_for(chat_id, username="", first_name=""):
    acc, created = BotAccount.objects.get_or_create(chat_id=chat_id, defaults={"username": (username or "")[:64], "first_name": (first_name or "")[:100]})
    fields = ["last_seen_at", "blocked"]
    acc.last_seen_at, acc.blocked = timezone.now(), False
    if not created and username and acc.username != username[:64]:
        acc.username, fields = username[:64], fields + ["username"]
    acc.save(update_fields=fields)
    return acc


def handle_message(chat_id, text, username="", first_name=""):
    """Botga kelgan xabar → [Reply]."""
    acc = account_for(chat_id, username, first_name)
    text = (text or "").strip()
    if text.startswith("/stop"):
        BotLink.objects.filter(account=acc).update(is_active=False)
        acc.state = {}
        acc.save(update_fields=["state"])
        return [Reply("Bog'lanish uzildi. Xabarlar endi kelmaydi. Qayta ulanish uchun SMS'dagi kodni yuboring.")]
    if text.startswith("/start"):
        payload = text.split(maxsplit=1)[1].strip().upper() if " " in text else ""
        if payload:
            return link(acc, payload)
        return _status(acc)
    if (acc.state or {}).get("step") == "referrer" and text and not text.startswith("/"):
        return referrer_search(acc, text)
    if CODE_RE.match(text.upper()):
        return link(acc, text.upper())
    return _status(acc)


def _status(acc):
    links = list(acc.links.filter(is_active=True).select_related("student"))
    if not links:
        return [Reply(HELP)]
    names = ", ".join(escape(ln.student.first_name) for ln in links)
    return [Reply(f"Siz ulangansiz: {names}. /stop — bog'lanishni uzish.")]


def _blocked(acc):
    now = timezone.now()
    if acc.fail_since and now - acc.fail_since > datetime.timedelta(hours=1):
        acc.fails, acc.fail_since = 0, None
    return acc.fails >= MAX_FAILS


def link(acc, code):
    if _blocked(acc):
        return [Reply("Juda ko'p noto'g'ri urinish. Bir soatdan keyin qayta urinib ko'ring.")]
    inv = BotInvite.objects.filter(code=code).select_related("student__parent", "branch").first()
    if inv is None or inv.student.is_deleted:
        acc.fails += 1
        acc.fail_since = acc.fail_since or timezone.now()
        acc.save(update_fields=["fails", "fail_since"])
        return [Reply("Kod topilmadi. SMS'dagi kodni tekshirib qayta yuboring.")]
    others = BotLink.objects.filter(invite=inv).exclude(account=acc).values("account").distinct().count()
    existing = BotLink.objects.filter(account=acc, student=inv.student).first()
    if others >= MAX_ACCOUNTS_PER_INVITE and not existing:
        return [Reply("Bu kod bilan ulanishlar soni cheklovga yetdi. Markaz administratoriga murojaat qiling.")]
    ln = existing or BotLink(account=acc, student=inv.student)
    ln.parent, ln.invite, ln.phone, ln.is_active = inv.parent, inv, inv.phone, True
    ln.role = ln.role or inv.role
    ln.save()
    if not ln.role:
        return [Reply("Kod qabul qilindi. Siz kimsiz?", buttons(("🎓 O'quvchining o'zi", f"rl:S:{inv.pk}"), ("👨‍👩 Ota-ona yoki vasiy", f"rl:G:{inv.pk}")))]
    return after_link(acc, ln)


def after_link(acc, ln):
    st = ln.student
    if ln.role == Role.GUARDIAN:
        hello = f"✅ Assalomu alaykum! Siz <b>{escape(st.first_name)}</b> ning vasiysi sifatida Codial botiga ulandingiz."
    else:
        hello = f"✅ Salom, <b>{escape(st.first_name)}</b>! Siz Codial botiga ulandingiz."
    replies = [Reply(hello + "\nBu yerga markazdan muhim xabarlar keladi.")]
    lead = Lead.objects.filter(student=st).select_related("branch").order_by("-created_at").first()
    if lead and not LeadSurvey.objects.filter(lead=lead).exists():
        sources = list(LeadSource.objects.filter(status="Faol", is_deleted=False).order_by("name"))
        if sources:
            acc.state = {"step": "source", "lead": str(lead.pk)}
            acc.save(update_fields=["state"])
            replies.append(Reply("Codial haqida qayerdan eshitdingiz? Bu bizga sizga o'xshash o'quvchilarni topishda yordam beradi:",
                                 buttons(*[(s.name, f"src:{s.pk}") for s in sources], per_row=2)))
    return replies


def handle_callback(chat_id, data):
    """Tugma bosildi → (qisqa javob, [Reply])."""
    acc = BotAccount.objects.filter(chat_id=chat_id).first()
    if not acc:
        return "Avval /start bosing", []
    kind, _, rest = data.partition(":")
    try:
        if kind == "rl":
            return role_chosen(acc, rest)
        if kind == "src":
            return source_chosen(acc, rest)
        if kind == "rf":
            return referrer_chosen(acc, rest)
    except Exception:  # noqa: BLE001 — bitta xato botni to'xtatmasin
        log.exception("Mijoz boti tugmasi: %s", data)
        return "Xatolik. Qayta urinib ko'ring", []
    return "Noma'lum amal", []


def role_chosen(acc, rest):
    code, _, inv_id = rest.partition(":")
    inv = BotInvite.objects.filter(pk=inv_id).first()
    ln = BotLink.objects.filter(account=acc, invite=inv).select_related("student__parent").first() if inv else None
    if not ln:
        return "Taklif topilmadi", []
    ln.role = Role.STUDENT if code == "S" else Role.GUARDIAN
    ln.save(update_fields=["role"])
    if not inv.role:
        BotInvite.objects.filter(pk=inv.pk).update(role=ln.role)  # keyingi ulanishda yana so'ralmasin
    return "✅", [Reply("✅ Rahmat!", done=True), *after_link(acc, ln)]


def _state_lead(acc, step):
    st = acc.state or {}
    if st.get("step") != step:
        return None
    return Lead.objects.filter(pk=st.get("lead")).select_related("branch", "student").first()


def is_referral_source(source):
    """«Tanishlardan», «tavsiya» yoki «Do'stlar (o'qiydi)» — tavsiya qiluvchi bizning talabamiz bo'lishi mumkin; «Do'stlar (o'qimaydi)» — yo'q."""
    n = source.name.translate(APOSTROPHES).lower()
    return any(w in n for w in REFERRAL_WORDS) or ("do'st" in n and "o'qimaydi" not in n)


def source_chosen(acc, src_id):
    lead = _state_lead(acc, "source")
    src = LeadSource.objects.filter(pk=src_id, is_deleted=False).first()
    if not lead or not src:
        return "Bu savol allaqachon yopilgan", [Reply("✅", done=True)]
    LeadSurvey.objects.update_or_create(lead=lead, defaults={"account": acc, "source": src})
    if is_referral_source(src):
        acc.state = {"step": "referrer", "lead": str(lead.pk)}
        acc.save(update_fields=["state"])
        return "✅", [Reply(f"✅ {escape(src.name)}", done=True), Reply("Sizga Codialni kim tavsiya qildi? Uning <b>ism va familiyasini</b> yozing:")]
    acc.state = {}
    acc.save(update_fields=["state"])
    return "✅", [Reply(f"✅ {escape(src.name)}", done=True), Reply("Rahmat! Javobingiz bizga juda foydali. 🙏")]


def candidates(lead, text, limit=5):
    """Tavsiya qiluvchi: shu filialdagi, shartnomasi bor (faol yoki tugagan) talabalar — ism/familiya bo'yicha."""
    tokens = [t for t in text.translate(APOSTROPHES).split() if len(t) >= 2][:3]
    if not tokens:
        return []
    qs = Student.objects.filter(branch=lead.branch, is_deleted=False, contracts__is_deleted=False).exclude(pk=lead.student_id).distinct()
    for t in tokens:
        qs = qs.filter(Q(first_name__icontains=t) | Q(last_name__icontains=t) | Q(father_name__icontains=t))
    return list(qs.order_by("first_name", "last_name")[:limit])


def referrer_search(acc, text):
    lead = _state_lead(acc, "referrer")
    if not lead:
        acc.state = {}
        acc.save(update_fields=["state"])
        return [Reply(HELP)]
    typed = text.strip()[:200]
    found = candidates(lead, typed)
    acc.state = {**acc.state, "typed": typed}
    acc.save(update_fields=["state"])
    pairs = [(f"{s.first_name} {s.last_name}".strip(), f"rf:{s.pk}") for s in found] + [("Bu ro'yxatda yo'q", "rf:none")]
    head = "Shulardan kimni nazarda tutdingiz?" if found else "Bunday ism topilmadi. Ismni boshqacha yozib ko'ring yoki tugmani bosing:"
    return [Reply(head, buttons(*pairs))]


def referrer_chosen(acc, rest):
    lead = _state_lead(acc, "referrer")
    if not lead:
        return "Bu savol allaqachon yopilgan", [Reply("✅", done=True)]
    typed = (acc.state or {}).get("typed", "")
    student = None if rest == "none" else Student.objects.filter(pk=rest, branch=lead.branch, is_deleted=False).first()
    if rest != "none" and not student:
        return "Talaba topilmadi", []
    with transaction.atomic():
        Referral.objects.update_or_create(lead=lead, defaults={
            "branch": lead.branch, "referrer_student": student, "referrer_text": typed,
            "state": Referral.State.PENDING if student else Referral.State.UNMATCHED})
    acc.state = {}
    acc.save(update_fields=["state"])
    label = f"{student.first_name} {student.last_name}".strip() if student else typed
    return "✅", [Reply(f"✅ {escape(label)}", done=True), Reply("Rahmat! Tavsiya qilgan do'stingiz haqida administratorlarga yetkazdik. 🙏")]

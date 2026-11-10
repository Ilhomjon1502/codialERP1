"""Instagram/Facebook target orqali tushgan lidlar (Meta Lead Ads → Google Sheets) → Codial ichki guruhiga Telegram xabari (to'xtash va xato haqidagi ogohlantirishlar — Bosh menejerga).

Jadval havola bo'yicha ochiq: CSV sifatida o'qiladi (`IG_LEADS_SHEET_URL`, deploy/.env). Ustunlar o'rniga qarab olinadi — jadvaldagi
sarlavha qatori buzuq, shuning uchun nomga tayanilmaydi. Xabardan tashqari lid ERP'dagi «kiruvchi lidlar» navbatiga ham tushadi (`crm.inbox`) — haqiqiy lid emas.
Kuzatuv: har 5 daqiqada; 10 kun yangi lid tushmasa to'xtaydi (Bosh menejerga xabar), botda `/instagram` qayta yoqadi.
"""

import csv
import datetime
import io
import logging
import re
import urllib.request
from html import escape
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.calls.services import normalize
from apps.core.roles import RoleCode
from apps.notifications import services as notif
from apps.notifications.models import IgLead, IgWatch, Outbox, TelegramLink

log = logging.getLogger(__name__)

EVERY = datetime.timedelta(minutes=5)
STOP_AFTER = datetime.timedelta(days=10)
FAIL_ALERT_AFTER = datetime.timedelta(hours=1)
MAX_PER_TICK = 20  # birdaniga ko'p qator qo'shilsa ham guruh xabarlarga to'lib ketmasin
TZ = ZoneInfo("Asia/Tashkent")

# ustun o'rni (A=0): id, vaqt, reklama nomi, adset nomi, kampaniya nomi, platforma, ism, telefon
C_ID, C_TIME, C_AD, C_ADSET, C_CAMPAIGN, C_PLATFORM, C_NAME, C_PHONE, C_PHONE2 = 0, 1, 3, 5, 7, 11, 12, 13, 14
COURSES = (  # adset/reklama matnidagi kalit so'z → kurs nomi
    (("kompyuter", "computer", "savodxon"), "Kompyuter savodxonligi"),
    (("frontend", "front-end"), "Frontend"),
    (("backend", "back-end"), "Backend"),
    (("flutter",), "Flutter"),
    (("kiber", "cyber"), "Kiber xavfsizlik"),
)


def sheet_csv_url():
    m = re.search(r"/d/([\w-]+)", settings.IG_LEADS_SHEET_URL or "")
    if not m:
        return ""
    g = re.search(r"gid=(\d+)", settings.IG_LEADS_SHEET_URL)
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv" + (f"&gid={g.group(1)}" if g else "")


def fetch_rows():
    with urllib.request.urlopen(sheet_csv_url(), timeout=30) as r:
        data = r.read().decode("utf-8-sig")
    return list(csv.reader(io.StringIO(data)))


def _cell(row, i):
    return (row[i] if len(row) > i else "").strip()


def parse(row):
    """Qator → lid (dict) yoki None (bo'sh/yarim yoki sarlavha qatori)."""
    lead_id = _cell(row, C_ID)
    if not lead_id.startswith("l:"):
        return None
    try:
        at = datetime.datetime.fromisoformat(_cell(row, C_TIME))
    except ValueError:
        return None
    phone = normalize(re.sub(r"^p:", "", _cell(row, C_PHONE))) or normalize(re.sub(r"^p:", "", _cell(row, C_PHONE2)))
    if not phone:
        return None
    adset = _cell(row, C_ADSET) or _cell(row, C_AD) or _cell(row, C_CAMPAIGN)
    return {"id": lead_id, "at": at, "phone": phone, "name": _cell(row, C_NAME) or "—", "adset": adset,
            "platform": "Facebook" if _cell(row, C_PLATFORM).lower().startswith("fb") else "Instagram",
            "hint": " ".join((_cell(row, C_AD), _cell(row, C_ADSET), _cell(row, C_CAMPAIGN))).lower()}


def course_of(hint):
    for keys, name in COURSES:
        if any(k in hint for k in keys):
            return name
    return "—"


def in_base(phone):
    """Shu telefon bazada bormi: «Ism (lid holati)» yoki ''."""
    from apps.crm.models import Lead, Student

    st = Student.objects.filter(Q(phone1=phone) | Q(phone2=phone)).first()
    if not st:
        return ""
    lead = Lead.objects.filter(student=st).order_by("-created_at").first()
    return f"{st.full_name}" + (f" ({dict(Lead.LeadStatus.choices).get(lead.status, lead.status)})" if lead else "")


def message(lead):
    when = lead["at"].astimezone(TZ).strftime("%d.%m.%Y %H:%M")
    text = (f"🆕 <b>Yangi lid ({lead['platform']})</b>\n{escape(lead['name'])} · +998{lead['phone']}\n"
            f"Kurs: {escape(course_of(lead['hint']))}\nManba: {lead['platform']}: {escape(lead['adset'] or '—')}\n🕒 {when}")
    known = in_base(lead["phone"])
    return text + (f"\n⚠️ Bazada bor: {escape(known)}" if known else "")


def send_group(text, key):
    """Lid xabarini Codial ichki guruhiga (IG_LEADS_CHAT_ID) navbatga qo'yadi — xodimlarning shaxsiy chatiga emas."""
    chat = settings.IG_LEADS_CHAT_ID
    if chat and not Outbox.objects.filter(chat_id=chat, key=key).exists():
        Outbox.objects.create(user=None, chat_id=chat, event="ig_lead", key=key, text=text)


def to_inbox(lead):
    """ERP'dagi kiruvchi lidlar navbatiga (haqiqiy lid emas — statistika/KPI'ga kirmaydi). Xato guruhga xabar yuborishni buzmasin."""
    from apps.crm import inbox

    try:
        inbox.add(lead["platform"], phone=lead["phone"], name=lead["name"] if lead["name"] != "—" else "", course_name=course_of(lead["hint"]).replace("—", ""),
                  info=lead["adset"], received_at=lead["at"], external_id=lead["id"])
    except Exception:  # noqa: BLE001
        log.exception("Kiruvchi lidlar navbatiga yozilmadi: %s", lead.get("id"))


def _watch():
    return IgWatch.objects.get_or_create(pk=1)[0]


def tick(now=None, rows=None):
    """Bot tsiklidan har daqiqada chaqiriladi; jadvalni har 5 daqiqada o'qiydi. Yuborilgan xabarlar soni."""
    if not sheet_csv_url():
        return 0
    now = now or timezone.now()
    w = _watch()
    if not w.active or (w.last_check_at and now - w.last_check_at < EVERY):
        return 0
    w.last_check_at = now
    try:
        rows = rows if rows is not None else fetch_rows()
    except Exception as e:  # noqa: BLE001 — tarmoq/ruxsat xatosi botni to'xtatmasin
        log.warning("Instagram jadvali o'qilmadi: %s", e)
        w.fail_since = w.fail_since or now
        if not w.fail_alerted and now - w.fail_since >= FAIL_ALERT_AFTER:
            w.fail_alerted = True
            notif.notify("ig_lead", "⚠️ <b>Instagram lidlari jadvali o'qilmayapti</b>\nBir soatdan beri jadvalga ulanib bo'lmadi "
                         "(havola ruxsati o'zgargan yoki o'chirilgan bo'lishi mumkin).", force=True, key=f"igfail:{now:%Y%m%d%H}")
        w.save()
        return 0
    w.fail_since, w.fail_alerted = None, False
    leads = [x for x in (parse(r) for r in rows) if x]
    first_run = not IgLead.objects.exists()
    seen = set(IgLead.objects.filter(lead_id__in=[x["id"] for x in leads]).values_list("lead_id", flat=True))
    fresh = sorted((x for x in leads if x["id"] not in seen), key=lambda x: x["at"])
    sent = 0
    if first_run:  # birinchi ishga tushish: mavjudlari «eski» — xabar yuborilmaydi
        IgLead.objects.bulk_create([IgLead(lead_id=x["id"], notified=False) for x in fresh], ignore_conflicts=True)
        w.last_new_at = max((x["at"] for x in leads), default=now)
        w.save()
        return 0
    for x in fresh[:MAX_PER_TICK]:
        _, created = IgLead.objects.get_or_create(lead_id=x["id"], defaults={"notified": True})
        if created:
            send_group(message(x), f"ig:{x['id']}")
            sent += 1
            to_inbox(x)
    for x in fresh[MAX_PER_TICK:]:  # qolganlari keyingi safar yuborilmasin deb belgilanadi, lekin bir xabarda aytiladi
        _, created = IgLead.objects.get_or_create(lead_id=x["id"], defaults={"notified": False})
        if created:
            to_inbox(x)
    if len(fresh) > MAX_PER_TICK:
        send_group(f"ℹ️ Jadvalga yana {len(fresh) - MAX_PER_TICK} ta lid tushgan — jadvaldan ko'ring.", f"igmore:{now:%Y%m%d%H%M}")
    if fresh:
        w.last_new_at = now
    elif w.last_new_at and now - w.last_new_at >= STOP_AFTER:
        w.active = False
        notif.notify("ig_lead", "⏹ <b>Instagram lidlari kuzatuvi to'xtatildi</b>\n10 kundan beri jadvalga yangi lid tushmadi. "
                     "Qayta yoqish: botga /instagram deb yozing.", force=True, key=f"igstop:{now:%Y%m%d}")
    w.save()
    return sent


def handle_command(chat_id):
    """Botda `/instagram` (faqat Bosh menejer/Admin): holatni ko'rsatadi, to'xtatilgan bo'lsa qayta yoqadi."""
    link = TelegramLink.objects.filter(chat_id=chat_id).select_related("user__role").first()
    if not link or link.user.employment_status != User.Employment.ACTIVE or link.user.role.code not in (RoleCode.BOSH_MENEJER, RoleCode.ADMIN):
        return "Bu buyruq faqat Bosh menejer uchun."
    if not sheet_csv_url():
        return "Instagram jadvali sozlanmagan."
    w = _watch()
    last = timezone.localtime(w.last_new_at).strftime("%d.%m.%Y %H:%M") if w.last_new_at else "hali yo'q"
    if w.active:
        return f"✅ Instagram lidlari kuzatilyapti (har 5 daqiqada). Oxirgi yangi lid: {last}."
    w.active, w.last_new_at, w.last_check_at = True, timezone.now(), None
    w.save()
    return "▶️ Instagram lidlari kuzatuvi qayta yoqildi. Yangi tushgan lidlar haqida xabar keladi."

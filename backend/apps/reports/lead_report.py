"""Instagram/Facebook lidlarining kunlik hisoboti (2026-11-18, buyurtmachi qolipi «Lid_hisoboti_shablon»).

Har kuni 19:00 (`daily_report` buyrug'i chaqiradi): shu kuni tushgan reklama lidlari (sayt kirmaydi) 22 ta holat bo'yicha sanaladi,
Google Sheets faylida shablon varag'idan nusxa ochilib (`DD.MM.YY`) sana va sonlar yoziladi, Bosh menejerga Telegram xabari boradi.
Hisob — «shu kuni tushgan lidlar hozirgi holati bo'yicha» (crm/outcomes.py). Qayta bajarilsa shu kun varag'i yangilanadi.
Guruh jami (neytral/sifatli/sifatsiz) varaqdagi formulalardan ham o'qiladi va bizning hisob bilan solishtiriladi."""

import datetime
import html
import logging
from collections import Counter

from django.conf import settings
from django.utils import timezone

from apps.calls.models import CallRecord
from apps.crm import outcomes
from apps.crm.models import InboxLead

from . import gsheets as gs

log = logging.getLogger(__name__)

FIRST_ROW = 3  # F3 — birinchi holat (outcomes.OUTCOMES[0])
EPOCH = datetime.date(1899, 12, 30)  # Google Sheets sana boshi
TOTAL_CELL, NEUTRAL_CELL, QUALITY_CELL, BAD_CELL = "F2", "I3", "I6", "I9"


def tab_title(day):
    return f"{day:%d.%m.%y}"


def collect(day):
    """→ {day, counts: {kod: son}, total, groups: {guruh: son}, kinds: {Instagram: n, Facebook: n}}."""
    lo = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
    items = list(InboxLead.objects.filter(kind__in=outcomes.REPORT_KINDS, received_at__gte=lo, received_at__lt=lo + datetime.timedelta(days=1))
                 .select_related("lead").order_by("received_at"))
    last_call = {}  # telefon → lid o'zi qo'ng'iroq qilgan oxirgi vaqt (lid tushgan kundan keyin)
    if items:
        for phone, at in CallRecord.objects.filter(phone__in={i.phone for i in items}, direction__in=outcomes.CALLED_US, started_at__gte=lo).values_list("phone", "started_at"):
            last_call[phone] = max(at, last_call.get(phone, at))
    counts = Counter()
    for it in items:  # «Kiruvchi qo'ng'iroq» — lid tushgandan KEYIN o'zi qo'ng'iroq qilgan
        counts[outcomes.effective(it, called=it.phone in last_call and last_call[it.phone] >= it.received_at)] += 1
    counts = {c: counts.get(c, 0) for c in outcomes.CODES}
    groups = {g: sum(n for c, n in counts.items() if outcomes.GROUP[c] == g) for g in outcomes.GROUP_LABELS}
    kinds = Counter(i.kind for i in items)
    return {"day": day, "counts": counts, "total": len(items), "groups": groups, "kinds": {k: kinds.get(k, 0) for k in outcomes.REPORT_KINDS}}


def message(data, url=None, sheet_error=None):
    """Telegram xabari (HTML)."""
    c, e = data["counts"], html.escape
    L = [f"📸 <b>Instagram/Facebook lidlari</b> · {data['day']:%d.%m.%Y}",
         f"Jami: <b>{data['total']}</b> (" + " · ".join(f"{k} {n}" for k, n in data["kinds"].items()) + ")"]
    for g, icon in ((outcomes.NEUTRAL, "⚪"), (outcomes.QUALITY, "🟢"), (outcomes.BAD, "🔴")):
        parts = [f"{e(outcomes.LABEL[k])} {c[k]}" for k in outcomes.CODES if outcomes.GROUP[k] == g and c[k]]
        L.append(f"{icon} <b>{outcomes.GROUP_LABELS[g]}: {data['groups'][g]}</b>" + (f" — {' · '.join(parts)}" if parts else ""))
    if c["new"]:
        L.append(f"⏳ {c['new']} ta lid hali ko'rib chiqilmagan (Yangi lid)")
    if url:
        L.append(f'📄 <a href="{url}">Google Sheets hisoboti</a>')
    if sheet_error:
        L.append(f"⚠️ Google Sheets'ga yozilmadi: {e(sheet_error)}")
    return "\n".join(L)


def configured():
    return bool(settings.GOOGLE_SERVICE_ACCOUNT_B64 and settings.LEAD_REPORT_SHEET_ID)


def write_sheet(data):
    """Shablon varag'idan nusxa (bo'lsa — shu kun varag'ini yangilaydi), sana va sonlarni yozadi. → {url, title, created, mismatch}."""
    sid, day = settings.LEAD_REPORT_SHEET_ID, data["day"]
    title = tab_title(day)
    sheets = gs.tabs(sid)["sheets"]
    found = next((s for s in sheets if s["title"].lower() == title.lower()), None)
    created = found is None
    if created:
        tpl = next((s for s in sheets if s["title"].strip().lower() == settings.LEAD_REPORT_TEMPLATE_TAB.strip().lower()), None)
        if not tpl:
            raise gs.SheetsError(f"Shablon varag'i topilmadi: «{settings.LEAD_REPORT_TEMPLATE_TAB}»")
        r = gs.batch_update([{"duplicateSheet": {"sourceSheetId": tpl["sheetId"], "newSheetName": title, "insertSheetIndex": 1}}], sid)
        found = r["replies"][0]["duplicateSheet"]["properties"]
    q = "'" + title.replace("'", "''") + "'"
    rows = [[data["counts"][c]] for c in outcomes.CODES]
    gs.values_update([{"range": f"{q}!D2", "values": [[(day - EPOCH).days]]},
                      {"range": f"{q}!F{FIRST_ROW}:F{FIRST_ROW + len(rows) - 1}", "values": rows}], sid)
    got = gs.values_get([f"{q}!{a}" for a in (TOTAL_CELL, NEUTRAL_CELL, QUALITY_CELL, BAD_CELL)], sid)
    read = [(v[0][0] if v and v[0] else None) for v in got]
    want = [data["total"], data["groups"][outcomes.NEUTRAL], data["groups"][outcomes.QUALITY], data["groups"][outcomes.BAD]]
    mismatch = [] if read == want else [{"cell": a, "sheet": r_, "ours": w} for a, r_, w in zip((TOTAL_CELL, NEUTRAL_CELL, QUALITY_CELL, BAD_CELL), read, want, strict=True) if r_ != w]
    if mismatch:
        log.warning("Lid hisoboti formulalari bizning hisobdan farq qiladi: %s", mismatch)
    return {"url": gs.sheet_url(found["sheetId"], sid), "title": found["title"], "created": created, "mismatch": mismatch}


def run(day=None, send=True):
    """Kunlik hisobot: varaqqa yozadi va Bosh menejerga yuboradi. Varaq xatosi xabarni to'xtatmaydi. → (xabar matni, varaq natijasi yoki None)."""
    from apps.notifications import services as notif

    day = day or timezone.localdate()
    data = collect(day)
    res, err = None, None
    if configured():
        try:
            res = write_sheet(data)
        except gs.SheetsError as e:
            err = str(e)
            log.warning("Lid hisoboti varaqqa yozilmadi: %s", e)
    else:
        err = "LEAD_REPORT_SHEET_ID yoki Google kaliti sozlanmagan"
    text = message(data, res["url"] if res else None, err)
    if res and res["mismatch"]:
        text += "\n⚠️ Varaq formulalari bizning hisobdan farq qildi: " + ", ".join(f"{m['cell']}={m['sheet']} (bizda {m['ours']})" for m in res["mismatch"])
    if send:
        notif.notify("ig_lead", text, force=True, key=f"igreport:{day}")
    return text, res

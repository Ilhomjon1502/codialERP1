"""Instagram/Facebook lidlarining kunlik hisoboti (2026-11-18, buyurtmachi qolipi «Lid_hisoboti_shablon»).

Har kuni 19:00 (`daily_report` buyrug'i chaqiradi): shu kuni ISHLANGAN reklama lidlari (sayt kirmaydi) 22 ta holat bo'yicha sanaladi,
Google Sheets faylida shablon varag'idan nusxa ochilib (`DD.MM.YY`) sana va sonlar yoziladi, Bosh menejerga Telegram xabari boradi.

Hisob holat o'zgarishlari tarixidan (`crm.InboxEvent`): hisobot kuni = oldingi kun 19:00 dan shu kun 19:00 gacha (kechqurun 19:00 dan keyingi
ish keyingi kun hisobotiga tushadi, hech narsa yo'qolmaydi). Kun ichida lid necha marta ishlansa ham, oxirgi holati bilan BIR marta sanaladi;
yangi tushgan lid — «Yangi lid». Eski lid (hisobot kunidan oldin tushgan) ishlansa, u ham shu kunda sanaladi, katak izohida esa
qaysi kunlardan ekani ko'rsatiladi («2 tasi 14.11.26 dan, 5 tasi 15.11.26 dan»). Eski kun varaqlari qayta yozilmaydi.
Guruh jami (neytral/sifatli/sifatsiz) varaqdagi formulalardan ham o'qiladi va bizning hisob bilan solishtiriladi."""

import datetime
import html
import logging
from collections import Counter, defaultdict

from django.conf import settings
from django.utils import timezone

from apps.calls.models import CallRecord
from apps.crm import inbox, outcomes
from apps.crm.models import InboxEvent, InboxLead

from . import gsheets as gs

log = logging.getLogger(__name__)

FIRST_ROW = 3  # F3 — birinchi holat (outcomes.OUTCOMES[0])
TOTAL_CELL, NEUTRAL_CELL, QUALITY_CELL, BAD_CELL = "F2", "I3", "I6", "I9"
COL_F = 5  # F ustuni (0-based) — izohlar shu ustunga


def tab_title(day):
    return f"{day:%d.%m.%y}"


def window(day):
    """Hisobot kuni oralig'i: (oldingi kun 19:00, shu kun 19:00]."""
    hi = timezone.make_aware(datetime.datetime.combine(day, outcomes.REPORT_CUTOFF))
    return hi - datetime.timedelta(days=1), hi


def sync_events(day):
    """Hisobot paytida aniqlanadigan holatlarni tarixga yozadi (bir marta): lid o'zi qo'ng'iroq qilgan («Kiruvchi qo'ng'iroq», faqat ochiq lidlar)
    va bog'langan haqiqiy lid sinov darsiga o'tgan («Demoga yozildi»)."""
    lo, hi = window(day)
    ads = InboxLead.objects.filter(kind__in=outcomes.REPORT_KINDS)
    open_items = list(ads.filter(status__in=[InboxLead.Status.NEW, InboxLead.Status.CALLBACK], received_at__lte=hi))
    if open_items:
        first = {}
        calls = CallRecord.objects.filter(phone__in={i.phone for i in open_items}, direction__in=outcomes.CALLED_US, started_at__gt=lo, started_at__lte=hi)
        for phone, at in calls.order_by("started_at").values_list("phone", "started_at"):
            first.setdefault(phone, at)
        done = set(InboxEvent.objects.filter(outcome="incoming", at__gt=lo, at__lte=hi, inbox__in=open_items).values_list("inbox_id", flat=True))
        for it in open_items:
            at = first.get(it.phone)
            if at and at >= it.received_at and it.pk not in done:  # lid tushgandan keyin o'zi qo'ng'iroq qilgan
                inbox.event(it, "incoming", at)
    # «Kachestvni lead» tarixi bor (hisobot boshlangandan keyin bog'langan) va haqiqiy lid sinov darsiga o'tgan, lekin hali yozilmagan
    linked = ads.filter(status=InboxLead.Status.LINKED, lead__status__in=outcomes.DEMO_LEAD_STATUSES, events__outcome="quality").distinct()
    had_demo = set(InboxEvent.objects.filter(outcome="demo", inbox__in=linked).values_list("inbox_id", flat=True))
    for it in linked:
        if it.pk not in had_demo:
            inbox.event(it, "demo", min(timezone.now(), hi))


def collect(day):
    """→ {day, counts: {kod: son}, total, groups: {guruh: son}, kinds: {Instagram: n, Facebook: n}, old: {kod: {sana: son}}, old_total}."""
    lo, hi = window(day)
    events = (InboxEvent.objects.filter(inbox__kind__in=outcomes.REPORT_KINDS, at__gt=lo, at__lte=hi).select_related("inbox").order_by("at", "id"))
    last = {}
    for ev in events:  # har bir lid uchun kun ichidagi oxirgi holat
        last[ev.inbox_id] = ev
    counts, kinds, old = Counter(), Counter(), defaultdict(Counter)
    for ev in last.values():
        counts[ev.outcome] += 1
        kinds[ev.inbox.kind] += 1
        if ev.inbox.received_at <= lo:  # hisobot kunidan oldin tushgan
            old[ev.outcome][timezone.localtime(ev.inbox.received_at).date()] += 1
    counts = {c: counts.get(c, 0) for c in outcomes.CODES}
    groups = {g: sum(n for c, n in counts.items() if outcomes.GROUP[c] == g) for g in outcomes.GROUP_LABELS}
    return {"day": day, "counts": counts, "total": len(last), "groups": groups, "kinds": {k: kinds.get(k, 0) for k in outcomes.REPORT_KINDS},
            "old": {c: dict(v) for c, v in old.items()}, "old_total": sum(sum(v.values()) for v in old.values())}


def old_note(by_date):
    """{sana: son} → «2 tasi 14.11.26 dan, 5 tasi 15.11.26 dan» (eski lidlar yo'q bo'lsa — '')."""
    return ", ".join(f"{n} tasi {d:%d.%m.%y} dan" for d, n in sorted(by_date.items()))


def message(data, url=None, sheet_error=None):
    """Telegram xabari (HTML)."""
    c, e = data["counts"], html.escape
    L = [f"📸 <b>Instagram/Facebook lidlari</b> · {data['day']:%d.%m.%Y}",
         f"Ishlangan lidlar: <b>{data['total']}</b> (" + " · ".join(f"{k} {n}" for k, n in data["kinds"].items()) + ")"
         + (f", shundan eski lidlar: {data['old_total']}" if data.get("old_total") else "")]
    for g, icon in ((outcomes.NEUTRAL, "⚪"), (outcomes.QUALITY, "🟢"), (outcomes.BAD, "🔴")):
        parts = [f"{e(outcomes.LABEL[k])} {c[k]}" for k in outcomes.CODES if outcomes.GROUP[k] == g and c[k]]
        L.append(f"{icon} <b>{outcomes.GROUP_LABELS[g]}: {data['groups'][g]}</b>" + (f" — {' · '.join(parts)}" if parts else ""))
    if url:
        L.append(f'📄 <a href="{url}">Google Sheets hisoboti</a>')
    if sheet_error:
        L.append(f"⚠️ Google Sheets'ga yozilmadi: {e(sheet_error)}")
    return "\n".join(L)


def configured():
    return bool(settings.GOOGLE_SERVICE_ACCOUNT_B64 and settings.LEAD_REPORT_SHEET_ID)


def note_requests(sheet_id, data):
    """F3:F24 kataklariga izoh: eski lidlar bo'lsa «2 tasi 14.11.26 dan, …», bo'lmasa eski izoh olib tashlanadi."""
    rows = [{"values": [{"note": old_note(data["old"][c])} if data["old"].get(c) else {}]} for c in outcomes.CODES]
    return [{"updateCells": {"start": {"sheetId": sheet_id, "rowIndex": FIRST_ROW - 1, "columnIndex": COL_F}, "rows": rows, "fields": "note"}}]


def write_sheet(data):
    """Shablon varag'idan nusxa (bo'lsa — shu kun varag'ini yangilaydi), sana, sonlar va izohlarni yozadi. → {url, title, created, mismatch}."""
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
    # D2 shablonda sana formatida emas — raqam bo'lib qolmasligi uchun matn sifatida (')
    gs.values_update([{"range": f"{q}!D2", "values": [["'" + day.strftime("%d.%m.%y")]]},
                      {"range": f"{q}!F{FIRST_ROW}:F{FIRST_ROW + len(rows) - 1}", "values": rows}], sid)
    gs.batch_update(note_requests(found["sheetId"], data), sid)
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
    sync_events(day)
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

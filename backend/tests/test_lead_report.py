"""Instagram/Facebook lidlarining kunlik hisoboti (crm/outcomes.py, reports/lead_report.py, daily_report ulanishi)."""

import datetime

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.calls.models import CallDevice, CallRecord
from apps.crm import inbox, outcomes
from apps.crm.models import InboxLead  # noqa: F401
from apps.notifications.models import Outbox, TelegramLink
from apps.reports import gsheets, lead_report

pytestmark = pytest.mark.django_db

NOW_ISO = lambda **kw: timezone.now() + datetime.timedelta(**kw)  # noqa: E731


@pytest.fixture
def now_commit(monkeypatch):
    monkeypatch.setattr("apps.notifications.services.transaction.on_commit", lambda f: f())


def _item(kind="Instagram", phone="901112233", at=None, **kw):
    it, _ = inbox.add(kind, phone=phone, name="Ali", external_id=kw.pop("external_id", f"l:{phone}{kind}"), received_at=at or timezone.now())
    for k, v in kw.items():
        setattr(it, k, v)
    if kw:
        it.save()
    return it


def test_sheet_layout_matches_template():
    assert len(outcomes.OUTCOMES) == 22  # F3:F24
    groups = [outcomes.GROUP[c] for c in outcomes.CODES]
    assert groups[:3] == [outcomes.NEUTRAL] * 3  # F3:F5
    assert groups[3:9] == [outcomes.QUALITY] * 6  # F6:F11
    assert groups[9:] == [outcomes.BAD] * 13  # F12:F24
    assert len(outcomes.CLOSE_OUTCOMES) == 15 and outcomes.CLOSE_OUTCOMES[0] == "schedule"  # «Yopilgan Leadlar» bloki (F10:F24)


def test_talk_requires_outcome_matching_action(branch, make_user):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    it = _item()
    at = NOW_ISO(days=1)
    with pytest.raises(ValidationError):
        inbox.talk(u, it, "gaplashdik", callback_at=at)  # holat tanlanmagan
    with pytest.raises(ValidationError):
        inbox.talk(u, it, "gaplashdik", callback_at=at, outcome="spam")  # yopish sababi qayta aloqada mumkin emas
    with pytest.raises(ValidationError):
        inbox.talk(u, it, "qiziqmadi", close=True, outcome="consult")  # qayta aloqa holati yopishda mumkin emas
    inbox.talk(u, it, "gaplashdik", callback_at=at, outcome="consult")
    it.refresh_from_db()
    assert (it.status, it.outcome) == ("callback", "consult")
    inbox.talk(u, it, "qiziqmadi", close=True, outcome="age")
    it.refresh_from_db()
    assert (it.status, it.outcome) == ("rejected", "age")
    inbox.reopen(u, it)
    it.refresh_from_db()
    assert (it.status, it.outcome) == ("new", "")


def at_(day, hour, minute=0):
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, minute)))


def test_events_are_recorded(branch, make_user):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    it = _item()
    assert list(it.events.values_list("outcome", flat=True)) == ["new"]
    inbox.talk(u, it, "x", callback_at=NOW_ISO(days=1), outcome="consult")
    inbox.talk(u, it, "y", close=True, outcome="spam")
    inbox.reopen(u, it)
    assert list(it.events.order_by("at", "id").values_list("outcome", flat=True)) == ["new", "consult", "spam", "new"]


def test_collect_counts_worked_leads_once_with_last_outcome(branch):
    day = timezone.localdate()
    lo, hi = lead_report.window(day)
    a = _item("Instagram", "901000001", lo + datetime.timedelta(hours=1))  # yangi, ishlanmagan
    b = _item("Instagram", "901000002", lo + datetime.timedelta(hours=2))
    c = _item("Facebook", "901000003", lo + datetime.timedelta(hours=3))
    _item("Sayt", "901000004", lo + datetime.timedelta(hours=3))  # sayt kirmaydi
    e = _item("Instagram", "901000005", lo - datetime.timedelta(days=3))  # eski lid
    inbox.event(b, "hesitate", lo + datetime.timedelta(hours=5))
    inbox.event(b, "consult", lo + datetime.timedelta(hours=6))  # b: kun ichida ikki marta, oxirgisi sanaladi
    inbox.event(c, "spam", lo + datetime.timedelta(hours=7))
    inbox.event(e, "unreachable", lo + datetime.timedelta(hours=8))  # eski lid ishlandi
    inbox.event(a, "demo", hi + datetime.timedelta(hours=1))  # 19:00 dan keyin — keyingi kun hisobotiga
    data = lead_report.collect(day)
    cnt = data["counts"]
    assert data["total"] == 4 and data["kinds"] == {"Instagram": 3, "Facebook": 1}
    assert (cnt["new"], cnt["consult"], cnt["spam"], cnt["unreachable"], cnt["demo"]) == (1, 1, 1, 1, 0) and sum(cnt.values()) == 4
    assert data["groups"] == {"neytral": 2, "sifatli": 1, "sifatsiz": 1}
    nxt = lead_report.collect(day + datetime.timedelta(days=1))
    assert nxt["counts"]["demo"] == 1 and nxt["total"] == 1


def test_old_leads_note_by_received_date(branch):
    day = timezone.localdate()
    lo, _ = lead_report.window(day)
    d1, d2 = lo - datetime.timedelta(days=4), lo - datetime.timedelta(days=3)
    for i, d in enumerate((d1, d1, d2, d2, d2, d2, d2)):
        it = _item("Instagram", f"90100001{i}", d, external_id=f"l:old{i}")
        inbox.event(it, "hesitate", lo + datetime.timedelta(hours=2))
    new = _item("Instagram", "901000099", lo + datetime.timedelta(hours=1))  # yangi lid — izohda yo'q
    inbox.event(new, "hesitate", lo + datetime.timedelta(hours=3))
    data = lead_report.collect(day)
    assert data["counts"]["hesitate"] == 8 and data["old_total"] == 7
    note = lead_report.old_note(data["old"]["hesitate"])
    assert note == f"2 tasi {timezone.localtime(d1):%d.%m.%y} dan, 5 tasi {timezone.localtime(d2):%d.%m.%y} dan"
    reqs = lead_report.note_requests(7, data)[0]["updateCells"]
    assert reqs["start"] == {"sheetId": 7, "rowIndex": 2, "columnIndex": 5} and reqs["fields"] == "note" and len(reqs["rows"]) == 22
    assert reqs["rows"][outcomes.CODES.index("hesitate")]["values"][0]["note"] == note
    assert reqs["rows"][0]["values"] == [{}]  # eski lid yo'q — izoh bo'sh (eskisi o'chadi)


def test_sync_events_incoming_call_and_demo(branch):
    dev = CallDevice.objects.create(name="Qabul", branch=branch)
    day = timezone.localdate()
    lo, hi = lead_report.window(day)
    a = _item("Instagram", "901000001", lo + datetime.timedelta(hours=1))
    b = _item("Instagram", "901000002", lo + datetime.timedelta(hours=1))
    c = _item("Instagram", "901000003", lo + datetime.timedelta(hours=1))

    def call(phone, hours, direction):
        CallRecord.objects.create(device=dev, branch=branch, external_id=f"{phone}{hours}", direction=direction, number=phone, phone=phone,
                                  started_at=lo + datetime.timedelta(hours=hours), duration=30)

    call("901000001", 3, "Kiruvchi")  # lid keyin o'zi qo'ng'iroq qildi
    call("901000002", 0, "Kiruvchi")  # lid tushishidan oldin — hisobga olinmaydi
    call("901000003", 3, "Chiquvchi")  # biz qo'ng'iroq qildik — kiruvchi emas
    lead_report.sync_events(day)
    lead_report.sync_events(day)  # takror ishga tushirish dublikat yozmaydi
    assert a.events.filter(outcome="incoming").count() == 1
    assert not b.events.filter(outcome="incoming").exists() and not c.events.filter(outcome="incoming").exists()
    cnt = lead_report.collect(day)["counts"]
    assert (cnt["incoming"], cnt["new"]) == (1, 2)


def test_message_text():
    d = {"day": datetime.date(2026, 11, 18), "total": 3, "kinds": {"Instagram": 2, "Facebook": 1}, "groups": {"neytral": 1, "sifatli": 1, "sifatsiz": 1},
         "counts": {c: 0 for c in outcomes.CODES}, "old": {}, "old_total": 2}
    d["counts"].update(new=1, demo=1, spam=1)
    text = lead_report.message(d, url="https://x/y")
    assert "18.11.2026" in text and "Ishlangan lidlar: <b>3</b> (Instagram 2 · Facebook 1), shundan eski lidlar: 2" in text
    assert "Sifatli: 1</b> — Demoga yozildi 1" in text and "Sifatsiz: 1</b> — Spam 1" in text
    assert 'href="https://x/y"' in text
    assert "yozilmadi: xato" in lead_report.message(d, sheet_error="xato")


class FakeSheets:
    """Google Sheets o'rniga: varaqlar va katakchalar xotirada; I3/I6/I9 — formulalar o'rnida bizning guruh yig'indilari."""

    def __init__(self, bad_formula=False):
        self.tabs_, self.cells, self.bad, self.calls = [{"sheetId": 1, "title": "Lid hisoboti"}], {}, bad_formula, []

    def tabs(self, sid=None):
        return {"title": "f", "sheets": list(self.tabs_)}

    def batch_update(self, requests, sid=None):
        self.calls.append(requests)
        if "updateCells" in requests[0]:
            return {}
        r = requests[0]["duplicateSheet"]
        props = {"sheetId": 2 + len(self.tabs_), "title": r["newSheetName"]}
        self.tabs_.append(props)
        return {"replies": [{"duplicateSheet": {"properties": props}}]}

    def values_update(self, data, sid=None):
        for d in data:
            self.cells[d["range"]] = d["values"]

    def values_get(self, ranges, sid=None):
        title = ranges[0].split("!")[0]
        col = self.cells[f"{title}!F3:F24"]
        n = [r[0] for r in col]
        sums = {"F2": sum(n), "I3": sum(n[:3]), "I6": sum(n[3:9]), "I9": sum(n[9:]) + (1 if self.bad else 0)}
        return [[[sums[r.split("!")[1]]]] for r in ranges]


@pytest.fixture
def fake(monkeypatch):
    f = FakeSheets()
    for name in ("tabs", "batch_update", "values_update", "values_get"):
        monkeypatch.setattr(gsheets, name, getattr(f, name))
    return f


@override_settings(LEAD_REPORT_SHEET_ID="SID", GOOGLE_SERVICE_ACCOUNT_B64="x", LEAD_REPORT_TEMPLATE_TAB="Lid hisoboti")
def test_write_sheet_duplicates_template_once_and_writes_counts(branch, fake):
    day = timezone.localdate()
    lo, _ = lead_report.window(day)
    it = _item("Instagram", "901000001", lo + datetime.timedelta(hours=1))
    inbox.event(it, "spam", lo + datetime.timedelta(hours=2))
    data = lead_report.collect(day)
    res = lead_report.write_sheet(data)
    title = f"{day:%d.%m.%y}"
    assert res["created"] and res["title"] == title and not res["mismatch"] and "gid=" in res["url"]
    assert fake.calls[0][0]["duplicateSheet"]["sourceSheetId"] == 1
    assert fake.cells[f"'{title}'!D2"] == [[f"'{day:%d.%m.%y}"]]
    f_col = [r[0] for r in fake.cells[f"'{title}'!F3:F24"]]
    assert len(f_col) == 22 and f_col[outcomes.CODES.index("spam")] == 1 and sum(f_col) == 1
    assert "updateCells" in fake.calls[1][0]  # katak izohlari
    again = lead_report.write_sheet(data)  # qayta — yangi varaq ochilmaydi, faqat qiymat va izohlar yangilanadi
    assert not again["created"] and sum("duplicateSheet" in c[0] for c in fake.calls) == 1


@override_settings(LEAD_REPORT_SHEET_ID="SID", GOOGLE_SERVICE_ACCOUNT_B64="x")
def test_write_sheet_reports_formula_mismatch(branch, monkeypatch):
    f = FakeSheets(bad_formula=True)
    for name in ("tabs", "batch_update", "values_update", "values_get"):
        monkeypatch.setattr(gsheets, name, getattr(f, name))
    res = lead_report.write_sheet(lead_report.collect(timezone.localdate()))
    assert [m["cell"] for m in res["mismatch"]] == ["I9"]


@override_settings(LEAD_REPORT_SHEET_ID="SID", GOOGLE_SERVICE_ACCOUNT_B64="x", LEAD_REPORT_TEMPLATE_TAB="Boshqa nom")
def test_run_sends_telegram_even_if_sheet_fails(branch, make_user, now_commit, fake):
    TelegramLink.objects.create(user=make_user("BOSH_MENEJER"), chat_id=777)
    _item()
    text, res = lead_report.run()
    assert res is None and "Google Sheets'ga yozilmadi" in text
    msg = Outbox.objects.get(event="ig_lead")
    assert msg.chat_id == 777 and "Instagram/Facebook lidlari" in msg.text
    lead_report.run()  # bir kunga bitta xabar
    assert Outbox.objects.filter(event="ig_lead").count() == 1


def test_run_without_google_still_sends_summary(branch, make_user, now_commit):
    TelegramLink.objects.create(user=make_user("BOSH_MENEJER"), chat_id=777)
    text, res = lead_report.run()
    assert res is None and "sozlanmagan" in text and Outbox.objects.filter(event="ig_lead").count() == 1


def test_api_talk_with_outcome_and_options(api, make_user, branch):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    c = api(u)
    it = _item()
    opts = c.get("/api/v1/inbox-leads/outcomes/").json()
    assert [o[0] for o in opts["callback"]] == ["hesitate", "unreachable", "consult"] and len(opts["close"]) == 15
    at = NOW_ISO(hours=2).isoformat()
    assert c.post(f"/api/v1/inbox-leads/{it.pk}/talk/", {"comment": "x", "callback_at": at}, format="json").status_code == 400  # holat yo'q
    r = c.post(f"/api/v1/inbox-leads/{it.pk}/talk/", {"comment": "x", "callback_at": at, "outcome": "unreachable"}, format="json")
    assert r.status_code == 200 and r.json()["outcome"] == "unreachable" and r.json()["outcome_label"] == "Bog'lanib bo'lmadi"
    assert InboxLead.objects.get(pk=it.pk).outcome == "unreachable"

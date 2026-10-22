"""Qo'ng'iroqlar ↔ CRM (2026-10-21): kartochkada qo'ng'iroqlar tarixi, suhbatdan keyingi izoh, kelmagan talaba bilan bog'lanish, voronka."""

import datetime

import pytest
from django.utils import timezone

from apps.calls.models import CallRecord
from apps.crm.models import Lead, LeadComment, Parent
from apps.education.models import Attendance, ParentCall
from apps.notifications import reminders
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import LeadSource
from tests.test_calls import call, device, ingest, paired  # noqa: F401 — fixtures
from tests.test_education import TODAY, take, world  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
H = datetime.timedelta
NUMBER = "+998900000000"  # world["students"][0].phone1


def iso(delta):
    return (timezone.now() + delta).isoformat()


def mk_lead(w, status="1", **kw):
    src, _ = LeadSource.objects.get_or_create(name="Instagram")
    return Lead.objects.create(branch=w["branch"], student=w["students"][0], source=src, course=w["course"], status=status, **kw)


@pytest.fixture
def ah(make_user):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    TelegramLink.objects.create(user=u, chat_id=5001)
    return u


def notes():
    return Outbox.objects.filter(event="lead_callback")


# ------------------------------------------------------------------ izoh kutiladi (eslatma to'xtamaydi)

def test_talk_without_pending_reminder_sends_note_prompt(api, world, paired, ah, django_capture_on_commit_callbacks):  # noqa: F811
    lead = mk_lead(world)  # 1-status, qayta bog'lanish vaqti yo'q
    with django_capture_on_commit_callbacks(execute=True):
        ingest(api, paired, [call(1, NUMBER, kind=2, duration=120)])
    lead.refresh_from_db()
    assert lead.callback_talked_at is not None
    m = notes().get()
    assert "izoh yozing" in m.text and world["students"][0].full_name in m.text and "chiquvchi" in m.text
    data = [b["callback_data"] for row in m.markup["inline_keyboard"] for b in row if "callback_data" in b]
    assert data == [f"lc:tm:{lead.pk}", f"lc:d3:{lead.pk}"]
    with django_capture_on_commit_callbacks(execute=True):
        ingest(api, paired, [call(1, NUMBER, kind=2, duration=120)])  # takror — yangi xabar yo'q
    assert notes().count() == 1


def test_talk_before_scheduled_time_keeps_reminder_but_as_note(api, world, paired, ah, django_capture_on_commit_callbacks):  # noqa: F811
    soon = timezone.now() + H(minutes=30)
    lead = mk_lead(world, callback_at=soon)
    with django_capture_on_commit_callbacks(execute=True):
        ingest(api, paired, [call(2, NUMBER, kind=1, duration=45)])  # gaplashilgan kiruvchi
    lead.refresh_from_db()
    assert lead.callback_talked_at is not None and lead.callback_at == soon and not notes().exists()  # eslatma to'xtamadi, hali kutyapti
    with django_capture_on_commit_callbacks(execute=True):
        assert reminders.lead_callbacks(timezone.localtime(soon) + H(minutes=1)) == 1
    m = notes().get()
    assert "allaqachon gaplashilgan" in m.text and "izoh yozing" in m.text and "lc:done" not in str(m.markup)


def test_no_prompt_for_other_statuses_or_no_conversation(api, world, paired, ah, django_capture_on_commit_callbacks):  # noqa: F811
    lead = mk_lead(world, status="2")
    with django_capture_on_commit_callbacks(execute=True):
        ingest(api, paired, [call(3, NUMBER, kind=2, duration=90)])
    lead.refresh_from_db()
    assert lead.callback_talked_at is None and not notes().exists()
    Lead.objects.filter(pk=lead.pk).update(status="1")
    with django_capture_on_commit_callbacks(execute=True):
        ingest(api, paired, [call(4, NUMBER, kind=3, duration=0), call(5, NUMBER, kind=2, minutes=5, duration=0)])  # javobsiz va ulanmagan
    lead.refresh_from_db()
    assert lead.callback_talked_at is None and not notes().exists()


def test_call_note_endpoint(api, world, ah):  # noqa: F811
    lead = mk_lead(world)
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=timezone.now() - H(minutes=5))
    c = api(ah)
    url = f"/api/v1/leads/{lead.pk}/call-note/"
    assert c.post(url, {"comment": "  "}, format="json").status_code == 400
    r = c.post(url, {"comment": "Narxni so'radi"}, format="json")  # 1-statusda qoladi, vaqt yo'q → keyingi vaqt majburiy
    assert r.status_code == 400 and "callback_at" in r.json()
    r = c.post(url, {"comment": "Narxni so'radi", "callback_at": iso(H(days=2))}, format="json")
    assert r.status_code == 200, r.content
    lead.refresh_from_db()
    assert lead.callback_talked_at is None and lead.callback_at and lead.callback_reminded_at is None
    assert LeadComment.objects.filter(lead=lead, comment="📞 Narxni so'radi").count() == 1
    # vaqti hali kelmagan bo'lsa — faqat izoh ham yetadi
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=timezone.now())
    assert c.post(url, {"comment": "Yana bog'landi"}, format="json").status_code == 200
    # 8-statusga o'tkazsa — vaqt majburiy; 3-statusga — vaqt tozalanadi
    assert c.post(url, {"comment": "Keyinroq", "status": "8"}, format="json").status_code == 400
    assert c.post(url, {"comment": "Sinovga yozildi", "status": "3"}, format="json").status_code == 200
    lead.refresh_from_db()
    assert lead.status == "3" and lead.callback_at is None
    assert c.post(url, {"comment": "x", "status": "99"}, format="json").status_code == 400


def test_plain_comment_clears_note_flag(api, world, ah):  # noqa: F811
    lead = mk_lead(world)
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=timezone.now())
    assert api(ah).post(f"/api/v1/leads/{lead.pk}/comments/", {"comment": "Gaplashdik"}, format="json").status_code == 201
    lead.refresh_from_db()
    assert lead.callback_talked_at is None


def test_morning_plan_lists_unnoted(world):  # noqa: F811
    lead = mk_lead(world)
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=timezone.now() - H(hours=20))
    assert "Gaplashilgan, izoh yozilmagan lidlar</b> — 1 ta" in reminders.plan_text(world["branch"], timezone.localdate())


# ------------------------------------------------------------------ kartochkada qo'ng'iroqlar tarixi

def test_call_history_on_lead_and_student(api, make_user, world, paired):  # noqa: F811
    lead = mk_lead(world)
    st = world["students"][0]
    par = Parent.objects.create(branch=world["branch"], first_name="Vali", phone="977776655")
    st.parent = par
    st.save()
    ingest(api, paired, [call(10, NUMBER, kind=2, minutes=0, duration=60), call(11, "+998977776655", kind=3, minutes=5, duration=0),
                         call(12, "+998911111111", kind=1, minutes=6, duration=10)])
    adm = api(make_user("ADMINISTRATOR"))
    d = adm.get(f"/api/v1/leads/{lead.pk}/calls/").json()
    assert d["allowed"] and d["count"] == 2 and d["last"]["direction"] == "Javobsiz" and {r["phone"] for r in d["results"]} == {"900000000", "977776655"}
    assert adm.get(f"/api/v1/students/{st.pk}/calls/").json()["count"] == 2
    hisobchi = api(make_user("HISOBCHI"))  # «Qo'ng'iroqlar» bo'limi huquqi yo'q — lidni ko'radi, tarixni emas
    r = hisobchi.get(f"/api/v1/leads/{lead.pk}/calls/").json()  # SMS ko'radi (2026-10-22), qo'ng'iroqlarni emas
    assert r["calls_allowed"] is False and r["count"] == 0 and r["results"] == [] and r["sms"] == {"count": 0, "results": []}
    assert api(make_user("USTOZ")).get(f"/api/v1/students/{st.pk}/calls/").json()["allowed"] is False


def test_calls_list_links_to_cards(api, world, paired, ah):  # noqa: F811
    lead = mk_lead(world)
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=timezone.now())
    ingest(api, paired, [call(20, NUMBER, kind=1, duration=30)])
    row = api(ah).get("/api/v1/calls/").json()["results"][0]
    assert row["contract_id"] == str(world["contracts"][0].pk) and row["lead_note_due"] is True and row["open_absences"] in (0, None)


# ------------------------------------------------------------------ kelmagan talaba bilan bog'lanish

def test_absence_contact_from_call(api, world, paired, ah):  # noqa: F811
    w = world
    assert take(api(w["teacher"]), w, [(w["contracts"][0], "X", ""), (w["contracts"][1], "1", "")]).status_code in (200, 201)
    ingest(api, paired, [call(30, NUMBER, kind=2, duration=95), call(31, "+998900000001", kind=2, minutes=1, duration=0)])
    rec = CallRecord.objects.get(external_id__startswith="30-")
    c = api(ah)
    row = c.get("/api/v1/calls/").json()["results"]
    assert next(r for r in row if r["id"] == str(rec.pk))["open_absences"] == 1
    url = f"/api/v1/calls/{rec.pk}/absence-contact/"
    assert c.post(url, {"comment": ""}, format="json").status_code == 400  # «Gaplashildi» — izoh majburiy
    r = c.post(url, {"comment": "Kasal bo'lgan, ertaga keladi", "parent_log": True}, format="json")
    assert r.status_code == 200, r.content
    assert r.json() == {"absences": 1, "parent_logs": 1}
    a = Attendance.objects.get(contract=w["contracts"][0], date=TODAY)
    assert a.contact_status == "Gaplashildi" and a.comment == "Kasal bo'lgan, ertaga keladi"
    pc = ParentCall.objects.get(contract=w["contracts"][0])
    assert pc.comment.startswith("📞") and pc.group_id == w["group"].pk
    assert c.post(url, {"comment": "yana"}, format="json").status_code == 400  # endi kutayotgani yo'q
    short = CallRecord.objects.get(external_id__startswith="31-")
    assert c.post(f"/api/v1/calls/{short.pk}/absence-contact/", {"comment": "x"}, format="json").status_code == 400  # suhbat bo'lmagan


def test_absence_contact_without_parent_log(api, world, paired, ah):  # noqa: F811
    w = world
    take(api(ah), w, [(w["contracts"][0], "0", "Kasal"), (w["contracts"][1], "1", "")])  # sababli — faqat menejerlar qo'yadi
    ingest(api, paired, [call(40, NUMBER, kind=1, duration=20)])
    rec = CallRecord.objects.get()
    r = api(ah).post(f"/api/v1/calls/{rec.pk}/absence-contact/", {"comment": "Gaplashildi", "parent_log": False}, format="json")
    assert r.json() == {"absences": 1, "parent_logs": 0} and not ParentCall.objects.exists()


# ------------------------------------------------------------------ voronka

def test_stats_funnel_by_source(api, world, paired, ah):  # noqa: F811
    w = world
    mk_lead(w, status="5")  # talaba 0: lid 5-status, shartnoma bor
    insta = LeadSource.objects.get(name="Instagram")
    tg = LeadSource.objects.create(name="Telegram")
    Lead.objects.create(branch=w["branch"], student=w["students"][1], source=tg, course=w["course"], status="2")
    ingest(api, paired, [call(50, NUMBER, kind=1), call(51, NUMBER, kind=2, minutes=3), call(52, "+998900000001", kind=1, minutes=4),
                         call(53, "+998911110000", kind=1, minutes=5)])
    f = api(ah).get("/api/v1/calls/stats/").json()
    assert f["funnel"] == {"callers": 3, "leads": 2, "started": 1, "contracts": 2, "no_lead": 1}
    by = {r["name"]: r for r in f["funnel_by_source"]}
    assert by[insta.name]["callers"] == 1 and by[insta.name]["started"] == 1 and by["Telegram"]["leads"] == 1

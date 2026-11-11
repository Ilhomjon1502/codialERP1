import datetime

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.crm import inbox
from apps.crm.models import InboxLead, Lead
from apps.notifications import ig_leads, reminders
from apps.notifications.models import Outbox, TelegramLink
from tests.test_ig_leads import URL, row

pytestmark = pytest.mark.django_db


@pytest.fixture
def now_commit(monkeypatch):
    monkeypatch.setattr("apps.notifications.services.transaction.on_commit", lambda f: f())


def test_add_is_idempotent_and_site_dedup(branch):
    a, new = inbox.add("Instagram", phone="901112233", name="Ali", external_id="l:1")
    assert new and a.status == "new"
    assert inbox.add("Instagram", phone="901112233", external_id="l:1") == (a, False)
    s, new = inbox.add("Sayt", phone="901112233", name="Vali")
    assert new
    assert inbox.add("Sayt", phone="901112233") == (None, False)  # 6 soat ichida takror emas
    assert InboxLead.objects.count() == 2


def test_ig_tick_feeds_inbox_but_not_real_leads(branch, make_user, now_commit):
    make_user("BOSH_MENEJER")
    with override_settings(IG_LEADS_SHEET_URL=URL, IG_LEADS_CHAT_ID=-100):
        now = timezone.now()
        ig_leads.tick(now, rows=[row("l:1")])  # birinchi ishga tushish — eskilar navbatga tushmaydi
        assert InboxLead.objects.count() == 0
        ig_leads.tick(now + datetime.timedelta(minutes=6), rows=[row("l:1"), row("l:2", phone="903635800", name="Farrux", platform="fb")])
    it = InboxLead.objects.get()
    assert (it.kind, it.name, it.phone, it.external_id, it.course_name) == ("Facebook", "Farrux", "903635800", "l:2", "Kompyuter savodxonligi")
    assert Lead.objects.count() == 0  # statistika/KPI'ga ta'sir qilmaydi


def test_talk_requires_comment_and_time_or_close(branch, make_user):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    it, _ = inbox.add("Instagram", phone="901112233", external_id="l:1")
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        inbox.talk(u, it, "", callback_at=timezone.now() + datetime.timedelta(hours=1))
    with pytest.raises(ValidationError):
        inbox.talk(u, it, "gaplashdik")  # vaqt ham yopish ham yo'q
    with pytest.raises(ValidationError):
        inbox.talk(u, it, "gaplashdik", callback_at=timezone.now() - datetime.timedelta(days=1))
    inbox.talk(u, it, "Ertaga qo'ng'iroq qiling", callback_at=timezone.now() + datetime.timedelta(days=1))
    it.refresh_from_db()
    assert it.status == "callback" and it.notes.count() == 1
    inbox.talk(u, it, "Qiziqmadi", close=True)
    it.refresh_from_db()
    assert it.status == "rejected" and it.callback_at is None
    inbox.reopen(u, it)
    it.refresh_from_db()
    assert it.status == "new"


def test_permissions_by_role(api, make_user, branch):
    inbox.add("Sayt", phone="901112233", name="Ali")
    for role, code in (("ADMINISTRATOR_HISOBCHI", 200), ("BOSH_MENEJER", 200), ("MARKETOLOG", 403), ("USTOZ", 403), ("ADMINISTRATOR", 403)):
        assert api(make_user(role)).get("/api/v1/inbox-leads/").status_code == code, role


def test_api_flow_summary_due_and_link(api, make_user, branch):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    c = api(u)
    it, _ = inbox.add("Instagram", phone="901112233", name="Ali", external_id="l:1")
    assert c.get("/api/v1/inbox-leads/summary/").json() == {"new": 1, "due": 0, "callback": 0, "linked": 0, "rejected": 0}
    at = (timezone.now() + datetime.timedelta(hours=1)).isoformat()
    r = c.post(f"/api/v1/inbox-leads/{it.pk}/talk/", {"comment": "Keyinroq", "callback_at": at}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "callback" and r.json()["notes"][0]["comment"] == "Keyinroq"
    InboxLead.objects.filter(pk=it.pk).update(callback_at=timezone.now() - datetime.timedelta(minutes=1))
    d = c.get("/api/v1/inbox-leads/due/").json()
    assert d["summary"]["due"] == 1 and len(d["due"]) == 1 and d["new"] == []
    assert c.post(f"/api/v1/inbox-leads/{it.pk}/link/", {"lead": "00000000-0000-0000-0000-000000000000"}, format="json").status_code == 400


def test_known_phone_flag(api, make_user, branch):
    from apps.crm.models import Student

    u = make_user("BOSH_MENEJER")
    Student.objects.create(branch=branch, first_name="Karim", last_name="Aliyev", phone1="901112233")
    inbox.add("Sayt", phone="901112233", name="Karim")
    row_ = api(u).get("/api/v1/inbox-leads/").json()["results"][0]
    assert row_["known"]["name"].startswith("Karim")


@override_settings(INBOX_SITE_KEY="sir123")
def test_site_ingest_key(api, branch):
    c = api()
    body = {"name": "Ali", "phone": "+998 90 111-22-33", "course": "Frontend", "message": "Narxi qancha?"}
    assert c.post("/api/v1/inbox/site/", body, format="json").status_code == 403
    assert c.post("/api/v1/inbox/site/", body, format="json", HTTP_X_INBOX_KEY="xato").status_code == 403
    assert c.post("/api/v1/inbox/site/", body, format="json", HTTP_X_INBOX_KEY="sir123").status_code == 201
    assert c.post("/api/v1/inbox/site/", {"phone": "12"}, format="json", HTTP_X_INBOX_KEY="sir123").status_code == 400
    it = InboxLead.objects.get()
    assert it.kind == "Sayt" and it.phone == "901112233" and it.info == "Narxi qancha?"


def test_bot_reminder_once(branch, make_user, now_commit):
    u = make_user("ADMINISTRATOR_HISOBCHI")
    TelegramLink.objects.create(user=u, chat_id=555)
    it, _ = inbox.add("Instagram", phone="901112233", name="Ali", external_id="l:1")
    InboxLead.objects.filter(pk=it.pk).update(status="callback", callback_at=timezone.now() - datetime.timedelta(minutes=2))
    assert reminders.inbox_callbacks() == 1
    assert reminders.inbox_callbacks() == 0
    assert Outbox.objects.filter(chat_id=555, event="lead_callback").count() == 1


def test_backfill_adds_only_missing_unique_leads(branch):
    from apps.crm.models import Student

    Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233")
    inbox.add("Instagram", phone="903635800", external_id="l:9")  # navbatda bor
    rows = [row("l:1", phone="901112233"), row("l:2", phone="903635800"), row("l:3", phone="911110000", at="2026-11-01T10:00:00-05:00"),
            row("l:4", phone="911110000", at="2026-11-02T10:00:00-05:00"), row("l:5", phone="922220000")]
    rep = ig_leads.backfill(rows)  # sinov — hech narsa yozilmaydi
    assert rep == {"rows": 5, "in_erp": 1, "in_queue": 1, "duplicate": 1, "added": 2} and InboxLead.objects.count() == 1
    ig_leads.backfill(rows, commit=True)
    assert sorted(InboxLead.objects.values_list("external_id", flat=True)) == ["l:4", "l:5", "l:9"]
    assert InboxLead.objects.get(external_id="l:4").status == "new"
    assert ig_leads.backfill(rows, commit=True)["added"] == 0  # qayta ishga tushirsa takror yo'q
    assert not Outbox.objects.filter(event="ig_lead").exists()


def _call(device, phone, minutes, direction="Chiquvchi", duration=40):
    from apps.calls.models import CallRecord

    return CallRecord.objects.create(device=device, branch=device.branch, external_id=f"x{minutes}{phone}", direction=direction, number=phone, phone=phone,
                                     started_at=timezone.now() + datetime.timedelta(minutes=minutes), duration=duration)


def test_inbox_row_shows_calls_and_note_due(api, make_user, branch):
    from apps.calls.models import CallDevice

    dev = CallDevice.objects.create(name="Qabul", branch=branch)
    u = make_user("ADMINISTRATOR_HISOBCHI")
    it, _ = inbox.add("Instagram", phone="901112233", name="Ali", external_id="l:1", received_at=timezone.now() - datetime.timedelta(hours=1))
    _call(dev, "901112233", -30, "Javobsiz", 0)
    row = api(u).get("/api/v1/inbox-leads/").json()["results"][0]
    assert row["calls"]["count"] == 1 and row["calls"]["note_due"] is False  # javobsiz — gaplashilmagan
    _call(dev, "901112233", -10, "Chiquvchi", 55)
    row = api(u).get("/api/v1/inbox-leads/").json()["results"][0]
    assert row["calls"]["count"] == 2 and row["calls"]["note_due"] is True  # gaplashildi, izoh yo'q
    inbox.talk(u, it, "Ertaga", callback_at=timezone.now() + datetime.timedelta(days=1))
    row = api(u).get("/api/v1/inbox-leads/").json()["results"][0]
    assert row["calls"]["note_due"] is False  # izoh yozildi
    _call(dev, "999999999", -5)  # boshqa raqam — hisobga olinmaydi
    assert api(u).get("/api/v1/inbox-leads/").json()["results"][0]["calls"]["count"] == 2


def test_calls_before_lead_arrived_are_ignored(api, make_user, branch):
    from apps.calls.models import CallDevice

    dev = CallDevice.objects.create(name="Qabul", branch=branch)
    u = make_user("BOSH_MENEJER")
    inbox.add("Sayt", phone="901112233", name="Ali")
    _call(dev, "901112233", -600)
    assert api(u).get("/api/v1/inbox-leads/").json()["results"][0]["calls"] is None


def test_calls_list_marks_unknown_number_as_inbox_lead(api, make_user, branch):
    from apps.calls.models import CallDevice

    dev = CallDevice.objects.create(name="Qabul", branch=branch)
    u = make_user("ADMINISTRATOR_HISOBCHI")
    inbox.add("Instagram", phone="901112233", name="Ali", course_name="Frontend", external_id="l:1")
    _call(dev, "901112233", 1, "Kiruvchi", 20)
    _call(dev, "905550000", 2, "Kiruvchi", 20)
    rows = {r["phone"]: r for r in api(u).get("/api/v1/calls/").json()["results"]}
    assert rows["901112233"]["inbox"]["kind"] == "Instagram" and rows["901112233"]["inbox"]["course"] == "Frontend"
    assert rows["905550000"]["inbox"] is None

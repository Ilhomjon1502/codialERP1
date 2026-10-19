"""Qo'ng'iroqlar: qurilmani ulash, telefondan qabul qilish (idempotent), CRM bilan solishtirish, qayta qo'ng'iroq, ruxsatlar."""

import datetime

import pytest

from apps.calls import services
from apps.calls.models import CallDevice, CallRecord
from apps.crm.models import Lead, Parent, Student
from apps.references.models import Course, LeadSource

D = CallRecord.Direction
T0 = int(datetime.datetime(2026, 10, 19, 9, 0, tzinfo=datetime.UTC).timestamp() * 1000)


def call(i, number, kind=1, minutes=0, duration=30, **extra):
    return {"id": i, "date": T0 + minutes * 60_000, "type": kind, "number": number, "duration": duration, **extra}


@pytest.fixture
def device(db, branch):
    return CallDevice.objects.create(name="Qabul telefoni", branch=branch)


@pytest.fixture
def paired(api, device):
    code = services.new_pair_code(device)
    r = api().post("/api/v1/calls/pair/", {"code": code.lower(), "app_version": "1.0"}, format="json")
    assert r.status_code == 200, r.data
    return r.data["token"]


def ingest(api, token, calls):
    return api().post("/api/v1/calls/ingest/", {"calls": calls}, format="json", HTTP_AUTHORIZATION=f"Device {token}")


def test_normalize():
    assert services.normalize("+998 (90) 123-45-67") == "901234567"
    assert services.normalize("901234567") == "901234567"
    assert services.normalize("1234") == ""
    assert services.normalize("+7 912 345 67 89") == ""


def test_pair_once_and_token_auth(api, device, paired):
    device.refresh_from_db()
    assert device.token_hash and not device.pair_code and device.app_version == "1.0"
    assert api().get("/api/v1/calls/ping/", HTTP_AUTHORIZATION=f"Device {paired}").data["name"] == "Qabul telefoni"
    # kod bir martalik
    assert api().post("/api/v1/calls/pair/", {"code": "AAAAAAAA"}, format="json").status_code == 400
    assert ingest(api, "noto'g'ri", []).status_code == 401
    # yangi kod — eski token bekor
    services.new_pair_code(device)
    assert ingest(api, paired, []).status_code == 401


def test_ingest_idempotent_and_matching(api, branch, paired):
    s = Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233", phone2="931112233")
    lead = Lead.objects.create(branch=branch, student=s, source=LeadSource.objects.create(name="Instagram"),
                               course=Course.objects.create(name="Frontend"))
    par = Parent.objects.create(branch=branch, first_name="Vali", phone="977776655")
    child = Student.objects.create(branch=branch, first_name="Bek", last_name="Valiyev", phone1="900000001", parent=par)
    batch = [call(1, "+998931112233"), call(2, "+998977776655", kind=2, minutes=5), call(3, "+998991234567", kind=3, minutes=7, duration=0)]
    r = ingest(api, paired, batch)
    assert r.data == {"accepted": 3, "duplicates": 0, "errors": []}
    assert ingest(api, paired, batch + [{"id": "x"}]).data["accepted"] == 0
    assert CallRecord.objects.count() == 3
    a, b, c = CallRecord.objects.order_by("started_at")
    assert (a.student, a.lead, a.direction, a.duration) == (s, lead, D.INCOMING, 30)
    assert (b.parent, b.student, b.direction) == (par, child, D.OUTGOING)
    assert c.student is None and c.direction == D.MISSED and c.is_first
    # o'sha raqamdan yana qo'ng'iroq — birinchi emas
    ingest(api, paired, [call(4, "991234567", minutes=60)])
    assert not CallRecord.objects.get(external_id__startswith="4-").is_first


def test_missed_closed_by_callback(api, paired):
    ingest(api, paired, [call(1, "991234567", kind=3, duration=0), call(2, "991234567", kind=5, minutes=1, duration=0)])
    assert CallRecord.objects.filter(callback_at__isnull=True).count() == 2
    ingest(api, paired, [call(3, "991234567", kind=2, minutes=10, duration=0)])
    assert CallRecord.objects.filter(direction__in=[D.MISSED, D.REJECTED], callback_at__isnull=False).count() == 2
    st = services.stats(CallRecord.objects.all())
    assert st["missed"] == 2 and st["missed_open"] == 0 and st["callback_minutes"] in (9, 10)


def test_list_permissions_and_rematch(api, make_user, branch, other_branch, paired):
    ingest(api, paired, [call(1, "991234567", kind=3, duration=0)])
    adm, teacher, other = make_user("ADMINISTRATOR"), make_user("USTOZ"), make_user("ADMINISTRATOR", branches=[other_branch])
    assert api(teacher).get("/api/v1/calls/").status_code == 403
    assert api(other).get("/api/v1/calls/").data["count"] == 0
    # keyin lid ochilsa — ro'yxatda ism chiqadi
    s = Student.objects.create(branch=branch, first_name="Yangi", last_name="Lid", phone1="991234567")
    row = api(adm).get("/api/v1/calls/?dir=missed_open").data["results"][0]
    assert row["student"] == s.pk and row["student_name"] == "Yangi Lid" and row["missed"]
    r = api(adm).post(f"/api/v1/calls/{row['id']}/callback/", {"done": True}, format="json")
    assert r.status_code == 200 and r.data["callback_at"]
    assert api(adm).patch(f"/api/v1/calls/{row['id']}/", {"comment": "Frontendga qiziqdi", "duration": 999}, format="json").status_code == 200
    rec = CallRecord.objects.get()
    assert rec.comment == "Frontendga qiziqdi" and rec.duration == 0
    assert api(adm).post("/api/v1/calls/", {}, format="json").status_code in (403, 405)
    assert api(adm).get("/api/v1/calls/stats/").data["total"] == 1


def test_device_admin_only_top(api, make_user, branch):
    adm, bm = make_user("ADMINISTRATOR"), make_user("BOSH_MENEJER")
    assert api(adm).post("/api/v1/call-devices/", {"name": "T", "branch": branch.pk}, format="json").status_code == 403
    r = api(bm).post("/api/v1/call-devices/", {"name": "T", "branch": branch.pk, "phone": "12345"}, format="json")
    assert r.status_code == 400
    r = api(bm).post("/api/v1/call-devices/", {"name": "T", "branch": branch.pk, "phone": "998204432"}, format="json")
    assert r.status_code == 201 and len(r.data["pair_code"]) == 8 and not r.data["paired"]


def test_daily_report_calls_section(api, branch, device, paired):
    from django.utils import timezone

    from apps.notifications.management.commands.daily_report import build

    now = int(timezone.now().timestamp() * 1000)
    Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233")
    ingest(api, paired, [
        {"id": 1, "date": now - 60_000, "type": 3, "number": "+998901112233", "duration": 0},
        {"id": 2, "date": now - 50_000, "type": 3, "number": "+998991234567", "duration": 0},
        {"id": 3, "date": now - 40_000, "type": 2, "number": "+998991234567", "duration": 20},
        {"id": 4, "date": now - 30_000, "type": 1, "number": "+998935554433", "duration": 125},
    ])
    text = build(timezone.localdate())
    assert "Qo'ng'iroqlar: 4</b> (kiruvchi 1 · chiquvchi 1 · javobsiz 2)" in text
    assert "Javobsiz qoldi: 1</b>" in text and "+998901112233 — Ali Valiyev" in text and "+998991234567 —" not in text
    assert "Javobsizlarga qayta bog'lanildi: 1 ta" in text and "aloqaga chiqmayapti" not in text
    CallDevice.objects.update(last_seen_at=timezone.now() - datetime.timedelta(hours=8))
    assert "Qabul telefoni aloqaga chiqmayapti" in build(timezone.localdate())


def test_morning_plan_night_missed_calls(api, branch, device, paired):
    from django.utils import timezone

    from apps.notifications import reminders

    day = datetime.date(2026, 10, 20)
    tz = timezone.get_current_timezone()

    def ms(d, h, m):
        return int(datetime.datetime.combine(d, datetime.time(h, m), tz).timestamp() * 1000)

    y = day - datetime.timedelta(days=1)
    Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233")
    ingest(api, paired, [
        {"id": 1, "date": ms(y, 18, 0), "type": 3, "number": "+998971110001", "duration": 0},   # 18:30 dan oldin — kirmaydi
        {"id": 2, "date": ms(y, 21, 15), "type": 3, "number": "+998901112233", "duration": 0},  # kirishi kerak (talaba)
        {"id": 3, "date": ms(day, 7, 45), "type": 3, "number": "+998901112233", "duration": 0},  # shu raqam yana — ×2
        {"id": 4, "date": ms(y, 22, 0), "type": 3, "number": "+998931110002", "duration": 0},   # keyin o'zi terdik — kirmaydi
        {"id": 5, "date": ms(day, 7, 0), "type": 2, "number": "+998931110002", "duration": 40},
        {"id": 6, "date": ms(day, 8, 40), "type": 3, "number": "+998941110003", "duration": 0},  # 8:30 dan keyin — kirmaydi
        {"id": 7, "date": ms(y, 23, 0), "type": 5, "number": "+998951110004", "duration": 0},   # rad etilgan, noma'lum
    ])
    text = reminders.plan_text(branch, day)
    assert "Tunda javobsiz qo'ng'iroqlar" in text and "2 raqam" in text
    assert "Ali Valiyev · +998901112233 — 21:15 (×2)" in text
    assert "noma'lum raqam · +998951110004" in text
    assert "971110001" not in text and "931110002" not in text and "941110003" not in text


def test_daily_report_without_device(db):
    from django.utils import timezone

    from apps.notifications.management.commands.daily_report import build

    assert "Qo'ng'iroqlar" not in build(timezone.localdate())


def test_list_query_count(api, make_user, paired, django_assert_max_num_queries):
    ingest(api, paired, [call(i, f"99{i:07d}", kind=1 + i % 3) for i in range(30)])
    adm = make_user("ADMINISTRATOR")
    c = api(adm)
    with django_assert_max_num_queries(12):
        assert c.get("/api/v1/calls/").data["count"] == 30


def test_stats_durations(api, paired):
    ingest(api, paired, [call(1, "991234567", duration=20), call(2, "991234568", kind=2, minutes=1, duration=90),
                         call(3, "991234569", minutes=2, duration=700), call(4, "991234560", kind=3, minutes=3, duration=0)])
    s = services.stats(CallRecord.objects.all())
    assert s["talk"] == 810 and s["talked"] == 3 and s["avg_talk"] == 270 and s["longest"] == 700
    assert (s["talk_in"], s["talk_out"]) == (720, 90)
    assert {d["label"]: d["n"] for d in s["by_duration"]} == {"1–30 s": 1, "30 s–1 daq": 0, "1–3 daq": 1, "3–5 daq": 0, "5–10 daq": 0, "10 daq+": 1}

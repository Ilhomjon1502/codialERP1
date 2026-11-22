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
    assert s["shortest"] == 20 and s["longest_call"]["duration"] == 700 and s["longest_call"]["phone"] == "991234569"
    assert s["shortest_call"]["phone"] == "991234567" and s["shortest_call"]["direction"] == "Kiruvchi"
    assert {d["label"]: d["n"] for d in s["by_duration"]} == {"1–30 s": 1, "30 s–1 daq": 0, "1–3 daq": 1, "3–5 daq": 0, "5–10 daq": 0, "10 daq+": 1}


def test_calls_section_in_roles_matrix(api, make_user):
    """Bo'lim «Rollar va ruxsatlar» jadvalida chiqadi (bootstrap sections) va Bosh menejer uni istalgan rolga bera/ola oladi."""
    bm, hisobchi = make_user("BOSH_MENEJER"), make_user("HISOBCHI")
    assert "calls" in [k for k, _ in api(bm).get("/api/v1/bootstrap/").data["sections"]]
    assert api(hisobchi).get("/api/v1/calls/").status_code == 403
    r = api(bm).post("/api/v1/roles/HISOBCHI/toggle/", {"section": "calls", "op": "v"}, format="json")
    assert r.status_code == 200 and "v" in r.data["perms"]["calls"]
    assert api(hisobchi).get("/api/v1/calls/").status_code == 200
    api(bm).post("/api/v1/roles/HISOBCHI/toggle/", {"section": "calls", "op": "v"}, format="json")
    assert api(make_user("HISOBCHI")).get("/api/v1/calls/").status_code == 403


# ---------- Suhbat yozuvlari (2026-11-18) ----------


def _upload(api, token, name="r.m4a", data=b"x" * 2048, ended_min=0, ended_sec=40, duration=40, sig="s1", number=None):
    from django.core.files.uploadedfile import SimpleUploadedFile

    ended = T0 + ended_min * 60_000 + ended_sec * 1000
    body = {"file": SimpleUploadedFile(name, data, content_type="audio/mp4"), "ended_at": ended, "duration": duration, "sig": sig}
    if number is not None:
        body["number"] = number
    return api().post("/api/v1/calls/recordings/", body, format="multipart", HTTP_AUTHORIZATION=f"Device {token}")


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def test_recording_matches_call_by_time(api, paired, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, minutes=0, duration=40), call(2, "+998907654321", kind=1, minutes=10, duration=30)])
    r = _upload(api, paired, ended_min=0, ended_sec=45, duration=45)  # birinchi qo'ng'iroq: boshlanishi 09:00, 40 s suhbat
    assert r.status_code == 200 and r.data["status"] == "ok", r.data
    first = CallRecord.objects.get(external_id__startswith="1-")
    assert first.audio and first.audio_duration == 45 and first.audio_size == 2048
    assert not CallRecord.objects.get(external_id__startswith="2-").audio
    # shu fayl qayta kelsa — takror
    assert _upload(api, paired, ended_min=0, ended_sec=45, duration=45).data["status"] == "duplicate"


def test_recording_stored_until_call_arrives(api, paired, media):
    """Mos qo'ng'iroq jurnalda yo'q: yozuv baribir saqlanadi (yo'qolmaydi); qo'ng'iroq kelganda server o'zi biriktiradi."""
    from apps.calls.models import CallRecording

    r = _upload(api, paired)
    assert r.data["status"] == "stored" and CallRecording.objects.count() == 1
    assert CallRecording.objects.get().call is None and CallRecording.objects.get().file
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    assert CallRecording.objects.get().call_id == CallRecord.objects.get().pk
    assert CallRecord.objects.get().audio
    assert _upload(api, paired).data["status"] == "duplicate"  # shu fayl qayta kelsa — takror


def test_recording_validates(api, paired, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    assert _upload(api, paired, name="x.exe").status_code == 400
    assert api().post("/api/v1/calls/recordings/", {"ended_at": T0}, format="multipart").status_code == 401


def test_recording_keeps_longer_file(api, paired, media):
    """Bitta qo'ng'iroqqa ikki fayl: asosiysi uzuni, ikkalasi ham ro'yxatda qoladi."""
    from apps.calls.models import CallRecording

    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    assert _upload(api, paired, ended_sec=60, duration=60, sig="a").data["status"] == "ok"
    assert _upload(api, paired, ended_sec=40, duration=30, sig="b").data["status"] == "ok"
    assert CallRecord.objects.get().audio_duration == 60
    assert CallRecording.objects.filter(call__isnull=False).count() == 2


def test_audio_playback_permissions_and_range(api, paired, make_user, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    _upload(api, paired, data=bytes(range(200)) * 10)
    rec = CallRecord.objects.get()
    url = f"/api/v1/calls/{rec.pk}/audio/"
    boss = make_user("BOSH_MENEJER")
    r = api(boss).get(url)
    assert r.status_code == 200 and b"".join(r.streaming_content) == bytes(range(200)) * 10
    assert r["Content-Type"] == "audio/mp4" and r["Accept-Ranges"] == "bytes"
    p = api(boss).get(url, HTTP_RANGE="bytes=10-19")
    assert p.status_code == 206 and p["Content-Range"] == "bytes 10-19/2000" and b"".join(p.streaming_content) == bytes(range(10, 20))
    assert api(boss).get(url, HTTP_RANGE="bytes=5000-").status_code == 416
    # Administrator qo'ng'iroqlarni ko'radi, lekin yozuvni eshita olmaydi (call_audio berilmagan)
    admin = make_user("ADMINISTRATOR")
    assert api(admin).get(url).status_code == 403
    assert api(admin).get("/api/v1/calls/").data["results"][0]["has_audio"] is True
    # audio=1 filtri
    assert api(boss).get("/api/v1/calls/?audio=1").data["count"] == 1


def test_purge_audio(api, paired, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    _upload(api, paired)
    assert services.purge_audio(7) == 1  # qo'ng'iroq 2026-10-19 da — 7 kundan eski
    rec = CallRecord.objects.get()
    assert not rec.audio and rec.audio_sig == ""


def test_recording_goes_to_the_call_with_the_same_number(api, paired, media):
    """2026-11-18: Robiya qo'ng'irog'i jurnalda hali yo'q paytda uning yozuvi eng yaqin boshqa qo'ng'iroqqa (Ilhom) yopishib qolgan edi."""
    ingest(api, paired, [call(1, "+998901111502", kind=2, minutes=0, duration=6)])
    late = dict(ended_min=2, ended_sec=7, duration=27)
    assert _upload(api, paired, sig="b", number="+998 90 333-34-31", **late).data["status"] == "stored"  # Ilhomga yopishmaydi
    assert not CallRecord.objects.get().audio
    ingest(api, paired, [call(2, "+998903333431", kind=2, minutes=1, duration=8)])  # Robiya qo'ng'irog'i keyin keldi
    assert CallRecord.objects.get(phone="903333431").audio and not CallRecord.objects.get(phone="901111502").audio


def test_recording_with_number_waits_for_its_call(api, paired, media):
    """Mos raqamli qo'ng'iroq hali jurnalda yo'q: boshqa raqamning yaqin qo'ng'irog'iga yopishmaydi, saqlanib turadi."""
    from apps.calls.models import CallRecording

    ingest(api, paired, [call(1, "+998901111502", kind=2, minutes=0, duration=40)])
    assert _upload(api, paired, number="+998903333431").data["status"] == "stored"
    assert not CallRecord.objects.get().audio and CallRecording.objects.get().call is None
    ingest(api, paired, [call(2, "+998903333431", kind=2, minutes=0, duration=40)])
    assert CallRecord.objects.get(phone="903333431").audio and not CallRecord.objects.get(phone="901111502").audio


def test_recordings_list_shows_linked_and_unlinked_and_plays_both(api, paired, make_user, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    _upload(api, paired, sig="a", data=b"A" * 3000)                                      # biriktiriladi
    _upload(api, paired, sig="b", number="+998909999999", data=b"B" * 3000, ended_min=30)  # biriktirilmaydi
    boss, admin = make_user("BOSH_MENEJER"), make_user("ADMINISTRATOR")
    allr = api(boss).get("/api/v1/call-recordings/").data
    assert allr["count"] == 2
    assert api(boss).get("/api/v1/call-recordings/?linked=1").data["count"] == 1
    un = api(boss).get("/api/v1/call-recordings/?linked=0").data["results"][0]
    assert un["linked"] is False and un["number"] == "909999999" and un["has_file"]
    assert api(boss).get("/api/v1/call-recordings/?q=909999999").data["count"] == 1
    assert api(boss).get("/api/v1/call-recordings/summary/").data == {"total": 2, "linked": 1, "unlinked": 1}
    r = api(boss).get(f"/api/v1/call-recordings/{un['id']}/audio/")
    assert r.status_code == 200 and b"".join(r.streaming_content) == b"B" * 3000
    assert api(admin).get("/api/v1/call-recordings/").status_code == 403  # ruxsat: faqat call_audio egalari


# ---------- Instagram/Facebook lidlari bilan suhbat audiosi → Telegram guruhi ----------

def _ig_setup(api, paired, media, kind="Instagram", received_min=-30, name="r.m4a"):
    from apps.crm import inbox

    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    started = datetime.datetime.fromtimestamp(T0 / 1000, tz=datetime.UTC)
    it, _ = inbox.add(kind, phone="901234567", name="Ali Valiyev", course_name="Frontend", info="reklama",
                      received_at=started + datetime.timedelta(minutes=received_min), external_id="l:1")
    assert _upload(api, paired, name=name).data["status"] == "ok"
    return it


def _ig_now():
    return datetime.datetime.fromtimestamp(T0 / 1000, tz=datetime.UTC) + datetime.timedelta(hours=1)


def test_ig_audio_sent_once_with_caption(api, paired, media, settings):
    from apps.calls import ig_audio

    settings.IG_CALLS_CHAT_ID = -100777
    _ig_setup(api, paired, media)
    # ilgari qo'ng'iroq: lid tushgandan keyin ikkita (biri javobsiz) — bu uchinchisi
    CallRecord.objects.update(audio_at=_ig_now() - datetime.timedelta(minutes=5))
    got = []
    assert ig_audio.tick(_ig_now(), sender=lambda c, lead, chat: got.append((chat, ig_audio.caption(c, lead)))) == 1
    chat, text = got[0]
    assert chat == -100777
    for part in ("Instagram lidi", "Ali Valiyev", "+998901234567", "Frontend", "1-marta", "Qo'ng'iroq:", "suhbat 0:40"):
        assert part in text, part
    assert ig_audio.tick(_ig_now(), sender=lambda *a: got.append(a)) == 0  # ikkinchi marta yuborilmaydi
    assert len(got) == 1


def test_ig_audio_unrelated_recordings_do_not_block_queue(api, paired, media, settings):
    from apps.calls import ig_audio

    settings.IG_CALLS_CHAT_ID = -100777
    _ig_setup(api, paired, media)
    mine = CallRecord.objects.get()
    CallRecord.objects.filter(pk=mine.pk).update(audio_at=_ig_now() - datetime.timedelta(minutes=5))
    # lidga aloqasiz 12 ta eski yozuv (oddiy qo'ng'iroqlar) — oldin ular navbatdagi 10 ta o'rinni egallab olardi
    for i in range(12):
        CallRecord.objects.create(device=mine.device, branch=mine.branch, external_id=f"other{i}", direction=D.OUTGOING, number="+998909990000", phone="909990000",
                                  started_at=mine.started_at - datetime.timedelta(hours=2), duration=30, audio=f"call_audio/x{i}.ogg", audio_size=5000,
                                  audio_at=_ig_now() - datetime.timedelta(hours=1, minutes=i))
    got = []
    assert ig_audio.tick(_ig_now(), sender=lambda c, lead, chat: got.append(c.pk)) == 1
    assert got == [mine.pk]


def test_ig_audio_counts_contacts_and_skips_other_leads(api, paired, media, settings):
    from apps.calls import ig_audio
    from apps.crm import inbox

    settings.IG_CALLS_CHAT_ID = -100777
    it = _ig_setup(api, paired, media, received_min=-30)
    c = CallRecord.objects.get()
    CallRecord.objects.update(audio_at=_ig_now() - datetime.timedelta(minutes=5))
    # shu raqamga lid tushgandan keyin yana 2 ta urinish (avval) bo'lgan
    for i, m in enumerate((-20, -10)):
        CallRecord.objects.create(device=c.device, branch=c.branch, external_id=f"x{i}", direction=D.OUTGOING, number="+998901234567", phone="901234567",
                                  started_at=c.started_at + datetime.timedelta(minutes=m), duration=0)
    assert ig_audio.contact_number(c, it) == 3
    # lid tushmagan raqam yoki «Sayt» lidi — yuborilmaydi
    CallRecord.objects.filter(pk=c.pk).update(phone="907777777")
    assert ig_audio.tick(_ig_now(), sender=lambda *a: pytest.fail("yuborilmasligi kerak")) == 0
    CallRecord.objects.filter(pk=c.pk).update(phone="901234567")
    inbox.InboxLead.objects.filter(pk=it.pk).update(kind="Sayt")
    assert ig_audio.tick(_ig_now(), sender=lambda *a: pytest.fail("yuborilmasligi kerak")) == 0


def test_ig_audio_retries_after_failure_and_waits_for_settle(api, paired, media, settings):
    from apps.calls import ig_audio

    settings.IG_CALLS_CHAT_ID = -100777
    _ig_setup(api, paired, media)
    CallRecord.objects.update(audio_at=_ig_now() - datetime.timedelta(seconds=10))
    assert ig_audio.tick(_ig_now(), sender=lambda *a: pytest.fail("yuklangach 60 soniya kutiladi")) == 0
    CallRecord.objects.update(audio_at=_ig_now() - datetime.timedelta(minutes=5))

    def boom(*a):
        raise RuntimeError("Telegram ishlamayapti")

    assert ig_audio.tick(_ig_now(), sender=boom) == 0
    assert CallRecord.objects.get().audio_tg_at is None  # qayta uriniladi
    assert ig_audio.tick(_ig_now(), sender=lambda *a: None) == 1
    settings.IG_CALLS_CHAT_ID = 0
    CallRecord.objects.update(audio_tg_at=None)
    assert ig_audio.tick(_ig_now(), sender=lambda *a: pytest.fail("guruh o'chiq")) == 0


def test_ig_audio_send_uses_voice_for_ogg_and_multipart(api, paired, media, settings, monkeypatch):
    import io
    import json as _json

    from apps.calls import ig_audio

    settings.TELEGRAM_BOT_TOKEN = "TEST"
    it = _ig_setup(api, paired, media, name="r.ogg")  # ShizuCallRecorder .ogg (Opus) yozadi
    seen = {}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=0):
        seen["url"], seen["body"] = req.full_url, req.data
        return Resp(_json.dumps({"ok": True, "result": {}}).encode())

    monkeypatch.setattr("apps.notifications.services.urllib.request.urlopen", fake_open)
    c = CallRecord.objects.get()
    ig_audio.send(c, it, -100777)
    assert seen["url"].endswith("/botTEST/sendVoice")
    assert b'name="voice"' in seen["body"] and b"Ali Valiyev" in seen["body"] and b'name="chat_id"' in seen["body"]


def test_recording_pending_logs_reason(api, paired, media, caplog):
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=40)])
    with caplog.at_level("WARNING"):
        r = _upload(api, paired, ended_min=30, number="+998909999999", sig="far")  # mos qo'ng'iroq yo'q
    assert r.data["status"] == "stored"
    assert "Yozuv saqlandi, mos qo'ng'iroq hali yo'q" in caplog.text


def test_recording_with_number_matches_by_end_not_file_duration(api, paired, media):
    # uzun suhbat: jurnalda 355 s (javobdan keyin), yozuv raqam terilganda boshlangan (+25 s jiringlash); fayl davomiyligi noto'g'ri o'qilgan (0)
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=355)])
    r = _upload(api, paired, ended_min=6, ended_sec=25 + 355 - 360 + 3, duration=0, number="+998901234567")
    assert r.data["status"] == "ok"
    assert CallRecord.objects.get().audio


def test_recording_with_number_picks_latest_call_of_that_number(api, paired, media):
    # bir raqamga ketma-ket ikki qo'ng'iroq: birinchisi 12 s, ikkinchisi javobsiz — har yozuv o'z qo'ng'irog'iga
    ingest(api, paired, [call(1, "+998901234567", kind=2, minutes=0, duration=12), call(2, "+998901234567", kind=2, minutes=1, duration=0)])
    first = _upload(api, paired, ended_min=0, ended_sec=30, duration=30, number="+998901234567", sig="a").data
    second = _upload(api, paired, ended_min=1, ended_sec=20, duration=20, number="+998901234567", sig="b").data
    assert first["status"] == second["status"] == "ok" and first["call"] != second["call"]
    by_ext = {c.external_id.split("-")[0]: str(c.pk) for c in CallRecord.objects.all()}
    assert first["call"] == by_ext["1"] and second["call"] == by_ext["2"]


def test_started_from_name():
    s = services.started_from_name("20261119_084646.894+0500_out_+998950619880.ogg")
    assert s == datetime.datetime(2026, 11, 19, 3, 46, 46, 894000, tzinfo=datetime.UTC)
    assert services.started_from_name("r.m4a") is None


def _named(minute_offset=0, sec=0, direction="out", number="+998901234567"):
    t = datetime.datetime.fromtimestamp(T0 / 1000, tz=datetime.UTC) + datetime.timedelta(minutes=minute_offset, seconds=sec)
    return f"{t:%Y%m%d_%H%M%S}.000+0000_{direction}_{number}.ogg"


def test_recording_matches_by_start_from_name_even_if_mtime_stale(api, paired, media):
    # javobsiz chiquvchi: jurnalda 0 s, yozuv jiringlashni olgan (57 s); fayl o'zgargan vaqti yozuv BOSHIdagi qiymatda qotib qolgan (ended ≈ start)
    ingest(api, paired, [call(1, "+998901234567", kind=2, minutes=0, duration=0)])
    r = _upload(api, paired, name=_named(0, 1), ended_min=0, ended_sec=2, duration=57, number="+998901234567")
    assert r.data["status"] == "ok" and CallRecord.objects.get().audio


def test_recording_start_picks_closest_call_of_same_number(api, paired, media):
    ingest(api, paired, [call(1, "+998901234567", kind=2, minutes=0, duration=12), call(2, "+998901234567", kind=2, minutes=5, duration=0)])
    a = _upload(api, paired, name=_named(0, 1), ended_min=0, ended_sec=40, duration=40, sig="a", number="+998901234567").data
    b = _upload(api, paired, name=_named(5, 1), ended_min=5, ended_sec=2, duration=30, sig="b", number="+998901234567").data
    by = {c.external_id.split("-")[0]: str(c.pk) for c in CallRecord.objects.all()}
    assert a["call"] == by["1"] and b["call"] == by["2"]


def test_recording_without_number_matches_answered_incoming_only(api, paired, media):
    # kiruvchi, raqam nomda yo'q (yashirin): yozuv javob berilganda boshlanadi — qo'ng'iroq jurnalda jiringlash boshidan (30 s oldin)
    ingest(api, paired, [call(1, "+998901234567", kind=1, minutes=0, duration=46), call(2, "+998909999999", kind=2, minutes=0, duration=0)])
    r = _upload(api, paired, name=_named(0, 32, "in", ""), ended_min=0, ended_sec=33, duration=46, number="")
    assert r.data["status"] == "ok"
    assert CallRecord.objects.get(audio__gt="").direction == D.INCOMING  # chiquvchi (boshqa raqam) ga yopishmadi


# ---------- Suhbat yozuvi to'liq emas → Telegram ogohlantirish (2026-11-20) ----------


@pytest.fixture
def watch(api, paired, make_user, django_capture_on_commit_callbacks, media):
    from apps.calls import rec_watch
    from apps.notifications.models import Outbox, TelegramLink

    u = make_user("ADMINISTRATOR")
    TelegramLink.objects.create(user=u, chat_id=4001)
    start = datetime.datetime.fromtimestamp(T0 / 1000, tz=datetime.UTC)

    def tick(minutes_after_start):
        with django_capture_on_commit_callbacks(execute=True):
            return rec_watch.tick(now=start + datetime.timedelta(minutes=minutes_after_start))

    return {"tick": tick, "outbox": lambda: Outbox.objects.filter(event="rec_problem"), "api": api, "token": paired}


def test_rec_watch_alerts_when_recording_missing_or_cut_short(watch):
    ingest(watch["api"], watch["token"], [call(1, "+998901234567", kind=2, minutes=0, duration=300)])  # 5 daqiqa suhbat, yozuv yo'q
    assert watch["tick"](8) == 0   # suhbat tugaganiga 5 daqiqa ham bo'lmadi: telefon yuklashga ulgurmagan bo'lishi mumkin
    assert watch["tick"](11) == 1
    m = watch["outbox"]().get()
    assert "5:00" in m.text and "yozuv yo'q" in m.text and "Shizuku" in m.text and "4567" in m.text
    assert watch["tick"](12) == 0 and watch["outbox"]().count() == 1  # har qo'ng'iroq haqida bir marta


def test_rec_watch_cut_short_recording(watch):
    ingest(watch["api"], watch["token"], [call(1, "+998901234567", kind=2, minutes=0, duration=300)])
    name = "20261019_090000.000+0000_out_+998901234567.ogg"  # yozuv 22 s / suhbat 300 s
    assert _upload(watch["api"], watch["token"], name=name, ended_sec=22, duration=22, sig="a", number="+998901234567").data["status"] == "ok"
    assert watch["tick"](11) == 1
    assert "yozuv 0:22" in watch["outbox"]().get().text


def test_rec_watch_ok_cases_do_not_alert(watch):
    ingest(watch["api"], watch["token"], [
        call(1, "+998901234567", kind=2, minutes=0, duration=300),   # to'liq yozilgan
        call(2, "+998907654321", kind=1, minutes=20, duration=60),   # kiruvchi: yozuv 1 s qisqa — normal
        call(3, "+998909999999", kind=2, minutes=40, duration=10),   # juda qisqa suhbat — e'tiborga olinmaydi
        call(4, "+998908888888", kind=3, minutes=60, duration=0),    # javobsiz
    ])
    _upload(watch["api"], watch["token"], ended_sec=305, duration=305, sig="a", number="+998901234567")
    _upload(watch["api"], watch["token"], ended_min=20, ended_sec=59, duration=59, sig="b", number="+998907654321")
    assert watch["tick"](90) == 0 and watch["outbox"]().count() == 0


def test_rec_watch_batches_and_cools_down(watch):
    ingest(watch["api"], watch["token"], [call(1, "+998901234567", kind=2, minutes=0, duration=120), call(2, "+998907654321", kind=1, minutes=3, duration=90)])
    assert watch["tick"](10) == 2 and watch["outbox"]().count() == 1  # ikkalasi bitta xabarda
    text = watch["outbox"]().get().text
    assert "4567" in text and "4321" in text
    ingest(watch["api"], watch["token"], [call(3, "+998906666666", kind=2, minutes=12, duration=100)])
    assert watch["tick"](20) == 0  # oldingi xabardan 10 daqiqa o'tmagan (now - COOLDOWN)


def test_recordings_list_shows_one_row_per_file(api, paired, make_user, media):
    """2026-11-20: telefon yozuv davom etayotganda uni bir necha marta yuklaydi — ro'yxatda eng uzun nusxa bitta qatorda (summary ham)."""
    ingest(api, paired, [call(1, "+998901234567", kind=2, duration=60)])
    name = "20261019_090000.000+0000_out_+998901234567.ogg"
    for sig, sec in (("a", 15), ("b", 25), ("c", 60), ("d", 40)):
        assert _upload(api, paired, name=name, ended_sec=sec, duration=sec, sig=sig, number="+998901234567", data=b"x" * (2000 + sec)).status_code == 200
    boss = make_user("BOSH_MENEJER")
    rows = api(boss).get("/api/v1/call-recordings/").data
    assert rows["count"] == 1 and rows["results"][0]["duration"] == 60
    assert api(boss).get("/api/v1/call-recordings/summary/").data == {"total": 1, "linked": 1, "unlinked": 0}
    from apps.calls.models import CallRecording

    assert CallRecording.objects.count() == 4  # bazada hammasi saqlangan


def test_ig_audio_caption_warns_when_recording_is_cut_short(api, paired, media, settings):
    """2026-11-22: 5:28 suhbat va 0:22 yozuv guruhga to'liq suhbat sifatida ketmasin — izohda ogohlantirish."""
    from apps.calls import ig_audio

    settings.IG_CALLS_CHAT_ID = -100777
    _ig_setup(api, paired, media)
    c = CallRecord.objects.get()
    assert "to'liq emas" not in ig_audio.caption(c, ig_audio.find_inbox(c))
    CallRecord.objects.filter(pk=c.pk).update(duration=328, audio_duration=22)
    c.refresh_from_db()
    text = ig_audio.caption(c, ig_audio.find_inbox(c))
    assert "Yozuv to'liq emas" in text and "0:22" in text and "5:28" in text

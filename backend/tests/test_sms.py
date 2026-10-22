"""SMS (2026-10-22): to'lov eslatmasi qolipi, navbat (administrator tasdig'i bilan), telefon olishi va natija, ruxsatlar."""

import datetime

import pytest
from django.utils import timezone

from apps.calls import services, sms
from apps.calls.models import CallDevice, SmsMessage, SmsTemplate
from apps.crm.models import Parent, Student
from apps.education.models import Contract, DueDismissal, Group
from apps.references.models import Course, CoursePrice, DayPattern, LessonTime, Room

pytestmark = pytest.mark.django_db
D = datetime.date
S = SmsMessage.State
MONTH = D(2026, 11, 1)
TEXT = "Hurmatli ota-ona, {talaba} ning {oy} oyi uchun {summa} so'm to'lov muddati {muddat}. Codial"


@pytest.fixture
def setup(branch, make_user, api):
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    CoursePrice.objects.create(branch=branch, course=course, effective_from=D(2026, 10, 1), price=1_300_000)
    g = Group.objects.create(
        branch=branch, course=course, day_pattern=DayPattern.objects.create(name="Dush,Chor,Jum", weekdays=[1, 3, 5]),
        time=LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"), teacher=make_user("USTOZ"),
        room=Room.objects.create(branch=branch, name="1", capacity=10), start_date=D(2026, 10, 1), number=1)
    parent = Parent.objects.create(branch=branch, first_name="Vali", last_name="Valiyev", phone="935556677")
    st = Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233", phone2="911112233", parent=parent)
    c = Contract.objects.create(branch=branch, student=st, course=course, group=g, number=1, start_date=D(2026, 10, 1))
    device = CallDevice.objects.create(name="Qabul", branch=branch)
    code = services.new_pair_code(device)
    token = api().post("/api/v1/calls/pair/", {"code": code}, format="json").data["token"]
    return {"contract": c, "device": device, "token": token, "user": make_user("ADMINISTRATOR_HISOBCHI"), "branch": branch}


def send(api, user, contract_ids, **extra):
    return api(user).post("/api/v1/sms/dues/", {"contracts": [str(i) for i in contract_ids], "month": "2026-11", "text": TEXT, **extra}, format="json")


def test_template_helpers():
    assert sms.plain("Toʻlov ‘muddati’ «10»") == "To'lov 'muddati' \"10\""
    assert sms.segments("a" * 160) == 1 and sms.segments("a" * 161) == 2
    assert sms.segments("я" * 70) == 1 and sms.segments("я" * 71) == 2
    with pytest.raises(Exception, match="Noma'lum"):
        sms.check_template("Salom {foo}")


def test_queue_all_numbers_with_rendered_text(setup, api):
    r = send(api, setup["user"], [setup["contract"].pk])
    assert r.status_code == 201, r.data
    assert r.data["messages"] == 3 and r.data["contracts"] == 1
    msgs = SmsMessage.objects.order_by("recipient")
    assert {m.phone for m in msgs} == {"901112233", "911112233", "935556677"}
    assert msgs[0].text == "Hurmatli ota-ona, Ali Valiyev ning noyabr oyi uchun 1 300 000 so'm to'lov muddati 10.11. Codial"
    assert all(m.status == S.QUEUED and m.device_id == setup["device"].pk for m in msgs)
    # takror bosilsa — shu oy olganlarga yana ketmaydi
    again = send(api, setup["user"], [setup["contract"].pk])
    assert again.data["messages"] == 0 and again.data["skipped_sent"] == 3


def test_preview_does_not_create(setup, api):
    r = send(api, setup["user"], [setup["contract"].pk], preview=True)
    assert r.status_code == 200 and r.data["messages"] == 3 and "1 300 000" in r.data["sample"]
    assert not SmsMessage.objects.exists()


def test_paid_or_dismissed_skipped(setup, api):
    DueDismissal.objects.create(contract=setup["contract"], month=MONTH)
    r = send(api, setup["user"], [setup["contract"].pk])
    assert r.data["messages"] == 0 and r.data["paid"] == 1


def test_no_device(setup, api):
    CallDevice.objects.update(status="Nofaol")
    r = send(api, setup["user"], [setup["contract"].pk])
    assert r.data["messages"] == 0 and r.data["no_device"] == [setup["branch"].name]


def test_phone_takes_and_reports(setup, api):
    send(api, setup["user"], [setup["contract"].pk])
    auth = {"HTTP_AUTHORIZATION": f"Device {setup['token']}"}
    out = api().get("/api/v1/calls/sms/outbox/", **auth).data["messages"]
    assert len(out) == 3 and out[0]["phone"].startswith("+998")
    assert SmsMessage.objects.filter(status=S.SENDING).count() == 3
    assert api().get("/api/v1/calls/sms/outbox/", **auth).data["messages"] == []  # ikkinchi marta berilmaydi
    res = [{"id": out[0]["id"], "ok": True}, {"id": out[1]["id"], "ok": False, "error": "Signal yo'q"}]
    assert api().post("/api/v1/calls/sms/report/", {"results": res}, format="json", **auth).data["updated"] == 2
    assert SmsMessage.objects.get(pk=out[0]["id"]).status == S.SENT
    failed = SmsMessage.objects.get(pk=out[1]["id"])
    assert failed.status == S.FAILED and failed.error == "Signal yo'q"
    # javob kelmagani 30 daqiqadan keyin «Xato» (qayta yuborilmaydi)
    SmsMessage.objects.filter(status=S.SENDING).update(taken_at=timezone.now() - datetime.timedelta(minutes=31))
    api().get("/api/v1/calls/sms/outbox/", **auth)
    assert SmsMessage.objects.filter(status=S.FAILED).count() == 2
    # qayta yuborish
    r = api(setup["user"]).post(f"/api/v1/sms/{failed.pk}/retry/")
    assert r.status_code == 200 and r.data["status"] == S.QUEUED
    assert api().get("/api/v1/calls/sms/outbox/").status_code == 401


def test_debtors_month_shows_sms_status(setup, api):
    send(api, setup["user"], [setup["contract"].pk])
    r = api(setup["user"]).get("/api/v1/debtors/month/?month=2026-11")
    row = next(x for x in r.data["results"] if x["id"] == str(setup["contract"].pk))
    assert row["sms"]["n"] == 3 and row["sms"]["queued"] == 3


def test_permissions_and_templates(setup, api, make_user):
    assert send(api, make_user("HISOBCHI"), [setup["contract"].pk]).status_code == 403
    assert send(api, make_user("USTOZ"), [setup["contract"].pk]).status_code == 403
    admin = make_user("ADMINISTRATOR")
    r = api(admin).post("/api/v1/sms-templates/", {"branch": str(setup["branch"].pk), "name": "To'lov", "text": "Toʻlov {summa}"}, format="json")
    assert r.status_code == 201, r.data
    assert SmsTemplate.objects.get().text == "To'lov {summa}"
    bad = api(admin).post("/api/v1/sms-templates/", {"branch": str(setup["branch"].pk), "name": "X", "text": "{nimadir}"}, format="json")
    assert bad.status_code == 400


def test_cancel_queued(setup, api):
    send(api, setup["user"], [setup["contract"].pk])
    r = api(setup["user"]).post("/api/v1/sms/cancel-all/")
    assert r.data["cancelled"] == 3 and not SmsMessage.objects.filter(status=S.QUEUED).exists()


def test_card_history_and_stats(setup, api):
    from apps.finance.models import Payment

    c = setup["contract"]
    send(api, setup["user"], [c.pk])
    SmsMessage.objects.filter(phone="901112233").update(status=S.SENT, sent_at=timezone.now())
    SmsMessage.objects.filter(phone="911112233").update(status=S.FAILED, error="Tarmoq yo'q")
    Payment.objects.create(branch=c.branch, contract=c, group=c.group, number=1, date=timezone.localdate(), amount=500_000)
    card = api(setup["user"]).get(f"/api/v1/students/{c.student_id}/calls/").data
    assert card["allowed"] and card["sms"]["count"] == 3 and card["sms"]["results"][0]["text"].startswith("Hurmatli")
    st = api(setup["user"]).get("/api/v1/sms/summary/").data
    assert st["sent"] == 1 and st["failed"] == 1 and st["queued"] == 1 and st["students"] == 1
    assert st["paid_after"] == 1 and st["paid_after_sum"] == 500_000
    assert st["by_recipient"] == [{"label": "Talaba", "n": 1}] and st["by_day"][0]["sent"] == 1


def inbox(api, token, msgs):
    return api().post("/api/v1/calls/sms/inbox/", {"messages": msgs}, format="json", HTTP_AUTHORIZATION=f"Device {token}")


def test_incoming_sms_matched_filtered_idempotent(setup, api):
    t = int(timezone.now().timestamp() * 1000)
    msgs = [{"id": 1, "date": t, "address": "+998901112233", "body": "Ertaga to'layman"},
            {"id": 2, "date": t, "address": "+998935556677", "body": "Rahmat"},
            {"id": 3, "date": t, "address": "UzCard", "body": "Kod: 1234"},
            {"id": 4, "date": t, "address": "900", "body": "Balans"},
            {"id": 5, "date": t, "address": "+998977776655", "body": "Kurs narxi qancha?"}]
    r = inbox(api, setup["token"], msgs)
    assert r.status_code == 200 and r.data == {"accepted": 3, "duplicates": 0, "skipped": 2, "errors": 0}
    assert inbox(api, setup["token"], msgs).data["accepted"] == 0  # takror
    inc = SmsMessage.objects.filter(direction="Kiruvchi")
    st = inc.get(phone="901112233")
    assert st.student == setup["contract"].student and st.contract == setup["contract"] and st.recipient == "Talaba"
    assert inc.get(phone="935556677").recipient == "Vasiy"
    assert inc.get(phone="977776655").student is None
    # kartochka: yozishma, jurnal filtri, statistika
    card = api(setup["user"]).get(f"/api/v1/students/{setup['contract'].student_id}/calls/").data["sms"]
    assert card["incoming"] == 2
    lst = api(setup["user"]).get("/api/v1/sms/?dir=Kiruvchi&known=0").data
    assert lst["count"] == 1 and lst["results"][0]["phone"] == "977776655"
    s = api(setup["user"]).get("/api/v1/sms/summary/").data
    assert s["incoming"] == 3 and s["incoming_known"] == 2 and s["incoming_unknown"] == 1 and s["total"] == 0


def test_reply_after_reminder_counted(setup, api):
    send(api, setup["user"], [setup["contract"].pk])
    SmsMessage.objects.filter(direction="Chiquvchi").update(status=S.SENT, sent_at=timezone.now())
    later = int((timezone.now() + datetime.timedelta(minutes=5)).timestamp() * 1000)
    inbox(api, setup["token"], [{"id": 9, "date": later, "address": "911112233", "body": "Xo'p"}])
    assert api(setup["user"]).get("/api/v1/sms/summary/").data["replied"] == 1

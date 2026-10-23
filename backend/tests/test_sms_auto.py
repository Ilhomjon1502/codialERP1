"""Avtomatik SMS qoidalari (2026-10-23): lid, shartnoma, oy boshi, oldindan to'lov bonusi, sababsiz kelmagan; muammo haqida ogohlantirish."""

import datetime

import pytest
from django.utils import timezone

from apps.calls import auto_sms, services, sms
from apps.calls.models import CallDevice, SmsMessage, SmsRule
from apps.crm.models import Parent, Student
from apps.education.models import Attendance, Contract, Group
from apps.finance.models import Payment
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import Course, CoursePrice, DayPattern, DiscountType, LeadSource, LessonTime, Room
from tests.test_crm import new_lead

pytestmark = pytest.mark.django_db
D = datetime.date
R, K = SmsRule.Key, SmsMessage.Kind
TODAY = D(2026, 11, 25)


@pytest.fixture
def env(branch, make_user, api):
    course = Course.objects.create(name="Kompyuter savodxonligi")
    course.branches.set([branch])
    CoursePrice.objects.create(branch=branch, course=course, effective_from=D(2026, 10, 1), price=1_300_000)
    g = Group.objects.create(
        branch=branch, course=course, day_pattern=DayPattern.objects.create(name="Dush,Chor,Jum", weekdays=[1, 3, 5]),
        time=LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"), teacher=make_user("USTOZ"),
        room=Room.objects.create(branch=branch, name="1", capacity=10), start_date=D(2026, 10, 1), number=192)
    device = CallDevice.objects.create(name="Qabul", branch=branch)
    token = api().post("/api/v1/calls/pair/", {"code": services.new_pair_code(device)}, format="json").data["token"]
    rules = {r.key: r for r in auto_sms.ensure_rules([branch])}

    def enable(key, **kw):
        r = rules[key]
        for k, v in {"enabled": True, "enabled_at": timezone.now() - datetime.timedelta(days=30), **kw}.items():
            setattr(r, k, v)
        r.save()
        return r

    def student(i=1, parent=True):
        par = Parent.objects.create(branch=branch, first_name="Vali", last_name="Valiyev", phone=f"93555667{i}") if parent else None
        return Student.objects.create(branch=branch, first_name="Muhsinjon", last_name=f"Karimov{i}", phone1=f"90111223{i}", phone2=f"91111223{i}", parent=par)

    def contract(st, **kw):
        return Contract.objects.create(branch=branch, student=st, course=course, group=g, number=Contract.objects.count() + 1,
                                       start_date=kw.pop("start_date", D(2026, 10, 1)), **kw)

    return {"branch": branch, "course": course, "group": g, "rules": rules, "enable": enable, "student": student, "contract": contract,
            "device": device, "token": token, "user": make_user("ADMINISTRATOR_HISOBCHI"), "make_user": make_user}


@pytest.fixture
def refs(env):
    return {"course": env["course"], "source": LeadSource.objects.create(name="Instagram"), "pattern": env["group"].day_pattern,
            "time": env["group"].time}


def texts():
    return list(SmsMessage.objects.order_by("created_at").values_list("text", flat=True))


def test_rules_created_disabled_and_nothing_sent_by_default(env, api, refs):
    assert {r.key for r in env["rules"].values()} == set(R.values) and not any(r.enabled for r in env["rules"].values())
    r = api(env["user"]).post("/api/v1/leads/", new_lead(refs), format="json")
    assert r.status_code == 201 and not SmsMessage.objects.exists()


def test_lead_sms_every_new_lead_to_all_numbers(env, api, refs):
    env["enable"](R.LEAD)
    c = api(env["user"])
    assert c.post("/api/v1/leads/", new_lead(refs), format="json").status_code == 201
    msgs = SmsMessage.objects.filter(kind=K.LEAD)
    assert sorted(msgs.values_list("phone", flat=True)) == ["901233323", "911112233"]
    assert set(texts()) == {"Codialga xush kelibsiz, AyTi ta'limini biz bilan o'rganing!"}
    assert all(m.status == "Navbatda" and m.lead_id and m.student_id for m in msgs)
    # boshqa lid — yana ketadi (har yangi lidga)
    c.post("/api/v1/leads/", new_lead(refs, first_name="Boshqa", last_name="Lid", phone1="931112233", phone2="941112233"), format="json")
    assert SmsMessage.objects.filter(kind=K.LEAD).count() == 4


def test_contract_sms_group_label_active_and_planned_not_ended(env):
    env["enable"](R.CONTRACT)
    st = env["student"](1)
    c = env["contract"](st)
    auto_sms.contract_created(c)
    assert set(texts()) == {"Muhsinjon Kompyuter savodxonligi 192 guruhiga qo'shildingiz."}
    assert SmsMessage.objects.count() == 3  # 1-, 2-telefon va vasiy
    auto_sms.contract_created(c)  # takror — ketmaydi
    assert SmsMessage.objects.count() == 3
    planned = env["contract"](env["student"](2), start_date=timezone.localdate() + datetime.timedelta(days=5))
    auto_sms.contract_created(planned)
    assert SmsMessage.objects.count() == 6
    ended = env["contract"](env["student"](3), start_date=D(2026, 1, 1), end_date=D(2026, 2, 1))
    auto_sms.contract_created(ended)
    assert SmsMessage.objects.count() == 6


def test_contract_sms_through_api_hook(env, api):
    env["enable"](R.CONTRACT)
    st = env["student"](4)
    r = api(env["user"]).post("/api/v1/contracts/", {"student": str(st.pk), "course": str(env["course"].pk), "group": str(env["group"].pk),
                                                      "start": "2026-10-01", "type": "Pullik"}, format="json")
    assert r.status_code == 201, r.data
    assert SmsMessage.objects.filter(kind=K.CONTRACT).count() == 3


def test_month_start_only_unpaid_active_paid_contracts(env):
    rule = env["enable"](R.MONTH_START)
    unpaid = env["contract"](env["student"](1))
    paid = env["contract"](env["student"](2))
    Payment.objects.create(branch=env["branch"], contract=paid, group=env["group"], number=1, date=D(2026, 11, 3), amount=1_300_000)
    grant = env["contract"](env["student"](3), type="Grant")
    ended = env["contract"](env["student"](4), start_date=D(2026, 1, 1), end_date=D(2026, 9, 1))
    n = auto_sms.run_rule(rule, D(2026, 11, 1))
    assert n == 3 and set(SmsMessage.objects.values_list("contract_id", flat=True)) == {unpaid.pk}
    assert texts()[0] == "Codial ichki tartib qoidalariga ko'ra oylik to'lovlarni shu oyning 10-sanasidan kechiktirmay to'lash kerak."
    assert auto_sms.run_rule(rule, D(2026, 11, 1)) == 0  # takror ketmaydi
    assert grant.pk and ended.pk


def test_month_start_skips_numbers_that_got_manual_reminder(env):
    rule = env["enable"](R.MONTH_START)
    c = env["contract"](env["student"](1))
    sms.queue_dues(env["user"], [c.pk], D(2026, 11, 1), "Qo'lda eslatma {summa}")
    assert SmsMessage.objects.filter(kind=K.DUE).count() == 3
    assert auto_sms.run_rule(rule, D(2026, 11, 1)) == 0


def test_prepay_bonus_amount_days_left_and_prepaid_skipped(env):
    DiscountType.objects.create(name="Avvaldan to'lov", max_amount=75_000)
    rule = env["enable"](R.PREPAY_BONUS)
    todo = env["contract"](env["student"](1))
    done = env["contract"](env["student"](2))
    Payment.objects.create(branch=env["branch"], contract=done, group=env["group"], number=1, date=D(2026, 11, 20), amount=3_000_000)  # kredit
    n = auto_sms.run_rule(rule, TODAY)
    assert n == 3 and set(SmsMessage.objects.values_list("contract_id", flat=True)) == {todo.pk}
    t = texts()[0]
    assert "75 000 so'm bonus" in t and "oy tugashiga 5 kun qoldi" in t and "dekabr oyi uchun" in t
    assert auto_sms.run_rule(rule, TODAY) == 0  # takror ketmaydi
    # 31 kunlik oy: 6 kun qoladi
    ctx = [p.ctx for p in auto_sms.plan_prepay_bonus(rule, D(2026, 10, 25))]
    assert ctx and ctx[0]["kun"] == "6"


def test_prepay_bonus_without_discount_type_alerts_and_sends_nothing(env, django_capture_on_commit_callbacks):
    rule = env["enable"](R.PREPAY_BONUS)
    env["contract"](env["student"](1))
    TelegramLink.objects.create(user=env["make_user"]("BOSH_MENEJER"), chat_id=123)
    with django_capture_on_commit_callbacks(execute=True):
        assert auto_sms.run_rule(rule, TODAY) == 0
    assert not SmsMessage.objects.exists() and Outbox.objects.filter(event="sms_problem").exists()


def attendance(env, contract, date, status="X", **kw):
    return Attendance.objects.create(branch=env["branch"], group=env["group"], course=env["course"], contract=contract, date=date, status=status,
                                     teacher=env["group"].teacher, day_pattern=env["group"].day_pattern, **kw)


def test_absence_sms_yesterday_real_date_talked_and_three_day_limit(env):
    rule = env["enable"](R.ABSENCE)
    a = env["contract"](env["student"](1))
    attendance(env, a, D(2026, 11, 24))                       # kecha, sababsiz
    b = env["contract"](env["student"](2))
    attendance(env, b, D(2026, 11, 24), status="0")           # sababli — ketmaydi
    c = env["contract"](env["student"](3))
    attendance(env, c, D(2026, 11, 24), contact_status="Gaplashildi")  # administrator gaplashgan — ketmaydi
    d = env["contract"](env["student"](4))
    attendance(env, d, D(2026, 11, 22))                       # 3 kun oldin, kech olingan — haqiqiy sana bilan
    n = auto_sms.run_rule(rule, TODAY)
    assert n == 6
    by_student = {m.student_id: m.text for m in SmsMessage.objects.all()}
    assert by_student[a.student_id] == "Kecha Muhsinjon darsga kelmagan ko'rinadi, aniqlik kiritish uchun 998204432 ga telefon qiling."
    assert by_student[d.student_id].startswith("22.11 kuni Muhsinjon darsga kelmagan")
    assert b.student_id not in by_student and c.student_id not in by_student
    # ertasi kuni — yana besabab bo'lsa ham, 3 kunda bittadan ko'p emas
    attendance(env, a, D(2026, 11, 25))
    assert auto_sms.run_rule(rule, D(2026, 11, 26)) == 0


def test_absence_before_enabled_not_sent_and_status_changed_not_sent(env):
    rule = env["enable"](R.ABSENCE, enabled_at=timezone.make_aware(datetime.datetime(2026, 11, 25, 12, 0)))
    a = env["contract"](env["student"](1))
    attendance(env, a, D(2026, 11, 20))  # yoqilishdan ancha oldin
    assert auto_sms.run_rule(rule, TODAY) == 0
    attendance(env, a, D(2026, 11, 24)).delete()
    row = attendance(env, a, D(2026, 11, 24))
    Attendance.objects.filter(pk=row.pk).update(status="0")  # ustoz keyin sababli qildi
    assert auto_sms.run_rule(rule, TODAY) == 0


def test_tick_runs_once_per_day_at_time_and_day(env):
    rule = env["enable"](R.MONTH_START)
    env["contract"](env["student"](1))
    tz = timezone.get_current_timezone()
    at = lambda day, h: timezone.make_aware(datetime.datetime(2026, 11, day, h, 0), tz)  # noqa: E731
    assert auto_sms.tick(at(1, 9)) == 0       # vaqti kelmagan
    assert auto_sms.tick(at(2, 11)) == 0      # boshqa kun
    assert auto_sms.tick(at(1, 10)) == 3
    rule.refresh_from_db()
    assert rule.last_run_on == D(2026, 11, 1) and auto_sms.tick(at(1, 12)) == 0


def test_disabled_rule_does_nothing_and_text_validation(env, api):
    c = api(env["user"])
    rules = c.get("/api/v1/sms-rules/").data
    assert len(rules) == 5 and all(not r["enabled"] and r["text"] for r in rules)
    absence = next(r for r in rules if r["key"] == "absence")
    bad = c.patch(f"/api/v1/sms-rules/{absence['id']}/", {"text": "{bonus} so'm"}, format="json")
    assert bad.status_code == 400 and "ishlatib bo'lmaydigan" in str(bad.data)
    ok = c.patch(f"/api/v1/sms-rules/{absence['id']}/", {"text": "{ism} kelmadi", "enabled": True, "send_time": "07:30"}, format="json")
    assert ok.status_code == 200 and ok.data["enabled"] and ok.data["send_time"] == "07:30"
    assert SmsRule.objects.get(pk=absence["id"]).enabled_at is not None
    assert auto_sms.tick(timezone.make_aware(datetime.datetime(2026, 11, 25, 6, 0))) == 0


def test_preview_lists_recipients_without_sending(env, api):
    rule = env["enable"](R.MONTH_START, enabled=False)
    env["contract"](env["student"](1))
    out = api(env["user"]).get(f"/api/v1/sms-rules/{rule.pk}/preview/").data
    assert out["scheduled"] and out["students"] == 1 and out["messages"] == 3 and out["real"] and "Muhsinjon Karimov1" in out["names"]
    assert not SmsMessage.objects.exists()
    lead_rule = env["rules"][R.LEAD]
    out = api(env["user"]).get(f"/api/v1/sms-rules/{lead_rule.pk}/preview/").data
    assert not out["scheduled"] and out["sample"].startswith("Codialga xush kelibsiz")


def test_rules_permissions(env, api):
    c = api(env["make_user"]("HISOBCHI"))  # sms: faqat ko'rish
    rid = c.get("/api/v1/sms-rules/").data[0]["id"]
    assert c.patch(f"/api/v1/sms-rules/{rid}/", {"enabled": True}, format="json").status_code == 403
    assert api(env["make_user"]("USTOZ")).get("/api/v1/sms-rules/").status_code == 403


def test_no_device_alerts_bm_once_a_day(env, django_capture_on_commit_callbacks):
    CallDevice.objects.all().delete()
    env["enable"](R.CONTRACT)
    TelegramLink.objects.create(user=env["make_user"]("BOSH_MENEJER"), chat_id=555)
    st = env["student"](1)
    with django_capture_on_commit_callbacks(execute=True):
        auto_sms.contract_created(env["contract"](st))
    with django_capture_on_commit_callbacks(execute=True):
        auto_sms.contract_created(env["contract"](env["student"](2)))
    assert not SmsMessage.objects.exists() and Outbox.objects.filter(event="sms_problem").count() == 1


def test_check_problems_stuck_failed_undelivered_once(env, django_capture_on_commit_callbacks):
    TelegramLink.objects.create(user=env["make_user"]("BOSH_MENEJER"), chat_id=777)
    now = timezone.now()
    old = now - datetime.timedelta(minutes=30)

    def sms_row(phone, **kw):
        m = SmsMessage.objects.create(branch=env["branch"], device=env["device"], phone=phone, text="x", **kw)
        SmsMessage.objects.filter(pk=m.pk).update(created_at=old)
        return m

    sms_row("901111111")                                                   # navbatda qotib qolgan
    sms_row("902222222", status="Xato", error="Tarmoq yo'q")               # xato
    sms_row("903333333", status="Yuborildi", delivery="Yetkazilmadi")      # yetmadi
    sms_row("904444444", status="Yuborildi", delivery="Yetkazildi")        # yaxshi
    with django_capture_on_commit_callbacks(execute=True):
        assert auto_sms.check_problems(now) == 3
    text = Outbox.objects.get(event="sms_problem").text
    assert "1 ta SMS 15 daqiqadan beri navbatda" in text and "Tarmoq yo'q" in text and "yetmadi" in text
    with django_capture_on_commit_callbacks(execute=True):
        assert auto_sms.check_problems(now + datetime.timedelta(minutes=20)) == 0  # har SMS haqida bir marta
    assert Outbox.objects.filter(event="sms_problem").count() == 1

"""M3: guruhlar, shartnomalar, davomat, qarz va KPI (CLAUDE.md 7.4, 8, 9)."""

import datetime
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.core.models import AuditLog
from apps.crm.models import Lead, Student
from apps.education import calc
from apps.education.models import Attendance, Contract, Group, MakeupRequest
from apps.payroll.models import KPIRate
from apps.references.models import Course, CoursePrice, DayPattern, LeadSource, LessonFrequency, LessonTime, Room

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
MONTH = TODAY.replace(day=1)
PREV = (MONTH - datetime.timedelta(days=1)).replace(day=1)


@pytest.fixture
def world(branch, make_user):
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    every_day = DayPattern.objects.create(name="", weekdays=[1, 2, 3, 4, 5, 6, 7])
    other_wd = (TODAY.isoweekday() % 7) + 1
    not_today = DayPattern.objects.create(name="", weekdays=[other_wd])
    time = LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00")
    room = Room.objects.create(branch=branch, name="1-xona", capacity=4)
    CoursePrice.objects.create(branch=branch, course=course, effective_from=PREV, price=600000)
    for m in (PREV, MONTH):
        f = LessonFrequency.objects.create(branch=branch, day_pattern=every_day, year=m.year, month=m.month, frequency=12, status="Tasdiqlangan")
        f.courses.set([course])
    teacher = make_user("USTOZ")
    supporter = make_user("YORDAMCHI")
    group = Group.objects.create(branch=branch, course=course, day_pattern=every_day, time=time, teacher=teacher, supporter=supporter, room=room,
                                 start_date=PREV, number=1)
    students = [Student.objects.create(branch=branch, first_name=f"Talaba{i}", last_name="Aliyev", phone1=f"90000000{i}") for i in range(3)]
    contracts = [Contract.objects.create(branch=branch, student=s, course=course, group=group, number=i + 1, start_date=PREV) for i, s in enumerate(students)]
    return {"course": course, "pattern": every_day, "not_today": not_today, "time": time, "room": room, "teacher": teacher, "supporter": supporter,
            "group": group, "students": students, "contracts": contracts, "branch": branch}


def rate(w, user, role_type, kind="O'zgarmas", fixed=0, percent=0, month=PREV):
    return KPIRate.objects.create(branch=w["branch"], user=user, role_type=role_type, course=w["course"], effective_from=month, type=kind,
                                  fixed_amount=fixed, percent=percent)


def take(c, w, marks=None, date=TODAY, **extra):
    body = {"group": str(w["group"].pk), "date": date.isoformat(), **extra}
    if marks is not None:
        body["marks"] = [{"contract": str(ct.pk), "status": st, **({"comment": cm} if cm else {})} for ct, st, cm in marks]
    return c.post("/api/v1/attendance/take/", body, format="json")


# ------------------------------------------------------------------ hisob-kitob (8.2, 8.3)

def test_debt_and_kpi_formulas(api, make_user, world):
    w = world
    rate(w, w["teacher"], "USTOZ", fixed=120000)
    rate(w, w["supporter"], "YORDAMCHI", kind="Foiz", percent=30)
    r = take(api(w["teacher"]), w, [(w["contracts"][0], "1", ""), (w["contracts"][1], "X", "")])
    assert r.status_code == 200, r.content
    r = take(api(make_user("ADMINISTRATOR")), w, [(w["contracts"][2], "0", "kasal")])  # Sababli — administrator (ustoz qo'ya olmaydi)
    assert r.status_code == 200, r.content
    rows = {a.contract_id: a for a in Attendance.objects.all()}
    came, absent, excused = (rows[c.pk] for c in w["contracts"])
    assert came.student_debt == 50000 and absent.student_debt == 50000 and excused.student_debt == 50000  # dars bo'ldimi — qarz yoziladi
    assert came.teacher_kpi == 10000 and excused.teacher_kpi == 10000 and absent.teacher_kpi == 0  # besabab — KPI yo'q
    assert came.supporter_kpi == 15000  # 30% × 600 000 / 12
    assert came.supporter_id == w["supporter"].pk and came.contact_status == "" and absent.contact_status == "Bog'lanishga"


def test_grant_nofaol_rounding_and_missing_frequency(world):
    w = world
    c0 = w["contracts"][0]
    c0.type = "Grant"
    c0.save()
    a = Attendance(branch=w["branch"], group=w["group"], course=w["course"], contract=c0, day_pattern=w["pattern"], date=TODAY, status="1", teacher=w["teacher"])
    calc.calculate(a)
    assert a.student_debt == 0 and a.teacher_kpi == 0
    LessonFrequency.objects.filter(year=MONTH.year, month=MONTH.month).update(frequency=7)
    b = Attendance(branch=w["branch"], group=w["group"], course=w["course"], contract=w["contracts"][1], day_pattern=w["pattern"], date=TODAY, status="1", teacher=w["teacher"])
    calc.calculate(b)
    assert b.student_debt == Decimal("85714")  # 600 000 / 7 = 85 714,28 → ROUND_HALF_UP
    assert b.calc_note == calc.NOTE_NO_RATE and b.teacher_kpi == 0
    b.status = "-"
    calc.calculate(b)
    assert b.student_debt == 0
    LessonFrequency.objects.update(status="Taklif")
    b.status = "1"
    calc.calculate(b)
    assert b.student_debt is None and b.teacher_kpi is None and calc.NOTE_NO_FREQ in b.calc_note  # «hisoblanmagan», 0 emas


def test_recalculation_on_frequency_price_and_contract_type(api, make_user, world):
    w = world
    take(api(w["teacher"]), w, [(c, "1", "") for c in w["contracts"]])
    f = LessonFrequency.objects.get(year=MONTH.year, month=MONTH.month)
    f.status = "Taklif"
    f.save()
    call_command("recalculate", month=f"{MONTH:%Y-%m}")
    assert Attendance.objects.filter(student_debt__isnull=True).count() == 3
    bm = api(make_user("BOSH_MENEJER"))
    assert bm.post(f"/api/v1/lesson-frequencies/{f.pk}/approve/").status_code == 200
    assert set(Attendance.objects.values_list("student_debt", flat=True)) == {Decimal(50000)}
    r = bm.post("/api/v1/course-prices/", {"branch": str(w["branch"].pk), "course": str(w["course"].pk), "effective_from": f"{MONTH:%Y-%m}", "price": 720000}, format="json")
    assert r.status_code in (200, 201)
    assert set(Attendance.objects.values_list("student_debt", flat=True)) == {Decimal(60000)}
    c0 = w["contracts"][0]
    assert bm.patch(f"/api/v1/contracts/{c0.pk}/", {"type": "Grant"}, format="json").status_code == 200
    assert Attendance.objects.get(contract=c0).student_debt == 0
    assert AuditLog.objects.filter(model="Shartnoma", detail__contains="qayta hisoblandi").exists()


# ------------------------------------------------------------------ guruhlar

def test_group_create_number_and_rules(api, make_user, world):
    w = world
    adm = api(make_user("ADMINISTRATOR"))
    body = {"course": str(w["course"].pk), "pattern": str(w["pattern"].pk), "time": str(w["time"].pk), "teacher": str(w["teacher"].pk),
            "room": str(w["room"].pk), "start": TODAY.isoformat()}
    r = adm.post("/api/v1/groups/", body, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["number"] == 2 and r.json()["name"] == "Frontend / #2" and r.json()["status"] == "Faol"
    assert adm.post("/api/v1/groups/", {**body, "end": TODAY.isoformat()}, format="json").json()["end"] == ["Boshlanish sanadan kichik bo'lolmaydi!"]
    assert adm.post("/api/v1/groups/", {**body, "teacher": str(w["supporter"].pk)}, format="json").status_code == 400
    assert adm.post("/api/v1/groups/", {**body, "supporter": str(w["teacher"].pk)}, format="json").status_code == 400
    other = Course.objects.create(name="Backend")
    other.branches.set([w["branch"]])
    gid = r.json()["id"]
    assert api(make_user("BOSH_MENEJER")).patch(f"/api/v1/groups/{gid}/", {"course": str(other.pk)}, format="json").status_code == 403
    assert api(make_user("ADMIN")).patch(f"/api/v1/groups/{gid}/", {"course": str(other.pk)}, format="json").status_code == 200
    # shartnomasi bor guruhda kurs o'zgarmaydi
    assert api(make_user("ADMIN")).patch(f"/api/v1/groups/{w['group'].pk}/", {"course": str(other.pk)}, format="json").status_code == 400


def test_group_status_fill_and_teacher_scope(api, make_user, world):
    w = world
    d = api(make_user("BOSH_MENEJER")).get("/api/v1/groups/?status=Faol").json()
    assert len(d) == 1 and d[0]["fill"] == {"n": 3, "cap": 4, "pct": 0.75, "free": 1, "label": "O'rtacha", "cls": "orange"}
    stranger = make_user("USTOZ")
    assert api(stranger).get("/api/v1/groups/").json() == []
    assert len(api(w["supporter"]).get("/api/v1/groups/").json()) == 1
    assert api(stranger).get("/api/v1/contracts/").json()["count"] == 0
    assert api(w["teacher"]).get("/api/v1/contracts/").json()["count"] == 3


# ------------------------------------------------------------------ shartnomalar

def test_contract_create_rules(api, make_user, world):
    w = world
    adm = api(make_user("ADMINISTRATOR"))
    st = Student.objects.create(branch=w["branch"], first_name="Yangi", last_name="Talaba", phone1="911111111")
    body = {"student": str(st.pk), "course": str(w["course"].pk), "group": str(w["group"].pk), "start": TODAY.isoformat()}
    assert adm.post("/api/v1/contracts/", {**body, "type": "Grant"}, format="json").status_code == 403
    assert adm.post("/api/v1/contracts/", {**body, "end": TODAY.isoformat()}, format="json").json()["stop_reason"]
    r = adm.post("/api/v1/contracts/", body, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["number"] == 4 and r.json()["type"] == "Pullik" and r.json()["status"] == "Faol" and r.json()["name"] == "Yangi Talaba №4"
    assert adm.post("/api/v1/contracts/", body, format="json").json()["group"] == ["Bu talabaning shu guruhda faol shartnomasi bor"]
    other = Course.objects.create(name="Backend")
    other.branches.set([w["branch"]])
    assert adm.post("/api/v1/contracts/", {**body, "course": str(other.pk)}, format="json").status_code == 400
    # yopish: sabab bilan
    cid = r.json()["id"]
    closed = adm.patch(f"/api/v1/contracts/{cid}/", {"end": (TODAY - datetime.timedelta(days=1)).isoformat(), "stop_reason": "Moliyaviy qiyinchilik"}, format="json")
    assert closed.status_code == 400  # tugash < boshlanish
    ok = adm.patch(f"/api/v1/contracts/{cid}/", {"end": TODAY.isoformat(), "stop_reason": "Moliyaviy qiyinchilik"}, format="json")
    assert ok.status_code == 200 and ok.json()["stop_reason"] == "Moliyaviy qiyinchilik"


def test_contract_balance_debtors_and_detail(api, make_user, world):
    w = world
    take(api(w["teacher"]), w, [(w["contracts"][0], "1", ""), (w["contracts"][1], "X", "")])
    Contract.objects.filter(pk=w["contracts"][2].pk).update(opening_balance=-20000)
    bm = api(make_user("BOSH_MENEJER"))
    d = bm.get("/api/v1/debtors/").json()
    assert d["count"] == 2 and d["total"] == 100000
    detail = bm.get(f"/api/v1/contracts/{w['contracts'][0].pk}/").json()
    assert detail["charged"] == 50000 and detail["balance"] == 50000 and len(detail["attendance"]) == 1
    assert api(make_user("USTOZ")).get("/api/v1/debtors/").status_code == 403
    lst = bm.get("/api/v1/contracts/?status=Faol&search=talaba1").json()
    assert lst["count"] == 1 and lst["results"][0]["balance"] == 50000


# ------------------------------------------------------------------ davomat olish

def test_take_rules_for_teacher(api, make_user, world):
    w = world
    t = api(w["teacher"])
    c0 = w["contracts"][0]
    assert take(api(make_user("USTOZ")), w, [(c0, "1", "")]).json()["group"] == ["Guruh topilmadi"]  # boshqa ustozga guruh ko'rinmaydi
    assert take(t, w, [(c0, "1", "")], date=TODAY - datetime.timedelta(days=1)).json()["date"] == ["Faqat bugunga davomat olish mumkin, xolos"]
    assert take(t, w, [(c0, "1", "")], date=TODAY + datetime.timedelta(days=1)).json()["date"] == ["Kelajak sana bilan davomat olib bo'lmaydi"]
    assert take(t, w, [(c0, "-", "")]).status_code == 403  # Nofaol — faqat menejerlar
    assert take(t, w, [(c0, "0", "kasal")]).status_code == 403  # ustoz faqat Keldi yoki Besabab (buyurtmachi qarori 2026-10-14)
    assert take(api(make_user("ADMINISTRATOR")), w, [(c0, "0", "")]).json()["comment"] == ["Sababli bo'lsa, sababini yozing"]
    assert sorted(t.get(f"/api/v1/attendance/take/?group={w['group'].pk}&date={TODAY}").json()["allowed"]) == ["1", "X"]
    assert take(api(w["supporter"]), w, [(c0, "1", "")]).status_code == 403  # yordamchi davomat olmaydi
    r = take(t, w, all=True)
    assert r.status_code == 200 and sum(1 for x in r.json()["rows"] if x["att"]) == 3
    assert take(t, w, [(c0, "X", "")]).status_code == 200  # bugungi belgini o'zgartirish mumkin
    assert Attendance.objects.get(contract=c0).status == "X" and Attendance.objects.count() == 3


def test_take_no_lesson_day_and_state(api, make_user, world):
    w = world
    g = w["group"]
    g.day_pattern = w["not_today"]
    g.save()
    s = api(make_user("BOSH_MENEJER")).get(f"/api/v1/attendance/take/?group={g.pk}&date={TODAY}").json()
    assert s["error"].startswith("Guruhning bu sanaga darsi yo'q") and s["rows"] == [] and s["nearest"]
    assert take(api(w["teacher"]), w, [(w["contracts"][0], "1", "")]).status_code == 400


def test_manager_past_dates_window_and_substitute(api, make_user, world):
    w = world
    rate(w, w["teacher"], "USTOZ", fixed=120000)
    sub = make_user("USTOZ")
    rate(w, sub, "USTOZ", fixed=240000)
    adm = api(make_user("ADMINISTRATOR"))
    c0, c1 = w["contracts"][:2]
    old = TODAY - datetime.timedelta(days=9)
    assert take(adm, w, [(c0, "1", "")], date=old).status_code == 403  # administrator — oxirgi 7 kun
    assert take(api(make_user("BOSH_MENEJER")), w, [(c0, "1", "")], date=old).status_code == 200
    r = take(adm, w, [(c1, "1", "")], date=TODAY - datetime.timedelta(days=2), sub_teacher=str(sub.pk))
    assert r.status_code == 200, r.content
    a = Attendance.objects.get(contract=c1)
    assert a.teacher_id == sub.pk and a.teacher_kpi == 20000  # KPI darsni o'tgan o'rindoshga
    assert take(api(make_user("FILIAL_MENEJERI")), w, [(c1, "1", "")], sub_teacher=str(sub.pk)).status_code == 403
    assert take(adm, w, [(c1, "1", "")], sub_teacher=str(w["teacher"].pk)).status_code == 400  # o'z ustozi o'rindosh emas


def test_contact_status_and_absent_list(api, make_user, world):
    w = world
    take(api(w["teacher"]), w, [(w["contracts"][0], "X", ""), (w["contracts"][1], "1", "")])
    a = Attendance.objects.get(contract=w["contracts"][0])
    adm = api(make_user("ADMINISTRATOR"))
    assert adm.patch(f"/api/v1/attendance/{a.pk}/", {"contact": "Gaplashildi"}, format="json").json()["comment"] == ["«Gaplashildi» bo'lsa izoh majburiy"]
    r = adm.patch(f"/api/v1/attendance/{a.pk}/", {"contact": "Gaplashildi", "comment": "Kasal ekan"}, format="json")
    assert r.status_code == 200 and r.json()["contact"] == "Gaplashildi"
    lst = adm.get(f"/api/v1/attendance/?month={TODAY:%Y-%m}&status=X,0").json()
    assert lst["count"] == 1 and lst["results"][0]["student_name"].startswith("Talaba0")
    came = Attendance.objects.get(contract=w["contracts"][1])
    assert adm.patch(f"/api/v1/attendance/{came.pk}/", {"contact": "Tushib bo'lmadi"}, format="json").status_code == 400


def test_makeup_flow(api, make_user, world):
    w = world
    rate(w, w["teacher"], "USTOZ", fixed=120000)
    t = api(w["teacher"])
    take(t, w, [(w["contracts"][0], "X", ""), (w["contracts"][1], "1", "")])
    a = Attendance.objects.get(contract=w["contracts"][0])
    assert a.teacher_kpi == 0
    body = {"attendance": str(a.pk), "makeup_date": TODAY.isoformat(), "comment": "Shanba kuni o'tdim"}
    assert api(make_user("USTOZ")).post("/api/v1/makeups/", body, format="json").status_code == 400  # ko'rinmaydi
    came = Attendance.objects.get(contract=w["contracts"][1])
    assert t.post("/api/v1/makeups/", {**body, "attendance": str(came.pk)}, format="json").status_code == 400
    r = t.post("/api/v1/makeups/", body, format="json")
    assert r.status_code == 201, r.content
    assert t.post("/api/v1/makeups/", body, format="json").json()["detail"] == "Bu dars uchun so'rov allaqachon yuborilgan"
    mid = r.json()["id"]
    assert t.post(f"/api/v1/makeups/{mid}/approve/").status_code == 403  # ustoz o'zi tasdiqlamaydi
    fm = api(make_user("FILIAL_MENEJERI"))
    assert fm.post(f"/api/v1/makeups/{mid}/approve/").status_code == 200
    a.refresh_from_db()
    assert a.status == "0" and a.teacher_kpi == 10000 and "Dars yetkazildi" in a.comment
    assert MakeupRequest.objects.get().status == "Tasdiqlandi"
    assert fm.post(f"/api/v1/makeups/{mid}/reject/", {"reason": "x"}, format="json").status_code == 400


def test_makeup_reject_needs_reason(api, make_user, world):
    w = world
    take(api(w["teacher"]), w, [(w["contracts"][0], "X", "")])
    a = Attendance.objects.get()
    mid = api(w["teacher"]).post("/api/v1/makeups/", {"attendance": str(a.pk), "makeup_date": TODAY.isoformat(), "comment": "o'tdim"}, format="json").json()["id"]
    adm = api(make_user("ADMINISTRATOR"))
    assert adm.post(f"/api/v1/makeups/{mid}/reject/", {}, format="json").status_code == 400
    r = adm.post(f"/api/v1/makeups/{mid}/reject/", {"reason": "Tasdiqlanmadi"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "Rad etildi"
    a.refresh_from_db()
    assert a.status == "X"


def test_stats_summary_and_journal(api, make_user, world):
    w = world
    rate(w, w["teacher"], "USTOZ", fixed=120000)
    take(api(w["teacher"]), w, [(w["contracts"][0], "1", ""), (w["contracts"][1], "X", "")])
    take(api(make_user("ADMINISTRATOR")), w, [(w["contracts"][2], "0", "kasal")])
    bm = api(make_user("BOSH_MENEJER"))
    s = bm.get(f"/api/v1/attendance/stats/?month={TODAY:%Y-%m}").json()
    assert s["by_group"][0] == {"group": str(w["group"].pk), "n": 3, "came": 1, "sab": 1, "bes": 1}
    my = api(w["teacher"]).get("/api/v1/attendance/summary/").json()
    assert my["kpi"] == 20000 and my["rows"] == 3 and my["absent"] == 1
    j = bm.get(f"/api/v1/groups/{w['group'].pk}/journal/?month={TODAY:%Y-%m}").json()
    assert len(j["contracts"]) == 3 and j["marks"][str(w["contracts"][1].pk)][TODAY.isoformat()] == "X"
    assert TODAY.isoformat() in j["days"] and j["frequency"]["frequency"] == 12


# ------------------------------------------------------------------ lid → shartnoma

def test_lead_group_and_create_contract(api, make_user, world):
    w = world
    st = Student.objects.create(branch=w["branch"], first_name="Lid", last_name="Talaba", phone1="933333333", phone2="944444444")
    lead = Lead.objects.create(branch=w["branch"], student=st, source=LeadSource.objects.create(name="Instagram"), course=w["course"], status="4")
    adm = api(make_user("ADMINISTRATOR"))
    assert adm.post(f"/api/v1/leads/{lead.pk}/contract/").status_code == 400  # status 5 emas
    r = adm.patch(f"/api/v1/leads/{lead.pk}/", {"status": "5", "group": str(w["group"].pk), "demo_date": TODAY.isoformat()}, format="json")
    assert r.status_code == 200 and r.json()["group"] == str(w["group"].pk)
    assert adm.post(f"/api/v1/leads/{lead.pk}/contract/").json()["detail"].startswith("Avval talaba ma'lumotlarini")
    Student.objects.filter(pk=st.pk).update(birth_date=datetime.date(2010, 1, 1))
    r = adm.post(f"/api/v1/leads/{lead.pk}/contract/")
    assert r.status_code == 201, r.content
    c = Contract.objects.get(pk=r.json()["id"])
    assert c.group_id == w["group"].pk and c.start_date == TODAY and c.type == "Pullik"
    assert adm.get(f"/api/v1/leads/{lead.pk}/").json()["has_contract"] is True
    assert adm.post(f"/api/v1/leads/{lead.pk}/contract/").status_code == 400
    b = adm.get("/api/v1/leads/board/").json()
    assert b["contract_rate"] == 1
    assert adm.get("/api/v1/leads/stats/").json()["by_source"][0]["contracts"] == 1
    # shartnomasi bor talaba yangi lid uchun «bo'sh» ro'yxatda chiqmaydi
    ids = [s["id"] for s in adm.get("/api/v1/students/?free=1").json()["results"]]
    assert str(w["students"][0].pk) not in ids
    # boshqa kursning guruhi tanlanmaydi
    other = Course.objects.create(name="Backend")
    other.branches.set([w["branch"]])
    g2 = Group.objects.create(branch=w["branch"], course=other, day_pattern=w["pattern"], time=w["time"], teacher=w["teacher"], room=w["room"], start_date=TODAY, number=1)
    assert adm.patch(f"/api/v1/leads/{lead.pk}/", {"group": str(g2.pk)}, format="json").status_code == 400


def test_soft_delete_used_references_blocked(api, make_user, world):
    bm = api(make_user("BOSH_MENEJER"))
    assert bm.delete(f"/api/v1/day-patterns/{world['pattern'].pk}/").status_code == 409  # guruhda ishlatilgan


def test_query_counts(api, make_user, world, django_assert_max_num_queries):
    w = world
    take(api(w["teacher"]), w, all=True)
    bm = api(make_user("BOSH_MENEJER"))
    with django_assert_max_num_queries(10):
        assert bm.get("/api/v1/contracts/").json()["count"] == 3
    with django_assert_max_num_queries(10):
        assert bm.get(f"/api/v1/attendance/?month={TODAY:%Y-%m}").json()["count"] == 3
    with django_assert_max_num_queries(10):
        assert len(bm.get("/api/v1/groups/").json()) == 1
    with django_assert_max_num_queries(25):
        bm.get(f"/api/v1/attendance/take/?group={w['group'].pk}&date={TODAY}")


def test_administrator_can_stop_old_contract_within_30_days(api, make_user, world):
    c = world["contracts"][0]
    Contract.objects.filter(pk=c.pk).update(start_date=TODAY - datetime.timedelta(days=60))
    adm = api(make_user("ADMINISTRATOR"))
    assert adm.patch(f"/api/v1/contracts/{c.pk}/", {"comment": "x", "type": "Pullik", "start": (TODAY - datetime.timedelta(days=60)).isoformat()}, format="json").status_code == 403
    old = (TODAY - datetime.timedelta(days=31)).isoformat()
    r = adm.patch(f"/api/v1/contracts/{c.pk}/", {"end": old, "stop_reason": "Moliyaviy qiyinchilik"}, format="json")
    assert r.status_code == 400 and r.json()["end"] == ["Tugash sanasini oxirgi 30 kun ichida qo'yish mumkin"]
    ok = (TODAY - datetime.timedelta(days=30)).isoformat()
    r = adm.patch(f"/api/v1/contracts/{c.pk}/", {"end": ok, "stop_reason": "Moliyaviy qiyinchilik", "comment": "To'xtatildi"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "Nofaol"
    assert api(make_user("USTOZ")).patch(f"/api/v1/contracts/{c.pk}/", {"end": ok}, format="json").status_code in (403, 404)

import datetime

import pytest
from django.utils import timezone

from apps.core.models import AuditLog
from apps.crm.models import Lead, LeadComment, Parent, Student
from apps.references.models import Course, DayPattern, LeadSource, LessonTime

pytestmark = pytest.mark.django_db


@pytest.fixture
def refs(branch):
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    return {
        "course": course,
        "source": LeadSource.objects.create(name="Instagram"),
        "pattern": DayPattern.objects.create(name="", weekdays=[1, 3, 5]),
        "time": LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"),
    }


def new_lead(refs, **kw):
    body = {"mode": "new", "first_name": "Abdusalom", "last_name": "Yangiboyev", "phone1": "901233323", "phone2": "911112233", "gender": "Erkak",
            "source": str(refs["source"].pk), "course": str(refs["course"].pk), "pattern": str(refs["pattern"].pk), "times": [str(refs["time"].pk)],
            "status": "2", "age_group": "16-18", "social": "Maktab o'quvchisi", "laptop": "Bor", "tags": ["VIP"], "comment": "Narxni so'radi"}
    body.update(kw)
    return body


def test_create_lead_with_new_student_and_comment(api, make_user, refs):
    c = api(make_user("ADMINISTRATOR"))
    r = c.post("/api/v1/leads/", new_lead(refs), format="json")
    assert r.status_code == 201, r.content
    d = r.json()
    assert d["status"] == "2" and d["social"] == "Maktab o'quvchisi" and d["has_contract"] is False
    assert d["student_data"]["full_name"] == "Abdusalom Yangiboyev" and d["student_data"]["phone2"] == "911112233"
    assert LeadComment.objects.get().comment == "Narxni so'radi"
    assert AuditLog.objects.filter(action="create", model="Lid").exists()
    detail = c.get(f"/api/v1/leads/{d['id']}/").json()
    assert detail["comments"][0]["comment"] == "Narxni so'radi" and detail["comments_count"] == 1


@pytest.mark.parametrize("field, value, msg", [
    ("first_name", "Ab", "Eng ozi 3 harf, ko'pi 20"),
    ("phone1", "90123", "9 sondan iborat bo'lsin. Namuna: 998883322"),
    ("phone2", "", "9 sondan iborat bo'lsin. Namuna: 998883322"),
    ("phone2", "901233323", "Ikki bir xil nomer kiritib bo'lmaydi!"),
])
def test_new_student_validation(api, make_user, refs, field, value, msg):
    r = api(make_user("ADMINISTRATOR")).post("/api/v1/leads/", new_lead(refs, **{field: value}), format="json")
    assert r.status_code == 400 and r.json()[field] == [msg]


def test_duplicate_student_by_name_and_phone(api, make_user, refs):
    c = api(make_user("ADMINISTRATOR"))
    assert c.post("/api/v1/leads/", new_lead(refs), format="json").status_code == 201
    dup = c.post("/api/v1/leads/", new_lead(refs, first_name="abdusalom", phone1="935554433", phone2="901233323"), format="json")
    assert dup.status_code == 400
    assert dup.json()["phone2"] == ["Ushbu o'quvchi avval kiritilgan. Lidlar yoki shartnomalar oynasidan qidiring"]
    # Ism bir xil, lekin telefonlar boshqa — boshqa odam
    ok = c.post("/api/v1/leads/", new_lead(refs, phone1="935554433", phone2="935554434"), format="json")
    assert ok.status_code == 201


def test_one_lead_per_student_and_free_students(api, make_user, refs, branch):
    c = api(make_user("ADMINISTRATOR"))
    lead = c.post("/api/v1/leads/", new_lead(refs), format="json").json()
    sid = lead["student"]
    r = c.post("/api/v1/leads/", new_lead(refs, mode="old", student=sid), format="json")
    assert r.status_code == 400 and r.json()["student"] == ["Bu talabaning lidi allaqachon ochilgan"]
    free = Student.objects.create(branch=branch, first_name="Bo'sh", last_name="Talaba", phone1="999999999")
    ids = [s["id"] for s in c.get("/api/v1/students/?free=1").json()["results"]]
    assert str(free.pk) in ids and sid not in ids
    assert c.post("/api/v1/leads/", new_lead(refs, mode="old", student=str(free.pk)), format="json").status_code == 201


def test_inactive_refs_rejected_for_new_but_kept_on_old(api, make_user, refs):
    c = api(make_user("ADMINISTRATOR"))
    lead = c.post("/api/v1/leads/", new_lead(refs), format="json").json()
    refs["source"].status = "Nofaol"
    refs["source"].save()
    r = c.post("/api/v1/leads/", new_lead(refs, phone1="935554433", phone2="935554434", first_name="Boshqa"), format="json")
    assert r.status_code == 400 and r.json()["source"] == ["Bu manba nofaol"]
    # Eski lidni tahrirlaganda nofaol manba saqlanib qoladi
    assert c.patch(f"/api/v1/leads/{lead['id']}/", {"status": "3"}, format="json").status_code == 200


def test_edit_window_for_administrator(api, make_user, refs):
    adm = make_user("ADMINISTRATOR")
    c = api(adm)
    lead = c.post("/api/v1/leads/", new_lead(refs), format="json").json()
    Lead.objects.filter(pk=lead["id"]).update(created_at=timezone.now() - datetime.timedelta(days=9))
    r = c.patch(f"/api/v1/leads/{lead['id']}/", {"status": "6"}, format="json")
    assert r.status_code == 403 and "oxirgi 7 kun" in r.json()["detail"]
    assert api(make_user("FILIAL_MENEJERI")).patch(f"/api/v1/leads/{lead['id']}/", {"status": "6"}, format="json").status_code == 200


def test_permissions_and_scope(api, make_user, refs, other_branch):
    lead = api(make_user("ADMINISTRATOR")).post("/api/v1/leads/", new_lead(refs), format="json").json()
    teacher = api(make_user("USTOZ"))
    assert teacher.get("/api/v1/leads/").json()["count"] == 1  # ko'rish mumkin
    assert teacher.post("/api/v1/leads/", new_lead(refs, phone1="935554433", phone2="935554434"), format="json").status_code == 403
    assert teacher.post(f"/api/v1/leads/{lead['id']}/comments/", {"comment": "x"}, format="json").status_code == 403
    stranger = api(make_user("FILIAL_MENEJERI", branches=[other_branch]))
    assert stranger.get("/api/v1/leads/").json()["count"] == 0
    assert stranger.get(f"/api/v1/leads/{lead['id']}/").status_code == 404


def test_board_stats_search(api, make_user, refs):
    c = api(make_user("BOSH_MENEJER"))
    for i, st in enumerate(["2", "3", "4", "5", "6"]):
        body = new_lead(refs, first_name=f"Talaba{i}", phone1=f"90000000{i}", phone2=f"91000000{i}", status=st)
        assert c.post("/api/v1/leads/", body, format="json").status_code == 201
    b = c.get("/api/v1/leads/board/").json()
    assert b["total"] == 5 and b["counts"]["3"] == 1 and len(b["columns"]["5"]) == 1
    assert b["reached"]["3"] == pytest.approx(3 / 5)  # 3, 4, 5-statuslar
    s = c.get("/api/v1/leads/stats/").json()
    assert s["by_status"]["6"] == 1 and s["by_source"][0]["n"] == 5 and s["by_age"]["16-18"] == 5
    assert c.get("/api/v1/leads/?search=talaba3").json()["count"] == 1
    assert c.get("/api/v1/leads/?search=910000004").json()["count"] == 1
    assert c.get("/api/v1/leads/?status=5").json()["count"] == 1


def test_student_fill_form_with_new_parent(api, make_user, refs):
    c = api(make_user("ADMINISTRATOR"))
    sid = c.post("/api/v1/leads/", new_lead(refs), format="json").json()["student"]
    bad = c.patch(f"/api/v1/students/{sid}/", {"father_name": "Anvar o.", "birth_date": "2010-05-01"}, format="json")
    assert bad.json()["father_name"] == ["Nuqta qo'yib bo'lmaydi!"]
    no_birth = c.patch(f"/api/v1/students/{sid}/", {"father_name": "Anvar o'g'li"}, format="json")
    assert no_birth.json()["birth_date"] == ["Majburiy maydon"]
    r = c.patch(f"/api/v1/students/{sid}/", {"father_name": "Anvar o'g'li", "birth_date": "2010-05-01", "new_parent": True, "p_first": "Anvar", "p_phone": "977776655"}, format="json")
    assert r.status_code == 200, r.content
    p = Parent.objects.get()
    assert r.json()["parent"] == str(p.pk) and p.last_name == "Yangiboyev"
    assert r.json()["full_name"] == "Abdusalom Yangiboyev Anvar o'g'li"


def test_comment_and_soft_delete(api, make_user, refs):
    bm = api(make_user("BOSH_MENEJER"))
    lead = bm.post("/api/v1/leads/", new_lead(refs, comment=""), format="json").json()
    assert bm.post(f"/api/v1/leads/{lead['id']}/comments/", {"comment": "  "}, format="json").status_code == 400
    assert bm.post(f"/api/v1/leads/{lead['id']}/comments/", {"comment": "Qayta qo'ng'iroq"}, format="json").status_code == 201
    assert bm.delete(f"/api/v1/leads/{lead['id']}/").status_code == 204
    assert Lead.all_objects.get(pk=lead["id"]).is_deleted
    # O'chirilgan lid talabasiga yangi lid ochsa bo'ladi
    assert bm.post("/api/v1/leads/", new_lead(refs, mode="old", student=lead["student"]), format="json").status_code == 201


def test_lead_list_query_count(api, make_user, refs, django_assert_max_num_queries):
    c = api(make_user("BOSH_MENEJER"))
    for i in range(8):
        c.post("/api/v1/leads/", new_lead(refs, first_name=f"Ism{i}x", phone1=f"90000001{i}", phone2=f"91000001{i}"), format="json")
    with django_assert_max_num_queries(12):
        assert len(c.get("/api/v1/leads/").json()["results"]) == 8
    with django_assert_max_num_queries(30):
        c.get("/api/v1/leads/board/")


def test_board_counts_not_inflated_by_comments(api, make_user, refs):
    c = api(make_user("BOSH_MENEJER"))
    lead = c.post("/api/v1/leads/", new_lead(refs, status="5"), format="json").json()
    for t in ("bir", "ikki", "uch"):
        c.post(f"/api/v1/leads/{lead['id']}/comments/", {"comment": t}, format="json")
    b = c.get("/api/v1/leads/board/").json()
    assert b["counts"]["5"] == 1 and b["total"] == 1
    s = c.get("/api/v1/leads/stats/").json()
    assert s["by_status"]["5"] == 1 and s["by_source"][0]["n"] == 1
    assert c.get("/api/v1/leads/").json()["results"][0]["comments_count"] == 4

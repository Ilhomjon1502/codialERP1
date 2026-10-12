import datetime

import pytest
from rest_framework.exceptions import ValidationError

from apps.core.models import AuditLog
from apps.references import services
from apps.references.models import Course, CoursePrice, DayPattern, LessonFrequency

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(make_user):
    return make_user("ADMIN")


def test_course_unique_name_case_insensitive(api, admin):
    c = api(admin)
    assert c.post("/api/v1/courses/", {"name": "Frontend"}, format="json").status_code == 201
    r = c.post("/api/v1/courses/", {"name": "  frontend "}, format="json")
    assert r.status_code == 400 and r.json()["name"] == ["Avval kiritilgan nom"]


def test_day_pattern_name_order_and_duplicate(api, admin):
    c = api(admin)
    r = c.post("/api/v1/day-patterns/", {"weekdays": ["5", "1", "3"]}, format="json")
    assert r.status_code == 201
    assert r.json()["name"] == "Dush, Chor, Jum" and r.json()["weekdays"] == [1, 3, 5]
    dup = c.post("/api/v1/day-patterns/", {"weekdays": [3, 5, 1]}, format="json")
    assert dup.status_code == 400 and dup.json()["weekdays"] == ["Avval kiritilgan, mavjudlarni tekshiring"]
    assert c.post("/api/v1/day-patterns/", {"weekdays": [8]}, format="json").status_code == 400


def test_lesson_time_rules(api, admin, branch):
    c = api(admin)
    body = {"branch": str(branch.pk), "start": "08:00", "end": "10:00"}
    r = c.post("/api/v1/lesson-times/", body, format="json")
    assert r.status_code == 201 and r.json()["start"] == "08:00"
    assert c.post("/api/v1/lesson-times/", body, format="json").json()["start"] == ["Avval qo'shilgan vaqt!"]
    bad = c.post("/api/v1/lesson-times/", {**body, "start": "12:00", "end": "11:00"}, format="json")
    assert bad.json()["end"] == ["Tugash vaqti boshlanishdan keyin bo'lsin"]


def test_soft_delete_unused_and_used(api, admin, branch):
    c = api(admin)
    free = c.post("/api/v1/day-patterns/", {"weekdays": [2]}, format="json").json()
    assert c.delete(f"/api/v1/day-patterns/{free['id']}/").status_code == 204
    assert DayPattern.all_objects.get(pk=free["id"]).is_deleted
    assert AuditLog.objects.filter(action="delete", object_id=free["id"]).exists()
    # O'chirilgan nomni qayta qo'shish mumkin
    assert c.post("/api/v1/day-patterns/", {"weekdays": [2]}, format="json").status_code == 201

    used = DayPattern.objects.create(name="", weekdays=[6, 7])
    LessonFrequency.objects.create(branch=branch, day_pattern=used, year=2026, month=10, frequency=9)
    r = c.delete(f"/api/v1/day-patterns/{used.pk}/")
    assert r.status_code == 409
    assert r.json()["detail"] == "«Shan, Yak» ishlatilgan (1 ta oydagi dars soni). O'chirib bo'lmaydi — tahrirlab, Nofaol qiling"
    assert c.patch(f"/api/v1/day-patterns/{used.pk}/", {"status": "Nofaol"}, format="json").json()["status"] == "Nofaol"


def test_audit_records_changes(api, admin):
    c = api(admin)
    src = c.post("/api/v1/lead-sources/", {"name": "Instagram"}, format="json").json()
    c.patch(f"/api/v1/lead-sources/{src['id']}/", {"status": "Nofaol"}, format="json")
    log = AuditLog.objects.filter(action="update", object_id=src["id"]).get()
    assert log.user == admin and log.changes == [["status", "Faol", "Nofaol"]]
    rows = c.get("/api/v1/audit-log/?action=update").json()
    assert rows["count"] == 1 and rows["results"][0]["detail"] == "status: Faol → Nofaol"


def test_course_price_upsert_by_month(api, admin, branch):
    course = Course.objects.create(name="Flutter")
    c = api(admin)
    body = {"branch": str(branch.pk), "course": str(course.pk), "effective_from": "2026-10", "price": 650000}
    r1 = c.post("/api/v1/course-prices/", body, format="json")
    assert r1.status_code == 201 and r1.json()["effective_from"] == "2026-10" and r1.json()["price"] == 650000
    r2 = c.post("/api/v1/course-prices/", {**body, "price": 700000}, format="json")
    assert r2.status_code == 200
    assert CoursePrice.objects.count() == 1 and CoursePrice.objects.get().price == 700000


def test_lesson_days_in_month():
    assert services.lesson_days_in_month(2026, 10, [1, 3, 5]) == 13  # oktabr 2026: 1-oktabr payshanba
    assert services.lesson_days_in_month(2026, 2, [6, 7]) == 8


def test_propose_copies_previous_courses_and_skips_existing(api, make_user, branch):
    fe, be = Course.objects.create(name="Frontend"), Course.objects.create(name="Backend")
    p = DayPattern.objects.create(name="", weekdays=[1, 3, 5])
    DayPattern.objects.create(name="", weekdays=[2, 4], status="Nofaol")
    prev = LessonFrequency.objects.create(branch=branch, day_pattern=p, year=2026, month=9, frequency=13, status="Tasdiqlangan")
    prev.courses.set([fe, be])
    fm = make_user("FILIAL_MENEJERI")
    c = api(fm)
    assert c.post("/api/v1/lesson-frequencies/propose/", {"month": "2026-10"}, format="json").json() == {"created": 1}
    f = LessonFrequency.objects.get(year=2026, month=10)
    assert f.frequency == 13 and f.status == "Taklif" and set(f.courses.all()) == {fe, be}
    assert c.post("/api/v1/lesson-frequencies/propose/", {"month": "2026-10"}, format="json").json() == {"created": 0}
    # Tasdiqlash: Filial menejeri mumkin, administrator emas
    assert api(make_user("ADMINISTRATOR")).post(f"/api/v1/lesson-frequencies/{f.pk}/approve/").status_code == 403
    r = c.post(f"/api/v1/lesson-frequencies/{f.pk}/approve/")
    assert r.status_code == 200 and r.json()["status"] == "Tasdiqlangan" and r.json()["approved_by"] == str(fm.pk)


def test_frequency_range_and_overlap(api, admin, branch):
    fe = Course.objects.create(name="Frontend")
    p = DayPattern.objects.create(name="", weekdays=[1, 3, 5])
    c = api(admin)
    body = {"branch": str(branch.pk), "pattern": str(p.pk), "year": 2026, "month": 11, "frequency": 30, "courses": [str(fe.pk)]}
    r = c.post("/api/v1/lesson-frequencies/", body, format="json")
    assert r.json()["frequency"] == ["Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos"]
    assert c.post("/api/v1/lesson-frequencies/", {**body, "frequency": 12}, format="json").status_code == 201
    dup = c.post("/api/v1/lesson-frequencies/", {**body, "frequency": 11}, format="json")
    assert dup.status_code == 400 and "Frontend" in dup.json()["courses"][0]


def test_month_start_validation():
    assert services.month_start("2026-10") == datetime.date(2026, 10, 1)
    with pytest.raises(ValidationError):
        services.month_start("oktabr")


def test_bootstrap_shape_and_query_count(api, admin, branch, django_assert_max_num_queries):
    from django.core.management import call_command

    call_command("seed_demo", password="")
    c = api(admin)
    with django_assert_max_num_queries(40):
        r = c.get("/api/v1/bootstrap/")
    data = r.json()
    for key in ["me", "roles", "edit_days", "branches", "courses", "rooms", "dayPatterns", "lessonTimes", "coursePrices",
                "lessonFreqs", "discountTypes", "expenseCats", "leadSources", "attendanceStatuses", "accounts", "users"]:
        assert key in data
    assert data["me"]["role"] == "ADMIN"
    assert data["edit_days"]["ADMINISTRATOR"]["payments"] == 0
    assert {d["name"] for d in data["discountTypes"]} >= {"50% Chegirma"}
    assert next(d for d in data["discountTypes"] if d["name"] == "50% Chegirma")["is_d50"] is True


def test_lead_source_and_expense_category_unique(api, admin):
    c = api(admin)
    assert c.post("/api/v1/lead-sources/", {"name": "Instagram"}, format="json").status_code == 201
    assert c.post("/api/v1/lead-sources/", {"name": "instagram"}, format="json").json()["name"] == ["Avval qo'shilgan nom!"]
    assert c.post("/api/v1/expense-categories/", {"name": "Ijara"}, format="json").status_code == 201
    assert c.post("/api/v1/expense-categories/", {"name": "IJARA"}, format="json").json()["name"] == ["Avval qo'shilgan nom!"]

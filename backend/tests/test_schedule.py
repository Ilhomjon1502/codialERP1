"""Dars jadvali (bosh sahifa): guruhlardan avtomatik, faol va rejadagi guruhlar, ustoz ham to'liq jadvalni ko'radi."""

import datetime

import pytest

from apps.education.models import Group
from apps.references.models import DayPattern, LessonTime, Room
from tests.test_finance import TODAY, fin  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db


def test_schedule_lists_active_and_planned_groups(api, make_user, fin, other_branch, django_assert_max_num_queries):  # noqa: F811
    g1 = fin["contract"].group
    other_teacher = make_user("USTOZ")
    t2 = LessonTime.objects.create(branch=fin["branch"], start_time="16:00", end_time="18:00")
    p2 = DayPattern.objects.create(name="", weekdays=[2, 4, 6])
    planned = Group.objects.create(branch=fin["branch"], course=g1.course, day_pattern=p2, time=t2, teacher=other_teacher, room=g1.room,
                                   start_date=TODAY + datetime.timedelta(days=10), number=2)
    Group.objects.create(branch=fin["branch"], course=g1.course, day_pattern=p2, time=t2, teacher=other_teacher, room=g1.room,
                         start_date=TODAY - datetime.timedelta(days=90), end_date=TODAY - datetime.timedelta(days=1), number=3)  # tugagan
    room_x = Room.objects.create(branch=other_branch, name="X", capacity=5)
    Group.objects.create(branch=other_branch, course=g1.course, day_pattern=p2, time=LessonTime.objects.create(branch=other_branch, start_time="08:00", end_time="10:00"),
                         teacher=other_teacher, room=room_x, start_date=TODAY, number=4)  # boshqa filial

    teacher = api(fin["teacher"])  # o'zi faqat g1 ustozi, lekin jadvalni to'liq ko'radi
    with django_assert_max_num_queries(12):
        d = teacher.get("/api/v1/schedule/").json()
    by_id = {x["id"]: x for x in d["groups"]}
    assert set(by_id) == {str(g1.pk), str(planned.pk)}
    assert by_id[str(g1.pk)]["status"] == "Faol" and by_id[str(g1.pk)]["students"] == 1 and by_id[str(g1.pk)]["weekdays"] == [1, 3, 5]
    assert by_id[str(planned.pk)]["status"] == "Rejada" and by_id[str(planned.pk)]["start"] == "16:00"
    assert by_id[str(g1.pk)]["teacher_name"] == fin["teacher"].full_name and "phone" not in str(d)
    assert [r["name"] for r in d["rooms"]] == ["1"]


def test_schedule_requires_login(client):
    assert client.get("/api/v1/schedule/").status_code in (401, 403)


def test_schedule_counts_students_and_leads_for_planned_group(fin, make_user, api):  # noqa: F811
    from apps.crm.models import Lead, Student
    from apps.education.models import Contract
    from apps.references.models import LeadSource

    g = fin["contract"].group
    g.start_date = TODAY + datetime.timedelta(days=20)
    g.save()
    st = Student.objects.create(branch=fin["branch"], first_name="Lola", last_name="Karimova", phone1="901112233")
    Lead.objects.create(branch=fin["branch"], student=st, source=LeadSource.objects.create(name="Instagram"), course=g.course, group=g, status="3")
    row = next(x for x in api(make_user("BOSH_MENEJER")).get("/api/v1/schedule/").json()["groups"] if x["id"] == str(g.pk))
    assert row["status"] == "Rejada" and row["leads"] == 1
    assert row["students"] == Contract.objects.filter(group=g).count()


def test_group_delete_only_when_empty(fin, make_user, api):  # noqa: F811
    from apps.education.models import Group

    g = fin["contract"].group
    bm = api(make_user("BOSH_MENEJER"))
    assert bm.delete(f"/api/v1/groups/{g.pk}/").status_code == 409  # shartnomasi bor
    empty = Group.objects.create(branch=g.branch, course=g.course, day_pattern=g.day_pattern, time=g.time, teacher=g.teacher, room=g.room,
                                 start_date=TODAY + datetime.timedelta(days=5), number=9)
    assert bm.delete(f"/api/v1/groups/{empty.pk}/").status_code == 204
    assert not Group.objects.filter(pk=empty.pk).exists()

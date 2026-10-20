"""Topshiriqlar: berish, ko'rinish doirasi, bajarish, uzaytirish, bekor qilish, bot eslatmalari va «✅ Bajarildi» tugmasi."""

import datetime

import pytest
from django.utils import timezone

from apps.notifications.models import Outbox, TelegramLink
from apps.tasks import services
from apps.tasks.models import StaffTask

pytestmark = pytest.mark.django_db


def link(user, chat):
    return TelegramLink.objects.update_or_create(user=user, defaults={"chat_id": chat, "linked_at": timezone.now()})[0]


def iso(dt):
    return timezone.localtime(dt).isoformat()


@pytest.fixture
def people(make_user):
    boss, admin, teacher = make_user("BOSH_MENEJER"), make_user("ADMINISTRATOR_HISOBCHI"), make_user("USTOZ")
    for i, u in enumerate((boss, admin, teacher)):
        link(u, 500 + i)
    return {"boss": boss, "admin": admin, "teacher": teacher}


def give(api, giver, assignee, hours=5, **extra):
    body = {"title": "Ota-onalarga qo'ng'iroq", "description": "Qarzdorlar ro'yxati bo'yicha", "assignee": str(assignee.pk),
            "due_at": iso(timezone.now() + datetime.timedelta(hours=hours)), "remind_before": 60, "remind_every": 0, **extra}
    return api(giver).post("/api/v1/tasks/", body, format="json")


def test_create_scope_and_notify(api, make_user, people, other_branch, django_capture_on_commit_callbacks):
    boss, admin, teacher = people["boss"], people["admin"], people["teacher"]
    with django_capture_on_commit_callbacks(execute=True):
        r = give(api, boss, admin)
    assert r.status_code == 201, r.content
    d = r.json()
    assert d["giver"] == str(boss.pk) and d["status"] == "Ochiq" and d["can_edit"] is True and d["can_done"] is True  # BM — Admin/BM bajarildi deya oladi
    m = Outbox.objects.get(event="task", user=admin)
    assert "Yangi topshiriq" in m.text and m.markup["inline_keyboard"][0][0]["callback_data"] == f"td:{d['id']}"
    g = Outbox.objects.get(event="task", user=boss)  # beruvchiga ham tasdiq
    assert "Topshiriq berildi" in g.text and "ulanmagan" not in g.text and d["assignee_linked"] is True
    # doira: bajaruvchi va beruvchi ko'radi, boshqa xodim — yo'q
    assert api(admin).get(f"/api/v1/tasks/{d['id']}/").status_code == 200
    assert api(teacher).get(f"/api/v1/tasks/{d['id']}/").status_code == 404
    assert [t["id"] for t in api(admin).get("/api/v1/tasks/?box=in").json()] == [d["id"]]
    assert [t["id"] for t in api(boss).get("/api/v1/tasks/?box=out").json()] == [d["id"]]
    # tekshiruvlar
    assert give(api, admin, teacher, hours=-1).json()["due_at"] == ["Muddat hozirgi vaqtdan keyin bo'lishi kerak"]
    stranger = make_user("ADMINISTRATOR", branches=[other_branch])
    assert give(api, teacher, stranger).json()["assignee"] == ["Bu xodimga topshiriq berib bo'lmaydi"]  # boshqa filial
    assert give(api, teacher, teacher).status_code == 201  # o'ziga eslatma
    assert api(make_user("USTOZ")).get("/api/v1/tasks/people/").status_code == 200


def test_done_extend_cancel_rules(api, people, django_capture_on_commit_callbacks):
    boss, admin, teacher = people["boss"], people["admin"], people["teacher"]
    tid = give(api, admin, teacher).json()["id"]
    assert api(teacher).patch(f"/api/v1/tasks/{tid}/", {"title": "x"}, format="json").status_code == 403  # bajaruvchi tahrirlay olmaydi
    assert api(teacher).post(f"/api/v1/tasks/{tid}/cancel/").status_code == 403
    StaffTask.objects.filter(pk=tid).update(last_reminded_at=timezone.now())
    new_due = timezone.now() + datetime.timedelta(days=2)
    with django_capture_on_commit_callbacks(execute=True):
        r = api(admin).patch(f"/api/v1/tasks/{tid}/", {"due_at": iso(new_due)}, format="json")
    assert r.status_code == 200 and StaffTask.objects.get(pk=tid).last_reminded_at is None  # eslatma qayta boshlanadi
    assert Outbox.objects.filter(user=teacher, text__contains="Muddat o'zgartirildi").exists()
    with django_capture_on_commit_callbacks(execute=True):
        r = api(teacher).post(f"/api/v1/tasks/{tid}/done/", {"comment": "Hammasiga qo'ng'iroq qildim"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "Bajarildi" and r.json()["done_comment"] == "Hammasiga qo'ng'iroq qildim"
    assert Outbox.objects.filter(user=admin, text__contains="Bajarildi").exists()
    assert api(admin).post(f"/api/v1/tasks/{tid}/cancel/").status_code == 400  # yopilgan
    assert api(admin).patch(f"/api/v1/tasks/{tid}/", {"title": "y"}, format="json").status_code == 400
    t2 = give(api, boss, teacher).json()["id"]
    r = api(boss).post(f"/api/v1/tasks/{t2}/cancel/", {"reason": "Kerak emas"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "Bekor qilindi"
    s = api(teacher).get("/api/v1/tasks/summary/").json()
    assert s["in_open"] == 0 and api(teacher).get("/api/v1/tasks/?status=Bajarildi").json()[0]["id"] == tid


def test_reminders_schedule(api, people, django_capture_on_commit_callbacks):
    admin, teacher = people["admin"], people["teacher"]
    now = timezone.now()
    tid = give(api, admin, teacher, hours=3, remind_before=60, remind_every=30, remind_giver=True).json()["id"]
    Outbox.objects.all().delete()
    with django_capture_on_commit_callbacks(execute=True):
        assert services.due_reminders(now) == 0  # muddatga 3 soat bor, eslatma 1 soat oldin boshlanadi
        assert services.due_reminders(now + datetime.timedelta(hours=2, minutes=1)) == 1
        assert services.due_reminders(now + datetime.timedelta(hours=2, minutes=10)) == 0  # 30 daqiqa o'tmagan
        assert services.due_reminders(now + datetime.timedelta(hours=2, minutes=32)) == 1
        assert services.due_reminders(now + datetime.timedelta(hours=5)) == 1  # muddat o'tgan — yopilmaguncha davom etadi
    got = list(Outbox.objects.filter(event="task").values_list("user_id", flat=True))
    assert got.count(teacher.pk) == 3 and got.count(admin.pk) == 3
    assert any("muddati" in t for t in Outbox.objects.filter(user=teacher).values_list("text", flat=True))  # muddat o'tgani aytiladi
    # Telegramdagi «✅ Bajarildi» tugmasi
    assert services.done_from_telegram(999, tid) == "Topshiriq topilmadi"
    assert services.done_from_telegram(501, tid).startswith("Topshiriqni bajaruvchi")  # admin — beruvchi, bajaruvchi emas
    assert services.done_from_telegram(502, tid) == "✅ Bajarildi deb belgilandi"
    with django_capture_on_commit_callbacks(execute=True):
        assert services.due_reminders(now + datetime.timedelta(hours=6)) == 0  # bajarildi — eslatma yo'q


def test_once_reminder_and_permissions(api, people, django_capture_on_commit_callbacks):
    tid = give(api, people["admin"], people["teacher"], hours=1, remind_before=0, remind_every=0).json()["id"]
    later = timezone.now() + datetime.timedelta(hours=1, minutes=1)
    with django_capture_on_commit_callbacks(execute=True):
        assert services.due_reminders(later) == 1
        assert services.due_reminders(later + datetime.timedelta(days=1)) == 0  # bir marta
    assert api(people["teacher"]).delete(f"/api/v1/tasks/{tid}/").status_code == 403  # bajaruvchi o'chira olmaydi
    assert give(api, people["admin"], people["teacher"], remind_every=7).json()["remind_every"] == ["Noto'g'ri qiymat"]


def test_giver_warned_when_assignee_not_linked(api, make_user, people, django_capture_on_commit_callbacks):
    nolink = make_user("ADMINISTRATOR")
    with django_capture_on_commit_callbacks(execute=True):
        d = give(api, people["admin"], nolink).json()
        give(api, people["teacher"], people["teacher"])  # o'ziga
    assert d["assignee_linked"] is False
    assert "ulanmagan" in Outbox.objects.get(event="task", user=people["admin"]).text
    assert Outbox.objects.filter(event="task", user=people["teacher"], text__contains="Yangi topshiriq").count() == 1  # o'ziga ham keladi


def test_given_inside_reminder_window_and_prefs_off(api, people, django_capture_on_commit_callbacks):
    admin, teacher = people["admin"], people["teacher"]
    TelegramLink.objects.filter(user__in=[admin, teacher]).update(prefs={"task": False})  # eslatmalarni o'chirgan
    with django_capture_on_commit_callbacks(execute=True):
        tid = give(api, admin, teacher, hours=1, remind_before=180, remind_every=0).json()["id"]  # eslatma oynasi allaqachon ochiq
    assert set(Outbox.objects.filter(event="task").values_list("user_id", flat=True)) == {admin.pk, teacher.pk}  # berilganda ikkalasiga ham boradi
    Outbox.objects.all().delete()
    now = timezone.now()
    with django_capture_on_commit_callbacks(execute=True):
        assert services.due_reminders(now + datetime.timedelta(minutes=5)) == 0  # «Yangi topshiriq» xabari yetarli — darhol takror yo'q
        assert services.due_reminders(now + datetime.timedelta(hours=1, minutes=1)) == 1  # bir martalik — muddat vaqtida
    assert not Outbox.objects.exists()  # xodim eslatmalarni o'chirgan — takroriy eslatma yuborilmaydi
    assert StaffTask.objects.get(pk=tid).last_reminded_at


def test_remind_from_now_repeats_until_done(api, people):
    from apps.tasks import services
    from apps.tasks.models import StaffTask

    tid = give(api, people["admin"], people["teacher"], hours=72, remind_before=525600, remind_every=60).json()["id"]
    t = StaffTask.objects.get(pk=tid)
    assert services.due_reminders(t.updated_at + datetime.timedelta(minutes=30)) == 0  # soat to'lmadi
    assert services.due_reminders(t.updated_at + datetime.timedelta(minutes=61)) == 1  # muddatdan 3 kun oldin ham eslatadi

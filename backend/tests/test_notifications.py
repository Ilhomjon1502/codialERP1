"""M8: Telegram — bog'lash, xabarlar navbati, kimga nima boradi, sozlamalar, davomat eslatmasi, kunlik hisobot (CLAUDE.md 12)."""

import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.crm.models import Lead, Student
from apps.notifications import services
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import LeadSource, LessonTime
from tests.test_education import world  # noqa: F401 — fixture
from tests.test_finance import fin  # noqa: F401, E402 — fixture

pytestmark = pytest.mark.django_db


def link(user, chat):
    lk, _ = TelegramLink.objects.get_or_create(user=user)
    lk.chat_id = chat
    lk.save()
    return lk


def test_link_flow_and_prefs(api, make_user):
    u = make_user("ADMINISTRATOR")
    c = api(u)
    d = c.get("/api/v1/notifications/me/").json()
    assert d["linked"] is False and len(d["code"]) == 8 and {"new_lead", "attendance_missing"} <= {e["key"] for e in d["events"]} and "daily_report" not in {e["key"] for e in d["events"]}
    assert "Kod topilmadi" in services.handle_message(111, "/start XXXXXXX")
    assert "Bog'landi" in services.handle_message(111, f"/start {d['code']}", "ali")
    d2 = c.get("/api/v1/notifications/me/").json()
    assert d2["linked"] is True and d2["code"] != d["code"]  # kod bir martalik
    assert "sifatida bog'langansiz" in services.handle_message(111, "/start")
    r = c.patch("/api/v1/notifications/me/", {"prefs": {"new_lead": False}}, format="json").json()
    assert next(e for e in r["events"] if e["key"] == "new_lead")["on"] is False
    assert c.patch("/api/v1/notifications/me/", {"prefs": {"nima": True}}, format="json").status_code == 400
    assert "uzildi" in services.handle_message(111, "/stop")
    assert c.get("/api/v1/notifications/me/").json()["linked"] is False


def test_new_lead_goes_to_branch_administrators(api, make_user, world, django_capture_on_commit_callbacks):  # noqa: F811
    adm, adm2, teacher, bm = make_user("ADMINISTRATOR"), make_user("ADMINISTRATOR_HISOBCHI"), make_user("USTOZ"), make_user("BOSH_MENEJER")
    for i, u in enumerate((adm, adm2, teacher, bm)):
        link(u, 100 + i)
    TelegramLink.objects.filter(user=adm2).update(prefs={"new_lead": False})
    body = {"mode": "new", "first_name": "Yangi", "last_name": "Lidov", "phone1": "933334455", "phone2": "944445566",
            "source": str(LeadSource.objects.create(name="Instagram").pk), "course": str(world["course"].pk), "status": "2"}
    with django_capture_on_commit_callbacks(execute=True):
        assert api(make_user("FILIAL_MENEJERI")).post("/api/v1/leads/", body, format="json").status_code == 201
    msgs = list(Outbox.objects.all())
    assert {m.user_id for m in msgs} == {adm.pk, bm.pk} and "Yangi Lidov" in msgs[0].text  # ustoz (standart o'chiq) va o'chirib qo'ygan xodim olmaydi
    sent = []
    assert services.send_pending(sender=lambda chat, text: sent.append(chat)) == 2
    assert sorted(sent) == [100, 103] and set(Outbox.objects.values_list("status", flat=True)) == {"sent"}


def test_send_failure_retries_then_fails(make_user):
    u = make_user("ADMINISTRATOR")
    Outbox.objects.create(user=u, chat_id=1, event="new_lead", text="x")

    def boom(chat, text):
        raise RuntimeError("tarmoq yo'q")

    for _ in range(5):
        services.send_pending(sender=boom)
    m = Outbox.objects.get()
    assert m.status == "failed" and m.attempts == 5 and "tarmoq" in m.error


def test_attendance_missing_once_per_day(make_user, world, django_capture_on_commit_callbacks):  # noqa: F811
    g = world["group"]
    g.time = LessonTime.objects.create(branch=g.branch, start_time=datetime.time(0, 0), end_time=datetime.time(0, 30))
    g.save()
    link(world["teacher"], 500)
    link(make_user("ADMINISTRATOR"), 501)
    with django_capture_on_commit_callbacks(execute=True):
        call_command("notify_attendance")
    with django_capture_on_commit_callbacks(execute=True):
        call_command("notify_attendance")
    assert Outbox.objects.filter(event="attendance_missing").count() == 2  # ustoz + administrator, takrorlanmaydi


def test_daily_report_to_boss(make_user, world, django_capture_on_commit_callbacks):  # noqa: F811
    bm = make_user("BOSH_MENEJER")
    link(bm, 900)
    Lead.objects.create(branch=world["branch"], student=Student.objects.create(branch=world["branch"], first_name="Abc", last_name="Def", phone1="955556677"),
                        source=LeadSource.objects.create(name="Sayt"), course=world["course"])
    with django_capture_on_commit_callbacks(execute=True):
        call_command("daily_report")
    m = Outbox.objects.get(event="daily_report")
    assert m.user == bm and "bugun +1 yangi" in m.text and f"{timezone.localdate():%d.%m.%Y}" in m.text and "Tizim auditi" in m.text


def test_user_choice_and_permission_limit(api, make_user, world, django_capture_on_commit_callbacks):  # noqa: F811
    teacher, hisobchi, admin = make_user("USTOZ"), make_user("HISOBCHI"), make_user("ADMIN")
    link(teacher, 700)
    link(hisobchi, 701)
    link(admin, 702)
    t = api(teacher).get("/api/v1/notifications/me/").json()
    keys = {e["key"] for e in t["events"]}
    assert "approval" not in keys and "daily_report" not in keys and "new_lead" in keys  # ustoz to'lovlarni ko'rmaydi
    assert api(teacher).patch("/api/v1/notifications/me/", {"prefs": {"approval": True}}, format="json").status_code == 400
    assert api(teacher).patch("/api/v1/notifications/me/", {"prefs": {"new_lead": True}}, format="json").status_code == 200
    assert api(hisobchi).patch("/api/v1/notifications/me/", {"prefs": {"daily_report": True}}, format="json").status_code == 400  # auditsiz — hisobot yo'q
    assert api(admin).patch("/api/v1/notifications/me/", {"prefs": {"daily_report": True}}, format="json").status_code == 200
    from apps.notifications import services as sv

    with django_capture_on_commit_callbacks(execute=True):
        sv.notify("new_lead", "x", branch=world["branch"])
        sv.daily_report("hisobot", key="d1")
    got = set(Outbox.objects.values_list("user_id", "event"))
    assert (teacher.pk, "new_lead") in got and (admin.pk, "daily_report") in got and (hisobchi.pk, "daily_report") not in got  # o'zi tanlagan xabar keldi


def test_daily_report_sections(api, make_user, django_capture_on_commit_callbacks):
    """Faol shartnomalar kurslar bo'yicha, lidlar holat va kurs bo'yicha, xarajatlar, audit — hammasi bitta xabarda."""
    from apps.core.models import AuditLog
    from apps.notifications.management.commands.daily_report import build
    from tests.test_finance import pay  # noqa: F401

    day = timezone.localdate()
    text = build(day)
    assert "Faol shartnomalar: 0" in text and "Xarajatlar: 0 so'm" in text and "Tizim auditi: 0 amal" in text
    u = make_user("ADMINISTRATOR", full_name="Gulnoza <b>")
    AuditLog.objects.create(user=u, action="delete", model="To'lov", object_repr="Ali №3")
    AuditLog.objects.create(user=u, action="create", model="Lid", object_repr="Vali")
    text = build(day)
    assert "Tizim auditi: 2 amal" in text and "Gulnoza &lt;b&gt; — <b>2</b> (✚1 ✎0 ✖1)" in text and "✖ To'lov: Ali №3" in text
    assert len(text) <= 4000


def test_daily_report_with_data(api, fin):  # noqa: F811
    from apps.crm.models import Lead
    from apps.finance.models import Expense
    from apps.notifications.management.commands.daily_report import build
    from tests.test_finance import pay

    day = timezone.localdate()
    pay(api(fin["cashier"]), fin, amount=300_000)
    Expense.objects.create(branch=fin["branch"], date=day, category=fin["cat"], name="Svet", quantity=1, price=120_000, total=120_000, cash_type="CASH",
                           account=fin["cash"], period_year=day.year, period_month=day.month)
    c = fin["contract"]
    Lead.objects.create(branch=fin["branch"], student=c.student, course=c.course, status="2", source=LeadSource.objects.create(name="Instagram"))
    text = build(day)
    assert "To'lovlar: 300 000 so'm</b> (1 ta)" in text and "Faol shartnomalar: 1</b>" in text and "• Frontend — <b>1</b>" in text
    assert "2. Yangi guruhga kutyapti — <b>1</b>" in text and "• Frontend — <b>1</b> (2: 1)" in text
    assert "Xarajatlar: 120 000 so'm</b> (1 ta)" in text and "• Kommunal — <b>120 000</b>" in text
    assert "Tizim auditi: 1 amal" in text  # to'lov yaratilgani audit'ga yozilgan

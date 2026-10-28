"""Xodimlar ish sifati hisoboti (PDF): ko'rsatkichlar, baholash va PDF yaratilishi."""

import datetime

import pytest
from django.utils import timezone

from apps.core.models import AuditLog
from apps.reports import staff_report
from apps.tasks.models import StaffTask

pytestmark = pytest.mark.django_db


def test_scores_reasons_and_pdf(make_user):
    today = timezone.localdate()
    frm = today - datetime.timedelta(days=6)
    a = make_user("ADMINISTRATOR_HISOBCHI", full_name="Faol xodim")
    b = make_user("ADMINISTRATOR_HISOBCHI", full_name="Sust xodim")
    make_user("ADMINISTRATOR_HISOBCHI", full_name="Hech kirmagan")  # hisobotga tushmaydi
    for i in range(6):
        AuditLog.objects.create(user=a, action="create", model="Lid", object_repr=f"x{i}")
    AuditLog.objects.create(user=b, action="update", model="Lid", changes=[["status", "5", "3"]])
    now = timezone.now()
    StaffTask.objects.create(title="Hisobotni topshirish", assignee=b, due_at=now - datetime.timedelta(days=1), created_by=a)
    StaffTask.objects.create(title="Ro'yxatni tekshirish", assignee=a, due_at=now - datetime.timedelta(hours=2),
                             status=StaffTask.Status.DONE, done_at=now - datetime.timedelta(hours=3), created_by=b)

    data = staff_report.grade(staff_report.collect(frm, today))
    by = {p["name"]: p for p in data["staff"]}
    assert set(by) == {"Faol xodim", "Sust xodim"}
    assert by["Sust xodim"]["reversals"] == 1
    assert by["Sust xodim"]["parts"]["tasks"] == 0
    assert by["Faol xodim"]["parts"]["tasks"] == 15
    assert any("Hisobotni topshirish" in x for x in by["Sust xodim"]["bad"])
    assert by["Faol xodim"]["score"] > by["Sust xodim"]["score"]
    assert all(p["grade"] in ("A'lo", "Yaxshi", "Qoniqarsiz") for p in data["staff"])

    pdf = staff_report.build_pdf(data)
    assert pdf.startswith(b"%PDF") and len(pdf) > 3000


def test_send_only_to_linked_bosh_menejer(make_user):
    from apps.notifications.models import TelegramLink

    bm = make_user("BOSH_MENEJER")
    adm = make_user("ADMINISTRATOR_HISOBCHI", full_name="Qabul <xodim>")
    TelegramLink.objects.create(user=bm, chat_id=111)
    TelegramLink.objects.create(user=adm, chat_id=222)
    AuditLog.objects.create(user=adm, action="create", model="Lid")
    today = timezone.localdate()
    data = staff_report.grade(staff_report.collect(today - datetime.timedelta(days=6), today))
    sent = []
    n = staff_report.send(data, b"%PDF-1.4", sender=lambda *a: sent.append(a))
    assert n == 1 and sent[0][0] == 111 and sent[0][1].endswith(".pdf")
    assert "Qabul &lt;xodim&gt;" in sent[0][3]


def test_empty_period_pdf():
    pdf = staff_report.report(datetime.date(2020, 1, 1), datetime.date(2020, 1, 7))
    assert pdf.startswith(b"%PDF")

"""Asoschi roli (2026-10-25): tizimda hech narsa ko'rmaydi, faqat Telegram botdan qisqa kunlik hisobot oladi."""

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import Role, RolePermission, User
from apps.calls.models import CallDevice, CallRecord
from apps.finance.models import Account
from apps.notifications import services
from apps.notifications.management.commands import daily_report
from apps.notifications.models import Outbox, TelegramLink

pytestmark = pytest.mark.django_db


def body(branch, **kw):
    return {"full_name": "Muhammad Amin Naziraliyev", "role": "ASOSCHI", "branches": [str(branch.pk)], **kw}


def test_role_has_only_the_report_section_and_only_admin_assigns(db):
    founder = Role.objects.get(code="ASOSCHI")
    assert founder.name == "Asoschi"
    assert {p.section: p.ops for p in RolePermission.objects.filter(role=founder) if p.ops} == {"founderReport": "v"}
    assert Role.objects.get(code="ADMIN").can_assign.filter(code="ASOSCHI").exists()
    assert not Role.objects.get(code="BOSH_MENEJER").can_assign.filter(code="ASOSCHI").exists()
    assert not Role.objects.get(code="FILIAL_MENEJERI").can_assign.filter(code="ASOSCHI").exists()
    assert not RolePermission.objects.filter(role__code="BOSH_MENEJER", section="founderReport").exclude(ops="").exists()


def test_admin_creates_founder_without_email_manager_cannot(api, make_user, branch):
    r = api(make_user("ADMIN")).post("/api/v1/users/", body(branch), format="json")
    assert r.status_code == 201, r.content
    u = User.objects.get(full_name="Muhammad Amin Naziraliyev")
    assert u.role.code == "ASOSCHI" and u.email is None and u.employment_status == "Faol"
    r = api(make_user("BOSH_MENEJER")).post("/api/v1/users/", body(branch, full_name="Boshqa Asoschi"), format="json")
    assert r.status_code == 400 and r.json()["role"] == ["Bu rolni tayinlash huquqingiz yo'q"]


def test_founder_sees_nothing_on_the_site(api, make_user):
    c = api(make_user("ASOSCHI"))
    assert c.get("/api/v1/leads/").status_code == 403 and c.get("/api/v1/payments/").status_code == 403
    assert c.get("/api/v1/audit-log/").status_code == 403 and c.get("/api/v1/calls/").status_code == 403


def test_founder_gets_only_the_short_daily_report(make_user, branch, django_capture_on_commit_callbacks):
    founder, boss = make_user("ASOSCHI"), make_user("BOSH_MENEJER")
    Account.objects.create(name="Emirat g'azna", cash_type="ALL", initial_balance=1_000_000)
    TelegramLink.objects.create(user=founder, chat_id=111)
    TelegramLink.objects.create(user=boss, chat_id=222)
    with django_capture_on_commit_callbacks(execute=True):
        call_command("daily_report")
        services.notify("new_lead", "yangi lid", branch=branch)  # boshqa xabarlar asoschiga bormaydi
        services.notify("approval", "tasdiq", branch=branch)
        services.notify("task", "topshiriq", default_users=[founder], force=True)
        services.notify("sms_problem", "sms", force=True)
    mine = Outbox.objects.filter(chat_id=111)
    assert [m.event for m in mine] == ["founder_report"]
    assert set(Outbox.objects.filter(chat_id=222).values_list("event", flat=True)) >= {"daily_report"}
    assert not Outbox.objects.filter(chat_id=222, event="founder_report").exists()
    short, full = mine[0].text, Outbox.objects.get(chat_id=222, event="daily_report").text
    assert short.startswith("📊 <b>Kunlik hisobot</b>") and "G'azna qoldiqlari" in short and "To'lovlar" in short and "Faol shartnomalar" in short
    assert "Tizim auditi" not in short and "Tizim auditi" in full and "Holat bo'yicha" not in short and "Holat bo'yicha" in full


def test_founder_event_list_has_only_the_report(api, make_user):
    founder = make_user("ASOSCHI")
    d = api(founder).get("/api/v1/notifications/me/").json()
    assert [e["key"] for e in d["events"]] == ["founder_report"]
    assert api(founder).patch("/api/v1/notifications/me/", {"prefs": {"new_lead": True}}, format="json").status_code == 400


def test_short_report_has_one_calls_line_and_no_details(branch, make_user):
    device = CallDevice.objects.create(name="Qabul", branch=branch)
    now = timezone.now()
    CallRecord.objects.create(device=device, branch=branch, external_id="1-1", direction="Javobsiz", number="+998901234567", phone="901234567", started_at=now)
    CallRecord.objects.create(device=device, branch=branch, external_id="2-2", direction="Chiquvchi", number="+998901234568", phone="901234568", started_at=now,
                              duration=95)
    day = timezone.localdate()
    short, full = daily_report.build(day, short=True), daily_report.build(day)
    assert "Qo'ng'iroqlar: 2" in short and "javobsiz 1" in short
    assert "Javobsiz qoldi" not in short and "Eng uzun suhbat" not in short and "Eng uzun suhbat" in full and "Javobsiz qoldi" in full


def test_founder_sample_layout(branch):
    """Asoschi hisobotining tartibi: to'lovlar, shartnomalar, lidlar, qo'ng'iroqlar (ixtiyoriy), xarajatlar, davomat (ixtiyoriy), g'azna — audit yo'q."""
    text = daily_report.build(timezone.localdate(), short=True)
    heads = [h for h in ("To'lovlar", "Faol shartnomalar", "Lidlar", "Xarajatlar", "G'azna qoldiqlari") if h in text]
    assert heads == ["To'lovlar", "Faol shartnomalar", "Lidlar", "Xarajatlar", "G'azna qoldiqlari"] or len(heads) >= 4
    positions = [text.index(h) for h in heads]
    assert positions == sorted(positions) and "🔍" not in text

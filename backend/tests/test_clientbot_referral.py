"""Mijozlar boti B5: tavsiya bonusi — lid o'qishni boshlab to'lov qilganda tavsiya qiluvchiga avtomatik chegirma."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.clientbot import cabinet
from apps.clientbot.models import BotConfig, ClientOutbox, Referral
from apps.crm.models import Lead, Student
from apps.education.models import Contract, Group
from apps.finance import services as fin
from apps.finance.models import Account, CashMovement, Payment
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import Course, CoursePrice, DayPattern, LeadSource, LessonTime, Room
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()


@pytest.fixture
def ref(branch, make_user, api):
    cashier = make_user("ADMINISTRATOR_HISOBCHI")
    boss = make_user("BOSH_MENEJER")
    cash = Account.objects.create(name="Emirat g'azna", cash_type="ALL", initial_balance=0)
    cash.responsible.set([cashier])
    card = Account.objects.create(name="Bosh g'azna", cash_type="CARD", initial_balance=0)
    card.responsible.set([boss])
    branch.default_cashbox, branch.noncash_cashbox = cash, card
    branch.save()
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    CoursePrice.objects.create(branch=branch, course=course, effective_from=datetime.date(2026, 1, 1), price=1_000_000)
    g = Group.objects.create(branch=branch, course=course, day_pattern=DayPattern.objects.create(name="Dush,Chor,Jum", weekdays=[1, 3, 5]),
                             time=LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"), teacher=make_user("USTOZ"),
                             room=Room.objects.create(branch=branch, name="1", capacity=10), start_date=datetime.date(2026, 1, 1), number=1)

    def student(first, phone):
        return Student.objects.create(branch=branch, first_name=first, last_name="Karimov", phone1=phone, phone2="")

    referrer, friend = student("Vali", "901110001"), student("Sardor", "901110002")
    rc = Contract.objects.create(branch=branch, student=referrer, course=course, group=g, number=1, start_date=datetime.date(2026, 9, 1))
    fc = Contract.objects.create(branch=branch, student=friend, course=course, group=g, number=2, start_date=TODAY)
    lead = Lead.objects.create(branch=branch, student=friend, source=LeadSource.objects.create(name="Do'stlar (o'qiydi)"), course=course, status="5")
    r = Referral.objects.create(branch=branch, lead=lead, referrer_student=referrer, referrer_text="Vali", state=Referral.State.PENDING)

    def pay(amount, cash_type="CASH", contract=None):
        body = {"contract": str((contract or fc).pk), "amount": amount, "cash_type": cash_type, "cashbox": str(cash.pk)}
        resp = api(cashier).post("/api/v1/payments/", body, format="json")
        assert resp.status_code == 201, resp.content
        return Payment.objects.get(pk=resp.json()["id"])

    return {"cashier": cashier, "boss": boss, "cash": cash, "referrer": referrer, "friend": friend, "rc": rc, "fc": fc, "lead": lead, "ref": r, "pay": pay,
            "branch": branch, "course": course, "group": g}


def bonus_payments():
    return Payment.objects.filter(discount_type__name="Tavsiya bonusi")


def test_bonus_after_cumulative_payments_reach_threshold(ref, api, on):  # noqa: F811
    ref["pay"](300_000)
    r = Referral.objects.get(pk=ref["ref"].pk)
    assert r.state == "Kutilmoqda" and not bonus_payments().exists()  # oy narxining 50% = 500 000 dan kam
    ref["pay"](200_000)
    r.refresh_from_db()
    assert r.state == "Berildi" and r.bonus == 75_000 and r.paid_at and r.payment.amount == 300_000
    bp = bonus_payments().get()
    assert (bp.contract, bp.amount, bp.discount, bp.discount_status, bp.cash_type) == (ref["rc"], 0, 75_000, "Tasdiqlandi", "")
    assert bp.discount_type.is_system and bp.discount_type.max_amount >= 75_000 and "Sardor" in bp.comment and r.bonus_payment == bp
    assert not CashMovement.objects.filter(source_id=bp.pk).exists()  # g'azna harakati yo'q
    detail = api(ref["cashier"]).get(f"/api/v1/contracts/{ref['rc'].pk}/").json()
    assert detail["balance"] == -75_000  # tavsiya qiluvchining balansi bonus qadar kamaydi (oldindan to'langan)
    assert api(ref["cashier"]).get("/api/v1/payments/").status_code == 200  # yaratuvchisiz yozuv ro'yxatni buzmaydi
    ref["pay"](500_000)  # keyingi to'lovlarda takror berilmaydi
    assert bonus_payments().count() == 1


def test_configurable_amount_percent_and_disable(ref, on):  # noqa: F811
    BotConfig.objects.create(branch=ref["branch"], referral_bonus=120_000, referral_min_percent=20)
    ref["pay"](200_000)  # 20% = 200 000
    r = Referral.objects.get(pk=ref["ref"].pk)
    assert r.state == "Berildi" and r.bonus == 120_000 and bonus_payments().get().discount == 120_000


def test_bonus_zero_disables(ref, on):  # noqa: F811
    BotConfig.objects.create(branch=ref["branch"], referral_bonus=0)
    ref["pay"](1_000_000)
    assert Referral.objects.get(pk=ref["ref"].pk).state == "Kutilmoqda" and not bonus_payments().exists()


def test_noncash_counts_only_after_confirmation(ref, on):  # noqa: F811
    p = ref["pay"](600_000, "CARD")
    assert p.noncash_status == "Tasdiqlashga"
    assert Referral.objects.get(pk=ref["ref"].pk).state == "Kutilmoqda"
    fin.approve_noncash(ref["boss"], p)
    assert Referral.objects.get(pk=ref["ref"].pk).state == "Berildi" and bonus_payments().count() == 1


def test_no_active_contract_for_referrer_rejects_and_tells_manager(ref, django_capture_on_commit_callbacks, on):  # noqa: F811
    TelegramLink.objects.create(user=ref["boss"], chat_id=777)
    Contract.objects.filter(pk=ref["rc"].pk).update(end_date=datetime.date(2026, 9, 30), stop_reason="Kursni tamomladi")
    with django_capture_on_commit_callbacks(execute=True):
        ref["pay"](600_000)
    r = Referral.objects.get(pk=ref["ref"].pk)
    assert r.state == "Rad etildi" and "faol shartnomasi yo'q" in r.comment and not bonus_payments().exists()
    note = Outbox.objects.get(event="referral")
    assert note.chat_id == 777 and "Tavsiya bonusi berilmadi" in note.text


def test_grant_contract_of_referrer_is_not_used(ref, on):  # noqa: F811
    Contract.objects.filter(pk=ref["rc"].pk).update(type="Grant")
    ref["pay"](600_000)
    assert Referral.objects.get(pk=ref["ref"].pk).state == "Rad etildi"


def test_admin_binding_after_payment_grants_immediately(ref, api, on):  # noqa: F811
    Referral.objects.filter(pk=ref["ref"].pk).update(referrer_student=None, state="Aniqlanmagan")
    ref["pay"](600_000)
    assert Referral.objects.get(pk=ref["ref"].pk).state == "Aniqlanmagan"
    r = api(ref["boss"]).patch(f"/api/v1/bot-referrals/{ref['ref'].pk}/", {"referrer_student": str(ref["referrer"].pk)}, format="json")
    assert r.status_code == 200 and r.json()["state"] == "Berildi" and r.json()["bonus"] == 75000
    assert bonus_payments().count() == 1


def test_referrer_and_manager_are_notified_and_cabinet_shows_bonus(ref, django_capture_on_commit_callbacks, on):  # noqa: F811
    TelegramLink.objects.create(user=ref["boss"], chat_id=888)
    link_phone(ref["referrer"], ref["referrer"].phone1, 5)
    with django_capture_on_commit_callbacks(execute=True):
        ref["pay"](500_000)
    msg = ClientOutbox.objects.get(kind="Bonus")
    assert msg.account.chat_id == 5 and "Sardor" in msg.text and "75 000" in msg.text and "keyingi to'lovingizdan ayiriladi" in msg.text
    note = Outbox.objects.get(event="referral")
    assert "Tavsiya bonusi berildi" in note.text and "Vali Karimov" in note.text and "Sardor Karimov" in note.text
    t = cabinet.payments_text(ref["referrer"])
    assert "🎁 chegirma <b>75 000</b> so'm (Tavsiya bonusi)" in t and "oldindan to'langan <b>75 000</b>" in t


def test_discount_only_and_unreferred_payments_do_nothing(ref, api, make_user, on):  # noqa: F811
    c = api(ref["cashier"])
    # tavsiyasiz talaba to'lov qilsa — bonus yo'q
    ref["pay"](600_000, contract=ref["rc"])
    assert not bonus_payments().exists() and Referral.objects.get(pk=ref["ref"].pk).state == "Kutilmoqda"
    # aniqlanmagan tavsiya — bonus yo'q
    Referral.objects.filter(pk=ref["ref"].pk).update(state="Aniqlanmagan", referrer_student=None)
    ref["pay"](600_000)
    assert not bonus_payments().exists()
    assert Decimal(c.get("/api/v1/payments/").json()["total"]) == 1_200_000

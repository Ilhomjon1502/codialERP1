"""Mijozlar boti: to'lov kiritilganda botga ulangan o'quvchi va vasiylarga xabar."""

import pytest

from apps.clientbot import payment_notice
from apps.clientbot.models import BotAccount, BotConfig, ClientOutbox
from apps.finance.models import Payment
from apps.references.models import DiscountType
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_clientbot_referral import ref  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db


def kinds(kind="To'lov"):
    return ClientOutbox.objects.filter(kind=kind)


def link_family(ref):  # noqa: F811
    """O'quvchi (1-telefon) va vasiy (2-telefon) — ikki alohida Telegram akkaunt."""
    st = ref["friend"]
    Student = type(st)
    Student.objects.filter(pk=st.pk).update(phone2="901110099")
    st.refresh_from_db()
    link_phone(st, st.phone1, 1)
    link_phone(st, st.phone2, 2)
    return st


def test_payment_notifies_student_and_guardian(ref, on):  # noqa: F811
    link_family(ref)
    p = ref["pay"](300_000)
    msgs = kinds().order_by("account__chat_id")
    assert [m.account.chat_id for m in msgs] == [1, 2] and all(m.key == f"payment:{p.pk}" and m.contract == ref["fc"] for m in msgs)
    t = msgs[0].text
    assert "To'lov qabul qilindi" in t and "Sardor Karimov" in t and "Frontend" in t and "<b>300 000</b> so'm (naqd)" in t
    assert f"chek №{p.number}" in t and "oldindan to'langan <b>300 000</b>" in t and "⏳" not in t and "Chegirma" not in t


def test_debt_balance_discount_and_noncash_note(ref, api, on):  # noqa: F811
    link_family(ref)
    dt = DiscountType.objects.create(name="Rag'batlantiruvchi", max_amount=100_000)
    body = {"contract": str(ref["fc"].pk), "amount": 100_000, "cash_type": "CARD", "discount": 50_000, "discount_type": str(dt.pk)}
    r = api(ref["cashier"]).post("/api/v1/payments/", body, format="json")
    assert r.status_code == 201, r.content
    t = kinds().first().text
    assert "Chegirma: 50 000 so'm" in t and "(karta)" in t and "⏳ Naqdsiz to'lov tasdiqlanishi kutilmoqda" in t


def test_unlinked_blocked_and_disabled_get_nothing(ref, on):  # noqa: F811
    ref["pay"](100_000)  # hech kim ulanmagan
    assert not kinds().exists()
    link_family(ref)
    BotAccount.objects.filter(chat_id=2).update(blocked=True)
    ref["pay"](100_000)
    assert [m.account.chat_id for m in kinds()] == [1]
    BotConfig.objects.update_or_create(branch=ref["branch"], defaults={"notify_payments": False})
    ref["pay"](100_000)
    assert kinds().count() == 1  # sozlama o'chiq — yangi xabar yo'q


def test_discount_only_edit_and_delete_do_not_notify_and_failure_is_harmless(ref, api, monkeypatch, on):  # noqa: F811
    link_family(ref)
    p = ref["pay"](200_000)
    assert kinds().count() == 2
    c = api(ref["cashier"])
    assert c.patch(f"/api/v1/payments/{p.pk}/", {"amount": 250_000}, format="json").status_code == 200  # tahrir — qayta xabar yo'q
    assert kinds().count() == 2
    assert c.delete(f"/api/v1/payments/{p.pk}/").status_code in (200, 204)
    assert kinds().count() == 2
    monkeypatch.setattr(payment_notice, "text_for", lambda p: 1 / 0)  # xabar tayyorlashda xato — to'lov baribir saqlanadi
    ref["pay"](100_000)
    assert Payment.objects.filter(amount=100_000).count() == 1


def test_referral_bonus_goes_to_referrer_and_payment_notice_only_to_payer(ref, on):  # noqa: F811
    link_phone(ref["referrer"], ref["referrer"].phone1, 5)
    link_phone(ref["friend"], ref["friend"].phone1, 6)
    ref["pay"](600_000)  # bonus ham tushadi
    assert [m.account.chat_id for m in kinds()] == [6]  # to'lov xabari — faqat to'lagan talabaga
    assert [m.account.chat_id for m in kinds("Bonus")] == [5]  # bonus xabari — tavsiya qiluvchiga; chegirma-only yozuvga to'lov xabari yo'q

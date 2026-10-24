"""Tavsiya bonusi (B5): lid «tanishimdan eshitdim» degan va tavsiya qiluvchi (shartnomali talaba) aniqlangan bo'lsa, lid **o'qishni boshlab to'lov qilganda**
tavsiya qiluvchiga bonus avtomatik beriladi.

Shart (filial sozlamasi `BotConfig`): lidning haqiqiy to'lovlari (naqd yoki tasdiqlangan naqdsiz) yig'indisi kurs oylik narxining kamida `referral_min_percent` foizi;
tavsiya qiluvchining faol (Pullik) shartnomasi bor. Bonus — `referral_bonus` so'm.
Bonus tavsiya qiluvchining shartnomasiga chegirma sifatida yoziladi: summasi 0, chegirma = bonus, turi «Tavsiya bonusi» (tizim turi) — shartnoma balansi
va «To'lovga tavsiya» hisobidan avtomatik ayriladi, ya'ni keyingi to'lovda to'lanadigan summa shuncha kamayadi. G'azna harakati yo'q.
Har tavsiyaga bir marta (`Referral.state` = Berildi). Tavsiya qiluvchiga botda xabar, Bosh menejerga Telegram'da xabar.
"""

import logging
from decimal import Decimal
from html import escape

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core import audit
from apps.education.calc import Calculator
from apps.education.models import Contract
from apps.education.services import NOFAOL, period_status
from apps.finance.models import Confirm, Payment
from apps.finance.services import next_payment_number
from apps.references.models import DiscountType

from . import services as bot
from .models import BotAccount, ClientOutbox, Referral

log = logging.getLogger(__name__)
BONUS_TYPE = "Tavsiya bonusi"


def real_payments(student):
    """Talabaning haqiqiy pul to'lovlari: naqd yoki tasdiqlangan naqdsiz (chegirma-only yozuvlar hisobga kirmaydi)."""
    return (Payment.objects.filter(contract__student=student, is_deleted=False, amount__gt=0)
            .filter(Q(cash_type="CASH") | Q(noncash_status=Confirm.CONFIRMED)))


def _threshold(payment, percent):
    c = payment.contract
    price = Calculator().price(c.branch_id, c.course_id, payment.date.replace(day=1))
    return None if price is None else Decimal(price) * percent / 100


def _bonus_type(amount):
    dt = DiscountType.objects.filter(name=BONUS_TYPE).first()
    if dt is None:
        return DiscountType.objects.create(name=BONUS_TYPE, max_amount=amount, is_system=True)
    if dt.max_amount < amount:
        dt.max_amount = amount
        dt.save(update_fields=["max_amount"])
    return dt


def referrer_contract(student, today=None):
    """Tavsiya qiluvchining faol yoki boshlanmagan Pullik shartnomasi (eng yangisi)."""
    today = today or timezone.localdate()
    cs = Contract.objects.filter(student=student, is_deleted=False, type=Contract.Type.PAID).select_related("branch", "group").order_by("-start_date")
    return next((c for c in cs if period_status(c.start_date, c.end_date, today) != NOFAOL), None)


def evaluate(ref):
    """Bonus shartini tekshiradi va bajarilsa beradi. Qaytaradi: yangi holat (yoki None — hech narsa o'zgarmadi)."""
    if ref.state != Referral.State.PENDING or not ref.referrer_student_id:
        return None
    cfg = bot.get_config(ref.branch)
    bonus = Decimal(cfg.referral_bonus or 0)
    if bonus <= 0:
        return None
    student = ref.lead.student
    pays = list(real_payments(student).select_related("contract").order_by("date", "created_at"))
    if not pays:
        return None
    need = _threshold(pays[0], cfg.referral_min_percent)
    if need is None or sum((p.amount for p in pays), Decimal(0)) < need:
        return None
    contract = referrer_contract(ref.referrer_student)
    if contract is None:
        ref.state, ref.comment = Referral.State.REJECTED, "Tavsiya qiluvchining faol shartnomasi yo'q — bonus berilmadi"
        ref.save(update_fields=["state", "comment", "updated_at"])
        _notify_staff(ref, None)
        return ref.state
    now = timezone.now()
    p = Payment(branch=contract.branch, contract=contract, group=contract.group, number=next_payment_number(contract.branch), date=timezone.localdate(), amount=0,
                discount=bonus, discount_type=_bonus_type(bonus), discount_status=Confirm.CONFIRMED, discount_confirmed_at=now,
                comment=f"Tavsiya bonusi: {student.first_name} {student.last_name}".strip())
    p.save()
    audit.log_create(None, p, detail="Tavsiya bonusi (avtomatik)")
    ref.state, ref.bonus, ref.payment, ref.bonus_payment, ref.paid_at = Referral.State.PAID, bonus, pays[0], p, now
    ref.save(update_fields=["state", "bonus", "payment", "bonus_payment", "paid_at", "updated_at"])
    _notify_referrer(ref, student, bonus)
    _notify_staff(ref, p)
    return ref.state


def on_payment(payment):
    """To'lov saqlandi yoki naqdsiz to'lov tasdiqlandi: shu talaba tavsiya orqali kelgan bo'lsa — bonus shartini tekshiradi. Xato to'lovni buzmaydi."""
    if not payment.amount:
        return
    try:
        with transaction.atomic():
            ref = (Referral.objects.select_for_update().select_related("lead__student", "branch", "referrer_student")
                   .filter(lead__student=payment.contract.student, state=Referral.State.PENDING).first())
            if ref:
                evaluate(ref)
    except Exception:  # noqa: BLE001
        log.exception("Tavsiya bonusi tekshirilmadi")


def _notify_referrer(ref, friend, bonus):
    accounts = BotAccount.objects.filter(links__student=ref.referrer_student, links__is_active=True, blocked=False).distinct()
    text = (f"🎁 <b>Tabriklaymiz!</b> Siz tavsiya qilgan <b>{escape(friend.first_name)}</b> Codialda o'qishni boshladi.\n"
            f"Sizga <b>{bot_money(bonus)}</b> so'm bonus berildi — keyingi to'lovingizdan ayiriladi. Rahmat! 🙏")
    for acc in accounts:
        if not ClientOutbox.objects.filter(account=acc, key=f"referral:{ref.pk}").exists():
            ClientOutbox.objects.create(account=acc, kind="Bonus", key=f"referral:{ref.pk}", text=text, student=ref.referrer_student)


def bot_money(v):
    return f"{int(v):,}".replace(",", " ")


def _notify_staff(ref, bonus_payment):
    from apps.notifications import services as notif

    who, friend = escape(ref.referrer_student.full_name), escape(ref.lead.student.full_name)
    if bonus_payment is not None:
        text = f"🎁 <b>Tavsiya bonusi berildi</b>\n{who} ← {friend}\nChegirma: {bot_money(ref.bonus)} so'm (shartnomasiga yozildi)"
    else:
        text = f"⚠️ <b>Tavsiya bonusi berilmadi</b>\n{who} ← {friend}\n{escape(ref.comment)}"
    notif.notify("referral", text, branch=ref.branch, key=f"referral:{ref.pk}")

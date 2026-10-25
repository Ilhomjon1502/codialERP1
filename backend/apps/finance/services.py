"""Moliya servislari: yagona pul harakatlari jurnali (ledger), g'azna balansi va pul amallari qoidalari (CLAUDE.md 7.5).

Har bir amal (to'lov, xarajat, o'tkazma, ayirboshlash, kreditor) saqlanganda `sync_movements` uning CashMovement qatorlarini
qayta yozadi; o'chirilsa — qatorlari o'chiriladi. G'azna balansi = boshlang'ich qoldiq + Σ tasdiqlangan harakatlar.
"""

import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.models import Status
from apps.core.permissions import NO_PERMISSION, can, check_edit_window, is_top, role_code, sees_all, today
from apps.core.roles import RoleCode
from apps.core.scoping import branch_ids
from apps.core.services import soft_delete
from apps.notifications import services as notif

from .models import (
    Account,
    CashMovement,
    CashType,
    Confirm,
    CreditorTransaction,
    Exchange,
    Expense,
    Payment,
    Transfer,
)

S = CashMovement.Source
MONEY = (CashType.CASH, CashType.CARD, CashType.BANK)
DISCOUNT_BM_DAYS = 30
NONCASH_DAYS = {RoleCode.BOSH_MENEJER: 360, RoleCode.FILIAL_MENEJERI: 7}
CREDITOR_DAYS = 7


def fmt(n):
    return f"{Decimal(n):,.0f}".replace(",", " ")


# ------------------------------------------------------------------ g'aznalar va balans

def my_accounts(user):
    """Foydalanuvchi pul qabul qila/chiqara oladigan faol g'aznalar: Admin va Bosh menejer — hammasi (buyurtmachi qarori 2026-10-13),
    boshqalar — mas'ul bo'lganlari."""
    qs = Account.objects.filter(status=Status.ACTIVE)
    return qs if is_top(user) else qs.filter(responsible=user)


def scoped_account_ids(user):
    """Ko'rinadigan g'aznalar: Admin va Bosh menejer — hammasi (None); boshqalar — mas'ul bo'lganlari va o'z filiallari g'aznalari."""
    if sees_all(user):
        return None
    ids = set(Account.objects.filter(responsible=user).values_list("id", flat=True))
    from apps.references.models import Branch

    for b in Branch.objects.filter(pk__in=branch_ids(user) or []):
        ids.update(x for x in (b.default_cashbox_id, b.noncash_cashbox_id) if x)
    return ids


def balances(account_ids=None):
    """{account_id: {"balance", "by_type": {CASH: ...}, "pending"}} — ikki aggregatsiya so'rovi bilan."""
    accs = Account.objects.all() if account_ids is None else Account.objects.filter(pk__in=account_ids)
    out = {}
    for a in accs:
        out[a.pk] = {"balance": Decimal(a.initial_balance), "by_type": {a.base_type: Decimal(a.initial_balance)}, "pending": Decimal(0)}
    mv = CashMovement.objects.filter(account_id__in=out.keys())
    for acc, ct, s in mv.filter(is_confirmed=True).values_list("account_id", "cash_type").annotate(s=Sum("amount")).values_list("account_id", "cash_type", "s"):
        out[acc]["balance"] += s
        out[acc]["by_type"][ct] = out[acc]["by_type"].get(ct, Decimal(0)) + s
    for acc, s in mv.filter(is_confirmed=False).values_list("account_id").annotate(s=Sum("amount")).values_list("account_id", "s"):
        out[acc]["pending"] += s
    return out


def balance(account, cash_type=None, exclude=None):
    """Tasdiqlangan balans (pul turi bo'yicha). exclude=(source_type, source_id) — tahrirlanayotgan amalning o'z qatorlari hisobga olinmaydi."""
    b = Decimal(account.initial_balance) if cash_type in (None, account.base_type) else Decimal(0)
    qs = CashMovement.objects.filter(account=account, is_confirmed=True)
    if cash_type:
        qs = qs.filter(cash_type=cash_type)
    if exclude:
        qs = qs.exclude(source_type=exclude[0], source_id=exclude[1])
    return b + (qs.aggregate(s=Sum("amount"))["s"] or 0)


def check_funds(user, account, cash_type, amount, exclude=None):
    """Chiqim g'azna qoldig'idan oshmasin (Admin va Bosh menejerdan tashqari)."""
    if is_top(user):
        return
    avail = balance(account, cash_type, exclude)
    if amount > avail:
        raise ValidationError({"amount": "G'aznada pul yo'q" if avail <= 0 else f"G'aznada {fmt(avail)} so'm pul bor"})


def sync_movements(source_type, obj, rows):
    """rows: [(account, cash_type, amount, is_confirmed, note)] — manbaning eski qatorlari o'chirilib, yangilari yoziladi."""
    CashMovement.objects.filter(source_type=source_type, source_id=obj.pk).delete()
    CashMovement.objects.bulk_create([
        CashMovement(account=acc, cash_type=ct, amount=amt, date=obj.date, source_type=source_type, source_id=obj.pk, is_confirmed=ok, note=str(note)[:255])
        for acc, ct, amt, ok, note in rows if amt
    ])


def check_account_type(account, cash_type, field="cashbox"):
    if account.cash_type not in (CashType.ALL, cash_type):
        raise ValidationError({field: f"«{account}» g'aznasi {account.get_cash_type_display().lower()} pul uchun"})


def _pick_cashier(user, account, given, field):
    ids = set(account.responsible.values_list("id", flat=True))
    if given:
        if given.pk not in ids:
            raise ValidationError({field: "G'azna mas'ullaridan biri bo'lsin"})
        return given
    if user.pk in ids:
        return user
    return account.responsible.order_by("full_name").first()


def _update(instance, user, d):
    before = audit.snapshot(instance)
    for k, v in d.items():
        setattr(instance, k, v)
    instance.updated_by = user
    instance.save()
    return before


def _check_new_date(user, section, d, msg_future="Kelasi davr bilan kiritib bo'lmaydi"):
    if d > today():
        raise ValidationError({"date": msg_future})
    check_edit_window(user, section, d, op="a")


# ------------------------------------------------------------------ to'lovlar

def next_payment_number(branch):
    return (Payment.all_objects.filter(branch=branch).aggregate(m=Max("number"))["m"] or 0) + 1


def payment_rows(p):
    if not p.amount:
        return []
    ok = p.cash_type == CashType.CASH or p.noncash_status == Confirm.CONFIRMED
    return [(p.cashbox, p.cash_type, p.amount, ok, p.contract)]


def _validate_payment(user, d, instance):
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    contract = get("contract")
    if instance is not None and "contract" in d and contract.pk != instance.contract_id:
        raise ValidationError({"contract": "Shartnomani o'zgartirib bo'lmaydi"})
    pay_date = get("date")
    if pay_date > today():
        raise ValidationError({"date": "Kelasi davr bilan kiritib bo'lmaydi"})
    if not is_top(user) and (instance is None or "date" in d) and pay_date != today():
        raise ValidationError({"date": "Faqat bugun bilan kiritish mumkin, xolos"})
    amount, discount = Decimal(get("amount") or 0), Decimal(get("discount") or 0)
    if amount < 0 or discount < 0:
        raise ValidationError({"amount": "Manfiy summa kiritib bo'lmaydi"})
    if not amount and not discount:
        raise ValidationError({"amount": "To'lov summasi yoki chegirma kiritilishi kerak"})
    out = {"branch": contract.branch, "group": contract.group, "amount": amount, "discount": discount}
    if amount:
        ct = get("cash_type")
        if ct not in MONEY:
            raise ValidationError({"cash_type": "To'lov shaklini tanlang"})
        if ct == CashType.CASH:
            box = get("cashbox")
            if box is None or not my_accounts(user).filter(pk=box.pk).exists():
                raise ValidationError({"cashbox": "Siz mas'ul bo'lgan faol g'aznani tanlang"})
            check_account_type(box, ct)
        else:
            box = contract.branch.noncash_cashbox
            if box is None:
                raise ValidationError({"cashbox": "Filial sozlamasida naqdsiz to'lovlar g'aznasi belgilanmagan"})
        out.update(cash_type=ct, cashbox=box, accountant=_pick_cashier(user, box, d.get("accountant"), "accountant"))
    else:
        out.update(cash_type="", cashbox=None, accountant=None)
    dtype = get("discount_type")
    if discount:
        if dtype is None:
            raise ValidationError({"discount_type": "Chegirma turini tanlang"})
        if dtype.is_system and not is_top(user):
            raise ValidationError({"discount_type": "Bu chegirma turini faqat Admin va Bosh menejer qo'llaydi"})
        if discount > dtype.max_amount:
            raise ValidationError({"discount": f"Bu chegirma turiga {fmt(dtype.max_amount)} so'mdan ortiqcha chegirma kiritib bo'lmaydi"})
        courses = list(dtype.courses.values_list("id", flat=True))
        if courses and contract.course_id not in courses:
            raise ValidationError({"discount_type": "Bu chegirma turi shartnoma kursiga tegishli emas"})
    else:
        out["discount_type"] = None
    return out


@transaction.atomic
def save_payment(user, d, instance=None):
    d = dict(d)
    if instance is not None:
        if instance.locked and not is_top(user):
            raise PermissionDenied("Tasdiqlangan to'lov va chegirmani faqat Admin va Bosh menejer o'zgartiradi")
        check_edit_window(user, "payments", instance.date)
    d.update(_validate_payment(user, d, instance))
    if instance is None:
        p = Payment(**d, number=next_payment_number(d["branch"]), created_by=user, updated_by=user)
        p.discount_status = Confirm.PENDING if p.discount else ""
        p.noncash_status = Confirm.PENDING if p.amount and p.cash_type != CashType.CASH else ""
        p.save()
        audit.log_create(user, p)
    else:
        p = instance
        old = (p.discount, p.discount_type_id, p.amount, p.cash_type)
        before = _update(p, user, d)
        if (p.discount, p.discount_type_id) != old[:2]:
            p.discount_status, p.discount_confirmed_by, p.discount_confirmed_at = (Confirm.PENDING if p.discount else ""), None, None
        if (p.amount, p.cash_type) != old[2:]:
            p.noncash_status, p.noncash_confirmed_by, p.noncash_confirmed_at = (Confirm.PENDING if p.amount and p.cash_type != CashType.CASH else ""), None, None
        p.save()
        audit.log_update(user, p, before)
    sync_movements(S.PAYMENT, p, payment_rows(p))
    if instance is None or (p.discount_status == Confirm.PENDING and p.discount_confirmed_by is None and "discount" in d) or "amount" in d:
        notif.payment_pending(p)
    if instance is None:
        _client_notice(p)
    _referral_check(p)
    return p


def _client_notice(p):
    """Yangi to'lov — botga ulangan o'quvchi va vasiylarga xabar (mijozlar boti)."""
    from apps.clientbot import payment_notice

    payment_notice.notify(p)


def _referral_check(p):
    """Tavsiya bonusi (mijozlar boti): to'lov tavsiya orqali kelgan lidniki bo'lsa — shart bajarilganda tavsiya qiluvchiga bonus."""
    from apps.clientbot import referrals

    referrals.on_payment(p)


@transaction.atomic
def delete_payment(user, p):
    if p.locked and not is_top(user):
        raise PermissionDenied("Tasdiqlangan to'lov va chegirmani faqat Admin va Bosh menejer o'zgartiradi")
    check_edit_window(user, "payments", p.date, op="d")
    soft_delete(p, user, check_usage=False)
    sync_movements(S.PAYMENT, p, [])


def _age_days(obj):
    return (today() - timezone.localtime(obj.created_at).date()).days


def can_approve_discount(user, p):
    code = role_code(user)
    return code == RoleCode.ADMIN or (code == RoleCode.BOSH_MENEJER and _age_days(p) <= DISCOUNT_BM_DAYS)


def can_approve_noncash(user, p):
    code = role_code(user)
    if code == RoleCode.ADMIN:
        return True
    days = NONCASH_DAYS.get(code)
    return days is not None and can(user, "payments", "p") and _age_days(p) <= days


@transaction.atomic
def approve_discount(user, p):
    if p.discount_status != Confirm.PENDING:
        raise ValidationError({"detail": "Tasdiq kutayotgan chegirma yo'q"})
    if not can_approve_discount(user, p):
        raise PermissionDenied(f"Chegirmani Admin, Bosh menejer esa {DISCOUNT_BM_DAYS} kun ichida tasdiqlaydi")
    before = audit.snapshot(p)
    p.discount_status, p.discount_confirmed_by, p.discount_confirmed_at, p.updated_by = Confirm.CONFIRMED, user, timezone.now(), user
    p.save()
    audit.log_update(user, p, before, detail="Chegirma tasdiqlandi")
    return p


@transaction.atomic
def approve_noncash(user, p):
    if p.noncash_status != Confirm.PENDING:
        raise ValidationError({"detail": "Tasdiq kutayotgan naqdsiz to'lov yo'q"})
    if not can_approve_noncash(user, p):
        raise PermissionDenied("Naqdsiz to'lovni Admin; Bosh menejer 360 kun, Filial menejeri 7 kun ichida tasdiqlaydi")
    before = audit.snapshot(p)
    p.noncash_status, p.noncash_confirmed_by, p.noncash_confirmed_at, p.updated_by = Confirm.CONFIRMED, user, timezone.now(), user
    p.save()
    sync_movements(S.PAYMENT, p, payment_rows(p))
    audit.log_update(user, p, before, detail="Naqdsiz to'lov tasdiqlandi — g'azna balansiga qo'shildi")
    _referral_check(p)
    return p


# ------------------------------------------------------------------ ichki o'tkazmalar

def transfer_rows(t):
    ok = t.status == Confirm.CONFIRMED
    return [(t.sender_account, t.cash_type, -t.amount, ok, f"→ {t.receiver_account}"), (t.receiver_account, t.cash_type, t.amount, ok, f"← {t.sender_account}")]


def can_modify_pending(user, t):
    """Tasdiqlanmagan o'tkazmani (tranzit) tahrirlash va o'chirish — buyurtmachi qarori 2026-10-19: tasdiqlanmaguncha sana muddatisiz,
    yaratgan xodim, jo'natuvchi g'azna mas'uli (Administrator+Hisobchi, Hisobchi), Admin va Bosh menejer."""
    return t.status == Confirm.PENDING and (is_top(user) or t.created_by_id == user.pk or t.sender_account.responsible.filter(pk=user.pk).exists())


@transaction.atomic
def save_transfer(user, d, instance=None):
    d = dict(d)
    if instance is not None:
        if instance.status == Confirm.PENDING:
            if not can_modify_pending(user, instance):
                raise PermissionDenied("Tasdiqlanmagan o'tkazmani uni yaratgan, jo'natuvchi g'azna mas'uli, Admin yoki Bosh menejer o'zgartiradi")
        else:
            if role_code(user) != RoleCode.ADMIN and any(k in d and d[k] != getattr(instance, k) for k in ("amount", "cash_type", "sender_account", "receiver_account")):
                raise PermissionDenied("Tasdiqlangan o'tkazma summasi, pul turi va g'aznalarini faqat Admin o'zgartiradi")
            if not is_top(user):
                raise PermissionDenied("Tasdiqlangan o'tkazmani faqat Admin va Bosh menejer o'zgartiradi")
            check_edit_window(user, "transfers", instance.date)
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    sender, receiver, amount = get("sender_account"), get("receiver_account"), Decimal(get("amount") or 0)
    d["date"] = get("date") or today()
    if d["date"] > today():
        raise ValidationError({"date": "Kelajak sana bo'lishi mumkin emas"})
    if not is_top(user) and d["date"] != today() and (instance is None or d["date"] != instance.date):
        raise ValidationError({"date": "Sanani faqat Admin va Bosh menejer o'zgartiradi"})
    if (instance is None or sender.pk != instance.sender_account_id) and not my_accounts(user).filter(pk=sender.pk).exists():
        raise ValidationError({"sender_account": "Siz mas'ul bo'lgan faol g'aznani tanlang"})
    if receiver.status != Status.ACTIVE or receiver.pk == sender.pk:
        raise ValidationError({"receiver_account": "Boshqa faol g'aznani tanlang"})
    d["cash_type"] = CashType.CASH  # o'tkazma faqat naqd pul uchun (7.5)
    if amount <= 0:
        raise ValidationError({"amount": "0 dan katta bo'lsin"})
    check_funds(user, sender, CashType.CASH, amount, exclude=(S.TRANSFER, instance.pk) if instance else None)
    d["sender_cashier"] = _pick_cashier(user, sender, d.get("sender_cashier"), "sender_cashier")
    d["receiver_cashier"] = _pick_cashier(user, receiver, d.get("receiver_cashier"), "receiver_cashier") if "receiver_cashier" in d or instance is None else instance.receiver_cashier
    if instance is None:
        t = Transfer.objects.create(**d, created_by=user, updated_by=user)
        audit.log_create(user, t)
        notif.transfer_created(t)
    else:
        t = instance
        before = _update(t, user, d)
        audit.log_update(user, t, before)
        notif.transfer_changed(t, "o'zgardi", user)
    sync_movements(S.TRANSFER, t, transfer_rows(t))
    return t


def can_confirm_transfer(user, t):
    return role_code(user) == RoleCode.ADMIN or t.receiver_account.responsible.filter(pk=user.pk).exists()


@transaction.atomic
def confirm_transfer(user, t):
    if t.status != Confirm.PENDING:
        raise ValidationError({"detail": "O'tkazma allaqachon tasdiqlangan"})
    if not can_confirm_transfer(user, t):
        raise PermissionDenied("O'tkazmani qabul qiluvchi g'azna mas'uli yoki Admin tasdiqlaydi")
    before = audit.snapshot(t)
    t.status, t.confirmed_by, t.confirmed_at, t.updated_by = Confirm.CONFIRMED, user, timezone.now(), user
    t.save()
    sync_movements(S.TRANSFER, t, transfer_rows(t))
    audit.log_update(user, t, before, detail="O'tkazma qabul qilindi")
    return t


@transaction.atomic
def delete_transfer(user, t):
    if t.status == Confirm.PENDING:
        if not can_modify_pending(user, t):
            raise PermissionDenied("Tasdiqlanmagan o'tkazmani uni yaratgan, jo'natuvchi g'azna mas'uli, Admin yoki Bosh menejer o'chiradi")
    else:
        if not is_top(user):
            raise PermissionDenied("Tasdiqlangan o'tkazmani faqat Admin va Bosh menejer o'chiradi")
        check_edit_window(user, "transfers", t.date, op="d")
    soft_delete(t, user, check_usage=False)
    sync_movements(S.TRANSFER, t, [])
    if t.status == Confirm.PENDING:
        notif.transfer_changed(t, "bekor qilindi", user)


# ------------------------------------------------------------------ pul ayirboshlash

@transaction.atomic
def save_exchange(user, d):
    """Faqat Admin va Bosh menejer (bo'lim ruxsati). Sana — bugun. Olingan ≤ berilgan; yo'qotish = farq."""
    d = dict(d, date=today())
    acc = d["account"]
    if not my_accounts(user).filter(pk=acc.pk).exists():
        raise ValidationError({"account": "Faol g'aznani tanlang"})
    if d["from_type"] == d["to_type"]:
        raise ValidationError({"to_type": "Boshqa pul turini tanlang"})
    if d["amount"] <= 0:
        raise ValidationError({"amount": "0 dan katta bo'lsin"})
    if d["amount_to"] > d["amount"]:
        raise ValidationError({"amount_to": f"{fmt(d['amount'])} dan katta bo'lolmaydi"})
    x = Exchange.objects.create(**d, created_by=user, updated_by=user)
    sync_movements(S.EXCHANGE, x, [(acc, x.from_type, -x.amount, True, f"{x.get_from_type_display()} → {x.get_to_type_display()}"),
                                   (acc, x.to_type, x.amount_to, True, f"{x.get_from_type_display()} → {x.get_to_type_display()}")])
    audit.log_create(user, x)
    return x


@transaction.atomic
def delete_exchange(user, x):
    soft_delete(x, user, check_usage=False)
    sync_movements(S.EXCHANGE, x, [])


# ------------------------------------------------------------------ xarajatlar

@transaction.atomic
def save_expense(user, d, instance=None):
    d = dict(d)
    if instance is not None:
        check_edit_window(user, "expenses", instance.date)
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    exp_date, category, account, ct = get("date"), get("category"), get("account"), get("cash_type")
    if instance is None or "date" in d:
        _check_new_date(user, "expenses", exp_date, "Kelajak sana bo'lishi mumkin emas")
    if (instance is None or "category" in d) and not category.allowed_roles.filter(code=role_code(user)).exists():
        raise ValidationError({"category": "Bu kategoriyaga sizning rolingiz xarajat kirita olmaydi"})
    if ct not in MONEY:
        raise ValidationError({"cash_type": "To'lov shaklini tanlang"})
    if (instance is None or "account" in d) and not my_accounts(user).filter(pk=account.pk).exists():
        raise ValidationError({"account": "Siz mas'ul bo'lgan faol g'aznani tanlang"})
    check_account_type(account, ct, "account")
    qty, price = int(get("quantity") or 0), Decimal(get("price") or 0)
    if qty < 1:
        raise ValidationError({"quantity": "Kamida 1"})
    if price < 0:
        raise ValidationError({"price": "Manfiy bo'lmasin"})
    d["total"] = qty * price
    if not (d.get("name") or get("name") or "").strip():
        raise ValidationError({"name": "Majburiy maydon"})
    # Hisob davri: standart — sanadan; boshqa davrni faqat Admin va Bosh menejer qo'yadi
    py, pm = d.pop("period_year", None), d.pop("period_month", None)
    if is_top(user) and py and pm:
        d["period_year"], d["period_month"] = int(py), int(pm)
    elif instance is None or "date" in d:
        d["period_year"], d["period_month"] = exp_date.year, exp_date.month
    try:
        check_funds(user, account, ct, d["total"], exclude=(S.EXPENSE, instance.pk) if instance else None)
    except ValidationError as e:
        raise ValidationError({"price": e.detail["amount"]}) from e
    d["cashier"] = _pick_cashier(user, account, d.get("cashier"), "cashier")
    if instance is None:
        e = Expense.objects.create(**d, created_by=user, updated_by=user)
        audit.log_create(user, e)
    else:
        e = instance
        before = _update(e, user, d)
        audit.log_update(user, e, before)
    sync_movements(S.EXPENSE, e, [(e.account, e.cash_type, -e.total, True, f"{e.category}: {e.name}")])
    return e


@transaction.atomic
def delete_expense(user, e):
    check_edit_window(user, "expenses", e.date, op="d")
    soft_delete(e, user, check_usage=False)
    sync_movements(S.EXPENSE, e, [])


# ------------------------------------------------------------------ kreditorlar

def creditor_current(creditor):
    """Joriy haqqi = boshlang'ich haqqi − Σ amallar («−» olish haqni oshiradi, «+» qaytarish kamaytiradi)."""
    return Decimal(creditor.initial_balance) - (creditor.transactions.aggregate(s=Sum("amount"))["s"] or 0)


@transaction.atomic
def save_creditor_tx(user, d):
    d = dict(d)
    if not d.get("amount"):
        raise ValidationError({"amount": "Summa 0 bo'lmasin: «−» qarz olish, «+» qarz qaytarish"})
    if d["date"] > today():
        raise ValidationError({"date": "Kelajak sana bilan kiritib bo'lmaydi"})
    if not is_top(user) and (today() - d["date"]).days > CREDITOR_DAYS:
        raise ValidationError({"date": "Bir hafta avvalgi sanagacha kiritish mumkin, xolos"})
    if d["cash_type"] not in MONEY:
        raise ValidationError({"cash_type": "Pul shaklini tanlang"})
    if not my_accounts(user).filter(pk=d["account"].pk).exists():
        raise ValidationError({"account": "Siz mas'ul bo'lgan faol g'aznani tanlang"})
    check_account_type(d["account"], d["cash_type"], "account")
    if d["amount"] > 0:
        check_funds(user, d["account"], d["cash_type"], d["amount"])
    t = CreditorTransaction.objects.create(**d, cashier=user, created_by=user, updated_by=user)
    sync_movements(S.CREDITOR, t, [(t.account, t.cash_type, -t.amount, True, t.creditor)])
    audit.log_create(user, t)
    return t


@transaction.atomic
def delete_creditor_tx(user, t):
    soft_delete(t, user, check_usage=False)
    sync_movements(S.CREDITOR, t, [])


def check_creditor_update(user, creditor, d):
    if "initial_balance" in d and d["initial_balance"] != creditor.initial_balance and role_code(user) != RoleCode.ADMIN:
        raise PermissionDenied("Boshlang'ich haqqini faqat Admin o'zgartiradi")


# ------------------------------------------------------------------ tasdiqlar soni (qo'ng'iroqcha)

def pending_counts(user, payments_qs, transfers_qs, makeups_qs, freqs_qs):
    """Faqat foydalanuvchi tasdiqlay oladiganlari."""
    pays = list(payments_qs.filter(Q(discount_status=Confirm.PENDING) | Q(noncash_status=Confirm.PENDING)))
    out = {
        "discounts": sum(1 for p in pays if p.discount_status == Confirm.PENDING and can_approve_discount(user, p)),
        "noncash": sum(1 for p in pays if p.noncash_status == Confirm.PENDING and can_approve_noncash(user, p)),
        "transfers": sum(1 for t in transfers_qs.filter(status=Confirm.PENDING).select_related("receiver_account") if can_confirm_transfer(user, t)),
        "makeups": makeups_qs.filter(status="Kutilmoqda").count() if can(user, "attendance", "p") else 0,
        "freqs": freqs_qs.filter(status="Taklif").count() if role_code(user) in (RoleCode.ADMIN, RoleCode.BOSH_MENEJER, RoleCode.FILIAL_MENEJERI) else 0,
    }
    out["total"] = sum(out.values())
    return out


def month_bounds(ym):
    y, m = (int(x) for x in str(ym).split("-")[:2])
    start = datetime.date(y, m, 1)
    return start, (start.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)


def require(user, section, op):
    if not can(user, section, op):
        raise PermissionDenied(NO_PERMISSION)


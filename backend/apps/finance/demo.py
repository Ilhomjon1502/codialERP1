"""seed_demo uchun moliya: o'tgan va joriy oy to'lovlari (naqd, karta, chegirmalar), xarajatlar, o'tkazmalar, ayirboshlash, kreditor.
Qayta ishga tushirilsa dublikat yaratmaydi (demo to'lovlar bo'lsa o'tkazib yuboriladi)."""

import datetime
import random
from decimal import Decimal

from django.utils import timezone

from apps.education.models import Contract
from apps.references.models import CoursePrice, DiscountType, ExpenseCategory
from apps.references.services import prev_month

from . import services
from .models import Account, Confirm, Creditor, CreditorTransaction, Exchange, Expense, Payment, Transfer

S = services.S
# (kategoriya kaliti, nomi, summa) — har oy
MONTHLY_EXPENSES = [("e1", "Ijara (Emirat)", 4_000_000), ("e2", "Elektr energiya", 650_000), ("e2", "Gaz va suv", 180_000), ("e3", "Internet", 300_000),
                    ("e4", "Instagram reklama", 1_200_000), ("e5", "Kantselyariya", 250_000)]


def _day(R, month, today):
    last = min((month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1), today)
    return month + datetime.timedelta(days=R.randint(0, max(0, (last - month).days)))


def _price(c, month):
    p = CoursePrice.objects.filter(branch=c.branch, course=c.course, effective_from__lte=month).order_by("-effective_from").values_list("price", flat=True).first()
    return Decimal(p or 500_000)


def seed(cmd, branch, users):
    if Payment.all_objects.filter(legacy_id__startswith="demo:pay").exists():
        return
    R = random.Random(20261015)
    today = timezone.localdate()
    month = today.replace(day=1)
    months = [prev_month(month), month]
    cash = Account.objects.get(legacy_id="demo:acc1")
    card = Account.objects.get(legacy_id="demo:acc2")
    staff = [users["u5"], users["u6"]]
    boss = users["u2"]
    promo = DiscountType.objects.filter(legacy_id="demo:d2").first()
    n = 0
    for c in Contract.objects.filter(branch=branch, start_date__lte=today).select_related("course", "group").order_by("number"):
        for m in months:
            if c.start_date > m + datetime.timedelta(days=20) or (c.end_date and c.end_date < m) or (m == month and R.random() < 0.3):
                continue
            if c.type == Contract.Type.GRANT:
                continue
            who = R.choice(staff)
            d = _day(R, max(m, c.start_date), today)
            noncash = R.random() < 0.25
            p = Payment(branch=branch, contract=c, group=c.group, number=services.next_payment_number(branch), date=d, amount=_price(c, m),
                        cash_type="CARD" if noncash else "CASH", cashbox=card if noncash else cash, accountant=who, created_by=who, updated_by=who,
                        legacy_id=f"demo:pay{n}")
            if noncash:
                ok = R.random() < 0.8 or m != month
                p.noncash_status = Confirm.CONFIRMED if ok else Confirm.PENDING
                p.noncash_confirmed_by, p.noncash_confirmed_at = (boss, timezone.now()) if ok else (None, None)
            if promo and R.random() < 0.1:
                p.discount_type, p.discount = promo, Decimal(R.choice([100_000, 150_000, 200_000]))
                ok = m != month or R.random() < 0.5
                p.discount_status = Confirm.CONFIRMED if ok else Confirm.PENDING
                p.discount_confirmed_by, p.discount_confirmed_at = (boss, timezone.now()) if ok else (None, None)
            p.save()
            Payment.objects.filter(pk=p.pk).update(created_at=timezone.make_aware(datetime.datetime.combine(d, datetime.time(10 + R.randint(0, 8), R.randint(0, 59)))))
            services.sync_movements(S.PAYMENT, p, services.payment_rows(p))
            n += 1
    cats = {c.legacy_id.split(":")[1]: c for c in ExpenseCategory.objects.filter(legacy_id__startswith="demo:")}
    for m in months:
        items = MONTHLY_EXPENSES + ([("e6", "Monitor 24\" (2 dona)", 3_200_000)] if m != month else [])
        for i, (ck, name, total) in enumerate(items):
            d = _day(R, m, today) if m == month else m + datetime.timedelta(days=4 + i)
            if d > today or ck not in cats:
                continue
            e = Expense.objects.create(branch=branch, date=d, category=cats[ck], name=name, quantity=1, price=total, total=total, cash_type="CASH", account=cash,
                                       cashier=users["u6"], period_year=m.year, period_month=m.month, created_by=users["u6"], updated_by=users["u6"],
                                       legacy_id=f"demo:exp-{m:%Y%m}-{i}")
            services.sync_movements(S.EXPENSE, e, [(cash, "CASH", -e.total, True, f"{e.category}: {e.name}")])
    for k, (days, amount, ok) in enumerate([(9, 3_000_000, True), (0, 1_000_000, False)]):
        t = Transfer.objects.create(date=today - datetime.timedelta(days=days), sender_account=cash, sender_cashier=users["u5"], amount=amount, receiver_account=card,
                                    receiver_cashier=boss, status=Confirm.CONFIRMED if ok else Confirm.PENDING, confirmed_by=boss if ok else None,
                                    confirmed_at=timezone.now() if ok else None, comment="Kassadan bosh g'aznaga", created_by=users["u5"], updated_by=users["u5"],
                                    legacy_id=f"demo:tr{k}")
        services.sync_movements(S.TRANSFER, t, services.transfer_rows(t))
    x = Exchange.objects.create(account=cash, date=today - datetime.timedelta(days=5), from_type="CASH", amount=500_000, to_type="CARD", amount_to=490_000,
                                comment="Naqdni kartaga", created_by=boss, updated_by=boss, legacy_id="demo:x1")
    services.sync_movements(S.EXCHANGE, x, [(cash, "CASH", -x.amount, True, "Naqd → Karta"), (cash, "CARD", x.amount_to, True, "Naqd → Karta")])
    cr = cmd.upsert(Creditor, "cr1", {"name": "Bank krediti", "initial_balance": 0})
    for k, (d, amount) in enumerate([(months[0] + datetime.timedelta(days=2), -10_000_000), (today - datetime.timedelta(days=3), 1_000_000)]):
        t = CreditorTransaction.objects.create(date=d, creditor=cr, amount=amount, cash_type="CARD", account=card, cashier=boss, comment="Kredit" if amount < 0 else "Qaytarildi",
                                               created_by=boss, updated_by=boss, legacy_id=f"demo:ctx{k}")
        services.sync_movements(S.CREDITOR, t, [(card, "CARD", -t.amount, True, cr)])
    cmd.created += n

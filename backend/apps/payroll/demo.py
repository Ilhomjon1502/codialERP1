"""seed_demo uchun oyliklar: o'tgan va joriy oy oylik belgilash, o'tgan oy oyligi berilgan (ba'zilari qisman), joriy oyga avans.
Qayta ishga tushirilsa dublikat yaratmaydi."""

import datetime
from decimal import Decimal

from django.utils import timezone

from apps.finance import services as fin
from apps.finance.models import Account, CashMovement
from apps.references.services import prev_month

from . import services
from .models import SalaryAssignment, SalaryPayout

# (xodim kaliti, belgilangan oylik, bonus) — ustozlarga asosan KPI
FIXED = [("u3", 6_000_000, 500_000), ("u4", 3_500_000, 0), ("u5", 4_000_000, 300_000), ("u6", 3_800_000, 0), ("u7", 1_000_000, 0),
         ("u8", 1_000_000, 200_000), ("u9", 800_000, 0), ("u10", 1_200_000, 0), ("u11", 600_000, 0), ("u12", 600_000, 0)]


def seed(cmd, branch, users):
    if SalaryAssignment.all_objects.filter(legacy_id__startswith="demo:sa").exists():
        return
    today = timezone.localdate()
    month = today.replace(day=1)
    prev = prev_month(month)
    cash = Account.objects.get(legacy_id="demo:acc1")
    cashier = users["u6"]
    created = []
    for key, fixed, bonus in FIXED:
        u = users[key]
        for m in (prev, month):
            a = SalaryAssignment.objects.create(branch=branch, user=u, year=m.year, month=m.month, fixed=fixed, bonus=bonus if m == prev else 0,
                                                fine=50_000 if key == "u9" and m == prev else 0, created_by=users["u2"], updated_by=users["u2"],
                                                legacy_id=f"demo:sa-{key}-{m:%Y%m}")
            created.append(a)
    services.compute(created)
    n = 0
    for a in created:
        if (a.year, a.month) == (prev.year, prev.month):
            amount = a.total if a.user_id not in (users["u7"].pk, users["u10"].pk) else (a.total * 8 // 10000) * 1000
            day, typ = month + datetime.timedelta(days=min(4, (today - month).days)), "O'zgarmas"
        elif a.fixed >= 3_000_000 and today.day >= 10:
            amount, day, typ = Decimal(1_000_000), today - datetime.timedelta(days=2), "O'zgarmas"  # avans
        else:
            continue
        if amount <= 0:
            continue
        p = SalaryPayout.objects.create(branch=branch, user=a.user, year=a.year, month=a.month, date=day, type=typ, amount=amount, cash_type="CASH",
                                        account=cash, cashier=cashier, comment="Avans" if (a.year, a.month) != (prev.year, prev.month) else "",
                                        created_by=cashier, updated_by=cashier, legacy_id=f"demo:sp{n}")
        fin.sync_movements(CashMovement.Source.SALARY, p, services.payout_rows(p))
        n += 1
    cmd.created += len(created) + n

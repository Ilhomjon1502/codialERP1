"""Nusxa bazadagi Administrator+Hisobchi ruxsatlari va kerakli ma'lumotnomalar (shaxsiy ma'lumotsiz)."""
from apps.accounts.models import Role, User
from apps.finance.models import Account
from apps.references.models import Branch

r = Role.objects.get(code="ADMINISTRATOR_HISOBCHI")
print("ROL:", r.name)
for p in r.permissions.all().order_by("section"):
    print("  ", p.section, p.ops if hasattr(p, "ops") else p.__dict__)
print("FILIAL:", [(b.name, b.status) for b in Branch.objects.all()])
print("G'AZNA:", [(a.name, a.cash_type, a.status, a.responsible.count()) for a in Account.objects.all()])
print("AH xodimlar soni:", User.objects.filter(role=r).count())

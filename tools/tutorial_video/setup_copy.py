"""Nusxa bazada video uchun «namuna» Administrator+Hisobchi xodimini tayyorlaydi.

Faqat lokal nusxa (DATABASE_URL) uchun. Parol tasodifiy yaratiladi va VIDEO_LOGIN faylga yoziladi.
Ishga tushirish: manage.py shell -c "exec(open('.../setup_copy.py', encoding='utf-8').read())"
"""
import json
import os
import secrets

from django.conf import settings

from apps.accounts.models import Role, User
from apps.finance.models import Account
from apps.references.models import Branch

assert "copy.sqlite3" in str(settings.DATABASES["default"]["NAME"]), "Faqat nusxa bazada ishlaydi!"

EMAIL = "namuna@codial.local"
login_file = os.environ["VIDEO_LOGIN"]
password = secrets.token_urlsafe(12)

user = User.objects.filter(email=EMAIL).first() or User(email=EMAIL)
user.full_name = "Namuna Administrator"
user.role = Role.objects.get(code="ADMINISTRATOR_HISOBCHI")
user.employment_status = "Faol"
user.is_active = True
user.set_password(password)
user.save()
user.branches.set(Branch.objects.filter(status="Faol"))
for acc in Account.objects.filter(status="Faol", cash_type="CASH"):
    acc.responsible.add(user)

with open(login_file, "w", encoding="utf-8") as f:
    json.dump({"email": EMAIL, "password": password}, f)
print("tayyor:", user.full_name, user.role.code, [b.name for b in user.branches.all()])

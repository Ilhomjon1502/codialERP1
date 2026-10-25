"""Namuna xodim uchun parol o'rnatish havolasini (pristine nusxa holatida) VIDEO_LOGIN faylga qo'shadi."""
import json
import os

from django.conf import settings

from apps.accounts.models import User
from apps.accounts.services import password_link

assert "pristine.sqlite3" in str(settings.DATABASES["default"]["NAME"]), "Faqat pristine nusxa bilan!"
path = os.environ["VIDEO_LOGIN"]
data = json.load(open(path, encoding="utf-8"))
link = password_link(User.objects.get(email=data["email"]))
data["set_password"] = "#/" + link.split("#/", 1)[1]
json.dump(data, open(path, "w", encoding="utf-8"))
print("havola tayyor")

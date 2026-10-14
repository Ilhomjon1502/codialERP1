"""Ertalab 8:30 — administratorlarga bugungi ish rejasi (buyurtmachi so'rovi 2026-10-14):
olinadigan to'lovlar (dars vaqti bo'yicha qarzdorlar), sinov darsiga keladiganlar, kelmaganlar bilan bog'lanish,
qayta bog'lanish kerak lidlar, kecha davomati olinmagan guruhlar. Har filial uchun alohida.
Cron: 30 8 * * *

    python manage.py morning_plan            # yuborish
    python manage.py morning_plan --print    # ekranga
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications import reminders
from apps.references.models import Branch


class Command(BaseCommand):
    help = "Administratorlarga ertalabki ish rejasi (Telegram)"

    def add_arguments(self, parser):
        parser.add_argument("--print", action="store_true", help="Yubormasdan ekranga chiqarish")

    def handle(self, *args, **opts):
        if opts["print"]:
            for b in Branch.objects.filter(status="Faol"):
                self.stdout.write(reminders.plan_text(b, timezone.localdate()))
            return
        n = reminders.morning_plan()
        self.stdout.write(f"Ertalabki reja navbatga qo'yildi: {n} ta filial")

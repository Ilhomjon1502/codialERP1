"""Har oy 1-kuni cron: har bir faol filial va dars kunlari jadvali uchun «Taklif» (CLAUDE.md 7.2).

    python manage.py propose_lesson_frequencies            # joriy oy
    python manage.py propose_lesson_frequencies --month 2026-11
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Status
from apps.references import services
from apps.references.models import Branch


class Command(BaseCommand):
    help = "Oydagi dars soni uchun kalendar bo'yicha takliflar yaratadi"

    def add_arguments(self, parser):
        parser.add_argument("--month", help="YYYY-MM (standart: joriy oy)")

    def handle(self, *args, month=None, **opts):
        d = services.month_start(month) if month else timezone.localdate().replace(day=1)
        total = 0
        for branch in Branch.objects.filter(status=Status.ACTIVE):
            n = services.propose_month(branch, d.year, d.month)
            total += n
            self.stdout.write(f"{branch}: {n} ta taklif")
        self.stdout.write(self.style.SUCCESS(f"{d:%Y-%m}: jami {total} ta taklif yaratildi"))

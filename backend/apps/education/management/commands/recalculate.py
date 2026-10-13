"""Davomat qatorlaridagi talaba qarzi va KPI ni qayta hisoblash (CLAUDE.md 8.5).

    python manage.py recalculate --month 2026-10
    python manage.py recalculate --all
"""

from django.core.management.base import BaseCommand, CommandError

from apps.education import calc
from apps.education.models import Attendance
from apps.references.services import month_start


class Command(BaseCommand):
    help = "Davomat qatorlaridagi qarz va KPI ni qayta hisoblaydi"

    def add_arguments(self, parser):
        parser.add_argument("--month", help="YYYY-MM")
        parser.add_argument("--all", action="store_true", help="Barcha oylar")

    def handle(self, *args, month=None, all=False, **opts):
        if all:
            n = calc.recalculate(Attendance.objects.all())
        elif month:
            d = month_start(month)
            n = calc.recalc_month(d.year, d.month)
        else:
            raise CommandError("--month YYYY-MM yoki --all bering")
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {n} ta qator o'zgardi"))

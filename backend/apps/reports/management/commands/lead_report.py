"""Instagram/Facebook lidlarining kunlik hisoboti: Google Sheets'ga yangi varaq + Bosh menejerga Telegram xabari.
Har kuni 19:00 da `daily_report` o'zi chaqiradi; qo'lda:

    python manage.py lead_report [--date YYYY-MM-DD] [--print] [--no-send]

`--print` — hech narsa yozmaydi va yubormaydi, faqat hisobni ko'rsatadi. `--no-send` — varaqni yozadi, Telegram'ga yubormaydi."""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.reports import lead_report


class Command(BaseCommand):
    help = "Instagram/Facebook lidlari kunlik hisoboti (Google Sheets + Telegram)"

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Kun (YYYY-MM-DD), standart — bugun")
        parser.add_argument("--print", action="store_true", help="Faqat hisobni ekranga chiqarish")
        parser.add_argument("--no-send", action="store_true", help="Telegram'ga yubormaslik")

    def handle(self, *args, **opts):
        try:
            day = datetime.date.fromisoformat(opts["date"]) if opts["date"] else timezone.localdate()
        except ValueError as e:
            raise CommandError("Sana YYYY-MM-DD ko'rinishida bo'lsin") from e
        if opts["print"]:
            self.stdout.write(lead_report.message(lead_report.collect(day)))
            return
        text, res = lead_report.run(day, send=not opts["no_send"])
        self.stdout.write(text)
        self.stdout.write(self.style.SUCCESS(f"Varaq: {res['title']} — {res['url']}") if res else self.style.WARNING("Google Sheets'ga yozilmadi"))

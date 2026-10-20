"""Google Sheets ulanishini tekshiradi: kalit, fayl, ruxsat. Hech narsa yozmaydi."""

from django.core.management.base import BaseCommand, CommandError

from apps.reports import gsheets


class Command(BaseCommand):
    help = "Google Sheets ulanishini tekshirish (kalit, fayl ID'si, ruxsat)"

    def handle(self, *args, **opts):
        try:
            email = gsheets.service_email()
            self.stdout.write(f"Service account: {email}")
            meta = gsheets.tabs()
        except gsheets.SheetsError as e:
            raise CommandError(str(e)) from e
        names = ", ".join(s["title"] for s in meta["sheets"]) or "—"
        self.stdout.write(self.style.SUCCESS(f"Ulandi: «{meta['title']}» — varaqlar: {names}"))

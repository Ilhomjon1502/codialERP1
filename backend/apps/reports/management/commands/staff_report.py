import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reports import staff_report


class Command(BaseCommand):
    help = ("Xodimlar ish sifati hisoboti (PDF). Standart davr — kechagacha oxirgi 7 kun "
            "(dushanba kuni — o'tgan hafta). --send — botga ulangan Bosh menejerga Telegram'da yuboradi (cron: dushanba 09:00).")

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="date_from")
        parser.add_argument("--to", dest="date_to")
        parser.add_argument("--out", help="PDF faylga saqlash")
        parser.add_argument("--send", action="store_true", help="Bosh menejerga Telegram'da yuborish")

    def handle(self, *args, **o):
        today = timezone.localdate()
        to = dt.date.fromisoformat(o["date_to"]) if o["date_to"] else today - dt.timedelta(days=1)
        frm = dt.date.fromisoformat(o["date_from"]) if o["date_from"] else to - dt.timedelta(days=6)
        data = staff_report.grade(staff_report.collect(frm, to))
        pdf = staff_report.build_pdf(data)
        for p in data["staff"]:
            self.stdout.write(f"{p['name']}: {p['score']} - {p['grade']} {p['parts']}")
        if o["out"]:
            with open(o["out"], "wb") as f:
                f.write(pdf)
            self.stdout.write(f"PDF: {o['out']}")
        if o["send"]:
            self.stdout.write(f"Telegram: {staff_report.send(data, pdf)} ta Bosh menejerga yuborildi")

import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.reports import teacher_report


class Command(BaseCommand):
    help = ("Ustozlar ish sifati hisoboti (PDF). Standart davr — o'tgan oy (cron: har oy 1-kuni 09:00). "
            "--send — botga ulangan Bosh menejerga Telegram'da yuboradi.")

    def add_arguments(self, parser):
        parser.add_argument("--month", help="YYYY-MM (standart — o'tgan oy)")
        parser.add_argument("--from", dest="date_from")
        parser.add_argument("--to", dest="date_to")
        parser.add_argument("--out", help="PDF faylga saqlash")
        parser.add_argument("--send", action="store_true", help="Bosh menejerga Telegram'da yuborish")

    def handle(self, *args, **o):
        if o["date_from"] or o["date_to"]:
            to = dt.date.fromisoformat(o["date_to"]) if o["date_to"] else timezone.localdate() - dt.timedelta(days=1)
            frm = dt.date.fromisoformat(o["date_from"]) if o["date_from"] else to.replace(day=1)
        else:
            first = dt.date.fromisoformat(f"{o['month']}-01") if o["month"] else (timezone.localdate().replace(day=1) - dt.timedelta(days=1)).replace(day=1)
            frm, to = first, (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        data = teacher_report.grade(teacher_report.collect(frm, to))
        pdf = teacher_report.build_pdf(data)
        for p in data["teachers"]:
            self.stdout.write(f"{p['name']}: {p['score']} - {p['grade']} {p['parts']}")
        if o["out"]:
            with open(o["out"], "wb") as f:
                f.write(pdf)
            self.stdout.write(f"PDF: {o['out']}")
        if o["send"]:
            self.stdout.write(f"Telegram: {teacher_report.send(data, pdf)} ta Bosh menejerga yuborildi")

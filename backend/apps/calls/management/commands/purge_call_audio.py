"""Eski suhbat yozuv fayllarini o'chiradi (disk to'lmasin). Qo'ng'iroq yozuvi (raqam, vaqt, davomiylik) qoladi.
Cron (tavsiya): har oy 1-kuni 04:00 —  python manage.py purge_call_audio --days 180"""

from django.core.management.base import BaseCommand

from apps.calls import services


class Command(BaseCommand):
    help = "N kundan eski suhbat yozuv fayllarini o'chiradi"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=180, help="Necha kundan eski (standart 180)")

    def handle(self, *args, **opts):
        n = services.purge_audio(opts["days"])
        self.stdout.write(f"{n} ta yozuv fayli o'chirildi (>{opts['days']} kun)")

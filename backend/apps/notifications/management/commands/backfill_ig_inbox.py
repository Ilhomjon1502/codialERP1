"""Instagram/Facebook jadvalidagi barcha lidlarni qayta ko'rib chiqadi; ERP'da yo'qlarini kiruvchi lidlar navbatiga «Yangi» qilib qo'shadi.

    python manage.py backfill_ig_inbox            # sinov: nechta qo'shilishini ko'rsatadi
    python manage.py backfill_ig_inbox --commit   # haqiqatan qo'shadi (Telegram xabari yuborilmaydi)
"""

from django.core.management.base import BaseCommand, CommandError

from apps.notifications import ig_leads


class Command(BaseCommand):
    help = "Jadvaldagi ERP'da yo'q lidlarni kiruvchi lidlar navbatiga qo'shadi"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Haqiqatan qo'shish (busiz — sinov)")

    def handle(self, *args, **opts):
        if not ig_leads.sheet_csv_url():
            raise CommandError("IG_LEADS_SHEET_URL sozlanmagan")
        rep = ig_leads.backfill(ig_leads.fetch_rows(), commit=opts["commit"])
        self.stdout.write(
            f"Jadvalda: {rep['rows']} ta lid\n  ERP'da bor (talaba/vasiy): {rep['in_erp']}\n  navbatda bor: {rep['in_queue']}\n"
            f"  takror raqam (oxirgisi olinadi): {rep['duplicate']}\n  {'QO‘SHILDI' if opts['commit'] else 'qo‘shiladi'}: {rep['added']}")
        if not opts["commit"]:
            self.stdout.write("Sinov — hech narsa saqlanmadi (saqlash uchun --commit)")

"""M11: demo ma'lumotlarni tozalash — haqiqiy ish uchun toza baza.

    python manage.py prepare_production --keep ilhomjon.office@gmail.com              # sinov: nima o'chishini ko'rsatadi
    python manage.py prepare_production --keep ilhomjon.office@gmail.com --commit     # haqiqatan o'chiradi

Saqlanadi: rollar va ruxsatlar, davomat statuslari, Emirat filiali, --keep dagi xodimlar (paroli, Telegram bilan).
Avval zaxira oling: bash deploy/backup.sh test
"""

from django.core.management.base import BaseCommand, CommandError

from apps.importer import reset


class Command(BaseCommand):
    help = "Demo ma'lumotlarni o'chirib, haqiqiy ish uchun toza baza tayyorlaydi"

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="append", default=[], help="Saqlanadigan xodim pochtasi (bir necha marta berish mumkin)")
        parser.add_argument("--branch", default="Emirat")
        parser.add_argument("--commit", action="store_true", help="Haqiqatan o'chirish (busiz — sinov rejimi)")

    def handle(self, *args, **opts):
        try:
            counts = reset.run(opts["keep"], branch_name=opts["branch"], commit=opts["commit"])
        except ValueError as e:
            raise CommandError(str(e)) from None
        title = "O'CHIRILDI" if opts["commit"] else "SINOV REJIMI — hech narsa o'chirilmadi, o'chiriladiganlar"
        self.stdout.write(f"{title}:")
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(f"Saqlanadi: rollar va ruxsatlar, davomat statuslari, «{opts['branch']}» filiali, xodimlar: {', '.join(opts['keep'])}")

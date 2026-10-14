"""O'tish kuni: paroli hali yo'q faol xodimlarga «parol o'rnatish» havolasini yuborish (M11).

    python manage.py send_invites              # kimga ketishini ko'rsatadi
    python manage.py send_invites --send       # haqiqatan yuboradi
"""

from django.core.management.base import BaseCommand

from apps.accounts import services
from apps.accounts.models import User
from apps.core.roles import RoleCode


class Command(BaseCommand):
    help = "Paroli yo'q faol xodimlarga parol o'rnatish havolasini yuboradi"

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Haqiqatan yuborish (busiz — faqat ro'yxat)")

    def handle(self, *args, **opts):
        users = [u for u in User.objects.filter(employment_status=User.Employment.ACTIVE, email__isnull=False).exclude(role__code=RoleCode.BOSHQA).order_by("full_name")
                 if not u.has_usable_password()]
        for u in users:
            if opts["send"]:
                services.send_password_link(u, invite=True)
            self.stdout.write(f"  {'yuborildi' if opts['send'] else 'yuboriladi'}: {u.full_name} <{u.email}>")
        self.stdout.write(f"Jami: {len(users)} ta xodim" + ("" if opts["send"] else " (yuborish uchun --send)"))

"""Dublikat talabani birlashtirish (AppSheet'da ikki marta kiritilgan, ism + familiya + telefon bir xil).

    python manage.py merge_students --keep <id> --drop <id>            # nima bo'lishini ko'rsatadi
    python manage.py merge_students --keep <id> --drop <id> --commit   # haqiqatan birlashtiradi
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.crm import services
from apps.crm.models import Student


def describe(s):
    leads = ", ".join(f"{lead.status} ({lead.comments.count()} izoh)" for lead in s.leads.all()) or "—"
    return (f"{s.pk} · {s.full_name} · {s.created_at:%d.%m.%Y} · lid: {leads} · shartnoma: {s.contracts.count()} · "
            f"qo'ng'iroq: {s.calls.count()} · SMS: {s.sms_messages.count()}")


class Command(BaseCommand):
    help = "Ikki talaba yozuvini bittaga birlashtiradi (--drop o'chiriladi)"

    def add_arguments(self, parser):
        parser.add_argument("--keep", required=True, help="Qoladigan talaba ID (yoki uning boshi)")
        parser.add_argument("--drop", required=True, help="O'chiriladigan talaba ID (yoki uning boshi)")
        parser.add_argument("--by", help="Kim nomidan (xodim pochtasi); bo'lmasa — birinchi Admin/BM")
        parser.add_argument("--commit", action="store_true", help="Haqiqatan birlashtirish (busiz — sinov)")

    def find(self, prefix):
        qs = Student.objects.filter(pk__startswith=prefix) if len(prefix) < 36 else Student.objects.filter(pk=prefix)
        if qs.count() != 1:
            raise CommandError(f"{prefix}: {qs.count()} ta talaba topildi")
        return qs.get()

    def handle(self, *args, **opts):
        keep, drop = self.find(opts["keep"]), self.find(opts["drop"])
        user = (User.objects.get(email=opts["by"]) if opts["by"]
                else User.objects.filter(role__code__in=["ADMIN", "BOSH_MENEJER"], is_active=True).order_by("created_at").first())
        self.stdout.write(f"Qoladi:     {describe(keep)}\nO'chiriladi: {describe(drop)}")
        with transaction.atomic():
            services.merge_students(user, keep, drop)
            self.stdout.write(f"Natija:     {describe(keep)}")
            if not opts["commit"]:
                transaction.set_rollback(True)
                self.stdout.write("Sinov — hech narsa saqlanmadi (saqlash uchun --commit)")
                return
        self.stdout.write("Birlashtirildi.")

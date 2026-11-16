"""Kiruvchi lidlar navbatidagi (Instagram/Facebook/sayt) hamma lidlarga bir marta SMS (2026-11-16, buyurtmachi qarori).

    python manage.py sms_inbox_backfill            # sinov: nechtasiga ketishini ko'rsatadi
    python manage.py sms_inbox_backfill --commit   # haqiqatan navbatga qo'yadi

Faqat reklamasi «Kompyuter savodxonligi» bo'lgan, raqami bazada (talaba, vasiy) yo'q va shu raqamga avval SMS ketmagan lidlarga.
«Lidga qo'shilgan» (bazada bor) va «Yopilgan» (gaplashilib, qiziqmagan) lidlar o'tkazib yuboriladi (`--closed` bilan yopilganlarga ham).
"""

from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.calls import auto_sms
from apps.calls.models import SmsMessage, SmsRule
from apps.crm.models import InboxLead

REASONS = {"kurs": "kursi Kompyuter savodxonligi emas", "bazada": "raqami bazada bor", "yuborilgan": "avval SMS yuborilgan", "qurilma": "SMS telefoni ulanmagan"}


class Command(BaseCommand):
    help = "Navbatdagi kiruvchi lidlarga bir martalik SMS"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Haqiqatan navbatga qo'yish (busiz — sinov)")
        parser.add_argument("--closed", action="store_true", help="«Yopilgan» lidlarni ham qo'shish")

    def handle(self, *args, **opts):
        statuses = [InboxLead.Status.NEW, InboxLead.Status.CALLBACK] + ([InboxLead.Status.REJECTED] if opts["closed"] else [])
        rules, res, seen = {}, Counter(), set()
        for item in InboxLead.objects.filter(status__in=statuses).order_by("-received_at"):
            if item.branch_id not in rules:
                rules[item.branch_id] = SmsRule.objects.filter(branch_id=item.branch_id, key="inbox_lead", is_deleted=False).select_related("branch").first()
            rule = rules[item.branch_id]
            if not rule:
                raise CommandError("«inbox_lead» qoidasi yo'q (migratsiya qo'llanganmi?)")
            if item.phone in seen:
                res["takror raqam"] += 1
                continue
            seen.add(item.phone)
            if opts["commit"]:
                r = auto_sms.enqueue_inbox(item, rule)
            elif not auto_sms.is_ks(item.course_name):
                r = "kurs"
            elif auto_sms.in_base(item.phone):
                r = "bazada"
            elif SmsMessage.all_objects.filter(key=f"inbox:{item.phone}").exists():
                r = "yuborilgan"
            else:
                r = True
            res["yuboriladi" if r is True else REASONS[r]] += 1
        for k, v in res.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(("NAVBATGA QO'YILDI: " if opts["commit"] else "Sinov — hech narsa yozilmadi. Yuboriladi: ") + str(res["yuboriladi"]))

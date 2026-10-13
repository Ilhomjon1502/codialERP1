"""Har kuni kechqurun Bosh menejerga hisobot (CLAUDE.md 12): to'lovlar, yangi lidlar, yangi shartnomalar, kelmaganlar, g'azna qoldiqlari.
Cron: 0 20 * * *

    python manage.py daily_report
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.core.roles import RoleCode
from apps.crm.models import Lead
from apps.education.models import Attendance, Contract
from apps.finance import services as fin
from apps.finance.models import Account, Payment
from apps.notifications import services


def build(day):
    pays = Payment.objects.filter(date=day)
    cash = pays.filter(cash_type="CASH").aggregate(s=Sum("amount"))["s"] or 0
    noncash = pays.exclude(cash_type="CASH").aggregate(s=Sum("amount"))["s"] or 0
    bal = fin.balances([a.pk for a in Account.objects.filter(status="Faol")])
    accounts = "\n".join(f"  • {a.name}: {services.money(bal[a.pk]['balance'])}" for a in Account.objects.filter(status="Faol"))
    return (f"📊 <b>Kunlik hisobot — {day:%d.%m.%Y}</b>\n"
            f"To'lovlar: {services.money(cash + noncash)} (naqd {services.money(cash)}, naqdsiz {services.money(noncash)}), {pays.count()} ta\n"
            f"Yangi lidlar: {Lead.objects.filter(created_at__date=day).count()}\n"
            f"Yangi shartnomalar: {Contract.objects.filter(created_at__date=day).count()}\n"
            f"Besabab kelmaganlar: {Attendance.objects.filter(date=day, status='X').count()} · sababli: {Attendance.objects.filter(date=day, status='0').count()}\n"
            f"G'azna qoldiqlari:\n{accounts}")


class Command(BaseCommand):
    help = "Bosh menejerlarga kunlik Telegram hisobot"

    def handle(self, *args, **opts):
        day = timezone.localdate()
        bosses = User.objects.filter(role__code=RoleCode.BOSH_MENEJER, employment_status=User.Employment.ACTIVE)
        services.notify(bosses, "daily_report", build(day), key=f"daily:{day}")
        self.stdout.write(f"Kunlik hisobot navbatga qo'yildi: {bosses.count()} ta Bosh menejer")

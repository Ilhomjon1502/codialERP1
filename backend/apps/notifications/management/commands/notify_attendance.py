"""Dars boshlanganidan N daqiqa (TELEGRAM_ATTENDANCE_DELAY_MIN, standart 30) o'tib davomat olinmagan guruhlar — ustoz va administratorlarga.
Cron: har 10 daqiqada. Bir guruhga bir kunda bitta xabar.

    python manage.py notify_attendance
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.education.models import Attendance, Group
from apps.education.services import FAOL, has_lesson, status_q
from apps.notifications import services


class Command(BaseCommand):
    help = "Davomat olinmagan guruhlar haqida Telegram xabari"

    def handle(self, *args, **opts):
        now = timezone.localtime()
        today = now.date()
        delay = datetime.timedelta(minutes=settings.TELEGRAM_ATTENDANCE_DELAY_MIN)
        taken = set(Attendance.objects.filter(date=today).values_list("group_id", flat=True))
        n = 0
        for g in Group.objects.filter(status_q(FAOL, today)).select_related("day_pattern", "time", "teacher", "branch", "course"):
            if g.pk in taken or not has_lesson(g, today):
                continue
            start = timezone.make_aware(datetime.datetime.combine(today, g.time.start_time))
            if now < start + delay:
                continue
            services.attendance_missing(
                g, f"⚠️ <b>Davomat olinmagan</b>: {g.name} ({g.time}, ustoz {g.teacher}). Dars boshlanganiga {int(delay.total_seconds() // 60)} daqiqadan oshdi.",
                key=f"att:{g.pk}:{today}")
            n += 1
        self.stdout.write(f"Davomati olinmagan guruhlar: {n}")

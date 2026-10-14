"""analytics_* view'larni qayta yaratish (odatda `migrate` o'zi qiladi).

    python manage.py ai_views
"""

from django.core.management.base import BaseCommand

from apps.ai_assistant import analytics


class Command(BaseCommand):
    help = "AI yordamchi uchun analytics_* view'larni qayta yaratadi"

    def handle(self, *args, **opts):
        analytics.create_views()
        self.stdout.write(f"Tayyor: {len(analytics.VIEW_NAMES)} ta view")

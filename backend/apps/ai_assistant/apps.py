import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate, pre_migrate

log = logging.getLogger(__name__)


def _drop(using="default", **kwargs):
    from django.db import connections

    from . import analytics

    try:
        analytics.drop_views(connections[using])
    except Exception as e:  # noqa: BLE001
        log.warning("analytics view'larni o'chirib bo'lmadi: %s", e)


def _create(using="default", plan=None, **kwargs):
    from django.db import connections

    from . import analytics

    try:
        analytics.create_views(connections[using])
    except Exception as e:  # noqa: BLE001 — qisman migratsiyada jadval hali bo'lmasligi mumkin
        log.warning("analytics view'larni yaratib bo'lmadi: %s", e)


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"
    verbose_name = "AI yordamchi"

    def ready(self):
        # Jadval ustunlari o'zgarsa PostgreSQL view'ni to'sib qo'ymasin: migratsiyadan oldin o'chiriladi, keyin qayta yaratiladi
        pre_migrate.connect(_drop, sender=self, dispatch_uid="ai_drop_views")
        post_migrate.connect(_create, sender=self, dispatch_uid="ai_create_views")

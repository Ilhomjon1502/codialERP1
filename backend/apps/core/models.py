import uuid

from django.conf import settings
from django.db import models


class Status(models.TextChoices):
    ACTIVE = "Faol", "Faol"
    INACTIVE = "Nofaol", "Nofaol"


class AliveManager(models.Manager):
    """Standart menejer: soft delete qilingan yozuvlar ko'rinmaydi."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    """Barcha biznes modellari uchun: kim/qachon yaratgan va o'zgartirgan, soft delete, AppSheet kaliti."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    legacy_id = models.CharField("AppSheet kaliti", max_length=64, null=True, blank=True, db_index=True)

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Yaratildi"
        UPDATE = "update", "O'zgartirildi"
        DELETE = "delete", "O'chirildi"
        LOGIN = "login", "Kirish"
        LOGOUT = "logout", "Chiqish"
        PASSWORD = "password", "Parol"
        IMPORT = "import", "Import"
        EXPORT = "export", "Eksport"
        AI = "ai", "AI so'rov"

    at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=16, choices=Action.choices, db_index=True)
    model = models.CharField("Bo'lim", max_length=64, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    object_repr = models.CharField("Yozuv", max_length=255, blank=True)
    changes = models.JSONField("O'zgarishlar [[maydon, eski, yangi]]", default=list, blank=True)
    detail = models.TextField(blank=True)

    class Meta:
        verbose_name = "Audit yozuvi"
        verbose_name_plural = "Audit tarixi"
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.action} {self.model} {self.object_repr}"

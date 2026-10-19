"""Qo'ng'iroqlar (buyurtmachi so'rovi 2026-10-19): administratorlar telefonidagi (Android) qo'ng'iroqlar jurnali.
Telefondagi «Codial qo'ng'iroqlar» ilovasi har qo'ng'iroqdan keyin `POST /api/v1/calls/ingest/` ga yuboradi."""

from django.db import models

from apps.core.models import BaseModel, Status


class CallDevice(BaseModel):
    """Qo'ng'iroqlarni yuboradigan telefon. Ilova bir martalik ulash kodi bilan doimiy token oladi (token — faqat xeshi saqlanadi)."""

    name = models.CharField("Nomi", max_length=100)
    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="call_devices", verbose_name="Filial")
    phone = models.CharField("SIM raqami", max_length=9, blank=True)
    status = models.CharField("Holat", max_length=8, choices=Status.choices, default=Status.ACTIVE)
    token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    pair_code = models.CharField(max_length=8, blank=True, db_index=True)
    pair_expires_at = models.DateTimeField(null=True, blank=True)
    paired_at = models.DateTimeField("Ulangan vaqti", null=True, blank=True)
    last_seen_at = models.DateTimeField("Oxirgi aloqa", null=True, blank=True)
    app_version = models.CharField("Ilova versiyasi", max_length=20, blank=True)

    class Meta:
        verbose_name = "Qo'ng'iroq qurilmasi"
        verbose_name_plural = "Qo'ng'iroq qurilmalari"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CallRecord(BaseModel):
    class Direction(models.TextChoices):
        INCOMING = "Kiruvchi", "Kiruvchi"
        OUTGOING = "Chiquvchi", "Chiquvchi"
        MISSED = "Javobsiz", "Javobsiz"
        REJECTED = "Rad etilgan", "Rad etilgan"
        BLOCKED = "Bloklangan", "Bloklangan"

    device = models.ForeignKey(CallDevice, on_delete=models.PROTECT, related_name="calls", verbose_name="Qurilma")
    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="calls")
    external_id = models.CharField("Telefondagi kalit", max_length=64)
    direction = models.CharField("Yo'nalish", max_length=12, choices=Direction.choices, db_index=True)
    number = models.CharField("Raqam (asl)", max_length=32, blank=True)
    phone = models.CharField("Raqam (9 xona)", max_length=9, blank=True, db_index=True)
    started_at = models.DateTimeField("Vaqti", db_index=True)
    duration = models.PositiveIntegerField("Suhbat (soniya)", default=0)
    contact_name = models.CharField("Telefondagi nomi", max_length=100, blank=True)
    sim = models.CharField("SIM", max_length=32, blank=True)
    is_first = models.BooleanField("Birinchi marta", default=False)
    student = models.ForeignKey("crm.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="calls")
    parent = models.ForeignKey("crm.Parent", null=True, blank=True, on_delete=models.SET_NULL, related_name="calls")
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="calls")
    comment = models.TextField("Izoh", blank=True)
    callback_at = models.DateTimeField("Qayta qo'ng'iroq vaqti", null=True, blank=True)
    callback_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "Qo'ng'iroq"
        verbose_name_plural = "Qo'ng'iroqlar"
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["branch", "started_at"]), models.Index(fields=["phone", "started_at"])]
        constraints = [models.UniqueConstraint(fields=["device", "external_id"], name="uniq_call_per_device")]

    def __str__(self):
        return f"{self.started_at:%Y-%m-%d %H:%M} {self.direction} {self.number}"

    @property
    def is_missed(self):
        return self.direction in (self.Direction.MISSED, self.Direction.REJECTED)

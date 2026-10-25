"""Bosh menejerning Telegram botga yuborgan ovozli (yoki yozma) buyrug'i: matni, Gemini ajratgan bandlar, tasdiq holati va natija."""

from django.db import models

from apps.core.models import BaseModel


class VoiceCommand(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "Tasdiq kutilmoqda", "Tasdiq kutilmoqda"
        EDITING = "Tuzatilmoqda", "Tuzatilmoqda"
        DONE = "Bajarildi", "Bajarildi"
        CANCELLED = "Bekor qilindi", "Bekor qilindi"
        ANSWERED = "Javob berildi", "Javob berildi"
        FAILED = "Xato", "Xato"
        REPLACED = "Tuzatildi", "Tuzatildi"

    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="voice_commands")
    chat_id = models.BigIntegerField()
    is_voice = models.BooleanField(default=True)
    duration = models.PositiveIntegerField("Ovoz davomiyligi (s)", default=0)
    said_at = models.DateTimeField("Ovoz yozilgan vaqt", null=True, blank=True)  # forward qilingan bo'lsa — asl vaqti
    transcript = models.TextField("Matn", blank=True)
    items = models.JSONField("Bandlar", default=list)  # [{"type", "raw", "picked", "result"}]
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    message_id = models.BigIntegerField("Tasdiq kartasi xabari", null=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")  # tuzatilgan buyruq
    model = models.CharField(max_length=64, blank=True)
    llm_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        verbose_name = "Ovozli buyruq"
        verbose_name_plural = "Ovozli buyruqlar"
        ordering = ["-created_at"]

    def __str__(self):
        return (self.transcript or "—")[:60]

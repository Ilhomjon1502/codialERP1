"""Topshiriqlar (buyurtmachi so'rovi 2026-10-16): xodimlar bir-biriga (yoki o'ziga) topshiriq beradi, bot eslatib turadi.
Beruvchi — `created_by`."""

from django.db import models

from apps.core.models import BaseModel


class StaffTask(BaseModel):
    class Status(models.TextChoices):
        OPEN = "Ochiq", "Ochiq"
        DONE = "Bajarildi", "Bajarildi"
        CANCELLED = "Bekor qilindi", "Bekor qilindi"

    title = models.CharField("Mavzu", max_length=200)
    description = models.TextField("Izoh", blank=True)
    assignee = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="tasks_received", verbose_name="Bajaruvchi")
    due_at = models.DateTimeField("Muddat")
    status = models.CharField("Holat", max_length=16, choices=Status.choices, default=Status.OPEN)
    remind_assignee = models.BooleanField("Bajaruvchiga eslatilsin", default=True)
    remind_giver = models.BooleanField("Beruvchiga eslatilsin", default=False)
    remind_before = models.PositiveIntegerField("Muddatdan necha daqiqa oldin eslatish boshlansin", default=60)
    remind_every = models.PositiveIntegerField("Har necha daqiqada takrorlansin (0 — bir marta)", default=0)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    done_comment = models.TextField("Natija izohi", blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField("Bekor qilish sababi", blank=True)

    class Meta:
        verbose_name = "Topshiriq"
        verbose_name_plural = "Topshiriqlar"
        ordering = ["due_at"]
        indexes = [models.Index(fields=["status", "due_at"]), models.Index(fields=["assignee", "status"]), models.Index(fields=["created_by", "status"])]

    def __str__(self):
        return self.title

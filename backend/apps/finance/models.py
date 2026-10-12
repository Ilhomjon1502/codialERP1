"""Moliya. M1 da faqat G'azna (Account) — filial sozlamalari unga bog'lanadi. Ledger va amallar M4 da."""

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, Status


class CashType(models.TextChoices):
    CASH = "CASH", "Naqd"
    BANK = "BANK", "Bank"
    CARD = "CARD", "Karta"
    ALL = "ALL", "Hammasi"  # faqat g'azna turi sifatida, to'lov/xarajatda tanlanmaydi


class Account(BaseModel):
    name = models.CharField("Nomi", max_length=100)
    responsible = models.ManyToManyField("accounts.User", blank=True, related_name="accounts", verbose_name="Mas'ullar")
    cash_type = models.CharField("Turi", max_length=4, choices=CashType.choices, default=CashType.CASH)
    initial_balance = models.DecimalField("Boshlang'ich qoldiq", max_digits=14, decimal_places=0, default=0, validators=[MinValueValidator(0)])
    start_date = models.DateField("Boshlang'ich qoldiq sanasi", null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "G'azna"
        verbose_name_plural = "G'aznalar"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name"], condition=Q(is_deleted=False), name="uniq_account_name")]

    def __str__(self):
        return self.name

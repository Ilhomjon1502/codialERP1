"""Oyliklar. M3 da faqat KPI stavkasi — davomat qatoridagi KPI hisobi unga tayanadi (CLAUDE.md 7.2, 8.3).
Stavkalarni kiritish ekrani, oylik belgilash va berish — M5."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

Money = dict(max_digits=14, decimal_places=0)


class KPIRate(BaseModel):
    """Stavka «amal qilish oyi» bilan: oy uchun shu oyda amalda bo'lgan oxirgi yozuv olinadi."""

    class RoleType(models.TextChoices):
        TEACHER = "USTOZ", "Ustoz"
        SUPPORTER = "YORDAMCHI", "Yordamchi"

    class Kind(models.TextChoices):
        FIXED = "O'zgarmas", "O'zgarmas"
        PERCENT = "Foiz", "Foiz"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="kpi_rates")
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="kpi_rates", verbose_name="Xodim")
    role_type = models.CharField("Kim sifatida", max_length=10, choices=RoleType.choices)
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="kpi_rates", verbose_name="Kurs")
    effective_from = models.DateField("Amal qilish oyi (1-kun)")
    type = models.CharField("Turi", max_length=10, choices=Kind.choices)
    fixed_amount = models.DecimalField("Bir o'quvchi uchun oylik summa", default=0, validators=[MinValueValidator(0)], **Money)
    percent = models.DecimalField("Foiz", max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        verbose_name = "KPI stavkasi"
        verbose_name_plural = "KPI stavkalari"
        ordering = ["user__full_name", "-effective_from"]
        constraints = [models.UniqueConstraint(fields=["branch", "user", "role_type", "course", "effective_from"], condition=Q(is_deleted=False), name="uniq_kpi_rate")]

    def __str__(self):
        v = f"{self.percent}%" if self.type == self.Kind.PERCENT else f"{self.fixed_amount:,.0f}".replace(",", " ")
        return f"{self.user} · {self.course} ({self.get_role_type_display()}): {v} ({self.effective_from:%Y-%m})"

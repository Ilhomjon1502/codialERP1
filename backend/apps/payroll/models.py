"""Oyliklar (CLAUDE.md 7.2, 7.5, 8.4): KPI stavkasi, oylik belgilash, oylik berish.
Hisob-kitob (KPI yig'indisi, jami, berilgan, oldingi oylardan qoldiq) — services.py."""

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


class SalaryAssignment(BaseModel):
    """Oylik belgilash (CLAUDE.md 7.5). Hisoblanadiganlar (KPI, jami, berilgan, qoldiq) — services.compute()."""

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="salary_assignments")
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="salary_assignments", verbose_name="Xodim")
    year = models.PositiveSmallIntegerField("Yil")
    month = models.PositiveSmallIntegerField("Oy", validators=[MinValueValidator(1), MaxValueValidator(12)])
    fixed = models.DecimalField("Belgilangan oylik", default=0, validators=[MinValueValidator(0)], **Money)
    bonus = models.DecimalField("Bonus", default=0, validators=[MinValueValidator(0)], **Money)
    kpi = models.DecimalField("KPI (qo'lda)", default=0, validators=[MinValueValidator(0)], **Money)
    fine = models.DecimalField("Jarima", default=0, validators=[MinValueValidator(0)], **Money)
    opening_balance = models.DecimalField("Boshlang'ich qoldiq (AppSheet'dan)", default=0, **Money)
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Oylik belgilash"
        verbose_name_plural = "Oylik belgilash"
        ordering = ["-year", "-month", "user__full_name"]
        indexes = [models.Index(fields=["branch", "year", "month"]), models.Index(fields=["user", "year", "month"])]
        constraints = [models.UniqueConstraint(fields=["branch", "user", "year", "month"], condition=Q(is_deleted=False), name="uniq_salary_assignment")]

    def __str__(self):
        return f"{self.user} · {self.month:02d}/{self.year}"


class SalaryPayout(BaseModel):
    class Kind(models.TextChoices):
        FIXED = "O'zgarmas", "O'zgarmas"
        BONUS = "Bonus", "Bonus"
        KPI = "KPI", "KPI"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="salary_payouts")
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="salary_payouts", verbose_name="Xodim")
    year = models.PositiveSmallIntegerField("Yil")
    month = models.PositiveSmallIntegerField("Oy", validators=[MinValueValidator(1), MaxValueValidator(12)])
    date = models.DateField("Sana")
    type = models.CharField("Turi", max_length=10, choices=Kind.choices, default=Kind.FIXED)
    amount = models.DecimalField("Summa", validators=[MinValueValidator(0)], **Money)
    cash_type = models.CharField("Pul turi", max_length=4)
    account = models.ForeignKey("finance.Account", on_delete=models.PROTECT, related_name="salary_payouts", verbose_name="G'azna")
    cashier = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Berdi")
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Oylik berish"
        verbose_name_plural = "Oylik berish"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["branch", "user", "year", "month"]), models.Index(fields=["branch", "date"])]

    def __str__(self):
        return f"{self.user}: {self.amount:,.0f} ({self.month:02d}/{self.year})".replace(",", " ")

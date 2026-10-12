"""Ma'lumotnomalar (Sozlamalar bo'limi, CLAUDE.md 7.2)."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, Status

ALIVE = Q(is_deleted=False)
WD_SHORT = ["", "Dush", "Sesh", "Chor", "Pay", "Jum", "Shan", "Yak"]
Money = dict(max_digits=14, decimal_places=0)


class Branch(BaseModel):
    name = models.CharField("Nomi", max_length=100)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    default_cashbox = models.ForeignKey("finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="default_for_branches", verbose_name="Standart g'azna")
    noncash_cashbox = models.ForeignKey("finance.Account", null=True, blank=True, on_delete=models.PROTECT, related_name="noncash_for_branches", verbose_name="Naqdsiz to'lovlar g'aznasi")

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name"], condition=ALIVE, name="uniq_branch_name")]

    def __str__(self):
        return self.name


class Course(BaseModel):
    name = models.CharField("Nomi", max_length=100)
    branches = models.ManyToManyField(Branch, blank=True, related_name="courses", verbose_name="Filiallar")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name"], condition=ALIVE, name="uniq_course_name")]

    def __str__(self):
        return self.name


class Room(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField("Xona nomi", max_length=100)
    capacity = models.PositiveSmallIntegerField("Sig'imi", validators=[MinValueValidator(1)])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "Xona"
        verbose_name_plural = "Xonalar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DayPattern(BaseModel):
    """Dars kunlari. weekdays — ISO raqamlar (Dushanba=1 … Yakshanba=7)."""

    name = models.CharField("Nomi", max_length=64)
    weekdays = models.JSONField("Hafta kunlari (ISO)")
    weekdays_key = models.CharField(max_length=16, editable=False)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "Dars kunlari"
        verbose_name_plural = "Dars kunlari"
        ordering = ["weekdays_key"]
        constraints = [models.UniqueConstraint(fields=["weekdays_key"], condition=ALIVE, name="uniq_day_pattern")]

    @staticmethod
    def name_for(weekdays):
        return ", ".join(WD_SHORT[d] for d in weekdays)

    def save(self, *args, **kwargs):
        self.weekdays = sorted({int(d) for d in self.weekdays})
        self.weekdays_key = ",".join(map(str, self.weekdays))
        self.name = self.name_for(self.weekdays)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class LessonTime(BaseModel):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="lesson_times")
    start_time = models.TimeField("Boshlanish")
    end_time = models.TimeField("Tugash")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "Dars vaqti"
        verbose_name_plural = "Dars vaqtlari"
        ordering = ["start_time"]
        constraints = [models.UniqueConstraint(fields=["branch", "start_time", "end_time"], condition=ALIVE, name="uniq_lesson_time")]

    def __str__(self):
        return f"{self.start_time:%H:%M} - {self.end_time:%H:%M}"


class CoursePrice(BaseModel):
    """Narx «amal qilish oyi» bilan: oy uchun shu oyda amalda bo'lgan oxirgi yozuv olinadi."""

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="course_prices")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="prices")
    effective_from = models.DateField("Amal qilish oyi (1-kun)")
    price = models.DecimalField("Narx (oyiga)", validators=[MinValueValidator(0)], **Money)

    class Meta:
        verbose_name = "Kurs narxi"
        verbose_name_plural = "Kurs narxlari"
        ordering = ["course__name", "-effective_from"]
        constraints = [models.UniqueConstraint(fields=["branch", "course", "effective_from"], condition=ALIVE, name="uniq_course_price")]

    def __str__(self):
        return f"{self.course}: {self.price:,.0f} ({self.effective_from:%Y-%m})".replace(",", " ")


class LessonFrequency(BaseModel):
    """Oydagi darslar soni. Tasdiqlanmagan oy uchun qarz va KPI hisoblanmaydi (CLAUDE.md 8.1)."""

    class FreqStatus(models.TextChoices):
        PROPOSED = "Taklif", "Taklif"
        APPROVED = "Tasdiqlangan", "Tasdiqlangan"

    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="lesson_frequencies")
    day_pattern = models.ForeignKey(DayPattern, on_delete=models.PROTECT, related_name="frequencies", verbose_name="Dars kunlari")
    courses = models.ManyToManyField(Course, blank=True, related_name="lesson_frequencies", verbose_name="Kurslar")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    frequency = models.PositiveSmallIntegerField("Oydagi dars soni", validators=[MinValueValidator(4), MaxValueValidator(26)])
    status = models.CharField(max_length=16, choices=FreqStatus.choices, default=FreqStatus.PROPOSED, db_index=True)
    approved_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Oydagi dars soni"
        verbose_name_plural = "Oydagi dars soni"
        ordering = ["-year", "-month", "day_pattern__weekdays_key"]
        indexes = [models.Index(fields=["branch", "year", "month"])]

    def __str__(self):
        return f"{self.day_pattern} · {self.month:02d}/{self.year}: {self.frequency}"


class DiscountType(BaseModel):
    name = models.CharField("Nomi", max_length=100)
    max_amount = models.DecimalField("Eng ko'p miqdori", validators=[MinValueValidator(0)], **Money)
    courses = models.ManyToManyField(Course, blank=True, related_name="discount_types")
    is_system = models.BooleanField("Tizim turi", default=False)
    is_discount50 = models.BooleanField("50% chegirma turi", default=False)

    class Meta:
        verbose_name = "Chegirma turi"
        verbose_name_plural = "Chegirma turlari"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name"], condition=ALIVE, name="uniq_discount_type")]

    def __str__(self):
        return self.name


class ExpenseCategory(BaseModel):
    class Kind(models.TextChoices):
        EXPENSE = "Xarajat", "Xarajat"
        REINVEST = "Qayta investitsiya", "Qayta investitsiya"
        DIVIDEND = "Dividend", "Dividend"
        EXTERNAL_DEBT = "Tashqi qarz", "Tashqi qarz"

    name = models.CharField("Nomi", max_length=100)
    kind = models.CharField("Turi", max_length=24, choices=Kind.choices, default=Kind.EXPENSE)
    allowed_roles = models.ManyToManyField("accounts.Role", blank=True, related_name="+", verbose_name="Kim qila oladi")

    class Meta:
        verbose_name = "Xarajat kategoriyasi"
        verbose_name_plural = "Xarajat kategoriyalari"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeadSource(BaseModel):
    name = models.CharField("Nomi", max_length=100)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "Lid manbasi"
        verbose_name_plural = "Lid manbalari"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AttendanceStatus(models.Model):
    class Code(models.TextChoices):
        KELDI = "1", "Keldi"
        SABABLI = "0", "Sababli"
        BESABAB = "X", "Besabab"
        NOFAOL = "-", "Nofaol"

    code = models.CharField(max_length=1, primary_key=True, choices=Code.choices)
    name = models.CharField(max_length=32)
    sort = models.PositiveSmallIntegerField(default=0)
    roles = models.ManyToManyField("accounts.Role", blank=True, related_name="+", verbose_name="Qo'ya oladigan rollar")

    class Meta:
        verbose_name = "Davomat statusi"
        verbose_name_plural = "Davomat statuslari"
        ordering = ["sort"]

    def __str__(self):
        return self.name

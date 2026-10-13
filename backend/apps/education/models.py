"""O'quv jarayoni: guruhlar, shartnomalar, davomat va qoldirilgan darslar (CLAUDE.md 7.4, 9).

Statuslar (Faol / Rejada / Nofaol) bazada saqlanmaydi — sanadan hisoblanadi (services.status_q).
Davomat qatoridagi qarz va KPI saqlanadi va narx, dars soni, stavka yoki status o'zgarganda qayta hisoblanadi (calc.py).
"""

from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

ALIVE = Q(is_deleted=False)
Money = dict(max_digits=14, decimal_places=0)


class Group(BaseModel):
    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="groups")
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="groups", verbose_name="Kurs")
    day_pattern = models.ForeignKey("references.DayPattern", on_delete=models.PROTECT, related_name="groups", verbose_name="Dars kunlari")
    time = models.ForeignKey("references.LessonTime", on_delete=models.PROTECT, related_name="groups", verbose_name="Dars vaqti")
    teacher = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="teacher_groups", verbose_name="Ustoz")
    supporter = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="supporter_groups", verbose_name="Yordamchi")
    room = models.ForeignKey("references.Room", on_delete=models.PROTECT, related_name="groups", verbose_name="Xona")
    start_date = models.DateField("Boshlanish sana")
    end_date = models.DateField("Tugash sana", null=True, blank=True)
    number = models.PositiveIntegerField("Raqami")
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ["course__name", "number"]
        indexes = [models.Index(fields=["branch", "start_date", "end_date"]), models.Index(fields=["teacher"]), models.Index(fields=["supporter"])]
        constraints = [models.UniqueConstraint(fields=["branch", "course", "number"], condition=ALIVE, name="uniq_group_number")]

    @property
    def name(self):
        return f"{self.course} / #{self.number}"

    def __str__(self):
        return self.name


class Contract(BaseModel):
    class Type(models.TextChoices):
        PAID = "Pullik", "Pullik"
        GRANT = "Grant", "Grant"

    class StopReason(models.TextChoices):
        FINISHED = "Kursni tamomladi", "Kursni tamomladi"
        FINANCIAL = "Moliyaviy qiyinchilik", "Moliyaviy qiyinchilik"
        QUALITY = "Dars sifatidan qoniqmadi", "Dars sifatidan qoniqmadi"
        CONDITIONS = "Markaz sharoiti yoqmadi", "Markaz sharoiti yoqmadi"
        LOW_PERF = "Chetlashtirildi - o'zlashtirish past", "Chetlashtirildi - o'zlashtirish past"
        BEHAVIOUR = "Chetlashtirildi - xulqi yomon", "Chetlashtirildi - xulqi yomon"
        OTHER_COURSE = "Kurs yoqmadi - Boshqa kursga o'tyapti", "Kurs yoqmadi - Boshqa kursga o'tyapti"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="contracts")
    student = models.ForeignKey("crm.Student", on_delete=models.PROTECT, related_name="contracts", verbose_name="Talaba")
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="contracts", verbose_name="Kurs")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="contracts", verbose_name="Guruh")
    type = models.CharField("Turi", max_length=8, choices=Type.choices, default=Type.PAID)
    number = models.PositiveIntegerField("Raqami")
    start_date = models.DateField("Boshlanish sana")
    end_date = models.DateField("Tugash sana", null=True, blank=True)
    stop_reason = models.CharField("To'xtatish sababi", max_length=48, choices=StopReason.choices, blank=True)
    comment = models.TextField("Izoh", blank=True)
    opening_balance = models.DecimalField("Boshlang'ich qoldiq (AppSheet'dan)", default=0, **Money)

    class Meta:
        verbose_name = "Shartnoma"
        verbose_name_plural = "Shartnomalar"
        ordering = ["-number"]
        indexes = [models.Index(fields=["branch", "start_date", "end_date"]), models.Index(fields=["group", "start_date"]), models.Index(fields=["student"])]
        constraints = [models.UniqueConstraint(fields=["branch", "number"], condition=ALIVE, name="uniq_contract_number")]

    @property
    def name(self):
        return f"{self.student} №{self.number}"

    def __str__(self):
        return self.name


class Attendance(BaseModel):
    class Contact(models.TextChoices):
        TO_CALL = "Bog'lanishga", "Bog'lanishga"
        TALKED = "Gaplashildi", "Gaplashildi"
        NO_ANSWER = "Tushib bo'lmadi", "Tushib bo'lmadi"
        WRONG_NUMBER = "Noto'g'ri raqam", "Noto'g'ri raqam"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="attendance")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="attendance")
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="attendance")
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="attendance")
    day_pattern = models.ForeignKey("references.DayPattern", on_delete=models.PROTECT, related_name="attendance", verbose_name="Dars kunlari")
    date = models.DateField("Sana")
    status = models.CharField("Status", max_length=1, choices=[("1", "Keldi"), ("0", "Sababli"), ("X", "Besabab"), ("-", "Nofaol")])
    teacher = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="taught_attendance", verbose_name="Darsni o'tgan ustoz")
    supporter = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="supported_attendance", verbose_name="Yordamchi")
    contact_status = models.CharField("Bog'lanish holati", max_length=16, choices=Contact.choices, blank=True)
    comment = models.TextField("Izoh", blank=True)
    # Hisoblangan (calc.py). None — hisoblanmagan: oy uchun dars soni tasdiqlanmagan yoki narx kiritilmagan
    student_debt = models.DecimalField("Talaba qarzi (dars narxi)", null=True, blank=True, **Money)
    teacher_kpi = models.DecimalField("Ustoz KPI", null=True, blank=True, **Money)
    supporter_kpi = models.DecimalField("Yordamchi KPI", null=True, blank=True, **Money)
    calc_note = models.CharField("Hisob izohi", max_length=64, blank=True)

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomat"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["branch", "date"]), models.Index(fields=["group", "date"]), models.Index(fields=["contract", "date"]),
            models.Index(fields=["teacher", "date"]), models.Index(fields=["supporter", "date"]), models.Index(fields=["status", "date"]),
        ]
        constraints = [models.UniqueConstraint(fields=["group", "contract", "date"], condition=ALIVE, name="uniq_attendance")]

    def __str__(self):
        return f"{self.contract.student} {self.date:%d.%m.%Y} = {self.get_status_display()}"


class MakeupRequest(BaseModel):
    """Ustoz besabab qoldirilgan darsni yetkazganini bildiradi; tasdiqlansa X → 0 va KPI yoziladi (CLAUDE.md 9)."""

    class Status(models.TextChoices):
        PENDING = "Kutilmoqda", "Kutilmoqda"
        APPROVED = "Tasdiqlandi", "Tasdiqlandi"
        REJECTED = "Rad etildi", "Rad etildi"

    attendance = models.ForeignKey(Attendance, on_delete=models.PROTECT, related_name="makeups")
    teacher = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="makeup_requests", verbose_name="Ustoz")
    makeup_date = models.DateField("Yetkazilgan sana")
    comment = models.TextField("Izoh")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField("Rad etish sababi", blank=True)

    class Meta:
        verbose_name = "Qoldirilgan dars so'rovi"
        verbose_name_plural = "Qoldirilgan dars so'rovlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.attendance} — {self.get_status_display()}"


# ------------------------------------------------------------------ M6: baholash (talaba → ustoz), ota-onalar bilan aloqa

class TeacherEvaluation(BaseModel):
    """Talaba ustozni baholaydi (javoblarni administrator kiritadi): 5 mezon, har biri 0–10."""

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="teacher_evaluations")
    date = models.DateField("Sana")
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="teacher_evaluations")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="teacher_evaluations")
    teacher = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="evaluations_received", verbose_name="Ustoz")
    s1 = models.PositiveSmallIntegerField("Mavzuni sodda tushuntira oladimi")
    s2 = models.PositiveSmallIntegerField("Dars qiziqmi, qiziq metodlar")
    s3 = models.PositiveSmallIntegerField("Adolatlimi, teng e'tibor")
    s4 = models.PositiveSmallIntegerField("Kerak vaqtda yordam beradimi")
    s5 = models.PositiveSmallIntegerField("Tavsiya berib ruhlantiradimi")
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Ustoz bahosi"
        verbose_name_plural = "Ustoz baholari"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["branch", "date"]), models.Index(fields=["teacher", "date"])]

    @property
    def total(self):
        return self.s1 + self.s2 + self.s3 + self.s4 + self.s5

    def __str__(self):
        return f"{self.teacher} ← {self.contract.student}: {self.total}"


class ParentCall(BaseModel):
    """Ota-onalar bilan aloqa (Parent_Comment). Telefonlar talabadan olinadi."""

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="parent_calls")
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="parent_calls")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="parent_calls")
    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="parent_calls")
    date = models.DateField("Sana")
    comment = models.TextField("Izoh")

    class Meta:
        verbose_name = "Ota-ona bilan aloqa"
        verbose_name_plural = "Ota-onalar bilan aloqa"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["branch", "date"]), models.Index(fields=["group", "date"])]

    def __str__(self):
        return f"{self.contract.student} · {self.date:%d.%m.%Y}"

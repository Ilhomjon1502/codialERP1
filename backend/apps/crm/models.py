"""CRM: ota-onalar, talabalar, lidlar va lid izohlari (CLAUDE.md 7.3)."""

from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel

ALIVE = Q(is_deleted=False)

AGE_GROUPS = ["9-12", "13-15", "16-18", "19-21", "22-24", "25-27", "28-30", "31-33", "34-36", "37-39", "40-42"]
SOCIAL_STATUSES = ["Maktab o'quvchisi", "Oliygoh talabasi", "Kompaniya xodimi", "Davlat xizmatchisi", "Vaqtincha ishsiz"]
LAPTOP_CHOICES = ["Bor", "Yo'q", "Sotib oladi"]
LEAD_TAGS = ["VIP", "Chegirma so'radi", "Ota-onasi qo'ng'iroq qiladi", "Kechki vaqt", "Hafta oxiri"]


class Parent(BaseModel):
    class Relation(models.TextChoices):
        FATHER = "Ota", "Ota"
        MOTHER = "Ona", "Ona"
        BROTHER_OLDER = "Aka", "Aka"
        BROTHER_YOUNGER = "Uka", "Uka"
        SISTER_OLDER = "Opa", "Opa"
        SISTER_YOUNGER = "Singil", "Singil"
        UNCLE_FATHER = "Amaki", "Amaki"
        UNCLE_MOTHER = "Tog'a", "Tog'a"
        AUNT_MOTHER = "Xola", "Xola"
        AUNT_FATHER = "Amma", "Amma"
        GRANDMOTHER = "Buvi", "Buvi"
        GRANDFATHER = "Bobo", "Bobo"
        OTHER = "Boshqa", "Boshqa"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="parents")
    relation = models.CharField("Kim bo'ladi", max_length=10, choices=Relation.choices, blank=True)
    first_name = models.CharField("Ismi", max_length=50)
    last_name = models.CharField("Familiyasi", max_length=50, blank=True)
    phone = models.CharField("Telefon", max_length=9)

    class Meta:
        verbose_name = "Ota-ona"
        verbose_name_plural = "Ota-onalar"
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["branch", "phone"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Student(BaseModel):
    class Gender(models.TextChoices):
        MALE = "Erkak", "Erkak"
        FEMALE = "Ayol", "Ayol"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="students")
    first_name = models.CharField("Ism", max_length=20)
    last_name = models.CharField("Familiya", max_length=20)
    father_name = models.CharField("Sharif", max_length=50, blank=True)
    gender = models.CharField("Jins", max_length=5, choices=Gender.choices, blank=True)
    phone1 = models.CharField("1-telefon", max_length=9)
    phone2 = models.CharField("2-telefon", max_length=9, blank=True)
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    parent = models.ForeignKey(Parent, null=True, blank=True, on_delete=models.PROTECT, related_name="children", verbose_name="Vasiy")

    class Meta:
        verbose_name = "Talaba"
        verbose_name_plural = "Talabalar"
        ordering = ["first_name", "last_name"]
        indexes = [models.Index(fields=["branch", "last_name", "first_name"]), models.Index(fields=["phone1"]), models.Index(fields=["phone2"])]

    @property
    def full_name(self):
        return " ".join(p for p in (self.first_name, self.last_name, self.father_name) if p)

    def __str__(self):
        return self.full_name


class Lead(BaseModel):
    class LeadStatus(models.TextChoices):
        CALL_BACK = "1", "Qayta bog'lanishga"
        WAITING_GROUP = "2", "Yangi guruhga kutyapti"
        DEMO_BOOKED = "3", "Sinov darsga yozildi"
        DEMO_ATTENDED = "4", "Sinov darsga qatnashdi"
        STARTED = "5", "O'qishni boshladi"
        REJECTED = "6", "Ma'qul kelmadi"
        REJECTED_LOW = "7", "Ma'qul kelmadi (Sifatsiz)"
        LATER = "8", "Keyinroq o'qiydi"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="leads")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="leads")
    source = models.ForeignKey("references.LeadSource", on_delete=models.PROTECT, related_name="leads", verbose_name="Manba")
    course = models.ForeignKey("references.Course", on_delete=models.PROTECT, related_name="leads", verbose_name="Kurs")
    day_pattern = models.ForeignKey("references.DayPattern", null=True, blank=True, on_delete=models.PROTECT, related_name="leads", verbose_name="Hafta kunlari")
    preferred_times = models.ManyToManyField("references.LessonTime", blank=True, related_name="leads", verbose_name="Ma'qul dars vaqti")
    status = models.CharField(max_length=1, choices=LeadStatus.choices, default=LeadStatus.WAITING_GROUP, db_index=True)
    group = models.ForeignKey("education.Group", null=True, blank=True, on_delete=models.PROTECT, related_name="leads", verbose_name="Guruh")
    demo_date = models.DateField("Sinov dars kuni", null=True, blank=True)
    demo_attended = models.BooleanField("Sinov darsga qatnashdi", null=True, blank=True)
    age_group = models.CharField("Yosh guruhi", max_length=5, blank=True)
    social_status = models.CharField("Ijtimoiy holati", max_length=32, blank=True)
    laptop = models.CharField("Noutbuk", max_length=12, blank=True)
    tags = models.JSONField("Teglar", default=list, blank=True)
    callback_at = models.DateTimeField("Qayta bog'lanish vaqti", null=True, blank=True, db_index=True)  # 1- va 8-statuslarda; shu vaqtda botdan eslatma
    callback_reminded_at = models.DateTimeField("Eslatma yuborilgan vaqt", null=True, blank=True)
    callback_talked_at = models.DateTimeField("Suhbat bo'lgan vaqt (izoh kutilmoqda)", null=True, blank=True)  # qayta bog'lanishdagi lid bilan gaplashilgan, izoh hali yozilmagan

    class Meta:
        verbose_name = "Lid"
        verbose_name_plural = "Lidlar"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["branch", "created_at"])]
        constraints = [models.UniqueConstraint(fields=["branch", "student"], condition=ALIVE, name="uniq_lead_per_student")]

    def __str__(self):
        return str(self.student)


class LeadComment(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="comments")
    comment = models.TextField("Izoh")

    class Meta:
        verbose_name = "Lid izohi"
        verbose_name_plural = "Lid izohlari"
        ordering = ["-created_at"]

    def __str__(self):
        return self.comment[:60]

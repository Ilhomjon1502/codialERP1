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


class SmsTemplate(BaseModel):
    """SMS qolipi (2026-10-22): administratorlar o'zi yozadi. O'rinbosarlar — `apps/calls/sms.py` PLACEHOLDERS ({talaba}, {summa}…)."""

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="sms_templates", verbose_name="Filial")
    name = models.CharField("Nomi", max_length=100)
    text = models.TextField("Matn")
    status = models.CharField("Holat", max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "SMS qolipi"
        verbose_name_plural = "SMS qoliplari"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SmsMessage(BaseModel):
    """Qabul telefoni orqali yuboriladigan SMS. Administrator «Yuborish»ni bosadi → navbat; telefondagi ilova olib, o'z SIM'idan yuboradi
    va natijani qaytaradi. 2026-10-22 dan mijozlardan **kelgan** SMS ham (direction = Kiruvchi, status «Qabul qilindi», vaqti — sent_at,
    telefondagi kalit — external_id; faqat oddiy raqamlardan, talaba/vasiy/lidga bog'lanadi)."""

    class Direction(models.TextChoices):
        OUT = "Chiquvchi", "Chiquvchi"
        IN = "Kiruvchi", "Kiruvchi"

    class State(models.TextChoices):
        QUEUED = "Navbatda", "Navbatda"
        SENDING = "Yuborilmoqda", "Yuborilmoqda"
        SENT = "Yuborildi", "Yuborildi"
        FAILED = "Xato", "Xato"
        CANCELLED = "Bekor qilindi", "Bekor qilindi"
        RECEIVED = "Qabul qilindi", "Qabul qilindi"

    class Kind(models.TextChoices):
        DUE = "To'lov eslatmasi", "To'lov eslatmasi"
        INCOMING = "Mijozdan", "Mijozdan"
        # Avtomatik SMS (2026-10-23, auto_sms.py)
        LEAD = "Yangi lid", "Yangi lid"
        CONTRACT = "Shartnoma", "Shartnoma"
        MONTH = "Oy boshi", "Oy boshi"
        BONUS = "Oldindan to'lov", "Oldindan to'lov"
        ABSENCE = "Kelmadi", "Kelmadi"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="sms_messages")
    direction = models.CharField("Yo'nalish", max_length=10, choices=Direction.choices, default=Direction.OUT, db_index=True)
    external_id = models.CharField("Telefondagi kalit", max_length=64, blank=True)
    student = models.ForeignKey("crm.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages")
    parent = models.ForeignKey("crm.Parent", null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages")
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages")
    device = models.ForeignKey(CallDevice, on_delete=models.PROTECT, related_name="sms_messages", verbose_name="Qurilma")
    contract = models.ForeignKey("education.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages")
    template = models.ForeignKey(SmsTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    kind = models.CharField("Turi", max_length=20, choices=Kind.choices, default=Kind.DUE)
    month = models.DateField("Oy", null=True, blank=True)
    phone = models.CharField("Raqam (9 xona)", max_length=9)
    recipient = models.CharField("Kimga", max_length=20, blank=True)  # Talaba / Talaba (2-tel) / Vasiy
    text = models.TextField("Matn")
    parts = models.PositiveSmallIntegerField("SMS soni", default=1)
    status = models.CharField("Holat", max_length=14, choices=State.choices, default=State.QUEUED, db_index=True)
    error = models.CharField("Xato", max_length=200, blank=True)
    # Qabul qiluvchiga yetib borishi (operator xabari; hamma operator yubormaydi — bo'sh = noma'lum): «Yetkazildi» | «Yetkazilmadi»
    delivery = models.CharField("Yetkazilishi", max_length=14, blank=True, db_index=True)
    delivered_at = models.DateTimeField("Yetkazilgan vaqti", null=True, blank=True)
    detail = models.CharField("Telefon ma'lumoti", max_length=200, blank=True)  # SIM, operator va operator xato kodi
    key = models.CharField("Takrorlanmaslik kaliti", max_length=140, blank=True)  # avtomatik SMS: bitta voqea + raqam = bitta SMS
    problem_alerted_at = models.DateTimeField("Muammo haqida xabar berilgan", null=True, blank=True)
    taken_at = models.DateTimeField("Telefon oldi", null=True, blank=True)
    sent_at = models.DateTimeField("Yuborildi", null=True, blank=True)

    class Meta:
        verbose_name = "SMS"
        verbose_name_plural = "SMS xabarlar"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["device", "status"]), models.Index(fields=["contract", "month"]), models.Index(fields=["branch", "created_at"]),
                   models.Index(fields=["phone", "created_at"])]
        constraints = [models.UniqueConstraint(fields=["device", "external_id"], condition=~models.Q(external_id=""), name="uniq_sms_in_per_device"),
                       models.UniqueConstraint(fields=["key"], condition=~models.Q(key=""), name="uniq_sms_auto_key")]

    def __str__(self):
        return f"{self.phone} {self.status}"


class SmsRule(BaseModel):
    """Avtomatik SMS qoidasi (2026-10-23): har filialda 5 ta; administratorlar yoqadi/o'chiradi, matn va vaqtini o'zgartiradi. Boshida o'chiq."""

    class Key(models.TextChoices):
        LEAD = "lead", "Yangi lid"
        CONTRACT = "contract", "Shartnoma tuzilganda"
        MONTH_START = "month_start", "Oy boshi: to'lov muddati"
        PREPAY_BONUS = "prepay_bonus", "Oldindan to'lov bonusi"
        ABSENCE = "absence", "Sababsiz kelmagan"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="sms_rules", verbose_name="Filial")
    key = models.CharField("Qoida", max_length=16, choices=Key.choices)
    enabled = models.BooleanField("Yoqilgan", default=False)
    text = models.TextField("Matn")
    send_time = models.TimeField("Yuborish vaqti", null=True, blank=True)  # jadvalli qoidalar uchun
    day = models.PositiveSmallIntegerField("Oyning kuni", null=True, blank=True)  # oy boshi (1), bonus (25)
    enabled_at = models.DateTimeField("Yoqilgan vaqti", null=True, blank=True)  # shundan oldingi voqealarga SMS ketmaydi
    last_run_on = models.DateField("Oxirgi ishga tushgan kun", null=True, blank=True)

    class Meta:
        verbose_name = "Avtomatik SMS qoidasi"
        verbose_name_plural = "Avtomatik SMS qoidalari"
        ordering = ["branch", "key"]
        constraints = [models.UniqueConstraint(fields=["branch", "key"], condition=models.Q(is_deleted=False), name="uniq_sms_rule")]

    def __str__(self):
        return f"{self.get_key_display()} ({self.branch})"

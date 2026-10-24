"""Telegram bot (CLAUDE.md 12): xodim akkauntini bog'lash va xabarlar navbati (outbox).
Xabar avval bazaga yoziladi, `run_bot` jarayoni yuboradi — sayt Telegram'ni kutmaydi, token bo'lmasa ham ishlaydi."""

import secrets

from django.db import models

EVENTS = [
    ("new_lead", "Yangi lid"),
    ("lead_change", "Lid o'zgarishi (status)"),
    ("contract_change", "Shartnoma: yangi yoki o'zgargan"),
    ("approval", "Tasdiq kutayotgan chegirma yoki naqdsiz to'lov"),
    ("transfer", "Tasdiq kutayotgan o'tkazma"),
    ("makeup", "Qoldirilgan dars so'rovi"),
    ("attendance_missing", "Davomat olinmagan"),
    ("daily_report", "Kunlik hisobot (19:00)"),
    ("lesson_start", "Dars boshlandi — davomat olish vaqti"),
    ("morning_plan", "Ertalabki ish rejasi (8:30): to'lovlar, sinov darslari, qo'ng'iroqlar"),
    ("debt_lesson", "Dars boshlanishiga 10 daqiqa: shu guruhdagi qarzdor talabalar"),
    ("demo_soon", "Sinov darsiga 10 daqiqa qoldi: talaba va guruh"),
    ("lead_callback", "Lid: qayta bog'lanish vaqti keldi"),
    ("task", "Topshiriqlar: yangi, eslatma, bajarildi"),
    ("sms_problem", "SMS yuborishda muammo: telefon aloqasiz, xato, yetkazilmadi"),
    ("survey", "Tamomlagan/to'xtagan talaba so'rovnomasiga javob berdi"),
    ("referral", "Tavsiya bonusi berildi yoki berilmadi"),
]
EVENT_KEYS = [k for k, _ in EVENTS]


def new_code():
    return secrets.token_hex(4).upper()


class TelegramLink(models.Model):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="telegram")
    code = models.CharField("Bog'lash kodi", max_length=16, unique=True, default=new_code)
    chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    username = models.CharField(max_length=64, blank=True)
    linked_at = models.DateTimeField(null=True, blank=True)
    prefs = models.JSONField("Qaysi xabarlar", default=dict, blank=True)

    class Meta:
        verbose_name = "Telegram bog'lanishi"
        verbose_name_plural = "Telegram bog'lanishlari"

    def __str__(self):
        return f"{self.user} → {self.chat_id or 'bog`lanmagan'}"


class ExtraRecipient(models.Model):
    """Qo'shimcha qabul qiluvchi (xodim akkaunti emas — masalan umumiy @codial_admin): tanlangan rollarga standart keladigan xabarlarning nusxasi shu chatga ham yuboriladi."""

    label = models.CharField("Nomi", max_length=80)
    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=64, blank=True)
    roles = models.JSONField("Qaysi rollar xabarlarining nusxasi", default=list)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Qo'shimcha Telegram qabul qiluvchi"
        verbose_name_plural = "Qo'shimcha Telegram qabul qiluvchilar"

    def __str__(self):
        return f"{self.label} ({self.chat_id})"


class Outbox(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Navbatda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Xato"

    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.CASCADE, related_name="+")  # bo'sh — qo'shimcha qabul qiluvchi (ExtraRecipient)
    chat_id = models.BigIntegerField()
    event = models.CharField(max_length=32, choices=EVENTS)
    key = models.CharField("Takrorlanmaslik kaliti", max_length=120, blank=True, db_index=True)
    text = models.TextField()
    markup = models.JSONField("Tugmalar (reply_markup)", default=dict, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Telegram xabari"
        verbose_name_plural = "Telegram xabarlari"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.event} → {self.user}: {self.status}"

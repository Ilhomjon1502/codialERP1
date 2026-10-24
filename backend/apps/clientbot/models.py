"""Mijozlar Telegram boti (2026-10-24): o'quvchi va vasiylar uchun alohida bot.

Bog'lash: lid/shartnoma SMS'ida har raqamga alohida kod (`BotInvite`) → bot `/start KOD` → `BotLink` (Telegram akkaunt ↔ talaba).
Bir raqam — bir taklif; bitta Telegram akkaunt bir necha farzandga (vasiy) ulanishi mumkin.
Xabarlar avval `ClientOutbox`ga yoziladi, `run_clientbot` jarayoni yuboradi (xodimlar botidagi Outbox kabi).
"""

import secrets

from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, Status

ALIVE = Q(is_deleted=False)
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 0/O, 1/I/L aralashmasin — SMS'dan qo'lda yozish mumkin


def new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


class BotConfig(BaseModel):
    """Filial sozlamalari (Qo'ng'iroqlar va SMS → Telegram bot → Sozlamalar)."""

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="bot_configs", verbose_name="Filial")
    invite_in_sms = models.BooleanField("Lid va shartnoma SMS'iga bot havolasi qo'shilsin", default=True)
    referral_bonus = models.DecimalField("Tavsiya bonusi (so'm)", max_digits=14, decimal_places=0, default=75_000)
    referral_min_percent = models.PositiveSmallIntegerField("Bonus uchun birinchi to'lov (oy narxining %)", default=50)
    reminder_days = models.PositiveSmallIntegerField("Start eslatmasi oralig'i (kun)", default=7)
    reminder_max = models.PositiveSmallIntegerField("Start eslatmasi ko'pi bilan (marta)", default=3)
    notify_payments = models.BooleanField("To'lov kiritilganda talaba va vasiyga botda xabar", default=True)

    class Meta:
        verbose_name = "Bot sozlamasi"
        verbose_name_plural = "Bot sozlamalari"
        constraints = [models.UniqueConstraint(fields=["branch"], condition=ALIVE, name="uniq_bot_config")]

    def __str__(self):
        return f"Bot sozlamasi ({self.branch})"


class BotInvite(BaseModel):
    """Taklif: talaba + bitta telefon raqami uchun bog'lash kodi. Kod SMS'da boradi."""

    class Role(models.TextChoices):
        STUDENT = "Talaba", "Talaba"
        GUARDIAN = "Vasiy", "Vasiy"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="bot_invites")
    student = models.ForeignKey("crm.Student", on_delete=models.CASCADE, related_name="bot_invites")
    parent = models.ForeignKey("crm.Parent", null=True, blank=True, on_delete=models.SET_NULL, related_name="bot_invites")
    phone = models.CharField("Raqam (9 xona)", max_length=9)
    role = models.CharField("Kim", max_length=8, choices=Role.choices, blank=True)  # bo'sh — ulanganda bot so'raydi
    code = models.CharField("Kod", max_length=16, unique=True, default=new_code)
    reminders = models.PositiveSmallIntegerField("Start eslatmalari (B2)", default=0)
    last_reminded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Bot taklifi"
        verbose_name_plural = "Bot takliflari"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["student", "phone"], condition=ALIVE, name="uniq_bot_invite")]

    def __str__(self):
        return f"{self.student} · {self.phone}"


class BotAccount(models.Model):
    """Telegram akkaunt (chat). Suhbat holati (`state`) — savol-javob qadamlari uchun."""

    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    state = models.JSONField(default=dict, blank=True)
    fails = models.PositiveSmallIntegerField("Noto'g'ri kod urinishlari", default=0)
    fail_since = models.DateTimeField(null=True, blank=True)
    blocked = models.BooleanField("Botni bloklagan", default=False)

    class Meta:
        verbose_name = "Bot akkaunti"
        verbose_name_plural = "Bot akkauntlari"

    def __str__(self):
        return f"{self.chat_id} {self.username}".strip()


class LinkAttempt(models.Model):
    """Shartnoma raqami orqali ulanishda talaba bo'yicha noto'g'ri telefon urinishlari (hisob-kitob: sutkada ko'pi bilan `MAX` ta) —
    raqamlarni ketma-ket sinab ko'rib birovning ma'lumotiga kirib bo'lmasin."""

    student = models.OneToOneField("crm.Student", on_delete=models.CASCADE, related_name="link_attempt")
    fails = models.PositiveSmallIntegerField(default=0)
    since = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ulanish urinishi"
        verbose_name_plural = "Ulanish urinishlari"

    def __str__(self):
        return f"{self.student}: {self.fails}"


class BotLink(models.Model):
    """Akkaunt ↔ talaba. `role` — talabaning o'zi yoki vasiy."""

    account = models.ForeignKey(BotAccount, on_delete=models.CASCADE, related_name="links")
    student = models.ForeignKey("crm.Student", on_delete=models.CASCADE, related_name="bot_links")
    parent = models.ForeignKey("crm.Parent", null=True, blank=True, on_delete=models.SET_NULL, related_name="bot_links")
    invite = models.ForeignKey(BotInvite, null=True, blank=True, on_delete=models.SET_NULL, related_name="links")
    role = models.CharField(max_length=8, choices=BotInvite.Role.choices, blank=True)  # bo'sh — hali tanlanmagan
    phone = models.CharField(max_length=9)
    linked_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bot bog'lanishi"
        verbose_name_plural = "Bot bog'lanishlari"
        ordering = ["-linked_at"]
        constraints = [models.UniqueConstraint(fields=["account", "student"], name="uniq_bot_link")]

    def __str__(self):
        return f"{self.account} → {self.student} ({self.role or '?'})"


class LeadSurvey(models.Model):
    """Lid botda «Codialni qayerdan topdingiz?» ga javob bergan. Admin kiritgan `Lead.source` o'zgarmaydi."""

    lead = models.OneToOneField("crm.Lead", on_delete=models.CASCADE, related_name="bot_survey")
    account = models.ForeignKey(BotAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    source = models.ForeignKey("references.LeadSource", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lid so'rovnomasi"
        verbose_name_plural = "Lid so'rovnomalari"
        ordering = ["-answered_at"]

    def __str__(self):
        return f"{self.lead} → {self.source}"


class Referral(BaseModel):
    """Tavsiya: lid «tanishimdan eshitdim» degan. Lid o'qishni boshlab birinchi to'lov qilganda tavsiya qiluvchiga bonus (B5)."""

    class State(models.TextChoices):
        UNMATCHED = "Aniqlanmagan", "Aniqlanmagan"  # ism yozilgan, lekin talabalar orasida topilmadi — administrator bog'laydi
        PENDING = "Kutilmoqda", "Kutilmoqda"
        PAID = "Berildi", "Berildi"
        REJECTED = "Rad etildi", "Rad etildi"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="referrals")
    lead = models.OneToOneField("crm.Lead", on_delete=models.CASCADE, related_name="referral")
    referrer_student = models.ForeignKey("crm.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals_made")
    referrer_text = models.CharField("Lid yozgan ism", max_length=200, blank=True)
    state = models.CharField(max_length=14, choices=State.choices, default=State.UNMATCHED, db_index=True)
    bonus = models.DecimalField("Bonus", max_digits=14, decimal_places=0, null=True, blank=True)
    payment = models.ForeignKey("finance.Payment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")  # lidning birinchi to'lovi
    bonus_payment = models.ForeignKey("finance.Payment", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")  # tavsiya qiluvchiga yozilgan chegirma
    paid_at = models.DateTimeField(null=True, blank=True)
    comment = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Tavsiya"
        verbose_name_plural = "Tavsiyalar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead} ← {self.referrer_student or self.referrer_text}"


class ClientOutbox(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Navbatda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Xato"

    account = models.ForeignKey(BotAccount, on_delete=models.CASCADE, related_name="outbox")
    kind = models.CharField("Turi (SMS turlari bilan bir xil)", max_length=24, blank=True)
    # Qaysi talaba/shartnoma/lid haqida va qaysi raqam o'rniga (SMS o'rniga botga ketgan xabarlar jurnali va takrorlanmaslik tekshiruvi uchun)
    student = models.ForeignKey("crm.Student", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    contract = models.ForeignKey("education.Contract", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    lead = models.ForeignKey("crm.Lead", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    month = models.DateField("Oy", null=True, blank=True)
    phone = models.CharField("Raqam (9 xona)", max_length=9, blank=True)
    recipient = models.CharField("Kimga", max_length=20, blank=True)
    key = models.CharField("Takrorlanmaslik kaliti", max_length=140, blank=True, db_index=True)
    text = models.TextField()
    markup = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Mijoz xabari"
        verbose_name_plural = "Mijoz xabarlari"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["contract", "month"])]

    def __str__(self):
        return f"{self.kind} → {self.account}: {self.status}"


class SurveyQuestion(BaseModel):
    """Tamomlash/to'xtatish so'rovnomasi savoli (B4). Bosh menejer «Telegram bot → So'rovnoma»da qo'shadi, tahrirlaydi, o'chiradi."""

    class Kind(models.TextChoices):
        CHOICE = "Tanlov", "Tanlov (variantlardan)"
        SCALE = "Baho", "Baho (1–5)"
        TEXT = "Matn", "Matn (o'zi yozadi)"

    class Flow(models.TextChoices):
        BOTH = "Hammasiga", "Hammasiga"
        COMPLETED = "Tamomlaganlarga", "Kursni tamomlaganlarga"
        STOPPED = "To'xtatganlarga", "To'xtatganlarga"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="survey_questions", verbose_name="Filial")
    key = models.CharField("Ichki kalit (reason — to'xtatish sababi)", max_length=24, blank=True)
    text = models.CharField("Savol", max_length=300)
    kind = models.CharField("Turi", max_length=8, choices=Kind.choices, default=Kind.CHOICE)
    options = models.JSONField("Variantlar", default=list, blank=True)
    allow_other = models.BooleanField("«Boshqa (yozaman)» varianti", default=False)
    flow = models.CharField("Kimga", max_length=16, choices=Flow.choices, default=Flow.BOTH)
    order = models.PositiveSmallIntegerField("Tartib", default=100)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = "So'rovnoma savoli"
        verbose_name_plural = "So'rovnoma savollari"
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.text


class ExitSurvey(BaseModel):
    """Shartnomasi tugagan talabaga yuborilgan so'rovnoma (shartnomaga bitta). Javob — birinchi javob bergan akkauntdan (o'quvchi yoki vasiy)."""

    class State(models.TextChoices):
        SENT = "Yuborildi", "Yuborildi"
        STARTED = "Jarayonda", "Jarayonda"
        DONE = "Tugadi", "Tugadi"

    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="exit_surveys")
    contract = models.ForeignKey("education.Contract", on_delete=models.CASCADE, related_name="exit_surveys")
    student = models.ForeignKey("crm.Student", on_delete=models.CASCADE, related_name="exit_surveys")
    flow = models.CharField(max_length=16, choices=SurveyQuestion.Flow.choices)  # BOTH bo'lmaydi: Tamomlaganlarga yoki To'xtatganlarga
    stop_reason = models.CharField("Shartnomadagi sabab (administrator kiritgan)", max_length=48, blank=True)
    state = models.CharField(max_length=10, choices=State.choices, default=State.SENT, db_index=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    account = models.ForeignKey(BotAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    respondent_role = models.CharField(max_length=8, blank=True)
    answers = models.JSONField("Javoblar [{q, key, question, kind, answer}]", default=list, blank=True)

    class Meta:
        verbose_name = "Tamomlash so'rovnomasi"
        verbose_name_plural = "Tamomlash so'rovnomalari"
        ordering = ["-sent_at"]
        constraints = [models.UniqueConstraint(fields=["contract"], condition=ALIVE, name="uniq_exit_survey")]

    def __str__(self):
        return f"{self.student} · {self.state}"

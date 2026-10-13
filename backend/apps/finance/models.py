"""Moliya (CLAUDE.md 7.5): g'aznalar, yagona pul harakatlari jurnali (CashMovement), to'lovlar, o'tkazmalar, ayirboshlash,
xarajatlar, kreditorlar. Har bir pul amali servis orqali CashMovement qatorlarini yaratadi (services.sync_movements)."""

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, Status

ALIVE = Q(is_deleted=False)
Money = dict(max_digits=14, decimal_places=0)


class CashType(models.TextChoices):
    CASH = "CASH", "Naqd"
    BANK = "BANK", "Bank"
    CARD = "CARD", "Karta"
    ALL = "ALL", "Hammasi"  # faqat g'azna turi sifatida, to'lov/xarajatda tanlanmaydi


MONEY_TYPES = [(CashType.CASH, "Naqd"), (CashType.CARD, "Karta"), (CashType.BANK, "Bank")]


class Confirm(models.TextChoices):
    PENDING = "Tasdiqlashga", "Tasdiqlashga"
    CONFIRMED = "Tasdiqlandi", "Tasdiqlandi"


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

    @property
    def base_type(self):
        """Boshlang'ich qoldiq qaysi pul turida hisoblanadi: «Hammasi» g'aznada — naqd."""
        return CashType.CASH if self.cash_type == CashType.ALL else self.cash_type

    def __str__(self):
        return self.name


class CashMovement(models.Model):
    """Yagona pul harakatlari jurnali. Manba (to'lov, xarajat…) o'zgarsa qatorlari qayta yoziladi — bu hosila ma'lumot,
    manba yozuvlari esa soft delete bilan saqlanadi. Balans = boshlang'ich qoldiq + Σ tasdiqlangan harakatlar."""

    class Source(models.TextChoices):
        PAYMENT = "payment", "To'lov"
        EXPENSE = "expense", "Xarajat"
        TRANSFER = "transfer", "O'tkazma"
        EXCHANGE = "exchange", "Ayirboshlash"
        CREDITOR = "creditor", "Kreditor"
        SALARY = "salary", "Oylik berish"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="movements")
    cash_type = models.CharField(max_length=4, choices=MONEY_TYPES)
    amount = models.DecimalField(**Money)
    date = models.DateField()
    source_type = models.CharField(max_length=10, choices=Source.choices)
    source_id = models.UUIDField()
    is_confirmed = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pul harakati"
        verbose_name_plural = "Pul harakatlari"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["account", "is_confirmed", "cash_type"]), models.Index(fields=["source_type", "source_id"]), models.Index(fields=["account", "date"])]

    def __str__(self):
        return f"{self.account} {self.amount:+} {self.cash_type} ({self.get_source_type_display()})"


class Payment(BaseModel):
    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="payments")
    contract = models.ForeignKey("education.Contract", on_delete=models.PROTECT, related_name="payments", verbose_name="Shartnoma")
    group = models.ForeignKey("education.Group", on_delete=models.PROTECT, related_name="payments", verbose_name="Guruh")
    number = models.PositiveIntegerField("Chek raqami")
    date = models.DateField("Sana")
    amount = models.DecimalField("Summa", default=0, validators=[MinValueValidator(0)], **Money)
    cash_type = models.CharField("To'lov shakli", max_length=4, choices=MONEY_TYPES, blank=True)
    cashbox = models.ForeignKey(Account, null=True, blank=True, on_delete=models.PROTECT, related_name="payments", verbose_name="G'azna")
    accountant = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="Hisobchi")
    discount_type = models.ForeignKey("references.DiscountType", null=True, blank=True, on_delete=models.PROTECT, related_name="payments", verbose_name="Chegirma turi")
    discount = models.DecimalField("Chegirma", default=0, validators=[MinValueValidator(0)], **Money)
    discount_status = models.CharField("Chegirma tasdig'i", max_length=12, choices=Confirm.choices, blank=True, db_index=True)
    discount_confirmed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    discount_confirmed_at = models.DateTimeField(null=True, blank=True)
    noncash_status = models.CharField("Naqdsiz tasdig'i", max_length=12, choices=Confirm.choices, blank=True, db_index=True)
    noncash_confirmed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    noncash_confirmed_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["branch", "date"]), models.Index(fields=["contract", "date"])]
        constraints = [models.UniqueConstraint(fields=["branch", "number"], condition=ALIVE, name="uniq_payment_number")]

    @property
    def locked(self):
        """Tasdiqlangan to'lov yoki chegirmani faqat Admin va Bosh menejer o'zgartiradi (6.4)."""
        return Confirm.CONFIRMED in (self.discount_status, self.noncash_status)

    def __str__(self):
        return f"{self.contract} · {self.amount:,.0f} ({self.date:%d.%m.%Y})".replace(",", " ")


class Transfer(BaseModel):
    date = models.DateField("Sana")
    sender_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transfers_out", verbose_name="Yuboruvchi g'azna")
    sender_cashier = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cash_type = models.CharField(max_length=4, choices=MONEY_TYPES, default=CashType.CASH)
    amount = models.DecimalField("Summa", validators=[MinValueValidator(0)], **Money)
    receiver_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transfers_in", verbose_name="Qabul qiluvchi g'azna")
    receiver_cashier = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=12, choices=Confirm.choices, default=Confirm.PENDING, db_index=True)
    confirmed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    confirmed_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "O'tkazma"
        verbose_name_plural = "O'tkazmalar"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.sender_account} → {self.receiver_account}: {self.amount:,.0f}".replace(",", " ")


class Exchange(BaseModel):
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="exchanges", verbose_name="G'azna")
    date = models.DateField("Sana")
    from_type = models.CharField(max_length=4, choices=MONEY_TYPES)
    amount = models.DecimalField("Berilgan", validators=[MinValueValidator(0)], **Money)
    to_type = models.CharField(max_length=4, choices=MONEY_TYPES)
    amount_to = models.DecimalField("Olingan", validators=[MinValueValidator(0)], **Money)
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Pul ayirboshlash"
        verbose_name_plural = "Pul ayirboshlash"
        ordering = ["-date", "-created_at"]

    @property
    def loss(self):
        return self.amount - self.amount_to

    def __str__(self):
        return f"{self.account}: {self.amount:,.0f} {self.from_type} → {self.amount_to:,.0f} {self.to_type}".replace(",", " ")


class Expense(BaseModel):
    branch = models.ForeignKey("references.Branch", on_delete=models.PROTECT, related_name="expenses")
    date = models.DateField("Sana")
    category = models.ForeignKey("references.ExpenseCategory", on_delete=models.PROTECT, related_name="expenses", verbose_name="Kategoriya")
    name = models.CharField("Nomi", max_length=150)
    quantity = models.PositiveIntegerField("Soni", default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField("Narxi", validators=[MinValueValidator(0)], **Money)
    total = models.DecimalField("Jami", **Money)
    cash_type = models.CharField("To'lov shakli", max_length=4, choices=MONEY_TYPES)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="expenses", verbose_name="G'azna")
    cashier = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="G'aznachi")
    period_year = models.PositiveSmallIntegerField("Hisob davri: yil")
    period_month = models.PositiveSmallIntegerField("Hisob davri: oy")
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["branch", "date"]), models.Index(fields=["branch", "period_year", "period_month"]), models.Index(fields=["category"])]

    def __str__(self):
        return f"{self.name}: {self.total:,.0f}".replace(",", " ")


class Creditor(BaseModel):
    name = models.CharField("Nomi", max_length=150)
    initial_balance = models.DecimalField("Boshlang'ich haqqi", default=0, **Money)

    class Meta:
        verbose_name = "Kreditor"
        verbose_name_plural = "Kreditorlar"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name"], condition=ALIVE, name="uniq_creditor_name")]

    def __str__(self):
        return self.name


class CreditorTransaction(BaseModel):
    """Belgisi: «−» qarz olish (g'aznaga pul kiradi), «+» qarz qaytarish (g'aznadan chiqadi). G'aznaga ta'siri: −amount."""

    date = models.DateField("Sana")
    creditor = models.ForeignKey(Creditor, on_delete=models.PROTECT, related_name="transactions")
    amount = models.DecimalField("Summa (− olish / + qaytarish)", **Money)
    cash_type = models.CharField(max_length=4, choices=MONEY_TYPES)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="creditor_transactions", verbose_name="G'azna")
    cashier = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    comment = models.TextField("Izoh", blank=True)

    class Meta:
        verbose_name = "Kreditor amali"
        verbose_name_plural = "Kreditor amallari"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.creditor}: {self.amount:+,.0f}".replace(",", " ")


class CreditorComment(BaseModel):
    creditor = models.ForeignKey(Creditor, on_delete=models.CASCADE, related_name="comments")
    comment = models.TextField("Izoh")

    class Meta:
        verbose_name = "Kreditor izohi"
        verbose_name_plural = "Kreditor izohlari"
        ordering = ["-created_at"]

    def __str__(self):
        return self.comment[:60]

"""Maydon nomlari prototip bilan bir xil: disc_status, nc_status, cashbox, sender/receiver, initial va h.k."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.core.permissions import role_code
from apps.education.models import Contract
from apps.references.models import DiscountType, ExpenseCategory

from . import services
from .models import MONEY_TYPES, Account, CashMovement, Creditor, CreditorComment, CreditorTransaction, Exchange, Expense, Payment, Transfer

Money = dict(max_digits=14, decimal_places=0)
USERS = User.objects.all()
ACCOUNTS = Account.objects.all()


class PaymentSerializer(serializers.ModelSerializer):
    contract = serializers.PrimaryKeyRelatedField(queryset=Contract.objects.all())
    amount = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    discount = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    cash_type = serializers.ChoiceField(choices=MONEY_TYPES, required=False, allow_blank=True)
    cashbox = serializers.PrimaryKeyRelatedField(queryset=ACCOUNTS, required=False, allow_null=True)
    accountant = serializers.PrimaryKeyRelatedField(queryset=USERS, required=False, allow_null=True)
    discount_type = serializers.PrimaryKeyRelatedField(queryset=DiscountType.objects.all(), required=False, allow_null=True)
    date = serializers.DateField(required=False)
    disc_status = serializers.CharField(source="discount_status", read_only=True)
    disc_by = serializers.PrimaryKeyRelatedField(source="discount_confirmed_by", read_only=True)
    disc_at = serializers.DateTimeField(source="discount_confirmed_at", read_only=True)
    nc_status = serializers.CharField(source="noncash_status", read_only=True)
    nc_by = serializers.PrimaryKeyRelatedField(source="noncash_confirmed_by", read_only=True)
    nc_at = serializers.DateTimeField(source="noncash_confirmed_at", read_only=True)
    contract_name = serializers.CharField(source="contract.name", read_only=True)
    locked = serializers.BooleanField(read_only=True)
    can_approve_disc = serializers.SerializerMethodField()
    can_approve_nc = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "branch", "contract", "contract_name", "group", "number", "date", "amount", "cash_type", "cashbox", "accountant", "discount_type",
                  "discount", "disc_status", "disc_by", "disc_at", "nc_status", "nc_by", "nc_at", "comment", "locked", "can_approve_disc", "can_approve_nc",
                  "created_by", "created_at"]
        read_only_fields = ["branch", "group", "number", "created_by", "created_at"]

    def get_can_approve_disc(self, p):
        return p.discount_status == "Tasdiqlashga" and services.can_approve_discount(self.context["request"].user, p)

    def get_can_approve_nc(self, p):
        return p.noncash_status == "Tasdiqlashga" and services.can_approve_noncash(self.context["request"].user, p)


class TransferSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(source="sender_account", queryset=ACCOUNTS)
    receiver = serializers.PrimaryKeyRelatedField(source="receiver_account", queryset=ACCOUNTS)
    sender_cashier = serializers.PrimaryKeyRelatedField(queryset=USERS, required=False, allow_null=True)
    receiver_cashier = serializers.PrimaryKeyRelatedField(queryset=USERS, required=False, allow_null=True)
    amount = serializers.DecimalField(min_value=0, **Money)
    date = serializers.DateField(required=False)
    direction = serializers.SerializerMethodField()
    can_confirm = serializers.SerializerMethodField()
    can_modify = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = ["id", "date", "sender", "sender_cashier", "cash_type", "amount", "receiver", "receiver_cashier", "status", "confirmed_by", "confirmed_at",
                  "comment", "direction", "can_confirm", "can_modify", "created_by", "created_at"]
        read_only_fields = ["cash_type", "status", "confirmed_by", "confirmed_at", "created_by", "created_at"]

    def _mine(self):
        if "_mine" not in self.context:
            self.context["_mine"] = set(Account.objects.filter(responsible=self.context["request"].user).values_list("id", flat=True))
        return self.context["_mine"]

    def get_direction(self, t):
        mine = self._mine()
        return "Chiquvchi" if t.sender_account_id in mine else "Kiruvchi" if t.receiver_account_id in mine else "Boshqa"

    def get_can_modify(self, t):
        """Tasdiqlanmaguncha tahrirlash va o'chirish (finance.services.can_modify_pending)."""
        from .services import can_modify_pending

        u = self.context["request"].user
        return can_modify_pending(u, t)

    def get_can_confirm(self, t):
        return t.status == "Tasdiqlashga" and (role_code(self.context["request"].user) == "ADMIN" or t.receiver_account_id in self._mine())


class ExchangeSerializer(serializers.ModelSerializer):
    from_type = serializers.ChoiceField(choices=MONEY_TYPES)
    to_type = serializers.ChoiceField(choices=MONEY_TYPES)
    amount = serializers.DecimalField(min_value=0, **Money)
    amount_to = serializers.DecimalField(min_value=0, **Money)
    loss = serializers.DecimalField(read_only=True, **Money)

    class Meta:
        model = Exchange
        fields = ["id", "account", "date", "from_type", "amount", "to_type", "amount_to", "loss", "comment", "created_by", "created_at"]
        read_only_fields = ["date", "created_by", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ExpenseCategory.objects.all())
    cash_type = serializers.ChoiceField(choices=MONEY_TYPES)
    account = serializers.PrimaryKeyRelatedField(queryset=ACCOUNTS)
    cashier = serializers.PrimaryKeyRelatedField(queryset=USERS, required=False, allow_null=True)
    price = serializers.DecimalField(min_value=0, **Money)
    quantity = serializers.IntegerField(min_value=1, error_messages={"min_value": "Kamida 1"})
    period_year = serializers.IntegerField(required=False, min_value=2020, max_value=2100)
    period_month = serializers.IntegerField(required=False, min_value=1, max_value=12)

    class Meta:
        model = Expense
        fields = ["id", "branch", "date", "category", "name", "quantity", "price", "total", "cash_type", "account", "cashier", "period_year", "period_month",
                  "comment", "created_by", "created_at"]
        read_only_fields = ["branch", "total", "created_by", "created_at"]


class CreditorSerializer(serializers.ModelSerializer):
    initial = serializers.DecimalField(source="initial_balance", required=False, default=0, **Money)
    current = serializers.DecimalField(read_only=True, default=0, **Money)

    class Meta:
        model = Creditor
        fields = ["id", "name", "initial", "current", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]

    def validate_name(self, v):
        v = " ".join(v.split())
        if Creditor.objects.filter(name__iexact=v).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Avval qo'shilgan nom")
        return v


class CreditorTxSerializer(serializers.ModelSerializer):
    cash_type = serializers.ChoiceField(choices=MONEY_TYPES)
    amount = serializers.DecimalField(**Money)

    class Meta:
        model = CreditorTransaction
        fields = ["id", "date", "creditor", "amount", "cash_type", "account", "cashier", "comment", "created_by", "created_at"]
        read_only_fields = ["cashier", "created_by", "created_at"]


class CreditorCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditorComment
        fields = ["id", "creditor", "comment", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class MovementSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="cash_type")
    src = serializers.CharField(source="get_source_type_display")
    ref = serializers.CharField(source="note")
    confirmed = serializers.BooleanField(source="is_confirmed")

    class Meta:
        model = CashMovement
        fields = ["id", "account", "type", "amount", "date", "source_type", "source_id", "src", "ref", "confirmed"]

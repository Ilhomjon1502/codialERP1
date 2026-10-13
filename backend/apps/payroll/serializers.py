"""Maydon nomlari prototip bilan bir xil: fixed (stavkada — fixed_amount), effective_from 'YYYY-MM', tkpi, skpi, carried, final."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.finance.models import MONEY_TYPES, Account
from apps.references.models import Course
from apps.references.serializers import YearMonthField

from .models import KPIRate, SalaryAssignment, SalaryPayout

Money = dict(max_digits=14, decimal_places=0)


class KPIRateSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    effective_from = YearMonthField()
    fixed = serializers.DecimalField(source="fixed_amount", min_value=0, required=False, default=0, **Money)
    percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False, default=0, coerce_to_string=False)

    class Meta:
        model = KPIRate
        fields = ["id", "branch", "user", "role_type", "course", "effective_from", "type", "fixed", "percent", "created_by", "created_at"]
        read_only_fields = ["branch", "created_by", "created_at"]


class SalaryAssignmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    fixed = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    bonus = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    kpi = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    fine = serializers.DecimalField(min_value=0, required=False, default=0, **Money)
    opening = serializers.DecimalField(source="opening_balance", required=False, default=0, **Money)
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    tkpi = serializers.DecimalField(read_only=True, default=0, **Money)
    skpi = serializers.DecimalField(read_only=True, default=0, **Money)
    total = serializers.DecimalField(read_only=True, default=0, **Money)
    given = serializers.DecimalField(read_only=True, default=0, **Money)
    carried = serializers.DecimalField(read_only=True, default=0, **Money)
    final = serializers.DecimalField(read_only=True, default=0, **Money)

    class Meta:
        model = SalaryAssignment
        fields = ["id", "branch", "user", "year", "month", "fixed", "bonus", "kpi", "fine", "opening", "comment",
                  "tkpi", "skpi", "total", "given", "carried", "final", "created_by", "created_at"]
        read_only_fields = ["branch", "created_by", "created_at"]


class SalaryPayoutSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    cash_type = serializers.ChoiceField(choices=MONEY_TYPES)
    amount = serializers.DecimalField(min_value=0, **Money)
    date = serializers.DateField(required=False)
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020, max_value=2100)

    class Meta:
        model = SalaryPayout
        fields = ["id", "branch", "user", "year", "month", "date", "type", "amount", "cash_type", "account", "cashier", "comment", "created_by", "created_at"]
        read_only_fields = ["branch", "cashier", "created_by", "created_at"]

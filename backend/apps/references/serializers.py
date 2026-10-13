"""Maydon nomlari front-end (prototip) bilan bir xil: start/end, max, pattern, effective_from='YYYY-MM' va h.k."""

import datetime

from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.core.permissions import can
from apps.core.roles import RoleCode
from apps.core.viewsets import BranchScopedSerializerMixin
from apps.finance import services as fin
from apps.finance.models import Account

from . import services
from .models import AttendanceStatus, Branch, Course, CoursePrice, DayPattern, DiscountType, ExpenseCategory, LeadSource, LessonFrequency, LessonTime, Room


class YearMonthField(serializers.Field):
    default_error_messages = {"invalid": "Oy formati: YYYY-MM"}

    def to_representation(self, value):
        return value.strftime("%Y-%m")

    def to_internal_value(self, data):
        try:
            y, m = (int(x) for x in str(data).split("-")[:2])
            return datetime.date(y, m, 1)
        except (TypeError, ValueError):
            self.fail("invalid")


HHMM = dict(format="%H:%M", input_formats=["%H:%M", "%H:%M:%S"])


def unique_name(model, value, instance, message, field="name"):
    value = " ".join(str(value).split())
    if model.objects.filter(**{f"{field}__iexact": value}).exclude(pk=getattr(instance, "pk", None)).exists():
        raise serializers.ValidationError(message)
    return value


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "status", "default_cashbox", "noncash_cashbox"]

    def validate_name(self, v):
        return unique_name(Branch, v, self.instance, "Avval qo'shilgan")


class CourseSerializer(serializers.ModelSerializer):
    branches = serializers.PrimaryKeyRelatedField(many=True, queryset=Branch.objects.all(), required=False)

    class Meta:
        model = Course
        fields = ["id", "name", "status", "branches"]

    def validate_name(self, v):
        return unique_name(Course, v, self.instance, "Avval kiritilgan nom")


class RoomSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "branch", "name", "capacity", "status"]
        extra_kwargs = {"capacity": {"min_value": 1, "error_messages": {"min_value": "Kamida 1"}}}


class DayPatternSerializer(serializers.ModelSerializer):
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=7), allow_empty=False)

    class Meta:
        model = DayPattern
        fields = ["id", "name", "weekdays", "status"]
        read_only_fields = ["name"]

    def validate_weekdays(self, v):
        key = ",".join(map(str, sorted(set(v))))
        if DayPattern.objects.filter(weekdays_key=key).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Avval kiritilgan, mavjudlarni tekshiring")
        return sorted(set(v))


class LessonTimeSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    start = serializers.TimeField(source="start_time", **HHMM)
    end = serializers.TimeField(source="end_time", **HHMM)

    class Meta:
        model = LessonTime
        fields = ["id", "branch", "start", "end", "status"]

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end": "Tugash vaqti boshlanishdan keyin bo'lsin"})
        if LessonTime.objects.filter(branch=branch, start_time=start, end_time=end).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError({"start": "Avval qo'shilgan vaqt!"})
        return attrs


class CoursePriceSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    effective_from = YearMonthField()
    price = serializers.DecimalField(max_digits=14, decimal_places=0, min_value=0)

    class Meta:
        model = CoursePrice
        fields = ["id", "branch", "course", "effective_from", "price"]


class LessonFrequencySerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    pattern = serializers.PrimaryKeyRelatedField(source="day_pattern", queryset=DayPattern.objects.all())
    courses = serializers.PrimaryKeyRelatedField(many=True, queryset=Course.objects.all(), required=False)
    frequency = serializers.IntegerField(
        min_value=4, max_value=26,
        error_messages={"min_value": "Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos", "max_value": "Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos"},
    )

    class Meta:
        model = LessonFrequency
        fields = ["id", "branch", "pattern", "courses", "year", "month", "frequency", "status", "approved_by", "approved_at"]
        read_only_fields = ["status", "approved_by", "approved_at"]

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        courses = attrs.get("courses", list(self.instance.courses.all()) if self.instance else [])
        services.check_frequency_overlap(get("branch"), get("day_pattern"), get("year"), get("month"), courses, getattr(self.instance, "pk", None))
        return attrs


class DiscountTypeSerializer(serializers.ModelSerializer):
    max = serializers.DecimalField(source="max_amount", max_digits=14, decimal_places=0, min_value=0)
    courses = serializers.PrimaryKeyRelatedField(many=True, queryset=Course.objects.all(), required=False)

    class Meta:
        model = DiscountType
        fields = ["id", "name", "max", "is_system", "courses"]

    def validate_name(self, v):
        return unique_name(DiscountType, v, self.instance, "Avval qo'shilgan nom!")


class ExpenseCategorySerializer(serializers.ModelSerializer):
    allowed_roles = serializers.SlugRelatedField(slug_field="code", many=True, queryset=Role.objects.all(), required=False)

    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "kind", "allowed_roles"]

    def validate_name(self, v):
        return unique_name(ExpenseCategory, v, self.instance, "Avval qo'shilgan nom!")


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = ["id", "name", "status"]

    def validate_name(self, v):
        return unique_name(LeadSource, v, self.instance, "Avval qo'shilgan nom!")


class AttendanceStatusSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="code", read_only=True)
    roles = serializers.SlugRelatedField(slug_field="code", many=True, queryset=Role.objects.all())

    class Meta:
        model = AttendanceStatus
        fields = ["id", "code", "name", "roles"]
        read_only_fields = ["code", "name"]


ACCOUNT_ROLES = {RoleCode.ADMIN, RoleCode.BOSH_MENEJER, RoleCode.ADMINISTRATOR_HISOBCHI, RoleCode.HISOBCHI}


class AccountSerializer(serializers.ModelSerializer):
    responsible = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)
    initial = serializers.DecimalField(source="initial_balance", max_digits=14, decimal_places=0, min_value=0, required=False)
    start = serializers.DateField(source="start_date", required=False, allow_null=True)

    balance = serializers.SerializerMethodField()
    by_type = serializers.SerializerMethodField()
    pending = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ["id", "name", "responsible", "cash_type", "initial", "start", "status", "balance", "by_type", "pending"]

    def _bal(self, a):
        """Balanslar context['balances'] da bir yo'la hisoblanadi; doiradan tashqari g'azna balansi ko'rsatilmaydi (None)."""
        req = self.context.get("request")
        if req is None or not can(req.user, "accounts"):
            return None
        if "balances" not in self.context:
            self.context["balances"] = fin.balances(fin.scoped_account_ids(req.user))
        return self.context["balances"].get(a.pk)

    def get_balance(self, a):
        b = self._bal(a)
        return b and b["balance"]

    def get_by_type(self, a):
        b = self._bal(a)
        return b and b["by_type"]

    def get_pending(self, a):
        b = self._bal(a)
        return b and b["pending"]

    def validate_name(self, v):
        return unique_name(Account, v, self.instance, "Avval qo'shilgan nom!")

    def validate_responsible(self, users):
        bad = [u.full_name for u in users if getattr(u.role, "code", None) not in ACCOUNT_ROLES]
        if bad:
            raise serializers.ValidationError(f"G'azna mas'uli faqat Admin, Bosh menejer, Administrator+Hisobchi yoki Hisobchi bo'ladi: {', '.join(bad)}")
        return users

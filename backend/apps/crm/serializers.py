"""Maydon nomlari prototip bilan bir xil: pattern, times, social, student_data va h.k."""

from rest_framework import serializers

from apps.core.viewsets import BranchScopedSerializerMixin
from apps.references.models import Course, DayPattern, LeadSource, LessonTime

from . import services
from .models import AGE_GROUPS, LAPTOP_CHOICES, LEAD_TAGS, SOCIAL_STATUSES, Lead, LeadComment, Parent, Student


class ParentSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ["id", "branch", "first_name", "last_name", "phone"]

    def validate_first_name(self, v):
        if len(services.clean(v)) < 3:
            raise serializers.ValidationError("Eng ozi 3 harf")
        return services.clean(v)

    def validate_phone(self, v):
        if not services.PHONE_RE.fullmatch(services.clean(v)):
            raise serializers.ValidationError(services.PHONE_MSG)
        return services.clean(v)


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = ["id", "branch", "first_name", "last_name", "father_name", "full_name", "gender", "phone1", "phone2", "birth_date", "parent"]
        read_only_fields = ["branch"]


class StudentUpdateSerializer(serializers.Serializer):
    """«Talaba ma'lumotlarini to'ldirish» formasi (+ ixtiyoriy yangi vasiy)."""

    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    father_name = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Student.Gender.choices, required=False, allow_blank=True)
    phone1 = serializers.CharField(required=False)
    phone2 = serializers.CharField(required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=Parent.objects.all(), required=False, allow_null=True)
    new_parent = serializers.BooleanField(required=False, default=False)
    p_first = serializers.CharField(required=False, allow_blank=True)
    p_phone = serializers.CharField(required=False, allow_blank=True)


class LeadCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadComment
        fields = ["id", "lead", "comment", "created_by", "created_at"]
        read_only_fields = ["lead", "created_by", "created_at"]


def _choice(values):
    return serializers.ChoiceField(choices=values, required=False, allow_blank=True)


class LeadSerializer(serializers.ModelSerializer):
    student_data = StudentSerializer(source="student", read_only=True)
    pattern = serializers.PrimaryKeyRelatedField(source="day_pattern", queryset=DayPattern.objects.all(), required=False, allow_null=True)
    times = serializers.PrimaryKeyRelatedField(source="preferred_times", queryset=LessonTime.objects.all(), many=True, required=False)
    source = serializers.PrimaryKeyRelatedField(queryset=LeadSource.objects.all())
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    social = serializers.ChoiceField(source="social_status", choices=SOCIAL_STATUSES, required=False, allow_blank=True)
    age_group = _choice(AGE_GROUPS)
    laptop = _choice(LAPTOP_CHOICES)
    tags = serializers.ListField(child=serializers.ChoiceField(choices=LEAD_TAGS), required=False)
    group = serializers.SerializerMethodField()
    has_contract = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Lead
        fields = ["id", "branch", "student", "student_data", "source", "course", "pattern", "times", "status", "group", "demo_date", "demo_attended",
                  "age_group", "social", "laptop", "tags", "has_contract", "comments_count", "created_at", "created_by", "updated_at", "updated_by"]
        read_only_fields = ["branch", "student", "created_at", "created_by", "updated_at", "updated_by"]

    def get_group(self, lead):
        return None  # M3: Group

    def get_has_contract(self, lead):
        return services.has_contract(lead.student)

    def validate(self, attrs):
        inst = self.instance
        get = lambda k: attrs.get(k, getattr(inst, k, None))  # noqa: E731
        times = attrs.get("preferred_times", list(inst.preferred_times.all()) if inst else [])
        branch = inst.branch if inst else self.context["branch"]
        services.check_lead_refs(branch, get("source"), get("course"), get("day_pattern"), times, instance=inst)
        return attrs


class LeadCreateSerializer(LeadSerializer):
    """Yangi lid: «Yangi talaba» (ism, familiya, 2 telefon) yoki «Bazadagi talaba» + ixtiyoriy izoh."""

    branch = serializers.PrimaryKeyRelatedField(read_only=True)
    mode = serializers.ChoiceField(choices=["new", "old"], write_only=True, default="new")
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), required=False, allow_null=True)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone1 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone2 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Student.Gender.choices, write_only=True, required=False, allow_blank=True)
    comment = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(LeadSerializer.Meta):
        fields = [*LeadSerializer.Meta.fields, "mode", "first_name", "last_name", "phone1", "phone2", "gender", "comment"]
        read_only_fields = ["created_at", "created_by", "updated_at", "updated_by"]

    def validate(self, attrs):
        return attrs  # tekshiruvlar create_lead servisida (talaba yaratish bilan birga)

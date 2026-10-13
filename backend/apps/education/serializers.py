"""Maydon nomlari prototip bilan bir xil: pattern, start/end, opening, contact, debt, tkpi, skpi va h.k."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.core.viewsets import BranchScopedSerializerMixin
from apps.crm.models import Student
from apps.references.models import Course, DayPattern, LessonTime, Room

from . import services
from .models import Attendance, Contract, Group, MakeupRequest

Money = dict(max_digits=14, decimal_places=0)


class GroupSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    pattern = serializers.PrimaryKeyRelatedField(source="day_pattern", queryset=DayPattern.objects.all())
    time = serializers.PrimaryKeyRelatedField(queryset=LessonTime.objects.all())
    teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    supporter = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    start = serializers.DateField(source="start_date")
    end = serializers.DateField(source="end_date", required=False, allow_null=True)
    name = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    fill = serializers.SerializerMethodField()
    last_att = serializers.DateField(read_only=True, default=None)

    class Meta:
        model = Group
        fields = ["id", "branch", "course", "pattern", "time", "teacher", "supporter", "room", "start", "end", "number", "name", "comment",
                  "status", "fill", "last_att", "created_by", "created_at"]
        read_only_fields = ["number", "created_by", "created_at"]

    def get_status(self, g):
        return services.period_status(g.start_date, g.end_date)

    def get_fill(self, g):
        n = getattr(g, "active_count", None)
        if n is None:
            n = services.roster(g, services.today()).count()
        return services.fill_of(n, g.room.capacity if g.room_id else 0)


class StudentBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "father_name", "full_name", "phone1", "phone2", "birth_date", "parent"]


class ContractSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    student_data = StudentBriefSerializer(source="student", read_only=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    start = serializers.DateField(source="start_date")
    end = serializers.DateField(source="end_date", required=False, allow_null=True)
    stop_reason = serializers.ChoiceField(choices=Contract.StopReason.choices, required=False, allow_blank=True)
    opening = serializers.DecimalField(source="opening_balance", read_only=True, **Money)
    name = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    charged = serializers.DecimalField(read_only=True, default=0, **Money)
    paid = serializers.DecimalField(read_only=True, default=0, **Money)
    discount = serializers.DecimalField(source="discount_sum", read_only=True, default=0, **Money)
    balance = serializers.DecimalField(read_only=True, default=0, **Money)

    class Meta:
        model = Contract
        fields = ["id", "branch", "student", "student_data", "course", "group", "type", "number", "name", "start", "end", "stop_reason", "comment",
                  "opening", "status", "charged", "paid", "discount", "balance", "created_by", "created_at"]
        read_only_fields = ["number", "created_by", "created_at"]

    def get_status(self, c):
        return services.period_status(c.start_date, c.end_date)


class AttendanceSerializer(serializers.ModelSerializer):
    pattern = serializers.PrimaryKeyRelatedField(source="day_pattern", read_only=True)
    contact = serializers.CharField(source="contact_status", read_only=True)
    debt = serializers.DecimalField(source="student_debt", read_only=True, **Money)
    tkpi = serializers.DecimalField(source="teacher_kpi", read_only=True, **Money)
    skpi = serializers.DecimalField(source="supporter_kpi", read_only=True, **Money)
    no_freq = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="contract.student.full_name", read_only=True)
    phone1 = serializers.CharField(source="contract.student.phone1", read_only=True)
    contract_number = serializers.IntegerField(source="contract.number", read_only=True)
    makeup = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "branch", "group", "course", "contract", "pattern", "date", "status", "teacher", "supporter", "contact", "comment",
                  "debt", "tkpi", "skpi", "calc_note", "no_freq", "student_name", "phone1", "contract_number", "makeup", "created_by", "created_at"]
        read_only_fields = fields

    def get_no_freq(self, a):
        return a.student_debt is None

    def get_makeup(self, a):
        """Oxirgi so'rov holati (Kelmaganlar ro'yxati uchun); prefetch qilingan bo'lsa qo'shimcha so'rovsiz."""
        ms = [m for m in a.makeups.all() if not m.is_deleted] if hasattr(a, "_prefetched_objects_cache") and "makeups" in a._prefetched_objects_cache else None
        if ms is None:
            return None
        ms.sort(key=lambda m: m.created_at, reverse=True)
        return ms[0].status if ms else None


class MarkSerializer(serializers.Serializer):
    contract = serializers.PrimaryKeyRelatedField(queryset=Contract.objects.all())
    status = serializers.ChoiceField(choices=["1", "0", "X", "-"])
    comment = serializers.CharField(required=False, allow_blank=True)


class TakeSerializer(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    date = serializers.DateField()
    marks = MarkSerializer(many=True, required=False)
    all = serializers.BooleanField(required=False, default=False)
    sub_teacher = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    sub_supporter = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)


class MakeupSerializer(serializers.ModelSerializer):
    attendance = serializers.PrimaryKeyRelatedField(queryset=Attendance.objects.all())
    att = serializers.SerializerMethodField()

    class Meta:
        model = MakeupRequest
        fields = ["id", "attendance", "att", "teacher", "makeup_date", "comment", "status", "reviewed_by", "reviewed_at", "reject_reason", "created_at"]
        read_only_fields = ["teacher", "status", "reviewed_by", "reviewed_at", "reject_reason", "created_at"]

    def get_att(self, m):
        a = m.attendance
        return {"date": a.date, "status": a.status, "group": a.group_id, "contract": a.contract_id, "student_name": a.contract.student.full_name}

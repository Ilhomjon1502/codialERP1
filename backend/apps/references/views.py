from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role, User
from apps.accounts.serializers import RoleSerializer, UserSerializer, me_payload
from apps.core.models import AuditLog
from apps.core.pagination import Pagination
from apps.core.permissions import SectionPermission, is_top, role_code
from apps.core.roles import MANAGER_ROLES, SECTIONS, edit_days_table
from apps.core.scoping import in_scope, scope_branch
from apps.core.serializers import AuditLogSerializer
from apps.core.viewsets import AuditedModelViewSet
from apps.education.serializers import GroupSerializer
from apps.education.views import scoped_groups
from apps.finance.models import Account

from . import serializers as s
from . import services
from .models import AttendanceStatus, Branch, Course, CoursePrice, DayPattern, DiscountType, ExpenseCategory, LeadSource, LessonFrequency, LessonTime, Room


class TopOnlyWriteMixin:
    """Filiallar: yaratish va o'zgartirish faqat Admin va Bosh menejer (CLAUDE.md 6.2)."""

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not is_top(request.user):
            raise PermissionDenied("Faqat Admin va Bosh menejer o'zgartiradi")


class BranchViewSet(TopOnlyWriteMixin, AuditedModelViewSet):
    section = "settings"
    queryset = Branch.objects.all()
    serializer_class = s.BranchSerializer


class CourseViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = Course.objects.prefetch_related("branches")
    serializer_class = s.CourseSerializer


class RoomViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = Room.objects.all()
    serializer_class = s.RoomSerializer
    branch_field = "branch"


class DayPatternViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = DayPattern.objects.all()
    serializer_class = s.DayPatternSerializer


class LessonTimeViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = LessonTime.objects.all()
    serializer_class = s.LessonTimeSerializer
    branch_field = "branch"


class CoursePriceViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = CoursePrice.objects.select_related("course")
    serializer_class = s.CoursePriceSerializer
    branch_field = "branch"
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        obj, created = services.set_course_price(request.user, d["branch"], d["course"], d["effective_from"], d["price"])
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class LessonFrequencyViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = LessonFrequency.objects.select_related("day_pattern").prefetch_related("courses")
    serializer_class = s.LessonFrequencySerializer
    branch_field = "branch"
    action_ops = {"propose": "a", "approve": "v"}

    def get_queryset(self):
        qs = super().get_queryset()
        ym = self.request.query_params.get("month")
        if ym:
            d = services.month_start(ym)
            qs = qs.filter(year=d.year, month=d.month)
        return qs

    def perform_update(self, serializer):
        """Tasdiqlangan yozuvning soni yoki kurslari o'zgarsa — eski va yangi kurslar qatorlari qayta hisoblanadi."""
        freq = serializer.instance
        old_courses = list(freq.courses.all())
        super().perform_update(serializer)
        if freq.status == LessonFrequency.FreqStatus.APPROVED:
            services.recalc_frequency(freq, courses={*old_courses, *freq.courses.all()})

    def perform_destroy(self, instance):
        courses = list(instance.courses.all())
        super().perform_destroy(instance)
        if instance.status == LessonFrequency.FreqStatus.APPROVED:
            services.recalc_frequency(instance, courses=courses)

    @action(detail=False, methods=["post"])
    def propose(self, request):
        d = services.month_start(request.data.get("month"))
        branch_id = request.data.get("branch")
        branches = Branch.objects.filter(status="Faol")
        if branch_id:
            branches = branches.filter(pk=branch_id)
        branches = [b for b in branches if in_scope(request.user, b.pk)]
        if not branches:
            raise ValidationError({"branch": "Filial topilmadi"})
        n = sum(services.propose_month(b, d.year, d.month, request.user) for b in branches)
        return Response({"created": n})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Tasdiqlaydi: Admin, Bosh menejer, Filial menejeri (prototipdagi canApproveFreq)."""
        if role_code(request.user) not in MANAGER_ROLES:
            raise PermissionDenied("Dars sonini faqat Admin, Bosh menejer va Filial menejeri tasdiqlaydi")
        freq = services.approve_frequency(request.user, self.get_object())
        return Response(self.get_serializer(freq).data)


class DiscountTypeViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = DiscountType.objects.prefetch_related("courses")
    serializer_class = s.DiscountTypeSerializer


class ExpenseCategoryViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = ExpenseCategory.objects.prefetch_related("allowed_roles")
    serializer_class = s.ExpenseCategorySerializer


class LeadSourceViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = LeadSource.objects.all()
    serializer_class = s.LeadSourceSerializer


class AttendanceStatusViewSet(AuditedModelViewSet):
    section = "settings"
    queryset = AttendanceStatus.objects.prefetch_related("roles")
    serializer_class = s.AttendanceStatusSerializer
    http_method_names = ["get", "patch", "head", "options"]


class AccountViewSet(AuditedModelViewSet):
    """G'aznalar. Mas'ullarni faqat Admin va Bosh menejer o'zgartiradi (CLAUDE.md 7.5). Balans va ledger — M4."""

    section = "accounts"
    queryset = Account.objects.prefetch_related("responsible")
    serializer_class = s.AccountSerializer

    def perform_update(self, serializer):
        if "responsible" in serializer.validated_data and not is_top(self.request.user):
            raise PermissionDenied("G'azna mas'ullarini faqat Admin va Bosh menejer o'zgartiradi")
        super().perform_update(serializer)

    def perform_create(self, serializer):
        if serializer.validated_data.get("responsible") and not is_top(self.request.user):
            raise PermissionDenied("G'azna mas'ullarini faqat Admin va Bosh menejer o'zgartiradi")
        super().perform_create(serializer)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit tarixi: Admin va Bosh menejer (bo'lim «audit»)."""

    section = "audit"
    permission_classes = [SectionPermission]
    pagination_class = Pagination

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user").order_by("-at")
        p = self.request.query_params
        if p.get("user"):
            qs = qs.filter(user_id=p["user"])
        if p.get("action"):
            qs = qs.filter(action=p["action"])
        if p.get("search"):
            q = p["search"]
            qs = qs.filter(Q(model__icontains=q) | Q(object_repr__icontains=q) | Q(detail__icontains=q))
        return qs

    serializer_class = AuditLogSerializer


def _ser(cls, qs, request):
    return cls(qs, many=True, context={"request": request}).data


@api_view(["GET"])
def bootstrap(request):
    """Kirgandan keyin bir marta: joriy xodim, rollar, muddatlar va barcha ma'lumotnomalar (kichik jadvallar).
    Kalitlar front-end to'plamlari nomi bilan bir xil. Katta jadvallar (lid, shartnoma, davomat…) bu yerga kirmaydi."""
    u = request.user
    scoped = lambda qs: scope_branch(qs, u)  # noqa: E731
    return Response({
        "me": me_payload(u),
        "sections": SECTIONS,
        "edit_days": edit_days_table(),
        "roles": _ser(RoleSerializer, Role.objects.prefetch_related("permissions", "can_assign"), request),
        "branches": _ser(s.BranchSerializer, Branch.objects.all(), request),
        "courses": _ser(s.CourseSerializer, Course.objects.prefetch_related("branches"), request),
        "rooms": _ser(s.RoomSerializer, scoped(Room.objects.all()), request),
        "dayPatterns": _ser(s.DayPatternSerializer, DayPattern.objects.all(), request),
        "lessonTimes": _ser(s.LessonTimeSerializer, scoped(LessonTime.objects.all()), request),
        "coursePrices": _ser(s.CoursePriceSerializer, scoped(CoursePrice.objects.all()), request),
        "lessonFreqs": _ser(s.LessonFrequencySerializer, scoped(LessonFrequency.objects.prefetch_related("courses")), request),
        "discountTypes": _ser(s.DiscountTypeSerializer, DiscountType.objects.prefetch_related("courses"), request),
        "expenseCats": _ser(s.ExpenseCategorySerializer, ExpenseCategory.objects.prefetch_related("allowed_roles"), request),
        "leadSources": _ser(s.LeadSourceSerializer, LeadSource.objects.all(), request),
        "attendanceStatuses": _ser(s.AttendanceStatusSerializer, AttendanceStatus.objects.prefetch_related("roles"), request),
        "accounts": _ser(s.AccountSerializer, Account.objects.prefetch_related("responsible"), request),
        "users": _ser(UserSerializer, User.objects.select_related("role").prefetch_related("branches"), request),
        "groups": _ser(GroupSerializer, scoped_groups(u), request),
    })


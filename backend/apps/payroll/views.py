from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core.pagination import Pagination
from apps.core.permissions import NO_PERMISSION, can, role_code
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet
from apps.crm.views import default_branch
from apps.education.models import Attendance
from apps.education.serializers import AttendanceSerializer
from apps.finance.services import month_bounds
from apps.references.services import month_start

from . import services
from .models import KPIRate, SalaryAssignment, SalaryPayout
from .serializers import KPIRateSerializer, SalaryAssignmentSerializer, SalaryPayoutSerializer

TEACHER_ROLES = services.TEACHERS | services.SUPPORTERS


class KPIRateViewSet(AuditedModelViewSet):
    """KPI stavkalari (bo'lim «salaries»). Kiritish va o'zgartirish — Admin, Bosh menejer, Filial menejeri. O'zgarsa davomat qatorlari qayta hisoblanadi."""

    section = "salaries"
    queryset = KPIRate.objects.select_related("user", "course")
    serializer_class = KPIRateSerializer

    def get_queryset(self):
        return services.scope(super().get_queryset(), self.request.user)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data, branch=default_branch(request.user, request.data.get("branch")))
        r, n = services.save_rate(request.user, d)
        return Response({**self.get_serializer(r).data, "recalculated": n}, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        r = self.get_object()
        ser = self.get_serializer(r, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        r, n = services.save_rate(request.user, dict(ser.validated_data), instance=r)
        return Response({**self.get_serializer(r).data, "recalculated": n})

    def perform_destroy(self, instance):
        services.delete_rate(self.request.user, instance)


class SalaryAssignmentViewSet(AuditedModelViewSet):
    """Oylik belgilash. ?month=YYYY-MM, ?user=. Hisoblangan maydonlar: tkpi, skpi, total, given, carried, final.
    /balances/ — xodim balansi (har xodimning oxirgi oyi), /{id}/breakdown/ — batafsil (tarix va shu oy berilganlari), POST /copy/ — o'tgan oydan nusxa."""

    section = "salaries"
    queryset = SalaryAssignment.objects.select_related("user")
    serializer_class = SalaryAssignmentSerializer
    action_ops = {"balances": "v", "breakdown": "v", "copy": "a"}

    def get_queryset(self):
        qs = services.scope(super().get_queryset(), self.request.user)
        p = self.request.query_params
        if p.get("month"):
            d = month_start(p["month"])
            qs = qs.filter(year=d.year, month=d.month)
        if p.get("user"):
            qs = qs.filter(user=p["user"])
        return qs.order_by("-year", "-month", "user__full_name")

    def _out(self, objs, many=True):
        rows = services.compute(objs if many else [objs])
        return self.get_serializer(rows if many else rows[0], many=many).data

    def list(self, request, *args, **kwargs):
        return Response(self._out(self.get_queryset()))

    def retrieve(self, request, *args, **kwargs):
        return Response(self._out(self.get_object(), many=False))

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data, branch=default_branch(request.user, request.data.get("branch")))
        return Response(self._out(services.save_assignment(request.user, d), many=False), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        a = self.get_object()
        ser = self.get_serializer(a, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(self._out(services.save_assignment(request.user, dict(ser.validated_data), instance=a), many=False))

    def perform_destroy(self, instance):
        services.delete_assignment(self.request.user, instance)

    @action(detail=False)
    def balances(self, request):
        return Response(self.get_serializer(services.latest_per_user(services.scope(SalaryAssignment.objects.all(), request.user)), many=True).data)

    @action(detail=True)
    def breakdown(self, request, pk=None):
        a = self.get_object()
        history = SalaryAssignment.objects.filter(branch=a.branch, user=a.user).order_by("-year", "-month")
        pays = SalaryPayout.objects.filter(branch=a.branch, user=a.user, year=a.year, month=a.month).order_by("date", "created_at")
        return Response({"assignment": self._out(a, many=False), "history": self._out(history),
                         "payouts": SalaryPayoutSerializer(pays, many=True, context=self.get_serializer_context()).data})

    @action(detail=False, methods=["post"])
    def copy(self, request):
        d = month_start(request.data.get("month"))
        n = services.copy_previous_month(request.user, default_branch(request.user, request.data.get("branch")), d.year, d.month)
        return Response({"created": n})


class SalaryPayoutViewSet(AuditedModelViewSet):
    """Oylik berish (g'aznadan chiqim — CashMovement SALARY). ?month= (sana bo'yicha), ?period=YYYY-MM (oylik davri), ?user=."""

    section = "salaries"
    queryset = SalaryPayout.objects.select_related("user", "account")
    serializer_class = SalaryPayoutSerializer
    pagination_class = Pagination

    def get_queryset(self):
        qs = services.scope(super().get_queryset(), self.request.user)
        p = self.request.query_params
        if p.get("month"):
            start, end = month_bounds(p["month"])
            qs = qs.filter(date__gte=start, date__lt=end)
        if p.get("period"):
            d = month_start(p["period"])
            qs = qs.filter(year=d.year, month=d.month)
        if p.get("user"):
            qs = qs.filter(user=p["user"])
        return qs.order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data, branch=default_branch(request.user, request.data.get("branch")))
        return Response(self.get_serializer(services.save_payout(request.user, d)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        p = self.get_object()
        ser = self.get_serializer(p, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(self.get_serializer(services.save_payout(request.user, dict(ser.validated_data), instance=p)).data)

    def perform_destroy(self, instance):
        services.delete_payout(self.request.user, instance)


def _kpi_scope(user):
    qs = scope_branch(Attendance.objects.all(), user)
    if role_code(user) in TEACHER_ROLES:
        qs = qs.filter(Q(teacher=user) | Q(supporter=user))
    return qs


@api_view(["GET"])
def kpi_tree(request):
    """Hisoblangan KPI: oy + xodim + rol + guruh bo'yicha yig'indilar (daraxt front-end'da). Ustoz/yordamchi — faqat o'ziniki."""
    if not can(request.user, "salaries"):
        raise PermissionDenied(NO_PERMISSION)
    entries = services.kpi_entries(_kpi_scope(request.user))
    if role_code(request.user) in TEACHER_ROLES:
        entries = [e for e in entries if e["user"] == request.user.pk]
    return Response(entries)


@api_view(["GET"])
def kpi_rows(request):
    """Daraxtda guruh tanlanganda: har bir davomat qatori (sana, shartnoma, status, KPI). ?month=&user=&role=&group="""
    if not can(request.user, "salaries"):
        raise PermissionDenied(NO_PERMISSION)
    p = request.query_params
    if not all(p.get(k) for k in ("month", "user", "role", "group")):
        raise ValidationError({"detail": "month, user, role, group kerak"})
    if role_code(request.user) in TEACHER_ROLES and str(request.user.pk) != p["user"]:
        raise PermissionDenied(NO_PERMISSION)
    start, end = month_bounds(p["month"])
    field = "teacher" if p["role"] == "USTOZ" else "supporter"
    qs = _kpi_scope(request.user).filter(date__gte=start, date__lt=end, group=p["group"], **{field: p["user"]}).select_related("contract__student").order_by("-date")
    return Response(AttendanceSerializer(qs, many=True).data)

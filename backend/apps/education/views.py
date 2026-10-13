import datetime

from django.db.models import Count, Prefetch, Q, Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.pagination import Pagination
from apps.core.permissions import check_edit_window, today
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet
from apps.crm.views import default_branch, search_q
from apps.references.models import LessonFrequency
from apps.references.services import month_start

from . import calc, services
from .models import Attendance, Contract, Group, MakeupRequest
from .serializers import AttendanceSerializer, ContractSerializer, GroupSerializer, MakeupSerializer, TakeSerializer

GROUP_QS = Group.objects.select_related("course", "room", "day_pattern")
CONTRACT_QS = Contract.objects.select_related("student", "group__course")
ATT_QS = Attendance.objects.select_related("contract__student")


def scoped_groups(user):
    """Filial doirasi + ustoz/yordamchi doirasi (6.3)."""
    return services.with_fill(services.teacher_scope(scope_branch(GROUP_QS, user), user, group_field=None))


def scoped_attendance(user):
    return services.teacher_scope(scope_branch(ATT_QS, user), user, extra=("teacher", "supporter"))


def parse_date(value, field="date"):
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError) as e:
        raise ValidationError({field: "Sana formati: YYYY-MM-DD"}) from e


def month_bounds(ym):
    start = month_start(ym)
    return calc.month_range(start)


class BranchDefaultMixin:
    """Yaratishda filial ko'rsatilmasa — foydalanuvchining yagona faol filiali (CLAUDE.md 2)."""

    def branch_for_create(self, data):
        return default_branch(self.request.user, data.get("branch"))


class GroupViewSet(BranchDefaultMixin, AuditedModelViewSet):
    """Guruhlar (bo'lim «groups»). ?status=Faol|Rejada|Nofaol. Ustoz va yordamchi — faqat o'z guruhlari."""

    section = "groups"
    queryset = GROUP_QS
    serializer_class = GroupSerializer
    branch_field = "branch"
    action_ops = {"journal": "v"}
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = services.with_fill(services.teacher_scope(super().get_queryset(), self.request.user, group_field=None))
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(services.status_q(p["status"]))
        if p.get("course"):
            qs = qs.filter(course=p["course"])
        return qs

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data={**request.data, "branch": str(self.branch_for_create(request.data).pk)})
        ser.is_valid(raise_exception=True)
        g = services.save_group(request.user, dict(ser.validated_data))
        return Response(self.get_serializer(self.get_queryset().get(pk=g.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        g = self.get_object()
        ser = self.get_serializer(g, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        services.save_group(request.user, dict(ser.validated_data), instance=g)
        return Response(self.get_serializer(self.get_queryset().get(pk=g.pk)).data)

    @action(detail=True)
    def journal(self, request, pk=None):
        """Oylik davomat jurnali: dars kunlari, faol va nofaol talabalar, belgilar, qarz va oydagi dars soni."""
        g = self.get_object()
        start, end = month_bounds(request.query_params.get("month") or f"{today():%Y-%m}")
        days = [start + datetime.timedelta(days=i) for i in range((end - start).days)]
        days = [d for d in days if services.has_lesson(g, d)]
        contracts = list(services.with_balance(CONTRACT_QS.filter(group=g)).filter(start_date__lt=end).order_by("student__first_name", "student__last_name"))
        marks = {}
        for cid, d, st in Attendance.objects.filter(group=g, date__gte=start, date__lt=end).values_list("contract_id", "date", "status"):
            marks.setdefault(str(cid), {})[d.isoformat()] = st
        freq = LessonFrequency.objects.filter(branch=g.branch, day_pattern=g.day_pattern, courses=g.course, year=start.year, month=start.month).first()
        ctx = self.get_serializer_context()
        return Response({
            "group": self.get_serializer(self.get_queryset().get(pk=g.pk)).data,
            "month": f"{start:%Y-%m}",
            "days": days,
            "contracts": ContractSerializer(contracts, many=True, context=ctx).data,
            "marks": marks,
            "frequency": {"frequency": freq.frequency, "status": freq.status} if freq else None,
        })


class ContractViewSet(BranchDefaultMixin, AuditedModelViewSet):
    """Shartnomalar (bo'lim «contracts»). ?status=, ?search=, ?course=, ?type=, ?group=, ?student=. Sahifalangan."""

    section = "contracts"
    queryset = CONTRACT_QS
    serializer_class = ContractSerializer
    branch_field = "branch"
    pagination_class = Pagination
    check_usage_on_delete = True
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self, with_status=True):
        qs = services.with_balance(services.teacher_scope(super().get_queryset(), self.request.user))
        p = self.request.query_params
        if with_status and p.get("status"):
            qs = qs.filter(services.status_q(p["status"]))
        if p.get("search"):
            s = p["search"].strip()
            qs = qs.filter(search_q(s, "student__") | (Q(number=int(s)) if s.isdigit() else Q(pk__in=[])))
        for key in ("course", "type", "group", "student"):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs.order_by("group__course__name", "group__number", "student__first_name", "student__last_name")

    def list(self, request, *args, **kwargs):
        """Sahifa + tablar uchun status bo'yicha sonlar (boshqa filtrlar hisobga olinadi)."""
        resp = super().list(request, *args, **kwargs)
        base = self.get_queryset(with_status=False).order_by()
        resp.data["counts"] = {st: base.filter(services.status_q(st)).count() for st in (services.FAOL, services.REJADA, services.NOFAOL)}
        return resp

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data={**request.data, "branch": str(self.branch_for_create(request.data).pk)})
        ser.is_valid(raise_exception=True)
        c = services.save_contract(request.user, dict(ser.validated_data))
        return Response(self.get_serializer(self.get_queryset().get(pk=c.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        c = self.get_object()
        ser = self.get_serializer(c, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        services.check_contract_edit(request.user, c, request.data.keys(), ser.validated_data.get("end_date"))
        services.save_contract(request.user, dict(ser.validated_data), instance=c)
        return Response(self.get_serializer(self.get_queryset().get(pk=c.pk)).data)

    def retrieve(self, request, *args, **kwargs):
        c = self.get_object()
        data = self.get_serializer(c).data
        att = ATT_QS.filter(contract=c).order_by("-date")
        data["attendance"] = AttendanceSerializer(att, many=True).data
        data["payments"] = []  # M4
        lead = c.student.leads.order_by("-created_at").first()
        data["age_group"] = lead.age_group if lead else ""
        p = c.student.parent
        data["parent"] = {"id": str(p.pk), "first_name": p.first_name, "last_name": p.last_name, "phone": p.phone} if p else None
        return Response(data)

    def perform_destroy(self, instance):
        check_edit_window(self.request.user, "contracts", instance.start_date, op="d")
        super().perform_destroy(instance)


class DebtorViewSet(AuditedModelViewSet):
    """Qarzdorlar (bo'lim «debtors»): balans > 0 shartnomalar, jami qarz bilan. Sahifalanmaydi — guruhlab ko'rsatiladi."""

    section = "debtors"
    queryset = CONTRACT_QS
    serializer_class = ContractSerializer
    branch_field = "branch"
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = services.with_balance(super().get_queryset()).filter(balance__gt=0)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(services.status_q(p["status"]))
        if p.get("course"):
            qs = qs.filter(course=p["course"])
        if p.get("search"):
            qs = qs.filter(search_q(p["search"], "student__"))
        return qs.order_by("-balance")

    def list(self, request, *args, **kwargs):
        rows = self.get_serializer(self.get_queryset(), many=True).data
        return Response({"count": len(rows), "total": sum(r["balance"] for r in rows), "results": rows})


class AttendanceViewSet(AuditedModelViewSet):
    """Davomat (bo'lim «attendance»).
    GET  /attendance/?month=&status=X,0&group=&contract=  — ro'yxat (Kelmaganlar), sahifalangan
    GET  /attendance/take/?group=&date=                    — davomat olish ekrani
    POST /attendance/take/                                 — belgilash (marks yoki all=true)
    PATCH /attendance/{id}/                                — bog'lanish holati va izoh
    GET  /attendance/stats/?month=  ·  GET /attendance/summary/?month= (joriy xodim uchun)"""

    section = "attendance"
    queryset = ATT_QS
    serializer_class = AttendanceSerializer
    branch_field = "branch"
    pagination_class = Pagination
    action_ops = {"take": "v", "stats": "v", "summary": "v"}
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = services.teacher_scope(super().get_queryset(), self.request.user, extra=("teacher", "supporter"))
        p = self.request.query_params
        if p.get("month"):
            start, end = month_bounds(p["month"])
            qs = qs.filter(date__gte=start, date__lt=end)
        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        for key in ("group", "contract", "contact"):
            if p.get(key):
                qs = qs.filter(**{"contact_status" if key == "contact" else key: p[key]})
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().prefetch_related(Prefetch("makeups", queryset=MakeupRequest.objects.all())).order_by("-date", "contract__student__first_name")
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request, *args, **kwargs):
        raise ValidationError({"detail": "Davomat «Davomat olish» ekranidan olinadi"})

    def partial_update(self, request, *args, **kwargs):
        a = self.get_object()
        services.set_contact(request.user, a, request.data.get("contact"), request.data.get("comment"))
        return Response(self.get_serializer(ATT_QS.get(pk=a.pk)).data)

    def _group(self, group_id):
        g = scoped_groups(self.request.user).filter(pk=group_id).first()
        if g is None:
            raise ValidationError({"group": "Guruh topilmadi"})
        return g

    @action(detail=False, methods=["get", "post"])
    def take(self, request):
        if request.method == "POST":
            ser = TakeSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            d = ser.validated_data
            g = self._group(d["group"].pk)
            sub = {"sub_teacher": d.get("sub_teacher"), "sub_supporter": d.get("sub_supporter")}
            if d.get("all"):
                services.mark_all_present(request.user, g, d["date"], **sub)
            else:
                services.mark(request.user, g, d["date"], d.get("marks") or [], **sub)
            return Response(self._take_state(g, d["date"]))
        g = self._group(request.query_params.get("group"))
        return Response(self._take_state(g, parse_date(request.query_params.get("date") or today().isoformat())))

    def _take_state(self, g, d):
        user = self.request.user
        error, nearest = "", None
        try:
            services.check_take(user, g, d)
        except ValidationError as e:
            v = next(iter(e.detail.values())) if isinstance(e.detail, dict) else e.detail
            error = v[0] if isinstance(v, list) else v
            nearest = services.nearest_lesson(g, min(d, today()))
        rows = list(services.with_balance(services.roster(g, d))) if not error else []
        att = {a.contract_id: a for a in ATT_QS.filter(group=g, date=d)}
        ctx = self.get_serializer_context()
        return {
            "group": GroupSerializer(services.with_fill(GROUP_QS).get(pk=g.pk), context=ctx).data,
            "date": d,
            "error": str(error),
            "nearest": nearest,
            "teacher_mode": services.is_teacher_mode(user),
            "can_sub": services.role_code(user) in services.SUBSTITUTE_SETTERS,
            "allowed": sorted(services.allowed_statuses(user)),
            "rows": [{"contract": ContractSerializer(c, context=ctx).data, "att": AttendanceSerializer(att[c.pk]).data if c.pk in att else None} for c in rows],
        }

    @action(detail=False)
    def stats(self, request):
        if not request.query_params.get("month"):
            raise ValidationError({"month": "Oyni tanlang"})
        return Response(services.attendance_stats(self.get_queryset()))

    @action(detail=False)
    def summary(self, request):
        """Ustoz va yordamchi uchun: shu oydagi KPI, dars qatorlari, besabab kelmaganlar, kutilayotgan so'rovlar."""
        u = request.user
        start, end = month_bounds(request.query_params.get("month") or f"{today():%Y-%m}")
        month = Attendance.objects.filter(date__gte=start, date__lt=end)
        t = month.filter(teacher=u).aggregate(k=Sum("teacher_kpi"), n=Count("id"))
        s = month.filter(supporter=u).aggregate(k=Sum("supporter_kpi"), n=Count("id"))
        mine = month.filter(Q(teacher=u) | Q(supporter=u))
        return Response({
            "kpi": (t["k"] or 0) + (s["k"] or 0),
            "rows": t["n"] + s["n"],
            "absent": mine.filter(status=calc.BESABAB).count(),
            "no_freq": mine.filter(student_debt__isnull=True).count(),
            "makeups_pending": MakeupRequest.objects.filter(teacher=u, status=MakeupRequest.Status.PENDING).count(),
        })


class MakeupViewSet(AuditedModelViewSet):
    """Qoldirilgan dars so'rovlari (bo'lim «attendance»): ustoz yuboradi, menejer va administratorlar tasdiqlaydi (p)."""

    section = "attendance"
    queryset = MakeupRequest.objects.select_related("attendance__contract__student")
    serializer_class = MakeupSerializer
    branch_field = "attendance__branch"
    action_ops = {"approve": "p", "reject": "p", "create": "v"}
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if services.role_code(self.request.user) in (services.TEACHERS | services.SUPPORTERS):
            qs = qs.filter(teacher=self.request.user)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        a = scoped_attendance(request.user).filter(pk=d["attendance"].pk).first()
        if a is None:
            raise ValidationError({"attendance": "Davomat qatori topilmadi"})
        m = services.request_makeup(request.user, a, d["makeup_date"], d.get("comment", ""))
        return Response(self.get_serializer(m).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return Response(self.get_serializer(services.approve_makeup(request.user, self.get_object())).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return Response(self.get_serializer(services.reject_makeup(request.user, self.get_object(), request.data.get("reason"))).data)

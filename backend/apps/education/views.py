import datetime
from decimal import Decimal

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.core import audit
from apps.core.models import AuditLog
from apps.core.pagination import Pagination
from apps.core.permissions import NO_PERMISSION, can, check_edit_window, today
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet
from apps.crm.models import Lead
from apps.crm.views import default_branch, search_q
from apps.references.models import LessonFrequency, Room
from apps.references.services import month_start

from . import calc, export, services
from . import dues as dues_mod
from .models import Attendance, Contract, DueDismissal, Group, MakeupRequest, ParentCall, TeacherEvaluation
from .serializers import (
    AttendanceSerializer,
    ContractSerializer,
    GroupSerializer,
    MakeupSerializer,
    ParentCallSerializer,
    TakeSerializer,
    TeacherEvaluationSerializer,
)

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
        from apps.finance.serializers import PaymentSerializer
        from apps.finance.views import PAYMENT_QS

        pays = PAYMENT_QS.filter(contract=c) if can(request.user, "payments") else PAYMENT_QS.none()
        data["payments"] = PaymentSerializer(pays, many=True, context=self.get_serializer_context()).data
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
    http_method_names = ["get", "post", "head", "options"]
    action_ops = {"month": "v", "dismiss": "v", "restore": "v"}

    @action(detail=False, methods=["get"])
    def month(self, request):
        """GET /debtors/month/?month=YYYY-MM&course=&group=&search=&state=wait|overdue — shu oy to'lovini qilmaganlar
        (kurs narxi bo'yicha, davomatga bog'liq emas; dues.py)."""
        p = request.query_params
        on = today()
        first = month_bounds(p["month"])[0] if p.get("month") else on.replace(day=1)
        base = CONTRACT_QS.filter(pk__in=self.get_queryset_unfiltered().values("pk"))
        if p.get("course"):
            base = base.filter(course=p["course"])
        if p.get("group"):
            base = base.filter(group=p["group"])
        if p.get("search"):
            base = base.filter(search_q(p["search"], "student__"))
        dues = {str(k): v for k, v in dues_mod.month_dues(base, first, on, "only" if p.get("dismissed") else "hide").items()}
        qs = services.with_balance(base.filter(pk__in=list(dues)))
        rows = []
        for r in self.get_serializer(qs, many=True).data:
            d = dues[str(r["id"])]
            conv = lambda v: str(v) if isinstance(v, datetime.date) else (int(v) if isinstance(v, Decimal) else v)  # noqa: E731
            rows.append({**r, **{k: conv(v) for k, v in d.items()}})
        if p.get("state") == "overdue":
            rows = [r for r in rows if r["overdue"]]
        elif p.get("state") == "wait":
            rows = [r for r in rows if not r["overdue"]]
        rows.sort(key=lambda r: (-r["to_pay"]))
        over = [r for r in rows if r["overdue"]]
        return Response({
            "month": f"{first:%Y-%m}", "count": len(rows), "total": sum(r["to_pay"] for r in rows),
            "overdue_count": len(over), "overdue_total": sum(r["to_pay"] for r in over), "results": rows,
        })

    def _dismiss(self, request, pk, on):
        """POST /debtors/{id}/dismiss/ | restore/ {month: YYYY-MM} — «To'lovga tavsiya»dan shu oy uchun olib tashlash / qaytarish."""
        if not can(request.user, "payments", "a"):
            raise PermissionDenied("To'lov qabul qiladiganlar (Administrator+Hisobchi, Hisobchi, Bosh menejer, Admin) olib tashlay oladi")
        c = get_object_or_404(self.get_queryset_unfiltered(), pk=pk)
        month = month_bounds(request.data["month"])[0] if request.data.get("month") else today().replace(day=1)
        row = DueDismissal.objects.filter(contract=c, month=month).first()
        if on and not row:
            row = DueDismissal.objects.create(contract=c, month=month, created_by=request.user)
            audit.log_create(request.user, row, f"To'lovga tavsiyadan olib tashlandi ({month:%Y-%m})")
        elif not on and row:
            row.is_deleted, row.deleted_at, row.deleted_by = True, timezone.now(), request.user
            row.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
            audit.log_delete(request.user, row, f"To'lovga tavsiyaga qaytarildi ({month:%Y-%m})")
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        return self._dismiss(request, pk, True)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        return self._dismiss(request, pk, False)

    def get_queryset_unfiltered(self):
        return super().get_queryset()

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
    action_ops = {"take": "v", "stats": "v", "summary": "v", "dates": "v", "gaps": "v"}
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = services.teacher_scope(super().get_queryset(), self.request.user, extra=("teacher", "supporter"))
        p = self.request.query_params
        if p.get("month"):
            start, end = month_bounds(p["month"])
            qs = qs.filter(date__gte=start, date__lt=end)
        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        for key in ("group", "contract", "contact", "course", "date"):
            if p.get(key):
                qs = qs.filter(**{"contact_status" if key == "contact" else key: p[key]})
        if p.get("search"):
            qs = qs.filter(search_q(p["search"], "contract__student__"))
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
    def dates(self, request):
        """Statistika (AppSheet'dagidek): tanlangan filtrlar (oy, kurs, guruh, shartnoma, qidiruv; `date` yuborilmaydi) bo'yicha sanalar va ularning qatorlar soni + jami KPI."""
        qs = self.get_queryset()
        days = list(qs.values("date").annotate(n=Count("id")).order_by("-date"))
        tot = qs.aggregate(n=Count("id"), tkpi=Sum("teacher_kpi"), skpi=Sum("supporter_kpi"), debt=Sum("student_debt"))
        return Response({"dates": days, "totals": {k: v or 0 for k, v in tot.items()}})

    @action(detail=False)
    def gaps(self, request):
        """Davomat olinmagan sanalar: shartnoma bo'yicha — shu o'quvchiga, guruh bo'yicha — butun guruhga (oy ichida, bugungacha)."""
        p = request.query_params
        start, end = month_bounds(p.get("month") or f"{today():%Y-%m}")
        last = min(end - datetime.timedelta(days=1), today())
        if p.get("contract"):
            c = _contract_in_scope(request.user, Contract.objects.get(pk=p["contract"]))
            lo, hi, g = max(start, c.start_date), min(last, c.end_date or last), c.group
            have = set(Attendance.objects.filter(contract=c, date__gte=lo, date__lte=hi).values_list("date", flat=True))
        elif p.get("group"):
            g = self._group(p["group"])
            lo, hi = start, last
            have = set(Attendance.objects.filter(group=g, date__gte=lo, date__lte=hi).values_list("date", flat=True))
        else:
            return Response({"dates": []})
        days = [lo + datetime.timedelta(days=i) for i in range((hi - lo).days + 1)] if hi >= lo else []
        return Response({"dates": [d for d in days if services.has_lesson(g, d) and d not in have]})

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


# ------------------------------------------------------------------ M6: baholash (talaba → ustoz), ota-onalar bilan aloqa, Excel eksport

def scoped_contracts(user):
    return services.teacher_scope(scope_branch(Contract.objects.select_related("group", "course", "branch", "student"), user), user)


def _contract_in_scope(user, contract):
    c = scoped_contracts(user).filter(pk=contract.pk).first()
    if c is None:
        raise ValidationError({"contract": "Shartnoma topilmadi"})
    return c


class TeacherEvaluationViewSet(AuditedModelViewSet):
    """Baholash: talaba ustozni baholaydi (bo'lim «evaluations»). Javoblarni administrator kiritadi. ?teacher=, ?month="""

    section = "evaluations"
    queryset = TeacherEvaluation.objects.select_related("contract__student")
    serializer_class = TeacherEvaluationSerializer
    branch_field = "branch"
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = services.teacher_scope(super().get_queryset(), self.request.user)
        p = self.request.query_params
        if p.get("teacher"):
            qs = qs.filter(teacher=p["teacher"])
        if p.get("month"):
            start, end = month_bounds(p["month"])
            qs = qs.filter(date__gte=start, date__lt=end)
        return qs.order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        d["contract"] = _contract_in_scope(request.user, d["contract"])
        return Response(self.get_serializer(services.save_evaluation(request.user, d)).data, status=status.HTTP_201_CREATED)


class ParentCallViewSet(AuditedModelViewSet):
    """Ota-onalar bilan aloqa (bo'lim «parentCalls»). Daraxt (kurs → guruh) front-end'da — shuning uchun sahifalanmaydi. ?month="""

    section = "parentCalls"
    queryset = ParentCall.objects.select_related("contract__student__parent")
    serializer_class = ParentCallSerializer
    branch_field = "branch"
    check_usage_on_delete = False
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = services.teacher_scope(super().get_queryset(), self.request.user)
        p = self.request.query_params
        if p.get("month"):
            start, end = month_bounds(p["month"])
            qs = qs.filter(date__gte=start, date__lt=end)
        if p.get("contract"):
            qs = qs.filter(contract=p["contract"])
        return qs.order_by("-date", "-created_at")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        d["contract"] = _contract_in_scope(request.user, d["contract"])
        p = services.save_parent_call(request.user, d)
        return Response(self.get_serializer(self.get_queryset().get(pk=p.pk)).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        r = self.get_object()
        ser = self.get_serializer(r, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        services.save_parent_call(request.user, dict(ser.validated_data), instance=r)
        return Response(self.get_serializer(self.get_queryset().get(pk=r.pk)).data)

    def perform_destroy(self, instance):
        check_edit_window(self.request.user, "parentCalls", instance.date, op="d")
        super().perform_destroy(instance)


@api_view(["GET"])
def export_contracts(request):
    """Shartnomalar .xlsx: ?groups=id,id (Shartnoma yuklash) yoki Shartnomalar ro'yxati filtrlari (?status=&course=&type=&search=).
    Ruxsat — «Shartnoma yuklash» yoki «Shartnomalar» ko'rish. Audit'ga «Eksport» yoziladi."""
    u = request.user
    if not (can(u, "export") or can(u, "contracts")):
        raise PermissionDenied(NO_PERMISSION)
    p = request.query_params
    qs = services.with_balance(scoped_contracts(u).select_related("student__parent"))
    if p.get("groups"):
        qs = qs.filter(group__in=[g for g in p["groups"].split(",") if g])
    if p.get("status"):
        qs = qs.filter(services.status_q(p["status"]))
    for key in ("course", "type"):
        if p.get(key):
            qs = qs.filter(**{key: p[key]})
    if p.get("search"):
        qs = qs.filter(search_q(p["search"], "student__"))
    qs = qs.order_by("group__course__name", "group__number", "student__first_name")
    data = export.contracts_xlsx(qs)
    audit.record(u, AuditLog.Action.EXPORT, "Shartnoma yuklash", detail=f"{qs.count()} ta shartnoma (.xlsx)")
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="shartnomalar-{today():%Y%m%d}.xlsx"'
    return resp


@api_view(["GET"])
def schedule(request):
    """Dars jadvali (bosh sahifa): filial doirasidagi faol va rejadagi guruhlar — xona, kun, vaqt, ustoz bo'yicha.
    Guruhlardan avtomatik tuziladi: guruh ochilsa qo'shiladi, tugasa yoki o'chirilsa tushadi. Ustozlar ham to'liq jadvalni ko'radi
    (faqat guruh nomi, ustoz va to'lish — talaba ma'lumotisiz)."""
    on = today()
    qs = scope_branch(Group.objects.filter(Q(end_date__isnull=True) | Q(end_date__gte=on)), request.user)
    qs = services.with_fill(qs.select_related("course", "day_pattern", "time", "teacher", "supporter", "room")).order_by("time__start_time", "course__name", "number")
    # Guruhdagi talabalar: tugamagan shartnomalar (rejadagilar ham); lidlar: shu guruhga yozilgan, hali shartnomasiz (3 — sinovga yozildi, 4 — sinovga qatnashdi)
    enrolled = Contract.objects.filter(group=OuterRef("pk")).filter(Q(end_date__isnull=True) | Q(end_date__gte=on)).order_by().values("group").annotate(n=Count("id")).values("n")
    lead_n = Lead.objects.filter(group=OuterRef("pk"), status__in=["3", "4"]).order_by().values("group").annotate(n=Count("id")).values("n")
    qs = qs.annotate(enrolled=Coalesce(Subquery(enrolled), 0), lead_count=Coalesce(Subquery(lead_n), 0))
    groups, rooms = [], {}
    for g in qs:
        if g.room_id:
            rooms[g.room_id] = g.room
        groups.append({
            "id": g.pk, "name": g.name, "course": g.course_id, "course_name": g.course.name, "weekdays": g.day_pattern.weekdays,
            "start": f"{g.time.start_time:%H:%M}", "end": f"{g.time.end_time:%H:%M}", "room": g.room_id,
            "teacher": g.teacher_id, "teacher_name": g.teacher.full_name, "supporter_name": g.supporter.full_name if g.supporter_id else "",
            "status": services.period_status(g.start_date, g.end_date, on), "start_date": g.start_date,
            "students": g.enrolled, "leads": g.lead_count, "capacity": g.room.capacity if g.room_id else 0,
        })
    for r in scope_branch(Room.objects.filter(status="Faol"), request.user):
        rooms.setdefault(r.pk, r)
    room_list = sorted(rooms.values(), key=lambda r: (r.name.lower(),))
    return Response({"rooms": [{"id": r.pk, "name": r.name, "capacity": r.capacity} for r in room_list], "groups": groups})

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.calls import services as call_services
from apps.core.pagination import Pagination
from apps.core.permissions import NO_PERMISSION, can, check_edit_window
from apps.core.scoping import branch_ids, in_scope
from apps.core.viewsets import AuditedModelViewSet
from apps.references.models import Branch

from . import services
from .models import Lead, Parent, Student
from .serializers import CallNoteSerializer, LeadCommentSerializer, LeadCreateSerializer, LeadSerializer, ParentSerializer, StudentSerializer, StudentUpdateSerializer

LEAD_QS = Lead.objects.select_related("student").prefetch_related("preferred_times").annotate(
    comments_count=Count("comments", filter=Q(comments__is_deleted=False)), has_contract_flag=services.contract_exists(),
).order_by("-created_at")


def search_q(text, prefix=""):
    q = Q()
    for word in str(text).split():
        q &= (Q(**{f"{prefix}first_name__icontains": word}) | Q(**{f"{prefix}last_name__icontains": word}) | Q(**{f"{prefix}father_name__icontains": word})
              | Q(**{f"{prefix}phone1__contains": word}) | Q(**{f"{prefix}phone2__contains": word}))
    return q


def default_branch(user, requested=None):
    """Filial bitta bo'lsa — o'zi tanlanadi (CLAUDE.md 2)."""
    qs = Branch.objects.filter(status="Faol")
    if requested:
        b = qs.filter(pk=requested).first()
        if not b or not in_scope(user, b.pk):
            raise ValidationError({"branch": "Bu filial sizning doirangizda emas"})
        return b
    ids = branch_ids(user)
    mine = [b for b in qs if ids is None or b.pk in ids]
    if len(mine) != 1:
        raise ValidationError({"branch": "Filialni tanlang"})
    return mine[0]


class LeadViewSet(AuditedModelViewSet):
    """Lidlar: ro'yxat (sahifalangan, filtrli), voronka, statistika, kartochka va izohlar. Bo'lim «leads»."""

    section = "leads"
    queryset = LEAD_QS
    branch_field = "branch"
    pagination_class = Pagination
    check_usage_on_delete = False
    action_ops = {"board": "v", "stats": "v", "comments": "a", "contract": "v", "call_note": "a", "calls": "v"}

    def get_serializer_class(self):
        return LeadCreateSerializer if self.action == "create" else LeadSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.action in ("create",):
            ctx["branch"] = default_branch(self.request.user, self.request.data.get("branch"))
        return ctx

    def filtered(self):
        qs = self.get_queryset()
        p = self.request.query_params
        if p.get("search"):
            qs = qs.filter(search_q(p["search"], "student__"))
        for key, field in (("course", "course"), ("source", "source"), ("status", "status")):
            if p.get(key):
                qs = qs.filter(**{field: p[key]})
        if p.get("paid"):
            qs = services.with_payments(qs).filter(paid_total__gt=0)
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filtered())
        return self.get_paginated_response(LeadSerializer(page, many=True, context=self.get_serializer_context()).data)

    def retrieve(self, request, *args, **kwargs):
        lead = self.get_object()
        data = LeadSerializer(lead, context=self.get_serializer_context()).data
        data["comments"] = LeadCommentSerializer(lead.comments.order_by("-created_at"), many=True).data
        return Response(data)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        branch = self.get_serializer_context()["branch"]
        mode, comment, student = d.pop("mode", "new"), d.pop("comment", ""), d.pop("student", None)
        new_student = None
        fields = ("first_name", "last_name", "phone1", "phone2", "gender")
        picked = {k: d.pop(k, "") for k in fields}
        if mode == "new":
            new_student = picked
            student = None
        lead = services.create_lead(request.user, branch, d, new_student=new_student, student=student, comment=comment)
        return Response(LeadSerializer(LEAD_QS.get(pk=lead.pk), context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        check_edit_window(self.request.user, "leads", serializer.instance.created_at)
        old = serializer.instance.status
        super().perform_update(serializer)
        if serializer.instance.status != old:
            services.notif.lead_changed(serializer.instance, old, self.request.user)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(LeadSerializer(LEAD_QS.get(pk=kwargs["pk"]), context=self.get_serializer_context()).data)

    def perform_destroy(self, instance):
        check_edit_window(self.request.user, "leads", instance.created_at, op="d")
        super().perform_destroy(instance)

    @action(detail=False)
    def board(self, request):
        b = services.board(self.filtered())
        ser = lambda items: LeadSerializer(items, many=True, context=self.get_serializer_context()).data  # noqa: E731
        return Response({**b, "columns": {s: ser(items) for s, items in b["columns"].items()}})

    @action(detail=False)
    def stats(self, request):
        return Response(services.stats(self.filtered()))

    @action(detail=True, methods=["post"])
    def contract(self, request, pk=None):
        """«Shartnoma tuzish» (5-status): yangi shartnoma id va raqamini qaytaradi. Ruxsat — Shartnomalar «qo'shish»."""
        if not can(request.user, "contracts", "a"):
            raise PermissionDenied(NO_PERMISSION)
        c = services.create_contract_from_lead(request.user, self.get_object())
        return Response({"id": str(c.pk), "number": c.number}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        c = services.add_comment(request.user, self.get_object(), request.data.get("comment"))
        return Response(LeadCommentSerializer(c).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="call-note")
    def call_note(self, request, pk=None):
        """Suhbatdan keyingi izoh + (ixtiyoriy) holat va keyingi qayta bog'lanish vaqti."""
        lead = self.get_object()
        ser = CallNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        services.save_call_note(request.user, lead, d["comment"], d.get("status") or None, d.get("callback_at"))
        return Response(LeadSerializer(LEAD_QS.get(pk=lead.pk), context=self.get_serializer_context()).data)

    @action(detail=True)
    def calls(self, request, pk=None):
        """Shu lidning (talaba, 1- va 2-telefon, vasiy) qo'ng'iroqlar tarixi. «Qo'ng'iroqlar» bo'limini ko'rish huquqi kerak."""
        lead = self.get_object()
        return Response(contact_history(request.user, lead.branch_id, lead.student))


def contact_history(user, branch_id, student):
    """Kartochka uchun: qo'ng'iroqlar («calls» ko'rish huquqi) va yuborilgan SMS'lar («sms» ko'rish huquqi, 2026-10-22)."""
    from apps.calls import sms as sms_services

    phones = call_services.student_phones(student)
    can_calls, can_sms = can(user, "calls", "v"), can(user, "sms", "v")
    out = call_services.history(branch_id, phones) if can_calls else {"count": 0, "results": [], "last": None}
    out.update(allowed=can_calls or can_sms, calls_allowed=can_calls, sms=sms_services.history(branch_id, student, phones) if can_sms else None)
    return out


class StudentViewSet(AuditedModelViewSet):
    """Talabalar (yaratish — lid orqali). ?free=1 — lidi ham, shartnomasi ham yo'q talabalar (lid formasi uchun)."""

    section = "leads"
    queryset = Student.objects.prefetch_related("contracts")
    serializer_class = StudentSerializer
    branch_field = "branch"
    pagination_class = Pagination
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("search"):
            qs = qs.filter(search_q(p["search"]))
        if p.get("free"):
            qs = qs.exclude(leads__is_deleted=False).exclude(contracts__is_deleted=False)
        return qs

    @action(detail=True)
    def calls(self, request, pk=None):
        """Talabaning (1- va 2-telefon, vasiy) qo'ng'iroqlar tarixi."""
        student = self.get_object()
        return Response(contact_history(request.user, student.branch_id, student))

    def partial_update(self, request, *args, **kwargs):
        student = self.get_object()
        check_edit_window(request.user, "leads", student.created_at)
        ser = StudentUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        new_parent = {"first_name": d.pop("p_first", ""), "phone": d.pop("p_phone", ""), "relation": d.pop("p_relation", "")} if d.pop("new_parent", False) else None
        d.pop("p_first", None), d.pop("p_phone", None)
        if d.get("parent") and not in_scope(request.user, d["parent"].branch_id):
            raise ValidationError({"parent": "Bu vasiy sizning doirangizda emas"})
        student = services.update_student(request.user, student, d, new_parent=new_parent)
        return Response(StudentSerializer(Student.objects.prefetch_related("contracts").get(pk=student.pk)).data)


class ParentViewSet(AuditedModelViewSet):
    section = "leads"
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    branch_field = "branch"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        s = self.request.query_params.get("search")
        if s:
            qs = qs.filter(Q(first_name__icontains=s) | Q(last_name__icontains=s) | Q(phone__contains=s))
        return qs


"""Mijozlar boti: bosh menejer/administratorlar uchun ko'rish va sozlash (Qo'ng'iroqlar va SMS → Telegram bot). Hammasi `clientbot` bo'limi ruxsati bilan."""

import datetime

from django.conf import settings
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.pagination import Pagination
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet
from apps.references.models import Branch

from . import services
from .models import BotConfig, BotInvite, BotLink, ClientOutbox, LeadSurvey, Referral

READ_ONLY = ["get", "head", "options"]


def _search(qs, q, *fields):
    q = (q or "").strip()
    if not q:
        return qs
    cond = Q()
    for f in fields:
        cond |= Q(**{f"{f}__icontains": q})
    digits = "".join(c for c in q if c.isdigit())
    return qs.filter(cond | Q(phone__contains=digits[-9:])) if digits and hasattr(qs.model, "phone") else qs.filter(cond)


# ---------- ulanganlar ----------


class BotLinkSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    parent_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="account.username", read_only=True)
    telegram_name = serializers.CharField(source="account.first_name", read_only=True)
    blocked = serializers.BooleanField(source="account.blocked", read_only=True)

    class Meta:
        model = BotLink
        fields = ["id", "student", "student_name", "parent_name", "role", "phone", "username", "telegram_name", "blocked", "linked_at", "is_active"]
        read_only_fields = fields

    def get_parent_name(self, ln):
        return str(ln.parent) if ln.parent_id else ""


class BotLinkViewSet(AuditedModelViewSet):
    """?role=Talaba|Vasiy&active=1|0&q=. `summary/` — umumiy ko'rsatkichlar."""

    section = "clientbot"
    branch_field = "student__branch"
    serializer_class = BotLinkSerializer
    pagination_class = Pagination
    http_method_names = READ_ONLY
    action_ops = {"summary": "v"}
    queryset = BotLink.objects.select_related("student", "parent", "account")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action != "list":
            return qs
        p = self.request.query_params
        if p.get("role") in BotInvite.Role.values:
            qs = qs.filter(role=p["role"])
        if p.get("active") in ("0", "1"):
            qs = qs.filter(is_active=p["active"] == "1")
        return _search(qs, p.get("q"), "student__first_name", "student__last_name", "account__username")

    @action(detail=False)
    def summary(self, request):
        u = request.user
        invites = scope_branch(BotInvite.objects.all(), u)
        links = scope_branch(BotLink.objects.filter(is_active=True), u, "student__branch")
        surveys = scope_branch(LeadSurvey.objects.all(), u, "lead__branch")
        refs = scope_branch(Referral.objects.all(), u)
        msgs = scope_branch(ClientOutbox.objects.all(), u, "student__branch")
        by_source = list(surveys.exclude(source=None).values("source__name").annotate(n=Count("pk")).order_by("-n").values_list("source__name", "n"))
        same = surveys.filter(source=F("lead__source")).count()
        linked_invites = invites.filter(links__is_active=True).distinct().count()
        return Response({
            "configured": services.configured(),
            "username": settings.CLIENT_BOT_USERNAME,
            "invites": invites.count(),
            "invited_students": invites.values("student").distinct().count(),
            "linked_invites": linked_invites,
            "unlinked_invites": invites.count() - linked_invites,
            "linked_students": links.values("student").distinct().count(),
            "students": links.filter(role=BotInvite.Role.STUDENT).values("student").distinct().count(),
            "guardians": links.filter(role=BotInvite.Role.GUARDIAN).values("student").distinct().count(),
            "accounts": links.values("account").distinct().count(),
            "surveys": surveys.count(),
            "surveys_same": same,
            "survey_sources": [{"name": n, "count": c} for n, c in by_source],
            "referrals": {s: refs.filter(state=s).count() for s in Referral.State.values},
            "outbox_pending": ClientOutbox.objects.filter(status=ClientOutbox.Status.PENDING).count(),
            "outbox_failed": ClientOutbox.objects.filter(status=ClientOutbox.Status.FAILED).count(),
            "messages_sent": msgs.filter(status=ClientOutbox.Status.SENT).count(),
            "messages_sent_30d": msgs.filter(status=ClientOutbox.Status.SENT, sent_at__gte=timezone.now() - datetime.timedelta(days=30)).count(),
            "messages_by_kind": [{"kind": k or "Bot", "count": n} for k, n in msgs.filter(status=ClientOutbox.Status.SENT).values_list("kind")
                                 .annotate(n=Count("pk")).order_by("-n")],
        })


# ---------- ulanmagan takliflar ----------


class BotInviteSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    linked = serializers.SerializerMethodField()

    class Meta:
        model = BotInvite
        fields = ["id", "student", "student_name", "phone", "role", "created_at", "linked"]
        read_only_fields = fields

    def get_linked(self, i):
        return any(ln.is_active for ln in i.links.all())


class BotInviteViewSet(AuditedModelViewSet):
    """Yuborilgan takliflar (SMS'dagi kodlar). ?linked=0 — hali ulanmaganlar."""

    section = "clientbot"
    branch_field = "branch"
    serializer_class = BotInviteSerializer
    pagination_class = Pagination
    http_method_names = READ_ONLY
    queryset = BotInvite.objects.select_related("student").prefetch_related("links")

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("linked") in ("0", "1"):
            has = Q(links__is_active=True)
            qs = qs.filter(has).distinct() if p["linked"] == "1" else qs.exclude(has)
        return _search(qs, p.get("q"), "student__first_name", "student__last_name")


# ---------- so'rovnoma javoblari ----------


class LeadSurveySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="lead.student.full_name", read_only=True)
    lead_source = serializers.CharField(source="lead.source.name", read_only=True)
    source_name = serializers.SerializerMethodField()
    course = serializers.CharField(source="lead.course.name", read_only=True)
    referrer = serializers.SerializerMethodField()

    class Meta:
        model = LeadSurvey
        fields = ["id", "lead", "student_name", "course", "lead_source", "source", "source_name", "referrer", "answered_at"]
        read_only_fields = fields

    def get_source_name(self, s):
        return s.source.name if s.source_id else ""

    def get_referrer(self, s):
        r = getattr(s.lead, "referral", None)
        return (str(r.referrer_student) if r and r.referrer_student_id else (r.referrer_text if r else ""))


class LeadSurveyViewSet(AuditedModelViewSet):
    """Mijoz botda aytgan manba (administrator kiritgan manba — `lead_source`). ?differs=1 — ikkisi har xil."""

    section = "clientbot"
    branch_field = "lead__branch"
    serializer_class = LeadSurveySerializer
    pagination_class = Pagination
    http_method_names = READ_ONLY
    queryset = LeadSurvey.objects.select_related("lead__student", "lead__source", "lead__course", "source", "lead__referral__referrer_student")

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("differs") == "1":
            qs = qs.exclude(source=F("lead__source"))
        if p.get("source"):
            qs = qs.filter(source_id=p["source"])
        return _search(qs, p.get("q"), "lead__student__first_name", "lead__student__last_name")


# ---------- tavsiyalar ----------


class ReferralSerializer(serializers.ModelSerializer):
    lead_student = serializers.CharField(source="lead.student.full_name", read_only=True)
    lead_status = serializers.CharField(source="lead.status", read_only=True)
    referrer_name = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = ["id", "created_at", "lead", "lead_student", "lead_status", "referrer_student", "referrer_name", "referrer_text", "state", "bonus",
                  "paid_at", "comment"]
        read_only_fields = ["lead", "bonus", "paid_at", "created_at"]

    def get_referrer_name(self, r):
        return r.referrer_student.full_name if r.referrer_student_id else ""

    def validate_state(self, v):
        if v == Referral.State.PAID:
            raise serializers.ValidationError("«Berildi» holatini tizim o'zi qo'yadi (lid birinchi to'lov qilganda)")
        if self.instance and self.instance.state == Referral.State.PAID:
            raise serializers.ValidationError("Bonus berilgan tavsiyani o'zgartirib bo'lmaydi")
        return v

    def validate_referrer_student(self, st):
        if st and (st.branch_id != self.instance.branch_id or st.pk == self.instance.lead.student_id):
            raise serializers.ValidationError("Bu talabani tanlab bo'lmaydi")
        return st

    def update(self, instance, data):
        if self.instance.state == Referral.State.PAID and set(data) - {"comment"}:
            raise serializers.ValidationError("Bonus berilgan tavsiyani o'zgartirib bo'lmaydi")
        if data.get("referrer_student") and "state" not in data and instance.state == Referral.State.UNMATCHED:
            data["state"] = Referral.State.PENDING  # administrator tavsiya qiluvchini bog'ladi
        return super().update(instance, data)


class ReferralViewSet(AuditedModelViewSet):
    """Tavsiyalar. Administrator «aniqlanmagan» ismni talabaga bog'laydi (PATCH referrer_student). ?state="""

    section = "clientbot"
    branch_field = "branch"
    serializer_class = ReferralSerializer
    pagination_class = Pagination
    http_method_names = ["get", "patch", "head", "options"]
    queryset = Referral.objects.select_related("lead__student", "referrer_student")

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("state") in Referral.State.values:
            qs = qs.filter(state=p["state"])
        return _search(qs, p.get("q"), "lead__student__first_name", "lead__student__last_name", "referrer_text")


# ---------- botga ketgan xabarlar ----------


class BotMessageSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="account.username", read_only=True)
    telegram_name = serializers.CharField(source="account.first_name", read_only=True)

    class Meta:
        model = ClientOutbox
        fields = ["id", "created_at", "kind", "student", "student_name", "phone", "recipient", "text", "status", "error", "sent_at", "username",
                  "telegram_name"]
        read_only_fields = fields

    def get_student_name(self, m):
        return m.student.full_name if m.student_id else ""


class BotMessageViewSet(AuditedModelViewSet):
    """Mijozlar botiga ketgan xabarlar (SMS o'rniga yoki bot ichida). ?status=pending|sent|failed&kind=&q="""

    section = "clientbot"
    branch_field = "student__branch"
    serializer_class = BotMessageSerializer
    pagination_class = Pagination
    http_method_names = READ_ONLY
    queryset = ClientOutbox.objects.select_related("student", "account").order_by("-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("status") in ClientOutbox.Status.values:
            qs = qs.filter(status=p["status"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        return _search(qs, p.get("q"), "student__first_name", "student__last_name", "account__username", "text")


# ---------- sozlamalar ----------


class BotConfigSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = BotConfig
        fields = ["id", "branch", "branch_name", "invite_in_sms", "referral_bonus", "referral_min_percent", "reminder_days", "reminder_max"]
        read_only_fields = ["branch"]

    def validate_referral_bonus(self, v):
        if v < 0:
            raise serializers.ValidationError("Manfiy bo'lmasin")
        return v

    def validate_referral_min_percent(self, v):
        if not 0 <= v <= 100:
            raise serializers.ValidationError("0 dan 100 gacha")
        return v

    def validate_reminder_days(self, v):
        if not 1 <= v <= 60:
            raise serializers.ValidationError("1 dan 60 kungacha")
        return v

    def validate_reminder_max(self, v):
        if not 0 <= v <= 10:
            raise serializers.ValidationError("0 dan 10 gacha")
        return v


class BotConfigViewSet(AuditedModelViewSet):
    """Filial sozlamalari (ro'yxat so'ralganda yetishmaganlari standart qiymat bilan yaratiladi). Faqat o'qish va tahrirlash."""

    section = "clientbot"
    branch_field = "branch"
    serializer_class = BotConfigSerializer
    http_method_names = ["get", "patch", "head", "options"]
    queryset = BotConfig.objects.select_related("branch")

    def list(self, request, *args, **kwargs):
        for b in scope_branch(Branch.objects.filter(is_deleted=False), request.user, "pk"):
            services.get_config(b)
        return super().list(request, *args, **kwargs)

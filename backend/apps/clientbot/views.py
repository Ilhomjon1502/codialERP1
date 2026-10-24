"""Mijozlar boti: bosh menejer/administratorlar uchun ko'rish va sozlash (Qo'ng'iroqlar va SMS → Telegram bot). Hammasi `clientbot` bo'limi ruxsati bilan."""

import datetime

from django.conf import settings
from django.db.models import Count, F, Prefetch, Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from apps.core.pagination import Pagination
from apps.core.scoping import scope_branch
from apps.core.viewsets import AuditedModelViewSet, BranchScopedSerializerMixin
from apps.crm.models import Student
from apps.education.models import Contract
from apps.references.models import Branch

from . import invites as bulk
from . import referrals, services, survey
from .models import BotConfig, BotInvite, BotLink, ClientOutbox, ExitSurvey, LeadSurvey, Referral, SurveyQuestion

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
        active = bulk.active_students(u)
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
            "active_students": active.count(),
            "active_linked": active.filter(bot_links__is_active=True).distinct().count(),
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


# ---------- faol talabalar: kim ulangan, kim ulanmagan ----------


class BotStudentSerializer(serializers.ModelSerializer):
    contracts_info = serializers.SerializerMethodField()
    phones = serializers.SerializerMethodField()
    linked = serializers.SerializerMethodField()
    linked_roles = serializers.SerializerMethodField()
    invited_at = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ["id", "full_name", "contracts_info", "phones", "linked", "linked_roles", "invited_at"]
        read_only_fields = fields

    def get_contracts_info(self, st):
        today = timezone.localdate()
        return [f"{c.course.name} / #{c.group.number}" for c in st.contracts.all() if not c.is_deleted and (c.end_date is None or c.end_date >= today)]

    def get_phones(self, st):
        from apps.calls.sms import recipients

        return [{"phone": p, "who": w} for p, w in recipients(st)]

    def get_linked(self, st):
        return any(ln.is_active for ln in st.bot_links.all())

    def get_linked_roles(self, st):
        return sorted({ln.role or "?" for ln in st.bot_links.all() if ln.is_active})

    def get_invited_at(self, st):
        times = [i.created_at for i in st.bot_invites.all() if not i.is_deleted]
        return max(times) if times else None


class BotStudentViewSet(AuditedModelViewSet):
    """Faol (yoki boshlanmagan) shartnomali talabalar va ularning bot holati. ?linked=0|1&q=. `invite/` — ulanmagan raqamlarga taklif SMS'i (preview: true — faqat hisob)."""

    section = "clientbot"
    serializer_class = BotStudentSerializer
    pagination_class = Pagination
    http_method_names = ["get", "post", "head", "options"]
    action_ops = {"invite": "e"}

    def get_queryset(self):
        qs = bulk.active_students(self.request.user).prefetch_related(
            Prefetch("contracts", queryset=Contract.objects.select_related("course", "group")), "bot_links", "bot_invites").order_by("first_name", "last_name")
        p = self.request.query_params
        if p.get("linked") in ("0", "1"):
            has = Q(bot_links__is_active=True)
            qs = qs.filter(has) if p["linked"] == "1" else qs.exclude(pk__in=Student.objects.filter(has).values("pk"))
        return _search(qs, p.get("q"), "first_name", "last_name")

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=False, methods=["post"])
    def invite(self, request):
        """{text, preview}: ulanmagan raqamlarga bot havolali SMS (administrator tasdig'i bilan; ulangan va avval taklif olganlarga yuborilmaydi)."""
        text = request.data.get("text") or bulk.DEFAULT_TEXT
        if request.data.get("preview"):
            return Response(bulk.preview(request.user, text))
        return Response(bulk.send(request.user, text), status=status.HTTP_201_CREATED)


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
        ref = super().update(instance, data)
        if ref.state == Referral.State.PENDING:
            referrals.evaluate(ref)  # lid allaqachon to'lov qilgan bo'lsa — bonus darrov beriladi
        return ref


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


# ---------- tamomlash so'rovnomasi ----------


class SurveyQuestionSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestion
        fields = ["id", "branch", "key", "text", "kind", "options", "allow_other", "flow", "order", "status"]
        read_only_fields = ["key"]

    def validate_text(self, v):
        v = (v or "").strip()
        if len(v) < 5:
            raise serializers.ValidationError("Savol matnini kiriting")
        return v

    def validate_options(self, v):
        if not isinstance(v, list):
            raise serializers.ValidationError("Variantlar ro'yxat bo'lsin")
        v = [str(x).strip() for x in v if str(x).strip()]
        if len(v) > 8 or any(len(x) > 40 for x in v):
            raise serializers.ValidationError("Ko'pi bilan 8 ta variant, har biri 40 belgigacha")
        return v

    def validate(self, d):
        kind = d.get("kind") or (self.instance.kind if self.instance else SurveyQuestion.Kind.CHOICE)
        if kind == SurveyQuestion.Kind.CHOICE:
            options = d["options"] if "options" in d else (self.instance.options if self.instance else [])
            if len(options) < 2:
                raise serializers.ValidationError({"options": "Tanlov savoli uchun kamida 2 ta variant kiriting"})
        else:
            d["options"], d["allow_other"] = [], False
        return d


class SurveyQuestionViewSet(AuditedModelViewSet):
    """So'rovnoma savollari (Bosh menejer qo'shadi/tahrirlaydi/o'chiradi). Ro'yxat so'ralganda filialda savol bo'lmasa standartlari yaratiladi."""

    section = "clientbot"
    branch_field = "branch"
    serializer_class = SurveyQuestionSerializer
    check_usage_on_delete = False  # javoblarda savol matni nusxasi saqlanadi
    queryset = SurveyQuestion.objects.select_related("branch")

    def list(self, request, *args, **kwargs):
        for b in scope_branch(Branch.objects.filter(is_deleted=False), request.user, "pk"):
            survey.ensure_questions(b)
        return super().list(request, *args, **kwargs)


class ExitSurveySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    course = serializers.CharField(source="contract.course.name", read_only=True)

    class Meta:
        model = ExitSurvey
        fields = ["id", "student", "student_name", "course", "flow", "stop_reason", "state", "sent_at", "completed_at", "respondent_role", "answers"]
        read_only_fields = fields


class ExitSurveyViewSet(AuditedModelViewSet):
    """Yuborilgan so'rovnomalar va javoblar. ?state=Yuborildi|Jarayonda|Tugadi&flow=&q=. `stats/` — sabablar va baholar."""

    section = "clientbot"
    branch_field = "branch"
    serializer_class = ExitSurveySerializer
    pagination_class = Pagination
    http_method_names = READ_ONLY
    action_ops = {"stats": "v"}
    queryset = ExitSurvey.objects.select_related("student", "contract__course")

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("state") in ExitSurvey.State.values:
            qs = qs.filter(state=p["state"])
        if p.get("flow") in (SurveyQuestion.Flow.COMPLETED, SurveyQuestion.Flow.STOPPED):
            qs = qs.filter(flow=p["flow"])
        return _search(qs, p.get("q"), "student__first_name", "student__last_name")

    @action(detail=False)
    def stats(self, request):
        return Response(survey.stats(self.get_queryset()))


# ---------- sozlamalar ----------


class BotConfigSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = BotConfig
        fields = ["id", "branch", "branch_name", "invite_in_sms", "referral_bonus", "referral_min_percent", "reminder_days", "reminder_max", "finance_in_bot"]
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

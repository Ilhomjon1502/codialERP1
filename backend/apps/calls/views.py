import datetime

from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.pagination import Pagination
from apps.core.viewsets import AuditedModelViewSet, BranchScopedSerializerMixin
from apps.education.models import Attendance, Contract

from . import services, sms
from .models import CallDevice, CallRecord, SmsMessage, SmsTemplate

D = CallRecord.Direction


# ---------- Telefondagi ilova uchun (sessiyasiz, qurilma tokeni bilan) ----------


def _device(request):
    auth = request.headers.get("Authorization", "")
    return services.device_by_token(auth[7:].strip()) if auth.startswith("Device ") else None


class DeviceAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class PairView(DeviceAPIView):
    """POST {code, app_version} → {token, device}. Kod Sozlamalar → Qo'ng'iroq qurilmalari'da chiqadi."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        device, token = services.pair(request.data.get("code"), request.data.get("app_version"))
        return Response({"token": token, "device": {"id": device.pk, "name": device.name, "branch": device.branch.name}})


class IngestView(DeviceAPIView):
    """POST {calls: [{id, date (ms), type (Android CallLog), number, duration, name, sim}], app_version}."""

    def post(self, request):
        device = _device(request)
        if not device:
            return Response({"detail": "Qurilma ulanmagan", "code": "device_unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(services.ingest(device, request.data.get("calls"), request.data.get("app_version")))


class PingView(DeviceAPIView):
    """Ilova ulanishni tekshiradi: {name, branch, last_external_ids}."""

    def get(self, request):
        device = _device(request)
        if not device:
            return Response({"detail": "Qurilma ulanmagan", "code": "device_unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        device.last_seen_at = timezone.now()
        device.save(update_fields=["last_seen_at"])
        return Response({"name": device.name, "branch": device.branch.name})


# ---------- Qurilmalar (Sozlamalar) ----------


class CallDeviceSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    paired = serializers.SerializerMethodField()
    pair_code = serializers.SerializerMethodField()

    class Meta:
        model = CallDevice
        fields = ["id", "name", "branch", "phone", "status", "paired", "paired_at", "last_seen_at", "app_version", "pair_code", "pair_expires_at"]
        read_only_fields = ["paired_at", "last_seen_at", "app_version", "pair_expires_at"]

    def validate_phone(self, v):
        p = services.normalize(v)
        if v and not p:
            raise serializers.ValidationError("9 sondan iborat bo'lsin. Namuna: 998883322")
        return p

    def get_paired(self, d):
        return bool(d.token_hash)

    def get_pair_code(self, d):
        return d.pair_code if d.pair_code and d.pair_expires_at and d.pair_expires_at > timezone.now() else ""


class CallDeviceViewSet(AuditedModelViewSet):
    section = "calls"
    branch_field = "branch"
    queryset = CallDevice.objects.select_related("branch")
    serializer_class = CallDeviceSerializer
    action_ops = {"pair_code": "a"}
    check_usage_on_delete = False

    def perform_create(self, serializer):
        super().perform_create(serializer)
        services.new_pair_code(serializer.instance)

    @action(detail=True, methods=["post"], url_path="pair-code")
    def pair_code(self, request, pk=None):
        """Yangi ulash kodi (eski token bekor bo'ladi)."""
        d = self.get_object()
        services.new_pair_code(d)
        return Response(self.get_serializer(d).data)


# ---------- Qo'ng'iroqlar ----------


class CallRecordSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    student_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    lead_status = serializers.CharField(source="lead.status", read_only=True, default="")
    lead_source = serializers.CharField(source="lead.source.name", read_only=True, default="")
    lead_course = serializers.CharField(source="lead.course.name", read_only=True, default="")
    has_contract = serializers.BooleanField(read_only=True, default=False)
    contract_id = serializers.UUIDField(read_only=True, default=None)
    open_absences = serializers.IntegerField(read_only=True, default=0)
    lead_note_due = serializers.SerializerMethodField()
    missed = serializers.BooleanField(source="is_missed", read_only=True)
    callback_by_name = serializers.CharField(source="callback_by.full_name", read_only=True, default="")

    class Meta:
        model = CallRecord
        fields = ["id", "started_at", "direction", "number", "phone", "duration", "contact_name", "sim", "is_first", "device", "device_name",
                  "student", "student_name", "parent", "parent_name", "lead", "lead_status", "lead_source", "lead_course", "has_contract", "contract_id",
                  "open_absences", "lead_note_due",
                  "missed", "callback_at", "callback_by_name", "comment"]
        read_only_fields = [f for f in fields if f != "comment"]

    def get_lead_note_due(self, r):
        return bool(r.lead_id and r.lead.callback_talked_at)

    def get_student_name(self, r):
        return r.student.full_name if r.student_id else ""

    def get_parent_name(self, r):
        return str(r.parent) if r.parent_id else ""


def _date(v):
    try:
        return datetime.date.fromisoformat(v) if v else None
    except ValueError:
        return None


class CallRecordViewSet(AuditedModelViewSet):
    """?from=&to= (sana), ?dir=Kiruvchi|Chiquvchi|missed|missed_open, ?known=0|1, ?first=1, ?q=raqam yoki ism, ?device=."""

    section = "calls"
    branch_field = "branch"
    serializer_class = CallRecordSerializer
    pagination_class = Pagination
    http_method_names = ["get", "post", "patch", "head", "options"]
    action_ops = {"callback": "e", "stats": "v", "absence_contact": "e"}
    queryset = CallRecord.objects.select_related("device", "student", "parent", "lead__source", "lead__course", "callback_by")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ("list", "stats"):
            qs = self._filter(qs)
        if self.action != "stats":
            today = timezone.localdate()
            active = Contract.objects.filter(student=OuterRef("student")).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
            absent = (Attendance.objects.filter(contract__student=OuterRef("student"), status__in=["X", "0"], contact_status=Attendance.Contact.TO_CALL,
                                                date__gte=today - datetime.timedelta(days=services.ABSENCE_DAYS)).order_by().values("contract__student")
                      .annotate(n=Count("id")).values("n"))
            qs = qs.annotate(has_contract=Exists(active), contract_id=Subquery(active.order_by("-start_date").values("id")[:1]),
                             open_absences=Subquery(absent))
        return qs

    def _filter(self, qs):
        p = self.request.query_params
        local = timezone.get_current_timezone()
        if d := _date(p.get("from")):
            qs = qs.filter(started_at__gte=datetime.datetime.combine(d, datetime.time.min, local))
        if d := _date(p.get("to")):
            qs = qs.filter(started_at__lt=datetime.datetime.combine(d + datetime.timedelta(days=1), datetime.time.min, local))
        missed = [D.MISSED, D.REJECTED]
        direction = p.get("dir")
        if direction == "missed":
            qs = qs.filter(direction__in=missed)
        elif direction == "missed_open":
            qs = qs.filter(direction__in=missed, callback_at__isnull=True)
        elif direction in D.values:
            qs = qs.filter(direction=direction)
        if p.get("known") == "1":
            qs = qs.filter(Q(student__isnull=False) | Q(parent__isnull=False))
        elif p.get("known") == "0":
            qs = qs.filter(student__isnull=True, parent__isnull=True)
        if p.get("first") == "1":
            qs = qs.filter(is_first=True)
        if p.get("device"):
            qs = qs.filter(device_id=p["device"])
        if q := (p.get("q") or "").strip():
            digits = "".join(c for c in q if c.isdigit())
            cond = Q(contact_name__icontains=q) | Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q)
            if digits:
                cond |= Q(number__contains=digits) | Q(phone__contains=digits[-9:])
            qs = qs.filter(cond)
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        services.rematch(page)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=True, methods=["post"])
    def callback(self, request, pk=None):
        """{done: true|false} — javobsiz qo'ng'iroqqa qayta qo'ng'iroq qilindi belgisi."""
        rec = services.set_callback(request.user, self.get_object(), bool(request.data.get("done", True)))
        return Response(self.get_serializer(rec).data)

    @action(detail=True, methods=["post"], url_path="absence-contact")
    def absence_contact(self, request, pk=None):
        """{comment, parent_log} — talabaning kelmagan darslari «Gaplashildi» (izoh majburiy), ota-onalar bilan aloqa jurnaliga ham yoziladi."""
        res = services.absence_contact(request.user, self.get_object(), request.data.get("comment"), bool(request.data.get("parent_log", True)))
        return Response(res)

    @action(detail=False)
    def stats(self, request):
        return Response(services.stats(self.get_queryset()))


# ---------- SMS (2026-10-22): telefon navbatni oladi, natijani qaytaradi ----------


class SmsOutboxView(DeviceAPIView):
    """GET → {messages: [{id, phone, text}]} — telefon yuborishi kerak bo'lgan SMS'lar (olingani «Yuborilmoqda»)."""

    def get(self, request):
        device = _device(request)
        if not device:
            return Response({"detail": "Qurilma ulanmagan", "code": "device_unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"messages": sms.outbox(device)})


class SmsReportView(DeviceAPIView):
    """POST {results: [{id, ok, error}]}."""

    def post(self, request):
        device = _device(request)
        if not device:
            return Response({"detail": "Qurilma ulanmagan", "code": "device_unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(sms.report(device, request.data.get("results")))


class SmsInboxView(DeviceAPIView):
    """POST {messages: [{id, date (ms), address, body}]} — mijozlardan kelgan SMS (2026-10-22). Faqat oddiy raqamlardan saqlanadi."""

    def post(self, request):
        device = _device(request)
        if not device:
            return Response({"detail": "Qurilma ulanmagan", "code": "device_unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(sms.ingest_inbox(device, request.data.get("messages")))


def _month(v):
    try:
        return datetime.date.fromisoformat(f"{v}-01") if v else timezone.localdate().replace(day=1)
    except ValueError as e:
        raise serializers.ValidationError({"month": ["Oy YYYY-MM ko'rinishida bo'lsin"]}) from e


class SmsTemplateSerializer(BranchScopedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SmsTemplate
        fields = ["id", "branch", "name", "text", "status"]

    def validate_text(self, v):
        return sms.check_template(v)


class SmsTemplateViewSet(AuditedModelViewSet):
    section = "sms"
    branch_field = "branch"
    queryset = SmsTemplate.objects.all()
    serializer_class = SmsTemplateSerializer
    check_usage_on_delete = False

    @action(detail=False)
    def placeholders(self, request):
        return Response([{"key": k, "label": v} for k, v in sms.PLACEHOLDERS.items()])


class SmsMessageSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    device_name = serializers.CharField(source="device.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SmsMessage
        fields = ["id", "created_at", "direction", "kind", "month", "contract", "student", "student_name", "parent_name", "lead", "phone",
                  "recipient", "text", "parts", "status", "error", "taken_at", "sent_at", "device_name", "created_by_name"]
        read_only_fields = fields

    def get_student_name(self, m):
        st = m.contract.student if m.contract_id else m.student
        return st.full_name if st else ""

    def get_parent_name(self, m):
        return str(m.parent) if m.parent_id else ""

    def get_created_by_name(self, m):
        return m.created_by.full_name if m.created_by_id and m.direction == SmsMessage.Direction.OUT else ""


class SmsMessageViewSet(AuditedModelViewSet):
    """Jurnal: ?dir=Chiquvchi|Kiruvchi&status=&known=0&from=&to=&q=&contract=&month=YYYY-MM. Yuborish: POST dues/ (preview: true — faqat hisob)."""

    section = "sms"
    branch_field = "branch"
    serializer_class = SmsMessageSerializer
    pagination_class = Pagination
    http_method_names = ["get", "post", "head", "options"]
    action_ops = {"dues": "a", "retry": "a", "cancel": "e", "cancel_all": "e", "summary": "v"}
    queryset = SmsMessage.objects.select_related("contract__student", "student", "parent", "device", "created_by")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action not in ("list", "summary"):
            return qs
        p = self.request.query_params
        local = timezone.get_current_timezone()
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("dir") in SmsMessage.Direction.values:
            qs = qs.filter(direction=p["dir"])
        if p.get("known") == "0":
            qs = qs.filter(student__isnull=True, parent__isnull=True, contract__isnull=True)
        if d := _date(p.get("from")):
            qs = qs.filter(created_at__gte=datetime.datetime.combine(d, datetime.time.min, local))
        if d := _date(p.get("to")):
            qs = qs.filter(created_at__lt=datetime.datetime.combine(d + datetime.timedelta(days=1), datetime.time.min, local))
        if p.get("contract"):
            qs = qs.filter(contract_id=p["contract"])
        if p.get("month"):
            qs = qs.filter(month=_month(p["month"]))
        if q := (p.get("q") or "").strip():
            digits = "".join(c for c in q if c.isdigit())
            cond = (Q(contract__student__first_name__icontains=q) | Q(contract__student__last_name__icontains=q)
                    | Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q) | Q(text__icontains=q))
            if digits:
                cond |= Q(phone__contains=digits[-9:])
            qs = qs.filter(cond)
        return qs

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        sms.rematch(page)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=False, methods=["post"])
    def dues(self, request):
        """{contracts: [id], month: YYYY-MM, text, template, skip_sent: true, preview: false} — to'lov eslatmasi."""
        d = request.data
        ids = d.get("contracts") or []
        if not isinstance(ids, list) or not ids:
            raise serializers.ValidationError({"contracts": ["Talaba tanlanmagan"]})
        month = _month(d.get("month"))
        if d.get("preview"):
            return Response(sms.preview_dues(request.user, ids, month, d.get("text")))
        tpl = SmsTemplate.objects.filter(pk=d["template"], is_deleted=False).first() if d.get("template") else None
        res = sms.queue_dues(request.user, ids, month, d.get("text"), template=tpl, skip_sent=d.get("skip_sent", True) is not False)
        return Response(res, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        return Response(self.get_serializer(sms.retry(request.user, self.get_object())).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(self.get_serializer(sms.cancel(request.user, self.get_object())).data)

    @action(detail=False, methods=["post"], url_path="cancel-all")
    def cancel_all(self, request):
        """Navbatdagi barcha SMS'ni bekor qilish (masalan, xato qolip bilan yuborilgan bo'lsa)."""
        return Response({"cancelled": sms.cancel_queued(request.user, super().get_queryset())})

    @action(detail=False)
    def summary(self, request):
        """Statistika (davr filtri bilan) + navbatda SMS kutayotgan telefonlar."""
        qs = self.get_queryset()
        devices = CallDevice.objects.filter(pk__in=qs.filter(status=SmsMessage.State.QUEUED).values("device"))
        return Response({**sms.stats(qs), "waiting_devices": [{"name": x.name, "last_seen_at": x.last_seen_at} for x in devices]})

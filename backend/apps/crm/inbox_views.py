"""Kiruvchi lidlar API (Instagram/Facebook/sayt): faqat Admin, Bosh menejer va Administrator+Hisobchi."""

import hmac

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from apps.calls.services import normalize
from apps.core.pagination import Pagination

from . import inbox
from .models import InboxLead, Lead


class InboxPermission(BasePermission):
    message = "Bu bo'lim faqat Bosh menejer va Administrator+Hisobchi uchun"

    def has_permission(self, request, view):
        return inbox.allowed(request.user)


class InboxSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    notes = serializers.SerializerMethodField()
    known = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = InboxLead
        fields = ["id", "kind", "name", "phone", "course_name", "info", "received_at", "status", "status_label", "callback_at", "lead", "lead_name", "notes", "known"]

    def get_notes(self, o):
        return [{"id": str(n.pk), "comment": n.comment, "by": str(n.created_by) if n.created_by else "", "at": n.created_at} for n in o.notes.all()]

    def get_known(self, o):
        return (self.context.get("known") or {}).get(o.phone)

    def get_lead_name(self, o):
        return o.lead.student.full_name if o.lead_id else ""


class InboxLeadViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [InboxPermission]
    serializer_class = InboxSerializer
    pagination_class = Pagination

    def get_queryset(self):
        return InboxLead.objects.select_related("lead__student", "branch").prefetch_related("notes__created_by")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["known"] = getattr(self, "_known", {})
        return ctx

    def list(self, request, *args, **kwargs):
        p, qs = request.query_params, self.get_queryset()
        st = p.get("status") or "open"
        if st == "open":
            qs = qs.filter(status__in=[InboxLead.Status.NEW, InboxLead.Status.CALLBACK])
        elif st != "all":
            qs = qs.filter(status=st)
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        for word in str(p.get("search", "")).split():
            qs = qs.filter(Q(name__icontains=word) | Q(phone__contains=word) | Q(course_name__icontains=word))
        qs = qs.order_by("callback_at", "-received_at") if st == InboxLead.Status.CALLBACK else qs.order_by("-received_at")
        page = self.paginate_queryset(qs)
        self._known = inbox.known_map({o.phone for o in page})
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(inbox.summary())

    @action(detail=False, methods=["get"])
    def due(self, request):
        """Bosh sahifa: yangilar va qayta aloqa vaqti kelganlar (oxirgi 30 tasi)."""
        now = timezone.now()
        qs = self.get_queryset()
        due = list(qs.filter(status=InboxLead.Status.CALLBACK, callback_at__lte=now).order_by("callback_at")[:30])
        new = list(qs.filter(status=InboxLead.Status.NEW).order_by("-received_at")[:30])
        self._known = inbox.known_map({o.phone for o in due + new})
        ser = lambda rows: self.get_serializer(rows, many=True).data  # noqa: E731
        return Response({"summary": inbox.summary(now), "due": ser(due), "new": ser(new)})

    def _item_response(self, item):
        item = self.get_queryset().get(pk=item.pk)
        self._known = inbox.known_map({item.phone})
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def talk(self, request, pk=None):
        """{comment, callback_at} yoki {comment, close: true}."""
        item = self.get_object()
        at = None
        if request.data.get("callback_at"):
            f = serializers.DateTimeField()
            try:
                at = f.to_internal_value(request.data["callback_at"])
            except serializers.ValidationError:
                raise ValidationError({"callback_at": "Sana va vaqt noto'g'ri"}) from None
        inbox.talk(request.user, item, request.data.get("comment"), callback_at=at, close=bool(request.data.get("close")))
        return self._item_response(item)

    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        """{lead: <lid ID>} — haqiqiy lid yaratilgach (yoki bazadagi lidga) bog'laydi."""
        item = self.get_object()
        lead = Lead.objects.select_related("student").filter(pk=request.data.get("lead")).first()
        if not lead:
            raise ValidationError({"lead": "Lid topilmadi"})
        inbox.link(request.user, item, lead)
        return self._item_response(item)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        item = self.get_object()
        inbox.reopen(request.user, item)
        return self._item_response(item)


class SiteIngestView(APIView):
    """Saytdagi forma serveridan: POST {name, phone, course, message} + sarlavha `X-Inbox-Key` (deploy/.env: INBOX_SITE_KEY)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        key = settings.INBOX_SITE_KEY
        if not key or not hmac.compare_digest(str(request.headers.get("X-Inbox-Key", "")), key):
            return Response({"detail": "Kalit noto'g'ri"}, status=http.HTTP_403_FORBIDDEN)
        phone = normalize(str(request.data.get("phone", "")))
        if not phone:
            return Response({"phone": ["Telefon 9 raqamdan iborat bo'lsin"]}, status=http.HTTP_400_BAD_REQUEST)
        item, created = inbox.add(InboxLead.Kind.SITE, phone=phone, name=str(request.data.get("name", "")), course_name=str(request.data.get("course", "")),
                                  info=str(request.data.get("message", "")))
        return Response({"ok": True, "created": created}, status=http.HTTP_201_CREATED if created else http.HTTP_200_OK)

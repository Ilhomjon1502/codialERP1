from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.permissions import is_top
from apps.core.viewsets import AuditedModelViewSet

from . import services
from .models import StaffTask

S = StaffTask.Status


class StaffTaskSerializer(serializers.ModelSerializer):
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True)
    giver = serializers.UUIDField(source="created_by_id", read_only=True)
    giver_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")
    overdue = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_done = serializers.SerializerMethodField()

    class Meta:
        model = StaffTask
        fields = ["id", "title", "description", "assignee", "assignee_name", "giver", "giver_name", "due_at", "status",
                  "remind_assignee", "remind_giver", "remind_before", "remind_every", "done_at", "done_comment",
                  "cancelled_at", "cancel_reason", "overdue", "can_edit", "can_done", "created_at"]
        read_only_fields = ["status", "done_at", "done_comment", "cancelled_at", "cancel_reason", "created_at"]

    def _user(self):
        return self.context["request"].user

    def get_overdue(self, t):
        return t.status == S.OPEN and t.due_at < timezone.now()

    def get_can_edit(self, t):
        return t.status == S.OPEN and services.is_giver(t, self._user())

    def get_can_done(self, t):
        u = self._user()
        return t.status == S.OPEN and (t.assignee_id == u.pk or is_top(u))


class StaffTaskViewSet(AuditedModelViewSet):
    """Topshiriqlar: ?box=in (menga) | out (men bergan) | all (Admin, BM); ?status=Ochiq|Bajarildi|Bekor qilindi; ?q=qidiruv."""

    section = "staffTasks"
    queryset = StaffTask.objects.select_related("assignee", "created_by")
    serializer_class = StaffTaskSerializer
    action_ops = {"done": "v", "cancel": "v", "summary": "v", "people": "v"}

    def get_queryset(self):
        u = self.request.user
        qs = services.scope(super().get_queryset(), u)
        if self.action != "list":
            return qs
        p = self.request.query_params
        box = p.get("box") or "in"
        if box == "in":
            qs = qs.filter(assignee=u)
        elif box == "out":
            qs = qs.filter(created_by=u)
        status = p.get("status") or S.OPEN
        qs = qs.filter(status=status)
        if p.get("q"):
            qs = qs.filter(Q(title__icontains=p["q"]) | Q(description__icontains=p["q"]))
        return qs.order_by("due_at") if status == S.OPEN else qs.order_by("-updated_at")[:200]

    def perform_create(self, serializer):
        serializer.instance = services.create(self.request.user, serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = services.update(self.request.user, serializer.instance, serializer.validated_data)

    def perform_destroy(self, instance):
        if not services.is_giver(instance, self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Topshiriqni faqat uni bergan xodim o'chiradi")
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def done(self, request, pk=None):
        t = services.complete(request.user, self.get_object(), request.data.get("comment", ""))
        return Response(self.get_serializer(t).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        t = services.cancel(request.user, self.get_object(), request.data.get("reason", ""))
        return Response(self.get_serializer(t).data)

    @action(detail=False)
    def summary(self, request):
        """Bosh sahifa va menyu uchun: menga berilgan ochiq / muddati o'tgan, men bergan ochiq."""
        u, now = request.user, timezone.now()
        mine = StaffTask.objects.filter(assignee=u, status=S.OPEN).aggregate(open=Count("id"), overdue=Count("id", filter=Q(due_at__lt=now)))
        given = StaffTask.objects.filter(created_by=u, status=S.OPEN).aggregate(open=Count("id"), overdue=Count("id", filter=Q(due_at__lt=now)))
        return Response({"in_open": mine["open"], "in_overdue": mine["overdue"], "out_open": given["open"], "out_overdue": given["overdue"]})

    @action(detail=False)
    def people(self, request):
        """Topshiriq berish mumkin bo'lgan xodimlar."""
        return Response([{"id": u.pk, "name": u.full_name, "role": u.role.code if u.role_id else ""}
                         for u in services.assignable(request.user).select_related("role").order_by("full_name")])

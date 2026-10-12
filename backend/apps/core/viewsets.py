"""Umumiy ViewSet: bo'lim ruxsati, filial doirasi, audit va soft delete."""

from django.db import transaction
from rest_framework import serializers, viewsets

from . import audit, services
from .permissions import SectionPermission
from .scoping import in_scope, scope_branch


class AuditedModelViewSet(viewsets.ModelViewSet):
    section = None
    permission_classes = [SectionPermission]
    branch_field = None  # masalan "branch" — filial doirasi bo'yicha filtrlanadi
    check_usage_on_delete = True
    pagination_class = None  # ma'lumotnomalar kichik; katta ro'yxatlar o'zida Pagination yoqadi
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.branch_field:
            qs = scope_branch(qs, self.request.user, self.branch_field)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        obj = serializer.save(created_by=user, updated_by=user)
        audit.log_create(user, obj)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        before = audit.snapshot(serializer.instance)
        obj = serializer.save(updated_by=user)
        audit.log_update(user, obj, before)

    def perform_destroy(self, instance):
        services.soft_delete(instance, self.request.user, check_usage=self.check_usage_on_delete)


class BranchScopedSerializerMixin:
    """`branch` maydoni foydalanuvchi filiallaridan bo'lishi shart; yaratilgandan keyin o'zgarmaydi."""

    def validate_branch(self, branch):
        user = self.context["request"].user
        if not in_scope(user, branch.pk):
            raise serializers.ValidationError("Bu filial sizning doirangizda emas")
        if self.instance is not None and self.instance.branch_id != branch.pk:
            raise serializers.ValidationError("Filialni o'zgartirib bo'lmaydi")
        return branch

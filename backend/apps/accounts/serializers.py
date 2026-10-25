"""Maydon nomlari front-end (ma'qullangan prototip) bilan bir xil: role — kod, status — Faol / Ishdan ketgan."""

import re

from rest_framework import serializers

from apps.core.permissions import is_top, perms_of, role_code
from apps.core.roles import TOP_ROLES, RoleCode
from apps.core.scoping import branch_ids
from apps.references.models import Branch

from .models import TEAMS, Role, User


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SlugRelatedField(slug_field="code", queryset=Role.objects.all())
    branches = serializers.PrimaryKeyRelatedField(many=True, queryset=Branch.objects.all(), required=False)
    status = serializers.ChoiceField(source="employment_status", choices=User.Employment.choices, required=False)
    teams = serializers.ListField(child=serializers.ChoiceField(choices=TEAMS), required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "role", "branches", "phone", "email", "teams", "status", "has_password", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_has_password(self, u):
        return u.has_usable_password()

    def validate_full_name(self, v):
        v = " ".join(v.split())
        if User.objects.filter(full_name__iexact=v).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Avval kiritilgan ism! Boshqa nom bering")
        return v

    def validate_email(self, v):
        v = (v or "").strip().lower() or None
        if v and User.objects.filter(email__iexact=v).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("Avval kiritilgan pochta!")
        return v

    def validate_phone(self, v):
        if v and not re.fullmatch(r"\d{9}", v):
            raise serializers.ValidationError("9 sondan iborat bo'lsin. Namuna: 998883322")
        return v

    def validate(self, attrs):
        actor = self.context["request"].user
        role = attrs.get("role") or getattr(self.instance, "role", None)
        assignable = set(actor.role.can_assign.values_list("code", flat=True)) if actor.role_id else set()
        if "role" in attrs and attrs["role"].code not in assignable:
            raise serializers.ValidationError({"role": "Bu rolni tayinlash huquqingiz yo'q"})
        if self.instance is not None and self.instance != actor:
            scope = branch_ids(actor)
            other_branch = scope is not None and not (set(self.instance.branches.values_list("id", flat=True)) & scope)
            if (self.instance.role and self.instance.role.code not in assignable) or other_branch:
                raise serializers.ValidationError({"detail": "Bu xodimni tahrirlash huquqingiz yo'q"})
        if role and role.code in TOP_ROLES:
            attrs["branches"] = []
        elif "branches" in attrs or self.instance is None:
            branches = attrs.get("branches") or []
            if not branches:
                raise serializers.ValidationError({"branches": "Kamida bitta filial tanlang"})
            scope = branch_ids(actor)
            if scope is not None and any(b.pk not in scope for b in branches):
                raise serializers.ValidationError({"branches": "Bu filial sizning doirangizda emas"})
        email = attrs.get("email", getattr(self.instance, "email", None))
        if role and role.code == RoleCode.BOSHQA:
            attrs["email"] = None
        elif role and role.code == RoleCode.ASOSCHI:
            pass  # asoschi tizimga kirmasligi mumkin: faqat botdan hisobot oladi — pochta ixtiyoriy
        elif not email:
            raise serializers.ValidationError({"email": "Majburiy maydon"})
        return attrs


class RoleSerializer(serializers.ModelSerializer):
    perms = serializers.SerializerMethodField()
    can_assign = serializers.SlugRelatedField(slug_field="code", many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["code", "name", "perms", "can_assign"]

    def get_perms(self, r):
        return {p.section: p.ops for p in r.permissions.all()}


def me_payload(user):
    return {
        "id": str(user.pk),
        "full_name": user.full_name,
        "email": user.email,
        "role": role_code(user),
        "branches": [str(b) for b in user.branches.values_list("id", flat=True)],
        "perms": perms_of(user),
        "is_top": is_top(user),
    }

"""Bo'lim ruxsatlari (rol matritsasi) va tahrirlash muddatlari. Har bir ViewSet `section` ni e'lon qiladi."""

import datetime

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .roles import TOP_ROLES, VIEW_ALL_ROLES, edit_days, edit_rule_text

NO_PERMISSION = "Sizning rolingizda bu amalga ruxsat yo'q"
METHOD_OPS = {"GET": "v", "HEAD": "v", "OPTIONS": "v", "POST": "a", "PUT": "e", "PATCH": "e", "DELETE": "d"}


def role_code(user):
    return getattr(getattr(user, "role", None), "code", None)


def perms_of(user):
    """{bo'lim: 'vaed'} — so'rov davomida bir marta o'qiladi."""
    if not user or not user.is_authenticated or not user.role_id:
        return {}
    cache = getattr(user, "_perms_cache", None)
    if cache is None:
        from apps.accounts.models import RolePermission

        cache = dict(RolePermission.objects.filter(role_id=user.role_id).values_list("section", "ops"))
        user._perms_cache = cache
    return cache


def can(user, section, op="v"):
    return bool(section) and op in perms_of(user).get(section, "")


def is_top(user):
    return role_code(user) in TOP_ROLES


def sees_all(user):
    """Hamma filial va hamma yozuvni ko'rish (Admin, Bosh menejer, asoschi). Tahrirlash va tasdiqlash huquqi buni bermaydi — u `is_top` va ruxsat matritsasida."""
    return role_code(user) in VIEW_ALL_ROLES


class SectionPermission(BasePermission):
    """GET → v, POST → a, PUT/PATCH → e, DELETE → d. Maxsus amallar: view.action_ops = {'approve': 'p'}."""

    message = NO_PERMISSION

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        op = getattr(view, "action_ops", {}).get(getattr(view, "action", None)) or METHOD_OPS.get(request.method, "v")
        return can(request.user, getattr(view, "section", None), op)


def today():
    return timezone.localdate()


def check_edit_window(user, section, record_date, op="e"):
    """Yozuv sanasidan beri o'tgan kun rol muddatidan oshsa — PermissionDenied (sababi bilan)."""
    if not can(user, section, op):
        raise PermissionDenied(NO_PERMISSION)
    days = edit_days(role_code(user), section)
    if days is None:
        return
    if isinstance(record_date, datetime.datetime):
        record_date = timezone.localtime(record_date).date()
    if days < 0 or (today() - record_date).days > days:
        raise PermissionDenied(f"Tahrirlash muddati o'tgan ({edit_rule_text(days)})")

"""Audit: har bir yaratish, o'zgartirish va o'chirish — kim, qachon, nima, eski → yangi qiymat (CLAUDE.md 6.4)."""

import datetime
import decimal
import uuid

from django.db import models

from .models import AuditLog


def _plain(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (decimal.Decimal,)):
        return int(v) if v == v.to_integral_value() else str(v)
    if isinstance(v, (datetime.date, datetime.time, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (list, tuple, set)):
        return sorted((_plain(x) for x in v), key=str)
    if isinstance(v, models.Model):
        return str(v)
    return str(v)


SKIP = {"id", "created_at", "created_by", "updated_at", "updated_by", "is_deleted", "deleted_at", "deleted_by", "password", "last_login"}


def snapshot(obj):
    """Yozuvning audit uchun ko'rinishi: oddiy maydonlar va M2M (nomlari bilan)."""
    data = {}
    for f in obj._meta.concrete_fields:
        if f.name in SKIP:
            continue
        if f.is_relation:
            rel = getattr(obj, f.name, None)
            data[f.name] = str(rel) if rel is not None else None
        else:
            data[f.name] = _plain(getattr(obj, f.attname))
    if obj.pk:
        for f in obj._meta.many_to_many:
            data[f.name] = sorted(str(x) for x in getattr(obj, f.name).all())
    return data


def diff(before, after):
    keys = sorted(set(before) | set(after))
    return [[k, before.get(k), after.get(k)] for k in keys if before.get(k) != after.get(k)]


def label(obj):
    return str(obj._meta.verbose_name).capitalize()


def record(user, action, model, obj_id="", obj_repr="", changes=None, detail=""):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        model=str(model)[:64],
        object_id=str(obj_id or "")[:64],
        object_repr=str(obj_repr or "")[:255],
        changes=changes or [],
        detail=detail or "",
    )


def log_create(user, obj, detail=""):
    return record(user, AuditLog.Action.CREATE, label(obj), obj.pk, obj, diff({}, snapshot(obj)), detail)


def log_update(user, obj, before, detail=""):
    changes = diff(before, snapshot(obj))
    if not changes and not detail:
        return None
    return record(user, AuditLog.Action.UPDATE, label(obj), obj.pk, obj, changes, detail)


def log_delete(user, obj, detail="Soft delete (yozuv bazada qoladi)"):
    return record(user, AuditLog.Action.DELETE, label(obj), obj.pk, obj, [], detail)

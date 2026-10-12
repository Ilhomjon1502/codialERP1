"""Umumiy servislar: soft delete (ishlatilgan ma'lumotnomani o'chirmaslik bilan)."""

from django.db import transaction
from django.utils import timezone

from . import audit
from .exceptions import Conflict


def usage(obj):
    """Yozuvga bog'langan (o'chirilmagan) yozuvlar: [(nomi, soni)]. Masalan [('guruh', 2), ('lid', 23)]."""
    out = []
    for rel in obj._meta.related_objects:
        accessor = rel.get_accessor_name()
        if not accessor:
            continue
        if rel.one_to_one:
            if getattr(obj, accessor, None) is not None:
                out.append((str(rel.related_model._meta.verbose_name).lower(), 1))
            continue
        n = getattr(obj, accessor).count()
        if n:
            out.append((str(rel.related_model._meta.verbose_name).lower(), n))
    return out


def usage_text(obj):
    return ", ".join(f"{n} ta {name}" for name, n in usage(obj))


@transaction.atomic
def soft_delete(obj, user, check_usage=True):
    """Ishlatilgan ma'lumotnoma yozuvi o'chirilmaydi, faqat nofaol qilinadi (CLAUDE.md 6.4)."""
    if check_usage:
        used = usage_text(obj)
        if used:
            raise Conflict(f"«{obj}» ishlatilgan ({used}). O'chirib bo'lmaydi — tahrirlab, Nofaol qiling")
    obj.is_deleted = True
    obj.deleted_at = timezone.now()
    obj.deleted_by = user
    obj.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
    audit.log_delete(user, obj)
    return obj

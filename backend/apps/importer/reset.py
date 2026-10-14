"""M11: demo ma'lumotlarni tozalab, haqiqiy ish uchun toza baza (buyurtmachi qarori 2026-10-14, docs/decisions.md).

Saqlanadi: rollar va ruxsatlar matritsasi, davomat statuslari, bitta filial (Emirat), ko'rsatilgan xodimlar akkaunti
(paroli va Telegram bog'lanishi bilan). Qolgan hammasi — demo xodimlar, ma'lumotnomalar, lidlar, shartnomalar, davomat,
pul, oyliklar, Telegram navbati, AI jurnali, audit, sessiyalar — butunlay o'chiriladi.

Sinov rejimi (standart) — nima o'chishini sanab, tranzaksiyani bekor qiladi."""

import collections

from django.apps import apps
from django.contrib.sessions.models import Session
from django.db import connection, transaction

from apps.accounts.models import Role, RolePermission, User
from apps.notifications.models import TelegramLink
from apps.references.models import AttendanceStatus, Branch

APPS = ["core", "accounts", "references", "crm", "education", "finance", "payroll", "notifications", "ai_assistant"]
KEEP = {Role, RolePermission, AttendanceStatus, Branch, User, TelegramLink}
USER_FKS = ("created_by", "updated_by", "deleted_by")


class Rollback(Exception):
    pass


def _raw(qs):
    """Bevosita DELETE (soft delete va PROTECT'siz). Tashqi kalitlar tranzaksiya oxirida tekshiriladi."""
    return qs._raw_delete(qs.db) or 0


def run(keep_emails, branch_name="Emirat", commit=False):
    keep_emails = [e.strip().lower() for e in keep_emails if e.strip()]
    if not keep_emails:
        raise ValueError("Saqlanadigan kamida bitta xodim pochtasi kerak (--keep)")
    counts = collections.Counter()
    try:
        with transaction.atomic():
            keep_users = list(User.objects.filter(email__in=keep_emails))
            missing = set(keep_emails) - {u.email.lower() for u in keep_users}
            if missing:
                raise ValueError(f"Bunday xodim topilmadi: {', '.join(sorted(missing))}")
            keep_ids = [u.pk for u in keep_users]
            branch = Branch.all_objects.filter(name=branch_name, is_deleted=False).first() or Branch.objects.create(name=branch_name)

            # 1. Ko'pga-ko'p jadvallar (o'chiriladigan modellarniki)
            models = [m for label in APPS for m in apps.get_app_config(label).get_models() if m not in KEEP]
            for m in models:
                for f in m._meta.many_to_many:
                    counts[f"{m._meta.verbose_name_plural} ↔ {f.verbose_name}"] += _raw(f.remote_field.through.objects.all())
            # 2. Asosiy jadvallar
            for m in models:
                qs = m.all_objects.all() if hasattr(m, "all_objects") else m._default_manager.all()
                counts[str(m._meta.verbose_name_plural)] += _raw(qs)
            # 3. Filial: faqat Emirat qoladi, g'azna bog'lanishlari tozalanadi
            Branch.all_objects.filter(pk=branch.pk).update(default_cashbox=None, noncash_cashbox=None, status="Faol", is_deleted=False)
            other_branches = Branch.all_objects.exclude(pk=branch.pk)
            User.branches.through.objects.filter(branch__in=other_branches).delete()
            counts["Boshqa filiallar"] += _raw(other_branches)
            # 4. Xodimlar: faqat saqlanadiganlar
            gone = User.objects.exclude(pk__in=keep_ids)
            for f in User._meta.many_to_many:
                _raw(f.remote_field.through.objects.filter(user__in=gone))
            counts["Telegram bog'lanishlari"] += _raw(TelegramLink.objects.exclude(user_id__in=keep_ids))
            counts["Xodimlar (demo)"] += _raw(gone)
            for u in keep_users:
                u.branches.set([branch])
            # 5. Saqlangan yozuvlarda o'chgan xodimlarga havolalar
            for m in (Role, Branch, User):
                fields = [f for f in USER_FKS if any(x.name == f for x in m._meta.fields)]
                if fields:
                    m._base_manager.update(**{f: None for f in fields})
            counts["Sessiyalar (hamma qayta kiradi)"] += _raw(Session.objects.all())
            connection.check_constraints()  # tashqi kalitlar butunligi — hozir tekshirilsin
            if not commit:
                raise Rollback
    except Rollback:
        pass
    return {k: v for k, v in counts.items() if v}

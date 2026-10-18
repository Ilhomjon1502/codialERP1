"""Yangi rol «Marketolog» (2026-10-18): lidlarga javobgar; qo'shimcha ruxsatni Bosh menejer yoki Filial menejeri Sozlamalarda beradi."""

from django.db import migrations

from apps.core.roles import DEFAULT_PERMISSIONS, RoleCode

CODE = RoleCode.MARKETOLOG.value


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    role, _ = Role.objects.get_or_create(code=CODE, defaults={"name": RoleCode.MARKETOLOG.label, "sort": 9})
    for sec, ops in DEFAULT_PERMISSIONS[CODE].items():
        perm, created = Perm.objects.get_or_create(role=role, section=sec, defaults={"ops": ops})
        if not created and not perm.ops and ops and sec == "staffTasks":  # 0007 ruxsatlarni bo'sh qoldirgan bo'lishi mumkin
            perm.ops = ops
            perm.save(update_fields=["ops"])
    for code in ("ADMIN", "BOSH_MENEJER", "FILIAL_MENEJERI"):
        holder = Role.objects.filter(code=code).first()
        if holder:
            holder.can_assign.add(role)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_staff_tasks_section")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

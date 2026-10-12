"""Rollar, boshlang'ich ruxsatlar matritsasi va RolePower (CLAUDE.md 6.1–6.2). Qayta ishga tushirilsa mavjudlarini o'zgartirmaydi."""

from django.db import migrations

from apps.core.roles import DEFAULT_PERMISSIONS, DEFAULT_ROLE_POWER, RoleCode


def seed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")
    roles = {}
    for i, (code, name) in enumerate(RoleCode.choices):
        role, created = Role.objects.get_or_create(code=code, defaults={"name": name, "sort": i})
        roles[code] = role
        if created:
            RolePermission.objects.bulk_create(
                RolePermission(role=role, section=sec, ops=ops) for sec, ops in DEFAULT_PERMISSIONS[code].items()
            )
    for code, targets in DEFAULT_ROLE_POWER.items():
        if not roles[code].can_assign.exists():
            roles[code].can_assign.set([roles[t] for t in targets])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]

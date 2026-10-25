"""Asoschi hamma bo'limni ko'radi (2026-10-25, buyurtmachi aniqlashtirishi): hamma bo'limda «ko'rish» ruxsati (tahrirlash va tasdiqlash yo'q)."""

from django.db import migrations

from apps.core.roles import SECTION_KEYS


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    role = Role.objects.filter(code="ASOSCHI").first()
    if role:
        for sec in SECTION_KEYS:
            Perm.objects.update_or_create(role=role, section=sec, defaults={"ops": "v"})


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_founder_role")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

"""Yangi bo'lim «Telegram bot (mijozlar)» (2026-10-24): o'quvchi/vasiy boti — ulanganlar, manba javoblari, tavsiyalar, sozlamalar."""

from django.db import migrations

OPS = {"ADMIN": "vaed", "BOSH_MENEJER": "vaed", "FILIAL_MENEJERI": "ve", "ADMINISTRATOR": "ve", "ADMINISTRATOR_HISOBCHI": "ve", "MARKETOLOG": "v"}


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    for role in Role.objects.all():
        Perm.objects.update_or_create(role=role, section="clientbot", defaults={"ops": OPS.get(role.code, "")})


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="clientbot").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_sms_section")]
    operations = [migrations.RunPython(forwards, backwards)]

"""Yangi bo'lim «Qo'ng'iroqlar» (2026-10-19): administratorlar telefonidagi qo'ng'iroqlar. Qurilma qo'shish — Admin, BM."""

from django.db import migrations

OPS = {"ADMIN": "vaed", "BOSH_MENEJER": "vaed", "FILIAL_MENEJERI": "ve", "ADMINISTRATOR": "ve", "ADMINISTRATOR_HISOBCHI": "ve",
       "MARKETOLOG": "v"}


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    for role in Role.objects.all():
        Perm.objects.update_or_create(role=role, section="calls", defaults={"ops": OPS.get(role.code, "")})


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="calls").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_alter_role_code")]
    operations = [migrations.RunPython(forwards, backwards)]

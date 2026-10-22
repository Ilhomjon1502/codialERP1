"""Yangi bo'lim «SMS» (2026-10-22): qabul telefoni orqali to'lov eslatmasi, qoliplar. Qoliplar va yuborish — administratorlar."""

from django.db import migrations

OPS = {"ADMIN": "vaed", "BOSH_MENEJER": "vaed", "FILIAL_MENEJERI": "vaed", "ADMINISTRATOR": "vae", "ADMINISTRATOR_HISOBCHI": "vae",
       "HISOBCHI": "v"}


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    for role in Role.objects.all():
        Perm.objects.update_or_create(role=role, section="sms", defaults={"ops": OPS.get(role.code, "")})


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="sms").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0010_calls_section")]
    operations = [migrations.RunPython(forwards, backwards)]

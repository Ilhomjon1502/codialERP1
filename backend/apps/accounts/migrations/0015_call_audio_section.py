"""Yangi bo'lim «Suhbat yozuvlarini eshitish» (2026-11-18): Admin, Bosh menejer va asoschi eshitadi; boshqa rolga Bosh menejer beradi."""

from django.db import migrations

OPS = {"ADMIN": "v", "BOSH_MENEJER": "v", "ASOSCHI": "v"}


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    for role in Role.objects.all():
        Perm.objects.update_or_create(role=role, section="call_audio", defaults={"ops": OPS.get(role.code, "")})


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="call_audio").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0014_founder_views_all")]
    operations = [migrations.RunPython(forwards, backwards)]

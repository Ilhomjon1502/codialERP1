"""Yangi bo'lim «Topshiriqlar» (2026-10-16): barcha rollarga ruxsat (Boshqa — yo'q). Admin, BM, FM — o'chirish ham."""

from django.db import migrations

OPS = {"ADMIN": "vaed", "BOSH_MENEJER": "vaed", "FILIAL_MENEJERI": "vaed", "ADMINISTRATOR": "vae", "ADMINISTRATOR_HISOBCHI": "vae",
       "HISOBCHI": "vae", "USTOZ": "vae", "YORDAMCHI": "vae", "USTOZ_YORDAMCHI": "vae"}


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    for role in Role.objects.all():
        Perm.objects.update_or_create(role=role, section="staffTasks", defaults={"ops": OPS.get(role.code, "")})


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="staffTasks").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_remove_grading_section")]
    operations = [migrations.RunPython(forwards, backwards)]

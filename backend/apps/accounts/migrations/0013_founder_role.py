"""Yangi rol «Asoschi» (2026-10-25): tizimda hech qanday bo'lim ko'rmaydi, faqat Telegram botdan qisqa kunlik hisobot oladi (bo'lim `founderReport`).
Rolni faqat Admin tayinlaydi."""

from django.db import migrations, models

from apps.core.roles import RoleCode

CODE = RoleCode.ASOSCHI.value


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    role, _ = Role.objects.get_or_create(code=CODE, defaults={"name": RoleCode.ASOSCHI.label, "sort": 11})
    for r in Role.objects.all():
        Perm.objects.update_or_create(role=r, section="founderReport", defaults={"ops": "v" if r.code == CODE else ""})
    admin = Role.objects.filter(code="ADMIN").first()
    if admin:
        admin.can_assign.add(role)


def backwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="founderReport").delete()
    apps.get_model("accounts", "Role").objects.filter(code=CODE).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0012_clientbot_section")]
    operations = [
        migrations.AlterField("role", "code", models.CharField(max_length=32, unique=True, choices=RoleCode.choices)),
        migrations.RunPython(forwards, backwards),
    ]

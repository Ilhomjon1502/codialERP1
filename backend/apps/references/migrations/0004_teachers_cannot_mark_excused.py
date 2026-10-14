"""Buyurtmachi qarori (2026-10-14): ustoz davomatda faqat «Keldi» yoki «Besabab» qo'yadi, «Sababli» — yo'q.
Sababli belgisini administratorlar va menejerlar qo'yadi (yoki ustoz «Darsni yetkazdim» so'rovi tasdiqlanganda tizim o'zi)."""

from django.db import migrations

TEACHERS = ["USTOZ", "USTOZ_YORDAMCHI", "YORDAMCHI"]


def forwards(apps, schema_editor):
    Status = apps.get_model("references", "AttendanceStatus")
    Role = apps.get_model("accounts", "Role")
    s = Status.objects.filter(code="0").first()
    if s:
        s.roles.remove(*Role.objects.filter(code__in=TEACHERS))


def backwards(apps, schema_editor):
    Status = apps.get_model("references", "AttendanceStatus")
    Role = apps.get_model("accounts", "Role")
    s = Status.objects.filter(code="0").first()
    if s:
        s.roles.add(*Role.objects.filter(code__in=["USTOZ", "USTOZ_YORDAMCHI"]))


class Migration(migrations.Migration):
    dependencies = [("references", "0003_remove_discounttype_is_discount50"), ("accounts", "0006_remove_grading_section")]
    operations = [migrations.RunPython(forwards, backwards)]

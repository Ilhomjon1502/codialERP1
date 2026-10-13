"""«Baholash bo'limi» (ustoz → talaba) olib tashlandi (buyurtmachi qarori 2026-10-13) — eski ruxsat yozuvlari o'chiriladi."""

from django.db import migrations


def forwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="grading").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_remove_tasks_section")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

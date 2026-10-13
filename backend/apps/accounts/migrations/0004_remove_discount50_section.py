"""«50% chegirmalar» bo'limi olib tashlandi (buyurtmachi qarori 2026-10-13) — eski ruxsat yozuvlari o'chiriladi."""

from django.db import migrations


def forwards(apps, schema_editor):
    apps.get_model("accounts", "RolePermission").objects.filter(section="discount50").delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_seed_roles")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

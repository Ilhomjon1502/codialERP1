"""Buyurtmachi qarori (2026-10-19): Administrator+Hisobchi davomatni to'liq tahrirlaydi — «Nofaol (–)» statusini ham qo'ya oladi."""

from django.db import migrations


def forwards(apps, schema_editor):
    Status = apps.get_model("references", "AttendanceStatus")
    Role = apps.get_model("accounts", "Role")
    s = Status.objects.filter(code="-").first()
    r = Role.objects.filter(code="ADMINISTRATOR_HISOBCHI").first()
    if s and r:
        s.roles.add(r)


class Migration(migrations.Migration):
    dependencies = [("references", "0005_branch_payment_due_day"), ("accounts", "0010_calls_section")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

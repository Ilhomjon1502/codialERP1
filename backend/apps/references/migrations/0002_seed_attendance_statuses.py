"""Davomat statuslari va ularni qo'ya oladigan rollar (prototipdagidek). Nofaol (–) — faqat menejerlar."""

from django.db import migrations

ALL_MARKERS = ["ADMIN", "BOSH_MENEJER", "FILIAL_MENEJERI", "ADMINISTRATOR", "ADMINISTRATOR_HISOBCHI", "USTOZ", "USTOZ_YORDAMCHI"]
STATUSES = [
    ("1", "Keldi", ALL_MARKERS),
    ("0", "Sababli", ALL_MARKERS),
    ("X", "Besabab", ALL_MARKERS),
    ("-", "Nofaol", ["ADMIN", "BOSH_MENEJER", "FILIAL_MENEJERI"]),
]


def seed(apps, schema_editor):
    AttendanceStatus = apps.get_model("references", "AttendanceStatus")
    Role = apps.get_model("accounts", "Role")
    for i, (code, name, roles) in enumerate(STATUSES):
        st, created = AttendanceStatus.objects.get_or_create(code=code, defaults={"name": name, "sort": i})
        if created:
            st.roles.set(Role.objects.filter(code__in=roles))


class Migration(migrations.Migration):
    dependencies = [("references", "0001_initial"), ("accounts", "0003_seed_roles")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]

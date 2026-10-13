"""«Baholash bo'limi» (ustoz → talaba) olib tashlandi (buyurtmachi qarori 2026-10-13)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("education", "0002_gradingsession_parentcall_studentgrade_and_more")]
    operations = [
        migrations.DeleteModel(name="StudentGrade"),
        migrations.DeleteModel(name="GradingSession"),
    ]

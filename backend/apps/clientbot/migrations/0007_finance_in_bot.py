"""To'lov va balans ma'lumotlari botda vaqtincha o'chiq (buyurtmachi qarori 2026-10-24): `notify_payments` → `finance_in_bot`, standart o'chiq."""

from django.db import migrations, models


def pause(apps, schema_editor):
    apps.get_model("clientbot", "BotConfig").objects.update(finance_in_bot=False)


class Migration(migrations.Migration):
    dependencies = [("clientbot", "0006_botconfig_notify_payments")]
    operations = [
        migrations.RenameField("botconfig", "notify_payments", "finance_in_bot"),
        migrations.AlterField(
            "botconfig", "finance_in_bot",
            models.BooleanField(default=False, verbose_name="To'lov va balans ma'lumotlari botda (to'lov xabari, kabinet, to'lov eslatmalari)"),
        ),
        migrations.RunPython(pause, migrations.RunPython.noop),
    ]

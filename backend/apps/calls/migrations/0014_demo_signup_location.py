"""Sinov darsi SMS'iga Codial lokatsiyasi (2026-11-25, buyurtmachi tanlagan matn). Faqat matn o'zgartirilmagan (avvalgi standart) qoidalar yangilanadi."""

from django.db import migrations

OLD = "{ism}, {kurs} sinov darsi {sana} ({hafta}) soat {vaqt} da. 10 daqiqa oldin keling. Kelolmasangiz 998204432 ga qo'ng'iroq qiling. Codial"
NEW = "{ism}, {kurs} sinov darsi {sana} ({hafta}) {vaqt} da. Kelolmasangiz: 998204432. Manzil: https://maps.app.goo.gl/Pt4LFgiEodV8o15Q8"


def forwards(apps, schema_editor):
    apps.get_model("calls", "SmsRule").objects.filter(key="demo_signup", text=OLD).update(text=NEW)


class Migration(migrations.Migration):
    dependencies = [("calls", "0013_demo_signup_sms")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]

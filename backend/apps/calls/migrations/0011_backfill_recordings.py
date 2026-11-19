"""Hozirgi qo'ng'iroqlarga biriktirilgan yozuvlar «Yozuvlar» jadvaliga ko'chiriladi (fayl nusxalanmaydi — bir faylga ishora)."""

import datetime

from django.db import migrations


def forward(apps, schema_editor):
    CallRecord = apps.get_model("calls", "CallRecord")
    CallRecording = apps.get_model("calls", "CallRecording")
    for c in CallRecord.objects.exclude(audio="").iterator():
        if CallRecording.objects.filter(call_id=c.pk).exists():
            continue
        ended = c.audio_at or c.started_at
        CallRecording.objects.create(
            device_id=c.device_id, branch_id=c.branch_id, file=c.audio.name, filename="", number=c.phone, direction=c.direction if c.direction in ("Kiruvchi", "Chiquvchi") else "",
            started_at=c.started_at, ended_at=ended, duration=c.audio_duration, size=c.audio_size, sig=c.audio_sig, call_id=c.pk)


def backward(apps, schema_editor):
    apps.get_model("calls", "CallRecording").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("calls", "0010_call_recording")]
    operations = [migrations.RunPython(forward, backward)]

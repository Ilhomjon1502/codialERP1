"""Suhbat yozuvi to'liq emas — xodimlarga darhol Telegram ogohlantirish (buyurtmachi so'rovi 2026-11-20).

Qabul telefonida yozuvni Shizuku orqali ShizuCallRecorder yozadi; Shizuku vaqti-vaqti bilan o'chib qoladi va suhbat o'rtasida yozuv uziladi
yoki fayl bo'sh chiqadi. Qizlar buni kech payqaydi — uzun suhbatlar yo'qoladi. Shuning uchun gaplashilgan qo'ng'iroqdan GRACE daqiqa o'tgach
yozuv bo'lmasa, yoki u suhbatdan sezilarli qisqa bo'lsa, Administrator, Administrator+Hisobchi va Bosh menejerga xabar boradi.
Telefon ilovasi (4.1 dan) Shizuku o'chganini o'zi ham xabar qiladi (`/calls/ping/?recorder=down`) — `recorder_down` shu zahoti ogohlantiradi.
`run_bot` har daqiqada `tick()` ni chaqiradi. Har qo'ng'iroq haqida bir marta (`CallRecord.rec_alert_at`); xabarlar orasida kamida COOLDOWN.
"""

import datetime
from html import escape

from django.db.models import Max, Q
from django.utils import timezone

from apps.core.models import Status

from .models import CallDevice, CallRecord

MIN_TALK = 15                                  # shundan qisqa suhbat — e'tiborga olinmaydi
GRACE = datetime.timedelta(minutes=5)          # suhbat tugagach telefon yozuvni yuklab bo'lishi uchun
WINDOW = datetime.timedelta(hours=3)           # eskirgan qo'ng'iroqlar haqida xabar berilmaydi
COOLDOWN = datetime.timedelta(minutes=10)      # xabarlar orasida (ketma-ket xatolar bitta xabarga jamlanadi)
MAX_LINES = 8
DOWN_GRACE = datetime.timedelta(minutes=2)     # qisqa uzilish (qayta ishga tushirish) uchun xabar berilmaydi
ALIVE = datetime.timedelta(minutes=30)         # telefon shuncha vaqt jim bo'lsa holat eskirgan hisoblanadi
DAY_FROM, DAY_TO = 8, 20                       # «yozuvchi o'chgan» xabari faqat ish vaqtida


def shortfall(duration):
    """Yozuv suhbatdan shuncha soniyadan ortiq qisqa bo'lsa — to'liq emas (kiruvchida yozuv 1–2 soniya qisqa bo'ladi, bu normal)."""
    return max(8, round(duration * 0.15))


def _mmss(s):
    return f"{s // 60}:{s % 60:02d}"


def _who(c):
    name = c.student.full_name if c.student_id else (c.contact_name or "")
    return f"{name} (…{c.phone[-4:]})" if name else (f"…{c.phone[-4:]}" if c.phone else "yashirin raqam")


def bad_calls(now):
    """Yozuvi to'liq bo'lmagan, haqida hali xabar berilmagan gaplashilgan qo'ng'iroqlar: [(qo'ng'iroq, eng uzun yozuv soniyasi)]."""
    qs = (CallRecord.objects.filter(rec_alert_at__isnull=True, direction__in=(CallRecord.Direction.INCOMING, CallRecord.Direction.OUTGOING), duration__gte=MIN_TALK,
                                    started_at__gte=now - WINDOW, is_deleted=False)
          .annotate(best=Max("recordings__duration", filter=Q(recordings__is_deleted=False))).select_related("student").order_by("started_at"))
    out = []
    for c in qs:
        if c.started_at + datetime.timedelta(seconds=c.duration) + GRACE > now:
            continue  # telefon yozuvni yuklashga ulgurmagan bo'lishi mumkin
        best = c.best or 0
        if best + shortfall(c.duration) < c.duration:
            out.append((c, best))
    return out


def text(items):
    lines = ["⚠️ <b>Suhbat yozuvi to'liq emas</b>"]
    for c, best in items[:MAX_LINES]:
        t = timezone.localtime(c.started_at).strftime("%H:%M")
        rec = f"yozuv {_mmss(best)}" if best else "yozuv yo'q"
        lines.append(f"• {t} · {c.direction.lower()} · {_who(c)} — suhbat {_mmss(c.duration)}, {rec}")
    if len(items) > MAX_LINES:
        lines.append(f"… va yana {len(items) - MAX_LINES} ta")
    lines.append("")
    lines.append("🔈 Eng ko'p sabab: qo'ng'iroq paytida <b>karnay tugmasini bosish</b> (yoqish yoki o'chirish) — shunda yozuv uziladi. "
                 "Karnayni faqat qo'ng'iroq boshlanishidan oldin tanlang va gaplashish paytida tegmang.")
    lines.append("Agar karnayga tegilmagan bo'lsa: qabul telefonida <b>Shizuku</b> ilovasini oching — «Shizuku is running» yozuvi bo'lishi kerak. O'chgan bo'lsa — "
                 "«Start via Wireless debugging» (Simsiz nosozlikni tuzatish) orqali qayta ishga tushiring.")
    return "\n".join(lines)


def recorder_down(now):
    """Telefon «yozuvchi o'chdi» degan qurilmalar haqida (qo'ng'iroq yo'qolmasidan oldin) ish vaqtida har 30 daqiqada xabar beradi."""
    from apps.notifications import services as notif

    local = timezone.localtime(now)
    if not DAY_FROM <= local.hour < DAY_TO:
        return
    devices = CallDevice.objects.filter(status=Status.ACTIVE, is_deleted=False, recorder_down_at__lte=now - DOWN_GRACE,
                                        last_seen_at__gte=now - ALIVE).select_related("branch")
    for d in devices:
        since = timezone.localtime(d.recorder_down_at).strftime("%H:%M")
        msg = (f"🔴 <b>Yozuvchi o'chgan</b> — {escape(d.name)} ({since} dan). Hozir qo'ng'iroqlar <b>yozilmayapti</b>.\n\n"
               "Telefonda <b>Shizuku</b> ilovasini oching va «Start via Wireless debugging» (Simsiz nosozlikni tuzatish) orqali ishga tushiring. "
               "Wi-Fi yoqilgan bo'lishi kerak.")
        notif.notify("rec_problem", msg, branch=d.branch, force=True, key=f"recdown:{d.pk}:{local:%Y%m%d%H}:{local.minute // 30}")


def tick(now=None):
    """Yozuvi to'liq bo'lmagan qo'ng'iroqlar haqida xabar beradi. Qaytaradi: xabarga kirgan qo'ng'iroqlar soni."""
    from apps.notifications import services as notif
    from apps.notifications.models import Outbox

    now = now or timezone.now()
    recorder_down(now)
    if Outbox.objects.filter(event="rec_problem", key__startswith="recprob:", created_at__gte=now - COOLDOWN).exists():
        return 0
    items = bad_calls(now)
    if not items:
        return 0
    notif.notify("rec_problem", text(items), force=True, key=f"recprob:{now:%Y%m%d%H%M}")
    CallRecord.objects.filter(pk__in=[c.pk for c, _ in items]).update(rec_alert_at=now)
    return len(items)

"""Instagram/Facebook lidlari bilan gaplashilgan qo'ng'iroq audiolari — Telegram guruhiga (buyurtmachi so'rovi 2026-11-18).

Qabul telefonidagi suhbat yozuvi ERP'ga tushgach (`attach_recording`), agar shu raqam Instagram/Facebook lidlar navbatidagi (`crm.InboxLead`)
lidniki bo'lsa va lid qo'ng'iroqdan oldin tushgan bo'lsa, bot yozuvni `IG_CALLS_CHAT_ID` guruhiga yuboradi. Izohda: lid kimligi, kurs, shu lid bilan
nechanchi bog'lanish, lid tushgan sana va vaqt, qo'ng'iroq vaqti va davomiyligi. Faqat gaplashilgan (davomiyligi > 0) qo'ng'iroqlar; har yozuv bir marta.
`run_bot` har daqiqada `tick()` ni chaqiradi (yozuv Telegram'ga saytdan emas, bot jarayonidan ketadi — sayt kutib qolmaydi).
"""

import datetime
import logging
from html import escape

from django.conf import settings
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.crm.models import InboxLead
from apps.notifications import services as tg

from .models import CallRecord
from .rec_watch import shortfall

log = logging.getLogger(__name__)
KINDS = (InboxLead.Kind.INSTAGRAM, InboxLead.Kind.FACEBOOK)
SETTLE = datetime.timedelta(seconds=60)   # yozuv yuklangach biroz kutamiz (bitta qo'ng'iroqqa ikki fayl bo'lsa — uzunrog'i qoladi)
WINDOW = datetime.timedelta(days=2)       # shu muddatda mos lid topilmasa — qaytib urinmaymiz
MIN_BYTES = 1024                          # bundan kichik fayl — ovozsiz sarlavha
VOICE_EXT = (".ogg", ".opus", ".oga")


def _local(dt):
    return timezone.localtime(dt).strftime("%d.%m.%Y %H:%M")


def find_inbox(call):
    """Qo'ng'iroq raqamiga mos Instagram/Facebook lidi (qo'ng'iroqdan oldin tushgan, eng oxirgisi) yoki None."""
    if not call.phone:
        return None
    return (InboxLead.objects.filter(branch_id=call.branch_id, phone=call.phone, kind__in=KINDS, received_at__lte=call.started_at)
            .order_by("-received_at").first())


def contact_number(call, lead):
    """Lid tushgandan beri shu raqam bilan nechanchi bog'lanish (javobsiz urinishlar ham sanaladi; shu qo'ng'iroq oxirgi)."""
    return CallRecord.objects.filter(branch_id=call.branch_id, phone=call.phone, started_at__gte=lead.received_at, started_at__lte=call.started_at).count()


def caption(call, lead):
    who = escape(lead.name) if lead.name else "Ism ko'rsatilmagan"
    direction = {"Chiquvchi": "chiquvchi", "Kiruvchi": "kiruvchi"}.get(call.direction, call.direction.lower())
    lines = [
        f"🎙 <b>{lead.kind} lidi bilan suhbat</b>",
        f"👤 <b>Kim:</b> {who} · +998{lead.phone}",
        f"📚 <b>Kurs:</b> {escape(lead.course_name) if lead.course_name else '—'}",
        f"🔁 <b>Bog'lanish:</b> {contact_number(call, lead)}-marta",
        f"🆕 <b>Lid tushgan:</b> {_local(lead.received_at)}",
        f"📞 <b>Qo'ng'iroq:</b> {_local(call.started_at)} · {direction} · suhbat {call.duration // 60}:{call.duration % 60:02d}",
    ]
    rec = call.audio_duration or 0
    if rec + shortfall(call.duration) < call.duration:  # yozuv uzilgan (Shizuku/karnay): guruh to'liq suhbat deb o'ylamasin
        lines.append(f"⚠️ <b>Yozuv to'liq emas:</b> {rec // 60}:{rec % 60:02d} (suhbat {call.duration // 60}:{call.duration % 60:02d})")
    return "\n".join(lines)[:1024]


def _file_for(call):
    name = call.audio.name
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "ogg"
    with call.audio.open("rb") as f:
        data = f.read()
    return f"suhbat_{call.started_at:%Y%m%d_%H%M}.{ext}", data, ext


def send(call, lead, chat):
    """Yozuvni guruhga yuboradi: OGG/Opus — ovozli xabar sifatida (shu yerning o'zida tinglanadi), boshqa turlar — audio fayl."""
    filename, data, ext = _file_for(call)
    cap = caption(call, lead)
    if f".{ext}" in VOICE_EXT:
        return tg.send_media("sendVoice", "voice", chat, filename, data, cap, "audio/ogg")
    return tg.send_media("sendAudio", "audio", chat, filename, data, cap, "audio/mpeg" if ext == "mp3" else "audio/mp4")


def tick(now=None, sender=None):
    """Yuborilmagan yozuvlarni guruhga jo'natadi. Qaytaradi: yuborilganlar soni."""
    chat = settings.IG_CALLS_CHAT_ID
    if not chat:
        return 0
    now = now or timezone.now()
    sender = sender or send
    # Faqat Instagram/Facebook lidiga tegishli yozuvlar navbatda: aks holda boshqa (lidga aloqasiz) yozuvlar oldingi 10 ta o'ringa tiqilib, hech narsa yuborilmay qolardi
    mine = InboxLead.objects.filter(branch_id=OuterRef("branch_id"), phone=OuterRef("phone"), kind__in=KINDS, received_at__lte=OuterRef("started_at"))
    qs = (CallRecord.objects.filter(audio_tg_at__isnull=True, audio_at__gte=now - WINDOW, audio_at__lte=now - SETTLE, duration__gt=0, audio_size__gte=MIN_BYTES)
          .exclude(audio="").filter(Exists(mine)).order_by("audio_at"))
    sent = 0
    for call in qs[:10]:
        lead = find_inbox(call)
        if not lead:
            continue
        # band qilib olamiz (ikkinchi jarayon qayta yubormasin); xato bo'lsa qaytaramiz
        if not CallRecord.objects.filter(pk=call.pk, audio_tg_at__isnull=True).update(audio_tg_at=now):
            continue
        try:
            sender(call, lead, chat)
            sent += 1
        except Exception:  # noqa: BLE001 — Telegram vaqtincha ishlamasa, keyingi daqiqada qayta uriniladi
            log.exception("Instagram lid audiosi guruhga yuborilmadi: %s", call.pk)
            CallRecord.objects.filter(pk=call.pk).update(audio_tg_at=None)
            break
    return sent

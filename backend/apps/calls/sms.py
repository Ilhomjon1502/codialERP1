"""SMS (2026-10-22, buyurtmachi so'rovi): «To'lovga tavsiya»dagi talabalarga qabul telefoni orqali to'lov eslatmasi.

Jarayon: administrator ro'yxatdan talabalarni tanlab, qolipni ko'rib «Yuborish»ni bosadi → `queue_dues` har bir raqamga
`SmsMessage` (Navbatda) yaratadi → telefondagi ilova `outbox` dan oladi (Yuborilmoqda), o'z SIM'idan yuboradi va `report`
bilan natijani qaytaradi (Yuborildi / Xato). Avtomatik yuborish yo'q — faqat administrator tasdig'i bilan.
"""

import datetime
import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import Status
from apps.core.scoping import scope_branch
from apps.education.dues import month_dues
from apps.education.models import Contract

from .models import CallDevice, SmsMessage
from .services import normalize

S = SmsMessage.State
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
PLACEHOLDERS = {
    "talaba": "Talabaning ism-familiyasi",
    "ism": "Talabaning ismi",
    "kurs": "Kurs nomi",
    "guruh": "Guruh nomi",
    "oy": "Oy nomi (masalan: noyabr)",
    "summa": "To'lov summasi (masalan: 450 000)",
    "muddat": "To'lov muddati (masalan: 10.11)",
}
OUTBOX_BATCH = 20
SENDING_TIMEOUT_MIN = 30  # telefon olgan, lekin natija qaytarmagan SMS shuncha daqiqadan keyin «Xato» (qayta yuborilmaydi — takror bo'lmasin)

# O'zbekcha apostroflar va «» GSM-7 da yo'q — bitta UCS-2 belgi butun SMSni 70 belgiga qisqartiradi (narx 2–3 barobar oshadi)
_PLAIN = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "`": "'", "«": '"', "»": '"', "“": '"', "”": '"', "—": "-", "–": "-", "…": "..."})
_GSM = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
_GSM_EXT = set("^{}\\[~]|€")
_TOKEN = re.compile(r"\{(\w+)\}")


def plain(text):
    return (text or "").translate(_PLAIN).strip()


def segments(text):
    """SMS bo'laklari soni: GSM-7 — 160 (bo'laklarda 153), aks holda UCS-2 — 70 (67)."""
    if all(c in _GSM or c in _GSM_EXT for c in text):
        n = sum(2 if c in _GSM_EXT else 1 for c in text)
        return 1 if n <= 160 else -(-n // 153)
    n = len(text)
    return 1 if n <= 70 else -(-n // 67)


def check_template(text):
    text = plain(text)
    if not text:
        raise ValidationError({"text": ["Matn kiriting"]})
    bad = sorted({t for t in _TOKEN.findall(text) if t not in PLACEHOLDERS})
    if bad:
        raise ValidationError({"text": [f"Noma'lum o'rinbosar: {', '.join('{' + b + '}' for b in bad)}. Mavjud: "
                                        + ", ".join("{" + k + "}" for k in PLACEHOLDERS)]})
    return text


def money(v):
    return f"{int(v):,}".replace(",", " ")


def render(text, ctx):
    return _TOKEN.sub(lambda m: str(ctx.get(m.group(1), m.group(0))), text)


def due_context(contract, info, month):
    s = contract.student
    return {
        "talaba": f"{s.first_name} {s.last_name}".strip(),
        "ism": s.first_name,
        "kurs": contract.course.name,
        "guruh": contract.group.name if contract.group_id else "",
        "oy": MONTHS[month.month - 1],
        "summa": money(info["to_pay"]),
        "muddat": f"{info['deadline']:%d.%m}",
    }


def recipients(student):
    """[(phone, kimga)] — talabaning 1- va 2-telefoni, vasiyning telefoni (takrorsiz)."""
    out, seen = [], set()
    for phone, who in ((student.phone1, "Talaba"), (student.phone2, "Talaba (2-tel)"),
                       (student.parent.phone if student.parent_id else "", "Vasiy")):
        p = normalize(phone)
        if p and p not in seen:
            seen.add(p)
            out.append((p, who))
    return out


def branch_device(branch_id):
    """Filialning faol, ulangan telefoni (oxirgi aloqa bo'yicha eng yangisi)."""
    return (CallDevice.objects.filter(branch_id=branch_id, status=Status.ACTIVE, is_deleted=False).exclude(token_hash="")
            .order_by("-last_seen_at").first())


def preview_dues(user, contract_ids, month, text):
    """Yuborishdan oldingi hisob: nechta talaba, nechta raqam, nechtasi shu oy SMS olgan, birinchi xabar namunasi."""
    return _dues(user, contract_ids, month, text, skip_sent=True, commit=False)


@transaction.atomic
def queue_dues(user, contract_ids, month, text, template=None, skip_sent=True):
    return _dues(user, contract_ids, month, text, skip_sent=skip_sent, commit=True, template=template)


def _dues(user, contract_ids, month, text, skip_sent, commit, template=None):
    text = check_template(text)
    month = month.replace(day=1)
    base = scope_branch(Contract.objects.filter(is_deleted=False), user).filter(pk__in=contract_ids or [])
    dues = month_dues(base, month)
    contracts = list(base.filter(pk__in=dues.keys()).select_related("student__parent", "course", "group", "branch"))
    sent = set(SmsMessage.objects.filter(contract__in=[c.pk for c in contracts], month=month, kind=SmsMessage.Kind.DUE,
                                         status__in=[S.QUEUED, S.SENDING, S.SENT], is_deleted=False).values_list("contract_id", "phone"))
    devices, no_device = {}, set()
    rows, skipped_sent, no_phone, sample = [], 0, 0, None
    for c in contracts:
        if c.branch_id not in devices:
            devices[c.branch_id] = branch_device(c.branch_id)
        dev = devices[c.branch_id]
        msg = render(text, due_context(c, dues[c.pk], month))
        sample = sample or msg
        phones = recipients(c.student)
        if not phones:
            no_phone += 1
            continue
        for phone, who in phones:
            if skip_sent and (c.pk, phone) in sent:
                skipped_sent += 1
                continue
            if not dev:
                no_device.add(c.branch.name)
                continue
            rows.append(SmsMessage(branch_id=c.branch_id, device=dev, contract=c, template=template, kind=SmsMessage.Kind.DUE, month=month,
                                   phone=phone, recipient=who, text=msg, parts=segments(msg), created_by=user, updated_by=user))
    if commit:
        SmsMessage.objects.bulk_create(rows)
    return {
        "contracts": len(contracts),
        "paid": len(set(map(str, contract_ids or []))) - len(contracts),  # to'lov qilgan yoki ro'yxatdan olib tashlangan
        "messages": len(rows),
        "parts": sum(r.parts for r in rows),
        "skipped_sent": skipped_sent,
        "no_phone": no_phone,
        "no_device": sorted(no_device),
        "sample": sample or "",
        "sample_parts": segments(sample) if sample else 0,
    }


def due_status(contract_ids, month):
    """«To'lovga tavsiya» ro'yxati uchun: {str(contract_id): {status, at, n}} — shu oy oxirgi SMS holati."""
    out = {}
    for m in (SmsMessage.objects.filter(contract__in=contract_ids, month=month, kind=SmsMessage.Kind.DUE, is_deleted=False)
              .exclude(status=S.CANCELLED).order_by("created_at").values("contract_id", "status", "created_at", "sent_at")):
        r = out.setdefault(str(m["contract_id"]), {"n": 0, "sent": 0, "failed": 0, "queued": 0})
        r["n"] += 1
        r["sent" if m["status"] == S.SENT else "failed" if m["status"] == S.FAILED else "queued"] += 1
        r["at"] = f"{timezone.localtime(m['sent_at'] or m['created_at']):%Y-%m-%d %H:%M}"
    return out


# ---------- Telefon uchun ----------


def _expire(device):
    limit = timezone.now() - datetime.timedelta(minutes=SENDING_TIMEOUT_MIN)
    SmsMessage.objects.filter(device=device, status=S.SENDING, taken_at__lt=limit).update(
        status=S.FAILED, error="Telefondan javob kelmadi", updated_at=timezone.now())


@transaction.atomic
def outbox(device):
    """Telefon oladigan navbat (ko'pi bilan OUTBOX_BATCH ta): «Yuborilmoqda» ga o'tadi."""
    now = timezone.now()
    if not device.last_seen_at or now - device.last_seen_at > datetime.timedelta(minutes=1):
        device.last_seen_at = now
        device.save(update_fields=["last_seen_at"])
    _expire(device)
    ids = list(SmsMessage.objects.filter(device=device, status=S.QUEUED, is_deleted=False).order_by("created_at")
               .values_list("pk", flat=True)[:OUTBOX_BATCH])
    if not ids:
        return []
    SmsMessage.objects.filter(pk__in=ids, status=S.QUEUED).update(status=S.SENDING, taken_at=now, updated_at=now)
    return [{"id": str(m.pk), "phone": f"+998{m.phone}", "text": m.text}
            for m in SmsMessage.objects.filter(pk__in=ids, status=S.SENDING).order_by("created_at")]


def report(device, results):
    """[{id, ok, error}] — telefondagi yuborish natijasi. Kechikib kelgan natija («Telefondan javob kelmadi»dan keyin) ham qabul qilinadi."""
    if not isinstance(results, list):
        raise ValidationError({"results": ["Ro'yxat kutilgan"]})
    now, n = timezone.now(), 0
    for r in results[:200]:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        ok = bool(r.get("ok"))
        n += SmsMessage.objects.filter(pk=r["id"], device=device, status__in=[S.SENDING, S.FAILED]).update(
            status=S.SENT if ok else S.FAILED, error="" if ok else str(r.get("error") or "Yuborilmadi")[:200],
            sent_at=now if ok else None, updated_at=now)
    return {"updated": n}


# ---------- Sayt uchun ----------


def retry(user, msg):
    if msg.status not in (S.FAILED, S.CANCELLED):
        raise ValidationError({"detail": "Faqat xato yoki bekor qilingan SMS qayta yuboriladi"})
    dev = branch_device(msg.branch_id)
    if not dev:
        raise ValidationError({"detail": "Filialda ulangan telefon yo'q"})
    msg.device, msg.status, msg.error, msg.taken_at, msg.sent_at, msg.updated_by = dev, S.QUEUED, "", None, None, user
    msg.save()
    return msg


def cancel(user, msg):
    if msg.status != S.QUEUED:
        raise ValidationError({"detail": "Faqat navbatdagi SMS bekor qilinadi (telefon olib bo'lgan)"})
    msg.status, msg.updated_by = S.CANCELLED, user
    msg.save()
    return msg


def cancel_queued(user, qs):
    return qs.filter(status=S.QUEUED).update(status=S.CANCELLED, updated_by=user, updated_at=timezone.now())


# ---------- Kartochka va statistika (2026-10-22) ----------


def history(branch_id, student, phones, limit=30):
    """Talabaga (shartnomalari bo'yicha) yoki uning raqamlariga yuborilgan SMS'lar — yangisi birinchi."""
    from django.db.models import Q

    qs = (SmsMessage.objects.filter(branch_id=branch_id, is_deleted=False).filter(Q(contract__student=student) | Q(phone__in=phones))
          .exclude(status=S.CANCELLED).select_related("created_by").order_by("-created_at"))
    rows = [{"id": str(m.pk), "created_at": m.created_at.isoformat(), "sent_at": m.sent_at.isoformat() if m.sent_at else None,
             "status": m.status, "phone": m.phone, "recipient": m.recipient, "text": m.text, "error": m.error, "kind": m.kind,
             "by": m.created_by.full_name if m.created_by_id else ""} for m in qs[:limit]]
    return {"count": qs.count(), "results": rows}


def stats(qs):
    """SMS statistikasi (`qs` — filtrlangan jurnal): holatlar, bo'laklar, kunlar, kimga, talabalar va SMS'dan keyingi to'lovlar."""
    from decimal import Decimal

    from django.db.models import Count, Q, Sum
    from django.db.models.functions import TruncDate

    from apps.finance.models import Payment

    by = {r["status"]: r["n"] for r in qs.order_by().values("status").annotate(n=Count("id"))}
    sent = qs.filter(status=S.SENT)
    local = timezone.get_current_timezone()
    by_day = [{"date": str(r["d"]), "sent": r["sent"], "failed": r["failed"]} for r in
              qs.exclude(status=S.CANCELLED).order_by().annotate(d=TruncDate("created_at", tzinfo=local)).values("d")
              .annotate(sent=Count("id", filter=Q(status=S.SENT)), failed=Count("id", filter=Q(status=S.FAILED))).order_by("d")]
    by_recipient = [{"label": r["recipient"] or "—", "n": r["n"]} for r in
                    sent.order_by().values("recipient").annotate(n=Count("id")).order_by("-n")]
    by_user = [{"label": r["created_by__full_name"] or "—", "n": r["n"]} for r in
               qs.exclude(status=S.CANCELLED).order_by().values("created_by__full_name").annotate(n=Count("id")).order_by("-n")]
    # SMS olgan (yuborilgan) shartnomalar: birinchi SMS sanasidan keyin to'lov qilganlarmi
    first = {}
    for cid, at in sent.exclude(contract=None).order_by("created_at").values_list("contract_id", "created_at"):
        first.setdefault(cid, timezone.localtime(at, local).date())
    paid, paid_sum = set(), Decimal(0)
    if first:
        for cid, d, amount in Payment.objects.filter(contract__in=first, is_deleted=False, date__gte=min(first.values())).values_list(
                "contract_id", "date", "amount"):
            if d >= first[cid]:
                paid.add(cid)
                paid_sum += amount or 0
    return {
        "by_status": by,
        "total": sum(n for s, n in by.items() if s != S.CANCELLED),
        "sent": by.get(S.SENT, 0),
        "failed": by.get(S.FAILED, 0),
        "queued": by.get(S.QUEUED, 0) + by.get(S.SENDING, 0),
        "parts": sent.aggregate(p=Sum("parts"))["p"] or 0,
        "students": len(first),
        "paid_after": len(paid),
        "paid_after_sum": int(paid_sum),
        "by_day": by_day,
        "by_recipient": by_recipient,
        "by_user": by_user,
    }

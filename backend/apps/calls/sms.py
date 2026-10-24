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
DELIVERED, UNDELIVERED = "Yetkazildi", "Yetkazilmadi"
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
PLACEHOLDERS = {
    "talaba": "Talabaning ism-familiyasi",
    "ism": "Talabaning ismi",
    "kurs": "Kurs nomi",
    "guruh": "Guruh nomi",
    "oy": "Oy nomi (masalan: noyabr)",
    "summa": "To'lov summasi (masalan: 450 000)",
    "muddat": "To'lov muddati (masalan: 10.11)",
    # avtomatik SMS qoidalari uchun (auto_sms.py)
    "muddat_kun": "To'lov muddati kuni (masalan: 10)",
    "kun": "Oy tugashiga qolgan kunlar soni",
    "bonus": "Oldindan to'lov bonusi (masalan: 75 000)",
    "keyingi_oy": "Keyingi oy nomi (masalan: dekabr)",
    "kecha": "«Kecha» yoki sana («21.10 kuni»)",
    "sana": "Dars sanasi (masalan: 21.10)",
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


def group_label(group):
    """«Kompyuter savodxonligi 192» (tizimdagi «Kompyuter savodxonligi / #192» o'rniga SMS uchun ixcham)."""
    return f"{group.course} {group.number}" if group else ""


def due_context(contract, info, month):
    s = contract.student
    return {
        "talaba": f"{s.first_name} {s.last_name}".strip(),
        "ism": s.first_name,
        "kurs": contract.course.name,
        "guruh": group_label(contract.group) if contract.group_id else "",
        "oy": MONTHS[month.month - 1],
        "summa": money(info["to_pay"]),
        "muddat": f"{info['deadline']:%d.%m}",
        "muddat_kun": str(info["deadline"].day),
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
    from apps.clientbot import services as bot

    text = check_template(text)
    month = month.replace(day=1)
    base = scope_branch(Contract.objects.filter(is_deleted=False), user).filter(pk__in=contract_ids or [])
    dues = month_dues(base, month)
    contracts = list(base.filter(pk__in=dues.keys()).select_related("student__parent", "course", "group", "branch"))
    kinds = [SmsMessage.Kind.DUE, SmsMessage.Kind.MONTH]
    sent = set(SmsMessage.objects.filter(contract__in=[c.pk for c in contracts], month=month, kind__in=kinds,
                                         status__in=[S.QUEUED, S.SENDING, S.SENT], is_deleted=False).values_list("contract_id", "phone"))
    sent |= bot.sent_pairs([c.pk for c in contracts], month, kinds)  # botga ketganlar ham «shu oy eslatma olgan» hisoblanadi
    devices, no_device = {}, set()
    rows, bot_msgs, skipped_sent, no_phone, sample = [], [], 0, 0, None
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
            accs = bot.accounts_for(c.student, phone, finance=True)
            if accs:  # raqam mijozlar botiga ulangan — SMS o'rniga botga
                bot_msgs.append((accs, c, phone, who, msg))
                continue
            if not dev:
                no_device.add(c.branch.name)
                continue
            rows.append(SmsMessage(branch_id=c.branch_id, device=dev, contract=c, template=template, kind=SmsMessage.Kind.DUE, month=month,
                                   phone=phone, recipient=who, text=msg, parts=segments(msg), created_by=user, updated_by=user))
    if commit:
        SmsMessage.objects.bulk_create(rows)
        for accs, c, phone, who, msg in bot_msgs:
            bot.deliver(accs, msg, kind=SmsMessage.Kind.DUE, key=f"due:{c.pk}:{month:%Y-%m}:{phone}:{timezone.now():%Y%m%d%H%M%S%f}", student=c.student,
                        contract=c, month=month, phone=phone, recipient=who)
    return {
        "contracts": len(contracts),
        "paid": len(set(map(str, contract_ids or []))) - len(contracts),  # to'lov qilgan yoki ro'yxatdan olib tashlangan
        "messages": len(rows),
        "bot_messages": len(bot_msgs),
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
    from apps.clientbot.models import ClientOutbox

    for m in (ClientOutbox.objects.filter(contract__in=contract_ids, month=month, kind=SmsMessage.Kind.DUE).order_by("created_at")
              .values("contract_id", "status", "created_at", "sent_at")):  # botga ketganlar ham ro'yxatda ko'rinsin
        r = out.setdefault(str(m["contract_id"]), {"n": 0, "sent": 0, "failed": 0, "queued": 0})
        r["n"] += 1
        r["sent" if m["status"] == "sent" else "failed" if m["status"] == "failed" else "queued"] += 1
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
    """[{id, ok, error, stage, info}] — telefondagi natija. stage = «sent» (standart: operatorga topshirildi) yoki «delivered»
    (operator qabul qiluvchiga yetganini yoki yetmaganini xabar qildi). info — SIM/operator/xato kodi (ERP'da sababni ko'rish uchun).
    Kechikib kelgan natija («Telefondan javob kelmadi»dan keyin) ham qabul qilinadi."""
    if not isinstance(results, list):
        raise ValidationError({"results": ["Ro'yxat kutilgan"]})
    now, n = timezone.now(), 0
    for r in results[:200]:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        ok = bool(r.get("ok"))
        info = str(r.get("info") or "")[:200]
        if r.get("stage") == "delivered":
            upd = {"delivery": DELIVERED if ok else UNDELIVERED, "delivered_at": now if ok else None, "updated_at": now}
            if info:
                upd["detail"] = info
            if not ok and r.get("error"):
                upd["error"] = str(r["error"])[:200]
            n += SmsMessage.objects.filter(pk=r["id"], device=device).update(**upd)
            continue
        upd = {"status": S.SENT if ok else S.FAILED, "error": "" if ok else str(r.get("error") or "Yuborilmadi")[:200],
               "sent_at": now if ok else None, "updated_at": now}
        if info:
            upd["detail"] = info
        n += SmsMessage.objects.filter(pk=r["id"], device=device, status__in=[S.SENDING, S.FAILED]).update(**upd)
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
    """Talabaning SMS yozishmasi: yuborilganlar (shartnomasi yoki raqamlari bo'yicha) va undan/vasiydan kelganlar — yangisi birinchi."""
    from django.db.models import Q

    qs = (SmsMessage.objects.filter(branch_id=branch_id, is_deleted=False)
          .filter(Q(contract__student=student) | Q(student=student) | Q(phone__in=phones))
          .exclude(status=S.CANCELLED).select_related("created_by").order_by("-created_at"))
    rows = [{"id": str(m.pk), "direction": m.direction, "created_at": m.created_at.isoformat(), "sent_at": m.sent_at.isoformat() if m.sent_at else None,
             "status": m.status, "delivery": m.delivery, "phone": m.phone, "recipient": m.recipient, "text": m.text, "error": m.error, "kind": m.kind,
             "by": m.created_by.full_name if m.created_by_id and m.direction == SmsMessage.Direction.OUT else ""} for m in qs[:limit]]
    return {"count": qs.count(), "incoming": qs.filter(direction=SmsMessage.Direction.IN).count(), "results": rows}


# ---------- Mijozlardan kelgan SMS (2026-10-22) ----------

MAX_INBOX = 500


def _active_contracts(student_ids):
    from django.db.models import Q

    today = timezone.localdate()
    out = {}
    for c in (Contract.objects.filter(student_id__in=student_ids, is_deleted=False).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
              .order_by("start_date")):
        out[c.student_id] = c.pk
    return out


def _who(phone, student, parent):
    if student and phone in (student.phone1, student.phone2):
        return "Talaba"
    return "Vasiy" if parent else ""


@transaction.atomic
def ingest_inbox(device, items):
    """Telefondan kelgan SMS'lar: [{id, date (ms), address, body}]. Faqat oddiy raqamlar (9 xonaga keltiriladigan) saqlanadi —
    qisqa raqam va nomli yuboruvchilar (bank, to'lov tizimlari, operator) o'tkazib yuboriladi. Takror (qurilma + kalit) yaratilmaydi."""
    from .services import match

    if not isinstance(items, list):
        raise ValidationError({"messages": ["Ro'yxat kutilgan"]})
    if len(items) > MAX_INBOX:
        raise ValidationError({"messages": [f"Bir so'rovda ko'pi {MAX_INBOX} ta"]})
    rows, skipped, errors = [], 0, 0
    for item in items:
        try:
            ext = f"{int(item['id'])}-{int(item['date'])}"
            at = datetime.datetime.fromtimestamp(int(item["date"]) / 1000, tz=datetime.UTC)
        except (KeyError, TypeError, ValueError):
            errors += 1
            continue
        phone = normalize(str(item.get("address") or ""))
        if not phone:
            skipped += 1
            continue
        rows.append({"external_id": ext, "phone": phone, "sent_at": at, "text": str(item.get("body") or "")[:2000]})
    existing = set(SmsMessage.all_objects.filter(device=device, external_id__in=[r["external_id"] for r in rows])
                   .values_list("external_id", flat=True))
    fresh = [r for r in rows if r["external_id"] not in existing]
    found = match(device.branch_id, {r["phone"] for r in fresh})
    contracts = _active_contracts({v[0].pk for v in found.values() if v[0]})
    created = []
    for r in fresh:
        if r["external_id"] in existing:  # bitta paket ichida takror
            continue
        existing.add(r["external_id"])
        student, parent, lead = found.get(r["phone"], (None, None, None))
        created.append(SmsMessage(
            branch_id=device.branch_id, device=device, direction=SmsMessage.Direction.IN, kind=SmsMessage.Kind.INCOMING, status=S.RECEIVED,
            student=student, parent=parent, lead=lead, contract_id=contracts.get(student.pk) if student else None,
            recipient=_who(r["phone"], student, parent), parts=segments(r["text"]) if r["text"] else 1, **r))
    SmsMessage.objects.bulk_create(created)
    device.last_seen_at = timezone.now()
    device.save(update_fields=["last_seen_at"])
    return {"accepted": len(created), "duplicates": len(rows) - len(created), "skipped": skipped, "errors": errors}


def rematch(messages):
    """Bazada topilmagan kiruvchi SMS'larni qayta solishtiradi (masalan, keyin lid ochilgan bo'lsa)."""
    from .services import match

    by_branch = {}
    for m in messages:
        if m.direction == SmsMessage.Direction.IN and m.phone and not (m.student_id or m.parent_id):
            by_branch.setdefault(m.branch_id, []).append(m)
    for branch_id, rows in by_branch.items():
        found = match(branch_id, {m.phone for m in rows})
        changed = []
        for m in rows:
            if m.phone in found:
                m.student, m.parent, m.lead = found[m.phone]
                m.recipient = _who(m.phone, m.student, m.parent)
                changed.append(m)
        if changed:
            SmsMessage.objects.bulk_update(changed, ["student", "parent", "lead", "recipient"])
    return messages


def stats(qs):
    """SMS statistikasi (`qs` — filtrlangan jurnal). Yuborilganlar: holatlar, bo'laklar, kimga, kim yubordi, SMS'dan keyingi to'lovlar.
    Kelganlar: jami, bazadagi va noma'lum raqamlardan, to'lov eslatmasidan keyin javob yozgan talabalar. Kunlar bo'yicha ikkalasi."""
    from decimal import Decimal

    from django.db.models import Count, Q, Sum
    from django.db.models.functions import Coalesce, TruncDate

    from apps.finance.models import Payment

    local = timezone.get_current_timezone()
    out_qs = qs.filter(direction=SmsMessage.Direction.OUT)
    in_qs = qs.filter(direction=SmsMessage.Direction.IN)
    by = {r["status"]: r["n"] for r in out_qs.order_by().values("status").annotate(n=Count("id"))}
    sent = out_qs.filter(status=S.SENT)
    by_day = [{"date": str(r["d"]), "sent": r["sent"], "failed": r["failed"], "incoming": r["incoming"]} for r in
              qs.exclude(status=S.CANCELLED).order_by().annotate(d=TruncDate(Coalesce("sent_at", "created_at"), tzinfo=local)).values("d")
              .annotate(sent=Count("id", filter=Q(status=S.SENT)), failed=Count("id", filter=Q(status=S.FAILED)),
                        incoming=Count("id", filter=Q(direction=SmsMessage.Direction.IN))).order_by("d")]
    by_recipient = [{"label": r["recipient"] or "—", "n": r["n"]} for r in
                    sent.order_by().values("recipient").annotate(n=Count("id")).order_by("-n")]
    by_user = [{"label": r["created_by__full_name"] or "—", "n": r["n"]} for r in
               out_qs.exclude(status=S.CANCELLED).order_by().values("created_by__full_name").annotate(n=Count("id")).order_by("-n")]
    # SMS olgan (yuborilgan) shartnomalar: birinchi SMS sanasidan keyin to'lov qilganlar va javob yozganlar
    first, first_at = {}, {}
    for cid, at, sid in sent.exclude(contract=None).order_by("created_at").values_list("contract_id", "created_at", "contract__student_id"):
        first.setdefault(cid, timezone.localtime(at, local).date())
        first_at.setdefault(sid, at)
    paid, paid_sum = set(), Decimal(0)
    if first:
        for cid, d, amount in Payment.objects.filter(contract__in=first, is_deleted=False, date__gte=min(first.values())).values_list(
                "contract_id", "date", "amount"):
            if d >= first[cid]:
                paid.add(cid)
                paid_sum += amount or 0
    replied = set()
    if first_at:
        for sid, at in SmsMessage.objects.filter(direction=SmsMessage.Direction.IN, student_id__in=first_at, is_deleted=False).values_list(
                "student_id", "sent_at"):
            if at and at >= first_at[sid]:
                replied.add(sid)
    total_in = in_qs.count()
    known_in = in_qs.filter(Q(student__isnull=False) | Q(parent__isnull=False)).count()
    return {
        "by_status": by,
        "total": sum(n for s, n in by.items() if s != S.CANCELLED),
        "sent": by.get(S.SENT, 0),
        "failed": by.get(S.FAILED, 0),
        "delivered": sent.filter(delivery=DELIVERED).count(),
        "undelivered": sent.filter(delivery=UNDELIVERED).count(),
        "queued": by.get(S.QUEUED, 0) + by.get(S.SENDING, 0),
        "parts": sent.aggregate(p=Sum("parts"))["p"] or 0,
        "students": len(first),
        "paid_after": len(paid),
        "paid_after_sum": int(paid_sum),
        "incoming": total_in,
        "incoming_known": known_in,
        "incoming_unknown": total_in - known_in,
        "incoming_numbers": in_qs.values("phone").distinct().count(),
        "replied": len(replied),
        "by_day": by_day,
        "by_recipient": by_recipient,
        "by_user": by_user,
    }

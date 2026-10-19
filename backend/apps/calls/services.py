"""Qo'ng'iroqlar servisi: telefondan kelgan jurnalni qabul qilish (idempotent), raqamni CRM bilan solishtirish,
javobsiz qo'ng'iroqqa qayta qo'ng'iroqni belgilash, qurilmani ulash (kod → token) va statistika."""

import datetime
import hashlib
import re
import secrets

from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import Status
from apps.crm.models import Lead, Parent, Student

from .models import CallDevice, CallRecord

D = CallRecord.Direction
# android.provider.CallLog.Calls.TYPE: 1 kiruvchi, 2 chiquvchi, 3 javobsiz, 4 ovozli pochta, 5 rad etilgan, 6 bloklangan,
# 7 boshqa qurilmada javob berilgan
ANDROID_TYPES = {1: D.INCOMING, 2: D.OUTGOING, 3: D.MISSED, 4: D.MISSED, 5: D.REJECTED, 6: D.BLOCKED, 7: D.INCOMING}
MAX_BATCH = 500
# Suhbat davomiyligi oraliqlari (soniya): [lo, hi) — gaplashilmagan (0) alohida hisoblanmaydi
DURATION_BUCKETS = [("1–30 s", 1, 31), ("30 s–1 daq", 31, 61), ("1–3 daq", 61, 181), ("3–5 daq", 181, 301), ("5–10 daq", 301, 601), ("10 daq+", 601, None)]
PAIR_MINUTES = 60
PAIR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # O/0, I/1 yo'q — telefonda terish oson


def normalize(number):
    """9 raqam (+998 siz): +998 90 123-45-67 → 901234567. O'zbek raqami bo'lmasa ''."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) == 12 and digits.startswith("998"):
        digits = digits[3:]
    return digits if len(digits) == 9 else ""


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- Qurilma ----------


def new_pair_code(device):
    """Bir martalik ulash kodi (8 belgi, 60 daqiqa). Eski token bekor bo'ladi — ilova qayta ulanadi."""
    device.pair_code = "".join(secrets.choice(PAIR_ALPHABET) for _ in range(8))
    device.pair_expires_at = timezone.now() + datetime.timedelta(minutes=PAIR_MINUTES)
    device.token_hash = ""
    device.save(update_fields=["pair_code", "pair_expires_at", "token_hash", "updated_at"])
    return device.pair_code


@transaction.atomic
def pair(code, app_version=""):
    """Ilova kodni yuboradi → doimiy token oladi (faqat shu javobda ko'rinadi)."""
    code = (code or "").strip().upper().replace(" ", "").replace("-", "")
    device = (CallDevice.objects.select_for_update().filter(pair_code=code, pair_expires_at__gt=timezone.now(), status=Status.ACTIVE)
              .first() if len(code) == 8 else None)
    if not device:
        raise ValidationError({"code": "Kod noto'g'ri yoki muddati o'tgan"})
    token = secrets.token_urlsafe(32)
    device.token_hash, device.pair_code, device.pair_expires_at = _hash(token), "", None
    device.paired_at = device.last_seen_at = timezone.now()
    device.app_version = (app_version or "")[:20]
    device.save()
    return device, token


def device_by_token(token):
    if not token:
        return None
    return CallDevice.objects.select_related("branch").filter(token_hash=_hash(token), status=Status.ACTIVE).first()


# ---------- CRM bilan solishtirish ----------


def match(branch_id, phones):
    """{telefon: (talaba, ota-ona, lid)} — bir necha so'rovda, faqat shu filial ichida."""
    phones = {p for p in phones if p}
    if not phones:
        return {}
    out = {}
    students = Student.objects.filter(branch_id=branch_id).filter(Q(phone1__in=phones) | Q(phone2__in=phones)).order_by("-created_at")
    for s in students:
        for p in (s.phone1, s.phone2):
            if p in phones and p not in out:
                out[p] = [s, s.parent if s.parent_id else None, None]
    parents = Parent.objects.filter(branch_id=branch_id, phone__in=phones).prefetch_related("children").order_by("-created_at")
    for par in parents:
        if par.phone in out:
            continue
        child = next((c for c in par.children.all() if not c.is_deleted), None)
        out[par.phone] = [child, par, None]
    student_ids = {v[0].pk for v in out.values() if v[0]}
    leads = {lead.student_id: lead for lead in Lead.objects.filter(branch_id=branch_id, student_id__in=student_ids)}
    for v in out.values():
        if v[0]:
            v[2] = leads.get(v[0].pk)
    return {p: tuple(v) for p, v in out.items()}


def rematch(records):
    """CRM'da topilmagan qatorlarni qayta solishtiradi (masalan, keyin lid ochilgan bo'lsa)."""
    by_branch = {}
    for r in records:
        if r.phone and not (r.student_id or r.parent_id):
            by_branch.setdefault(r.branch_id, []).append(r)
    for branch_id, rows in by_branch.items():
        found = match(branch_id, {r.phone for r in rows})
        changed = []
        for r in rows:
            if r.phone in found:
                r.student, r.parent, r.lead = found[r.phone]
                changed.append(r)
        if changed:
            CallRecord.objects.bulk_update(changed, ["student", "parent", "lead"])
    return records


# ---------- Qabul qilish ----------


def _parse(item):
    try:
        ext = f"{int(item['id'])}-{int(item['date'])}"
        kind = ANDROID_TYPES[int(item["type"])]
        started = datetime.datetime.fromtimestamp(int(item["date"]) / 1000, tz=datetime.UTC)
        duration = max(0, int(item.get("duration") or 0))
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"yaroqsiz qator: {e}") from e
    number = str(item.get("number") or "")[:32]
    return {"external_id": ext, "direction": kind, "number": number, "phone": normalize(number), "started_at": started,
            "duration": duration, "contact_name": str(item.get("name") or "")[:100], "sim": str(item.get("sim") or "")[:32]}


def _mark_callbacks(rec):
    """Chiquvchi qo'ng'iroq yoki gaplashilgan kiruvchi — shu raqamdan oldingi javobsiz qo'ng'iroqlar yopiladi."""
    if not rec.phone or not (rec.direction == D.OUTGOING or (rec.direction == D.INCOMING and rec.duration > 0)):
        return
    CallRecord.objects.filter(branch_id=rec.branch_id, phone=rec.phone, direction__in=[D.MISSED, D.REJECTED],
                              started_at__lt=rec.started_at, callback_at__isnull=True).update(callback_at=rec.started_at)


@transaction.atomic
def ingest(device, items, app_version=""):
    """Telefondan kelgan qatorlar. Avval kelgani (qurilma + kalit) qayta yaratilmaydi. Natija: {qabul, takror, xato}."""
    if not isinstance(items, list):
        raise ValidationError({"calls": "Ro'yxat kutilgan"})
    if len(items) > MAX_BATCH:
        raise ValidationError({"calls": f"Bir so'rovda ko'pi {MAX_BATCH} ta"})
    rows, errors = [], []
    for i, item in enumerate(items):
        try:
            rows.append(_parse(item))
        except ValueError as e:
            errors.append({"index": i, "error": str(e)})
    existing = set(CallRecord.all_objects.filter(device=device, external_id__in=[r["external_id"] for r in rows])
                   .values_list("external_id", flat=True))
    fresh = sorted((r for r in rows if r["external_id"] not in existing), key=lambda r: r["started_at"])
    found = match(device.branch_id, {r["phone"] for r in fresh})
    seen = set(CallRecord.objects.filter(branch_id=device.branch_id, phone__in={r["phone"] for r in fresh if r["phone"]})
               .values_list("phone", flat=True).distinct())
    created = 0
    for r in fresh:
        if r["external_id"] in existing:  # bitta paket ichida takror
            continue
        existing.add(r["external_id"])
        student, parent, lead = found.get(r["phone"], (None, None, None))
        rec = CallRecord.objects.create(device=device, branch_id=device.branch_id, student=student, parent=parent, lead=lead,
                                        is_first=bool(r["phone"]) and r["phone"] not in seen, **r)
        seen.add(r["phone"])
        _mark_callbacks(rec)
        created += 1
    device.last_seen_at = timezone.now()
    if app_version:
        device.app_version = str(app_version)[:20]
    device.save(update_fields=["last_seen_at", "app_version", "updated_at"])
    return {"accepted": created, "duplicates": len(rows) - created, "errors": errors}


def set_callback(user, rec, done=True):
    if not rec.is_missed:
        raise ValidationError({"detail": "Faqat javobsiz qo'ng'iroqni belgilash mumkin"})
    rec.callback_at, rec.callback_by = (timezone.now(), user) if done else (None, None)
    rec.updated_by = user
    rec.save(update_fields=["callback_at", "callback_by", "updated_by", "updated_at"])
    return rec


# ---------- Statistika ----------


def stats(qs):
    """Yo'nalishlar, javobsiz (qayta qo'ng'iroq qilinmagan), o'rtacha qayta javob vaqti, soatlar va kunlar, manba va lid statusi."""
    missed = Q(direction__in=[D.MISSED, D.REJECTED])
    total = qs.aggregate(
        total=Count("id"), talk=Sum("duration"), answered=Count("id", filter=Q(direction=D.INCOMING)),
        outgoing=Count("id", filter=Q(direction=D.OUTGOING)), missed=Count("id", filter=missed),
        missed_open=Count("id", filter=missed & Q(callback_at__isnull=True)),
        talked=Count("id", filter=Q(duration__gt=0)), longest=Max("duration"),
        talk_in=Sum("duration", filter=Q(direction=D.INCOMING)), talk_out=Sum("duration", filter=Q(direction=D.OUTGOING)),
        new_numbers=Count("phone", filter=Q(is_first=True), distinct=True),
        unknown=Count("phone", filter=Q(student__isnull=True, parent__isnull=True) & ~Q(phone=""), distinct=True),
    )
    wait = qs.filter(missed, callback_at__isnull=False).annotate(
        w=ExpressionWrapper(F("callback_at") - F("started_at"), output_field=DurationField())).aggregate(a=Avg("w"))["a"]
    total["talk"] = total["talk"] or 0
    total["talk_in"], total["talk_out"], total["longest"] = total["talk_in"] or 0, total["talk_out"] or 0, total["longest"] or 0
    total["avg_talk"] = round(total["talk"] / total["talked"]) if total["talked"] else 0  # faqat gaplashilganlar bo'yicha
    buckets = qs.aggregate(**{f"b{i}": Count("id", filter=Q(duration__gte=lo) & (Q(duration__lt=hi) if hi else Q()))
                              for i, (_, lo, hi) in enumerate(DURATION_BUCKETS)})
    total["by_duration"] = [{"label": label, "n": buckets[f"b{i}"]} for i, (label, _, _) in enumerate(DURATION_BUCKETS)]
    total["callback_minutes"] = round(wait.total_seconds() / 60) if wait else None
    local = timezone.get_current_timezone()
    by_hour = {h: {"in": 0, "out": 0, "missed": 0} for h in range(24)}
    for row in qs.annotate(h=ExtractHour("started_at", tzinfo=local)).values("h", "direction").annotate(n=Count("id")):
        key = "out" if row["direction"] == D.OUTGOING else "missed" if row["direction"] in (D.MISSED, D.REJECTED) else "in"
        by_hour[row["h"]][key] += row["n"]
    by_day = list(qs.annotate(d=TruncDate("started_at", tzinfo=local)).values("d").order_by("d").annotate(
        n=Count("id"), missed=Count("id", filter=missed)))
    by_source = list(qs.filter(lead__isnull=False).values(name=F("lead__source__name")).annotate(
        n=Count("id"), numbers=Count("phone", distinct=True)).order_by("-n"))
    by_status = list(qs.filter(lead__isnull=False).values(st=F("lead__status")).annotate(n=Count("phone", distinct=True)).order_by("st"))
    labels = dict(Lead.LeadStatus.choices)
    return {
        **total,
        "by_hour": [{"hour": h, **v} for h, v in by_hour.items()],
        "by_day": [{"date": r["d"].isoformat(), "n": r["n"], "missed": r["missed"]} for r in by_day if r["d"]],
        "by_source": by_source,
        "by_lead_status": [{"status": r["st"], "label": f"{r['st']}. {labels.get(r['st'], '')}", "n": r["n"]} for r in by_status],
    }

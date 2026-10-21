"""Qo'ng'iroqlar servisi: telefondan kelgan jurnalni qabul qilish (idempotent), raqamni CRM bilan solishtirish,
javobsiz qo'ng'iroqqa qayta qo'ng'iroqni belgilash, qurilmani ulash (kod → token) va statistika."""

import datetime
import hashlib
import re
import secrets

from django.db import transaction
from django.db.models import Avg, Count, DurationField, Exists, ExpressionWrapper, F, Max, OuterRef, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import Status
from apps.crm.models import Lead, Parent, Student
from apps.crm.services import CALLBACK_STATUSES
from apps.education.models import Attendance, Contract

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


def _note_prompt(rec):
    """Gaplashilgan qo'ng'iroq (suhbat > 0) qayta bog'lanishdagi lid (1- va 8-status) raqamiga bo'lsa — izoh kutiladi (2026-10-21):
    lidga «suhbat bo'lgan vaqt» yoziladi. Eslatma to'xtamaydi: vaqti hali kelmagan bo'lsa — o'sha vaqtda «izoh yozing» ko'rinishida boradi;
    eslatma allaqachon yuborilgan yoki vaqt belgilanmagan bo'lsa — darhol «izoh yozing» xabari."""
    if not rec.lead_id or rec.duration <= 0 or rec.direction not in (D.OUTGOING, D.INCOMING):
        return
    lead = Lead.objects.select_related("student", "course", "branch").filter(pk=rec.lead_id, status__in=CALLBACK_STATUSES).first()
    if not lead or (lead.callback_talked_at and lead.callback_talked_at >= rec.started_at):
        return
    Lead.objects.filter(pk=lead.pk).update(callback_talked_at=rec.started_at)
    lead.callback_talked_at = rec.started_at
    pending = lead.callback_at and lead.callback_at > timezone.now() and lead.callback_reminded_at is None
    if not pending:
        from apps.notifications import reminders

        reminders.lead_call_note(lead, rec)


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
        _note_prompt(rec)
        created += 1
    device.last_seen_at = timezone.now()
    if app_version:
        device.app_version = str(app_version)[:20]
    device.save(update_fields=["last_seen_at", "app_version", "updated_at"])
    return {"accepted": created, "duplicates": len(rows) - created, "errors": errors}


def student_phones(student):
    """Talabaning 1-, 2-telefoni va vasiyning telefoni (9 xona)."""
    phones = {student.phone1, student.phone2}
    if student.parent_id:
        phones.add(student.parent.phone)
    return {p for p in phones if p}


def history(branch_id, phones, limit=30):
    """Raqamlar bo'yicha qo'ng'iroqlar tarixi (yangisi birinchi) + oxirgi aloqa."""
    qs = CallRecord.objects.filter(branch_id=branch_id, phone__in=phones).order_by("-started_at")
    rows = [{"id": r.pk, "started_at": r.started_at.isoformat(), "direction": r.direction, "duration": r.duration, "phone": r.phone, "comment": r.comment,
             "missed": r.is_missed, "callback_at": r.callback_at.isoformat() if r.callback_at else None} for r in qs[:limit]]
    return {"allowed": True, "count": qs.count(), "results": rows, "last": rows[0] if rows else None}


ABSENCE_DAYS = 14  # shuncha kun ichidagi kelmaganlar «bog'lanish kutayotgan» hisoblanadi


def open_absences(student, today=None):
    """Talabaning bog'lanish kutayotgan kelmagan darslari (besabab va sababli, «Bog'lanishga» holatida, oxirgi 14 kun)."""
    today = today or timezone.localdate()
    return Attendance.objects.filter(contract__student=student, status__in=["X", "0"], contact_status=Attendance.Contact.TO_CALL,
                                     date__gte=today - datetime.timedelta(days=ABSENCE_DAYS)).select_related("contract", "group")


@transaction.atomic
def absence_contact(user, rec, comment, parent_log=True):
    """Gaplashilgan qo'ng'iroq → talabaning kelmagan darslari «Gaplashildi» deb belgilanadi (izoh majburiy) va (ixtiyoriy) ota-onalar bilan
    aloqa jurnaliga yoziladi (har bir shartnoma uchun bitta). Qaytaradi: {absences, parent_logs}."""
    from apps.core.permissions import can
    from apps.education import services as edu

    text = " ".join(str(comment or "").split())
    if not text:
        raise ValidationError({"comment": "Izoh majburiy"})
    if not rec.student_id or rec.duration <= 0 or rec.direction not in (D.OUTGOING, D.INCOMING):
        raise ValidationError({"detail": "Gaplashilgan qo'ng'iroq va bazadagi talaba kerak"})
    rows = list(open_absences(rec.student))
    if not rows:
        raise ValidationError({"detail": "Bog'lanish kutayotgan kelmagan dars yo'q"})
    for a in rows:
        edu.set_contact(user, a, Attendance.Contact.TALKED, text)
    logs = 0
    if parent_log and can(user, "parentCalls", "a"):
        for c in {a.contract for a in rows}:
            edu.save_parent_call(user, {"contract": c, "comment": f"📞 {text}"})
            logs += 1
    return {"absences": len(rows), "parent_logs": logs}


def set_callback(user, rec, done=True):
    if not rec.is_missed:
        raise ValidationError({"detail": "Faqat javobsiz qo'ng'iroqni belgilash mumkin"})
    rec.callback_at, rec.callback_by = (timezone.now(), user) if done else (None, None)
    rec.updated_by = user
    rec.save(update_fields=["callback_at", "callback_by", "updated_by", "updated_at"])
    return rec


# ---------- Statistika ----------


def _brief(r):
    """Statistikada «kim bilan» ko'rsatish uchun: eng uzun va eng qisqa suhbat."""
    if r is None:
        return None
    name = r.student.full_name if r.student_id else str(r.parent) if r.parent_id else r.contact_name
    return {"id": r.pk, "name": name, "phone": r.phone, "number": r.number, "direction": r.direction,
            "started_at": r.started_at.isoformat(), "duration": r.duration}


def _funnel(qs, lead_ids):
    """Manba → qo'ng'iroq → lid → o'qishni boshladi → shartnoma: davrda qo'ng'iroq qilgan raqamlar va ularga mos lidlar."""
    leads = (Lead.objects.filter(pk__in=lead_ids).annotate(hc=Exists(Contract.objects.filter(student=OuterRef("student"))))
             .values(name=F("source__name")).annotate(leads=Count("id"), started=Count("id", filter=Q(status="5")), contracts=Count("id", filter=Q(hc=True))))
    callers = {r["name"]: r["callers"] for r in qs.filter(lead__isnull=False).values(name=F("lead__source__name")).annotate(callers=Count("phone", distinct=True))}
    rows = [{"name": r["name"], "callers": callers.get(r["name"], 0), "leads": r["leads"], "started": r["started"], "contracts": r["contracts"]} for r in leads]
    rows.sort(key=lambda r: -r["callers"])
    total_callers = qs.exclude(phone="").values("phone").distinct().count()
    with_lead = sum(r["callers"] for r in rows)
    return {
        "funnel": {"callers": total_callers, "leads": sum(r["leads"] for r in rows), "started": sum(r["started"] for r in rows),
                   "contracts": sum(r["contracts"] for r in rows), "no_lead": max(total_callers - with_lead, 0)},
        "funnel_by_source": rows,
    }


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
    talk = qs.filter(duration__gt=0).select_related("student", "parent")
    total["longest_call"] = _brief(talk.order_by("-duration", "started_at").first())
    total["shortest_call"] = _brief(talk.order_by("duration", "started_at").first())
    total["shortest"] = total["shortest_call"]["duration"] if total["shortest_call"] else 0
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
    lead_ids = set(qs.filter(lead__isnull=False).values_list("lead_id", flat=True).distinct())
    funnel = _funnel(qs, lead_ids)
    return {
        **total,
        **funnel,
        "by_hour": [{"hour": h, **v} for h, v in by_hour.items()],
        "by_day": [{"date": r["d"].isoformat(), "n": r["n"], "missed": r["missed"]} for r in by_day if r["d"]],
        "by_source": by_source,
        "by_lead_status": [{"status": r["st"], "label": f"{r['st']}. {labels.get(r['st'], '')}", "n": r["n"]} for r in by_status],
    }

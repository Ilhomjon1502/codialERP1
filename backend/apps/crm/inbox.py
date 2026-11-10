"""Kiruvchi lidlar navbati (2026-11-10): Instagram/Facebook target va saytdan kelgan lidlar.

Bular haqiqiy `Lead` emas — oylik statistika, voronka va marketolog KPI'siga kirmaydi. Administrator+Hisobchi (va Bosh menejer) ular bilan
gaplashadi: haqiqiy lidga qo'shadi (`link`), izoh yozib qayta aloqa vaqtini belgilaydi (`talk`, vaqti kelganda yana bosh sahifada chiqadi
va botdan eslatma boradi) yoki yopadi.
"""

import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.permissions import NO_PERMISSION, role_code
from apps.core.roles import RoleCode
from apps.references.models import Branch

from .models import InboxLead, InboxNote, Lead, Student

ROLES = (RoleCode.ADMIN, RoleCode.BOSH_MENEJER, RoleCode.ADMINISTRATOR_HISOBCHI)
LEEWAY_MIN = 10
SITE_DEDUP = datetime.timedelta(hours=6)


def allowed(user):
    return bool(user and user.is_authenticated and role_code(user) in ROLES)


def require(user):
    if not allowed(user):
        raise PermissionDenied(NO_PERMISSION)


def _branch():
    return Branch.objects.filter(status="Faol").order_by("created_at").first()


def add(kind, *, phone, name="", course_name="", info="", received_at=None, external_id=None):
    """Navbatga lid qo'shadi (idempotent: tashqi ID bo'yicha; ID yo'q bo'lsa shu raqam va manba, so'nggi 6 soatda — takror emas).
    Qaytaradi: (yozuv, yangi_mi). Filial yo'q yoki telefon bo'sh bo'lsa — (None, False)."""
    branch = _branch()
    if not branch or not phone:
        return None, False
    if external_id:
        found = InboxLead.all_objects.filter(external_id=external_id).first()
        if found:
            return found, False
    now = received_at or timezone.now()
    if not external_id and InboxLead.objects.filter(kind=kind, phone=phone, received_at__gte=now - SITE_DEDUP).exists():
        return None, False
    item = InboxLead.objects.create(branch=branch, kind=kind, external_id=external_id or None, name=(name or "")[:100], phone=phone,
                                    course_name=(course_name or "")[:60], info=(info or "")[:300], received_at=now)
    return item, True


def _note(user, item, text):
    n = InboxNote.objects.create(inbox=item, comment=text, created_by=user, updated_by=user)
    audit.log_create(user, n)
    return n


@transaction.atomic
def talk(user, item, comment, *, callback_at=None, close=False):
    """Gaplashildi: izoh majburiy. Yoki qayta aloqa vaqti (kelajakda), yoki «yopish» (qiziqmadi / noto'g'ri raqam) — biri majburiy."""
    require(user)
    if item.status in (InboxLead.Status.LINKED, InboxLead.Status.REJECTED):
        raise ValidationError({"detail": "Bu lid allaqachon yopilgan"})
    text = str(comment or "").strip()
    if not text:
        raise ValidationError({"comment": "Izoh majburiy"})
    before = audit.snapshot(item)
    if close:
        item.status, item.callback_at = InboxLead.Status.REJECTED, None
    else:
        if not callback_at:
            raise ValidationError({"callback_at": "Qayta aloqa sanasi va vaqtini kiriting (yoki lidni yoping)"})
        if callback_at < timezone.now() - datetime.timedelta(minutes=LEEWAY_MIN):
            raise ValidationError({"callback_at": "Bu vaqt o'tib ketgan — kelajakdagi sana va vaqtni kiriting"})
        item.status, item.callback_at = InboxLead.Status.CALLBACK, callback_at
    item.callback_reminded_at = None
    item.updated_by = user
    item.save()
    _note(user, item, text)
    audit.log_update(user, item, before)
    return item


@transaction.atomic
def link(user, item, lead):
    """Haqiqiy lidga bog'lash (lid saytdagi lid formasi orqali yaratilgan yoki bazada bor edi)."""
    require(user)
    if item.status == InboxLead.Status.LINKED:
        raise ValidationError({"detail": "Bu lid allaqachon lidga qo'shilgan"})
    if lead.branch_id != item.branch_id:
        raise ValidationError({"lead": "Lid boshqa filialdan"})
    before = audit.snapshot(item)
    item.status, item.lead, item.callback_at, item.updated_by = InboxLead.Status.LINKED, lead, None, user
    item.save()
    _note(user, item, f"✅ Haqiqiy lidga qo'shildi: {lead.student.full_name}")
    audit.log_update(user, item, before)
    return item


@transaction.atomic
def reopen(user, item):
    require(user)
    if item.status != InboxLead.Status.REJECTED:
        raise ValidationError({"detail": "Faqat yopilgan lidni qayta ochish mumkin"})
    before = audit.snapshot(item)
    item.status, item.updated_by, item.callback_at = InboxLead.Status.NEW, user, None
    item.save()
    _note(user, item, "↩️ Qayta ochildi")
    audit.log_update(user, item, before)
    return item


def known_map(phones):
    """{telefon: {name, lead}} — shu raqam bazadagi talabada bormi (lid bo'lsa uning ID si ham)."""
    phones = {p for p in phones if p}
    if not phones:
        return {}
    out = {}
    for st in Student.objects.filter(Q(phone1__in=phones) | Q(phone2__in=phones)).order_by("created_at"):
        lead = Lead.objects.filter(student=st).order_by("-created_at").first()
        for p in (st.phone1, st.phone2):
            if p in phones:
                out[p] = {"name": st.full_name, "lead": str(lead.pk) if lead else None}
    return out


def summary(now=None):
    """Bosh sahifa uchun: yangi, qayta aloqa vaqti kelgan, kutayotgan qayta aloqalar."""
    now = now or timezone.now()
    live = InboxLead.objects
    cb = live.filter(status=InboxLead.Status.CALLBACK)
    return {"new": live.filter(status=InboxLead.Status.NEW).count(), "due": cb.filter(callback_at__lte=now).count(),
            "callback": cb.count()}


# ---------- Qo'ng'iroqlar bilan bog'lash (2026-11-10) ----------

def calls_map(items):
    """{inbox_id: {count, last_at, last_direction, last_duration, talked_at, note_due}} — lid tushgandan keyin shu raqam bilan bo'lgan qo'ng'iroqlar
    (telefondan kelgan `calls.CallRecord`). `note_due` — gaplashilgan qo'ng'iroq bor, lekin undan keyin izoh yozilmagan."""
    from apps.calls.models import CallRecord

    items = list(items)
    if not items:
        return {}
    recs = list(CallRecord.objects.filter(phone__in={i.phone for i in items}, started_at__gte=min(i.received_at for i in items)).order_by("started_at"))
    out = {}
    for it in items:
        mine = [r for r in recs if r.phone == it.phone and r.started_at >= it.received_at]
        if not mine:
            continue
        talked = [r for r in mine if r.duration > 0 and r.direction in ("Kiruvchi", "Chiquvchi")]
        last_note = max((n.created_at for n in it.notes.all()), default=None)
        talked_at = talked[-1].started_at if talked else None
        out[it.pk] = {"count": len(mine), "last_at": mine[-1].started_at, "last_direction": mine[-1].direction, "last_duration": mine[-1].duration,
                      "talked_at": talked_at,
                      "note_due": bool(talked_at and it.status in (InboxLead.Status.NEW, InboxLead.Status.CALLBACK) and (not last_note or talked_at > last_note))}
    return out


def open_by_phone(phones):
    """{telefon: {id, kind, name, course, status}} — shu raqamli ochiq (Yangi/Qayta aloqa) kiruvchi lid; qo'ng'iroqlar jurnalida ko'rsatish uchun."""
    phones = {p for p in phones if p}
    if not phones:
        return {}
    out = {}
    for it in InboxLead.objects.filter(phone__in=phones, status__in=[InboxLead.Status.NEW, InboxLead.Status.CALLBACK]).order_by("received_at"):
        out[it.phone] = {"id": str(it.pk), "kind": it.kind, "name": it.name, "course": it.course_name, "status": it.status}
    return out

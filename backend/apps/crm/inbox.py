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

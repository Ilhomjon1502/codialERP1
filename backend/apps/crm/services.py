"""CRM servislari: talaba va lid yaratish, dublikat tekshiruvi, voronka va statistika (CLAUDE.md 7.3, 20.6)."""

import datetime
import re

from django.db import transaction
from django.db.models import Count, DecimalField, Exists, Min, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.models import Status
from apps.core.permissions import NO_PERMISSION, can, check_edit_window
from apps.notifications import services as notif

from .models import Lead, LeadComment, Parent, Student

PHONE_RE = re.compile(r"\d{9}")
PHONE_MSG = "9 sondan iborat bo'lsin. Namuna: 998883322"
DUPLICATE_MSG = "Ushbu o'quvchi avval kiritilgan. Lidlar yoki shartnomalar oynasidan qidiring"
CALLBACK_STATUSES = ("1", "8")  # qayta bog'lanish vaqti belgilanadigan holatlar (2026-10-21)
CALLBACK_LEEWAY_MIN = 10  # vaqt kiritishda ozgina orqaga ruxsat (daqiqa)


def clean(s):
    return " ".join(str(s or "").split())


def validate_name(value, field):
    v = clean(value)
    if not 3 <= len(v) <= 20:
        raise ValidationError({field: "Eng ozi 3 harf, ko'pi 20"})
    return v


def validate_father_name(value):
    """Sharif majburiy emas (2026-10-21): bo'sh bo'lishi mumkin; kiritilsa — nuqtasiz, kamida 3 harf."""
    v = clean(value)
    if not v:
        return ""
    if "." in v:
        raise ValidationError({"father_name": "Nuqta qo'yib bo'lmaydi!"})
    if len(v) < 3:
        raise ValidationError({"father_name": "Eng ozi 3 harfdan iborat bo'lsin!"})
    return v


def validate_phones(phone1, phone2, phone2_required=False):
    phone1, phone2 = clean(phone1), clean(phone2)
    if not PHONE_RE.fullmatch(phone1):
        raise ValidationError({"phone1": PHONE_MSG})
    if phone2 or phone2_required:
        if not PHONE_RE.fullmatch(phone2):
            raise ValidationError({"phone2": PHONE_MSG})
        if phone2 == phone1:
            raise ValidationError({"phone2": "Ikki bir xil nomer kiritib bo'lmaydi!"})
    return phone1, phone2


def find_duplicate(branch, first_name, last_name, phones, exclude_pk=None):
    """Dublikat: shu filialda ism + familiya bir xil (katta-kichik harf farqsiz) VA telefonlardan biri mos (20.6, 3)."""
    phones = [p for p in phones if p]
    if not phones:
        return None
    qs = Student.objects.filter(branch=branch, first_name__iexact=first_name, last_name__iexact=last_name).exclude(pk=exclude_pk)
    return qs.filter(Q(phone1__in=phones) | Q(phone2__in=phones)).first()


def has_contract(student):
    return student.contracts.exists()


def contract_exists():
    """Lid uchun: talabasining (o'chirilmagan) shartnomasi bormi — annotatsiya."""
    from apps.education.models import Contract

    return Exists(Contract.objects.filter(student=OuterRef("student")))


def with_payments(qs):
    """«To'lov qilganlar» tabi: talabasining barcha shartnomalari bo'yicha to'lovlar jami va birinchi to'lov sanasi."""
    from apps.finance.models import Payment

    pays = Payment.objects.filter(contract__student=OuterRef("student"), is_deleted=False).order_by().values("contract__student")
    return qs.annotate(
        paid_total=Coalesce(Subquery(pays.annotate(s=Sum("amount")).values("s")), Value(0), output_field=DecimalField(max_digits=14, decimal_places=0)),
        first_paid=Subquery(pays.annotate(m=Min("date")).values("m")),
    )


def check_lead_group(lead_branch, course, group, instance=None):
    """Guruh — shu filial va kursning Faol yoki Rejadagi guruhi (3, 4, 5-statuslarda tanlanadi)."""
    if group is None:
        return
    from apps.education.services import NOFAOL, period_status

    if group.branch_id != lead_branch.pk or group.course_id != getattr(course, "pk", None):
        raise ValidationError({"group": "Guruh shu filial va kursdan bo'lsin"})
    if (instance is None or instance.group_id != group.pk) and period_status(group.start_date, group.end_date) == NOFAOL:
        raise ValidationError({"group": "Guruh nofaol"})


@transaction.atomic
def create_contract_from_lead(user, lead):
    """5-statusdagi lid: filial, talaba, kurs, guruh, boshlanish = sinov dars kuni, turi Pullik (CLAUDE.md 7.3)."""
    from apps.education import services as edu

    if lead.status != Lead.LeadStatus.STARTED:
        raise ValidationError({"detail": "Shartnoma «5. O'qishni boshladi» statusida tuziladi"})
    if has_contract(lead.student):
        raise ValidationError({"detail": "Bu talabaning shartnomasi bor"})
    if not lead.group_id:
        raise ValidationError({"group": "Avval lidga guruh tanlang"})
    if not lead.student.birth_date:
        raise ValidationError({"detail": "Avval talaba ma'lumotlarini to'ldiring (sharif, tug'ilgan sana)"})
    return edu.save_contract(user, {"branch": lead.branch, "student": lead.student, "course": lead.course, "group": lead.group,
                                    "start_date": lead.demo_date or timezone.localdate()})


@transaction.atomic
def create_student(user, branch, *, first_name, last_name, phone1, phone2, gender="", father_name="", phone2_required=True):
    first_name = validate_name(first_name, "first_name")
    last_name = validate_name(last_name, "last_name")
    phone1, phone2 = validate_phones(phone1, phone2, phone2_required)
    if find_duplicate(branch, first_name, last_name, [phone1, phone2]):
        raise ValidationError({"phone2": DUPLICATE_MSG})
    st = Student.objects.create(branch=branch, first_name=first_name, last_name=last_name, father_name=clean(father_name), gender=gender or "",
                                phone1=phone1, phone2=phone2, created_by=user, updated_by=user)
    audit.log_create(user, st)
    return st


@transaction.atomic
def update_student(user, student, data, new_parent=None):
    """«Talaba ma'lumotlarini to'ldirish»: tug'ilgan sana majburiy (sharif — ixtiyoriy), vasiy tanlanadi yoki yangisi (kim bo'lishi bilan) qo'shiladi."""
    before = audit.snapshot(student)
    first_name = validate_name(data.get("first_name", student.first_name), "first_name")
    last_name = validate_name(data.get("last_name", student.last_name), "last_name")
    father_name = validate_father_name(data.get("father_name", student.father_name))
    phone1, phone2 = validate_phones(data.get("phone1", student.phone1), data.get("phone2", student.phone2))
    if find_duplicate(student.branch, first_name, last_name, [phone1, phone2], exclude_pk=student.pk):
        raise ValidationError({"phone1": DUPLICATE_MSG})
    birth_date = data.get("birth_date", student.birth_date)
    if not birth_date:
        raise ValidationError({"birth_date": "Majburiy maydon"})
    parent = data.get("parent", student.parent)
    if new_parent:
        p_first = clean(new_parent.get("first_name"))
        p_phone = clean(new_parent.get("phone"))
        relation = clean(new_parent.get("relation"))
        if not relation:
            raise ValidationError({"p_relation": "Vasiy kimligini tanlang (ota, ona, aka…)"})
        if p_first and len(p_first) < 3:
            raise ValidationError({"p_first": "Eng ozi 3 harf"})
        if not p_first and relation == Parent.Relation.OTHER:
            raise ValidationError({"p_first": "«Boshqa» bo'lsa, ismini yozing"})
        if not PHONE_RE.fullmatch(p_phone):
            raise ValidationError({"p_phone": PHONE_MSG})
        parent = Parent.objects.create(branch=student.branch, relation=relation, first_name=p_first or relation, last_name=last_name, phone=p_phone,
                                       created_by=user, updated_by=user)
        audit.log_create(user, parent)
    if parent and parent.branch_id != student.branch_id:
        raise ValidationError({"parent": "Vasiy boshqa filialdan"})
    student.first_name, student.last_name, student.father_name = first_name, last_name, father_name
    student.phone1, student.phone2 = phone1, phone2
    student.gender = data.get("gender", student.gender) or ""
    student.birth_date, student.parent, student.updated_by = birth_date, parent, user
    student.save()
    audit.log_update(user, student, before)
    return student


def validate_callback(instance, status, attrs):
    """1- va 8-statuslarda qayta bog'lanish sanasi va vaqti majburiy (holat o'zgarganda yoki vaqt tahrirlanganda), kelajakda bo'lsin.
    Boshqa holatlarda vaqt tozalanadi. attrs ga `callback_at` / `callback_reminded_at` qo'yadi."""
    if status not in CALLBACK_STATUSES:
        attrs["callback_at"] = None
        attrs["callback_reminded_at"] = None
        attrs["callback_talked_at"] = None
        return
    changed_status = instance is None or instance.status != status
    if not changed_status and "callback_at" not in attrs:
        return
    at = attrs.get("callback_at")
    if not at:
        raise ValidationError({"callback_at": "Qayta bog'lanish sanasi va vaqtini kiriting"})
    if at < timezone.now() - datetime.timedelta(minutes=CALLBACK_LEEWAY_MIN):
        raise ValidationError({"callback_at": "Bu vaqt o'tib ketgan — kelajakdagi sana va vaqtni kiriting"})
    attrs["callback_reminded_at"] = None


@transaction.atomic
def callback_action(user, lead, action, now=None):
    """Botdagi qayta bog'lanish tugmalari: done — «Qo'ng'iroq qilindi» (vaqt tozalanadi, izoh yoziladi), h1 — 1 soatga, tm — ertaga shu vaqtda.
    Huquq va muddat saytdagi bilan bir xil. Qaytaradi: qisqa javob."""
    now = now or timezone.localtime()
    if not can(user, "leads", "e"):
        raise PermissionDenied(NO_PERMISSION)
    check_edit_window(user, "leads", lead.created_at)
    if lead.status not in CALLBACK_STATUSES:
        raise ValidationError({"detail": "Lid holati o'zgargan — qayta bog'lanish kerak emas"})
    before = audit.snapshot(lead)
    if action == "done":
        lead.callback_at = None
        msg = "✅ Qo'ng'iroq qilindi deb belgilandi"
        c = LeadComment.objects.create(lead=lead, comment=f"📞 Qo'ng'iroq qilindi (Telegram): {user}", created_by=user, updated_by=user)
        audit.log_create(user, c)
    elif action == "h1":
        lead.callback_at = now + datetime.timedelta(hours=1)
        msg = f"✅ Bugun {timezone.localtime(lead.callback_at):%H:%M} ga ko'chirildi"
    elif action == "d3":
        base = timezone.localtime(lead.callback_at).time() if lead.callback_at else now.time().replace(second=0, microsecond=0)
        lead.callback_at = timezone.make_aware(datetime.datetime.combine(now.date() + datetime.timedelta(days=3), base))
        msg = f"✅ 3 kundan keyin {base:%H:%M} ga ko'chirildi"
    elif action == "tm":
        base = timezone.localtime(lead.callback_at).time() if lead.callback_at else now.time().replace(second=0, microsecond=0)
        lead.callback_at = timezone.make_aware(datetime.datetime.combine(now.date() + datetime.timedelta(days=1), base))
        msg = f"✅ Ertaga {base:%H:%M} ga ko'chirildi"
    else:
        raise ValidationError({"detail": "Noma'lum amal"})
    lead.callback_reminded_at = None
    lead.updated_by = user
    lead.save()
    audit.log_update(user, lead, before)
    return msg


def check_lead_refs(branch, source, course, day_pattern, times, instance=None):
    """Yangi qiymat tanlansa — faqat faol manba, kurs, dars kunlari va vaqtlar (eski lidning qiymati saqlanib qoladi)."""
    def changed(field, value):
        return instance is None or getattr(instance, f"{field}_id") != getattr(value, "pk", None)

    if source and changed("source", source) and source.status != Status.ACTIVE:
        raise ValidationError({"source": "Bu manba nofaol"})
    if course and changed("course", course):
        if course.status != Status.ACTIVE or not course.branches.filter(pk=branch.pk).exists():
            raise ValidationError({"course": "Bu kurs filialda faol emas"})
    if day_pattern and changed("day_pattern", day_pattern) and day_pattern.status != Status.ACTIVE:
        raise ValidationError({"pattern": "Bu dars kunlari nofaol"})
    old_times = set(instance.preferred_times.values_list("pk", flat=True)) if instance else set()
    for t in times or []:
        if t.branch_id != branch.pk:
            raise ValidationError({"times": "Dars vaqti boshqa filialdan"})
        if t.pk not in old_times and t.status != Status.ACTIVE:
            raise ValidationError({"times": f"{t} — nofaol dars vaqti"})


@transaction.atomic
def create_lead(user, branch, data, *, new_student=None, student=None, comment=""):
    """Lid yaratish: yangi talaba bilan yoki bazadagi talaba uchun. Bitta talaba — bitta filialda bitta lid."""
    if new_student:
        student = create_student(user, branch, **new_student)
    elif student is None:
        raise ValidationError({"student": "Majburiy maydon"})
    elif student.branch_id != branch.pk:
        raise ValidationError({"student": "Talaba boshqa filialdan"})
    if Lead.objects.filter(branch=branch, student=student).exists():
        raise ValidationError({"student": "Bu talabaning lidi allaqachon ochilgan"})
    if has_contract(student):
        raise ValidationError({"student": "Shartnomasi bor talabaga yangi lid ochilmaydi"})
    times = data.pop("preferred_times", [])
    check_lead_refs(branch, data.get("source"), data.get("course"), data.get("day_pattern"), times)
    check_lead_group(branch, data.get("course"), data.get("group"))
    lead = Lead.objects.create(branch=branch, student=student, created_by=user, updated_by=user, **data)
    lead.preferred_times.set(times)
    audit.log_create(user, lead)
    if clean(comment):
        add_comment(user, lead, comment)
    notif.lead_created(lead)
    return lead


@transaction.atomic
def add_comment(user, lead, text):
    text = str(text or "").strip()
    if not text:
        raise ValidationError({"comment": "Izoh bo'sh"})
    c = LeadComment.objects.create(lead=lead, comment=text, created_by=user, updated_by=user)
    audit.log_create(user, c)
    if lead.callback_talked_at:  # suhbatdan keyingi izoh yozildi — «izoh kutilmoqda» belgisi o'chadi
        Lead.objects.filter(pk=lead.pk).update(callback_talked_at=None)
    return c


@transaction.atomic
def save_call_note(user, lead, comment, status=None, callback_at=None, now=None):
    """Suhbatdan keyingi izoh (2026-10-21): izoh majburiy; lid shu holatda (1 yoki 8) qolsa — keyingi qayta bog'lanish vaqtini belgilash mumkin
    (vaqti allaqachon o'tgan yoki yo'q bo'lsa — majburiy); holatni ham o'zgartirsa bo'ladi. «Izoh kutilmoqda» belgisi o'chadi."""
    now = now or timezone.now()
    text = clean(comment)
    if not text:
        raise ValidationError({"comment": "Izoh majburiy"})
    if not can(user, "leads", "a"):
        raise PermissionDenied(NO_PERMISSION)
    new_status = status or lead.status
    if new_status not in Lead.LeadStatus.values:
        raise ValidationError({"status": "Noto'g'ri holat"})
    if new_status != lead.status or callback_at is not None:
        if not can(user, "leads", "e"):
            raise PermissionDenied(NO_PERMISSION)
        check_edit_window(user, "leads", lead.created_at)
    attrs = {} if callback_at is None else {"callback_at": callback_at}
    if new_status in CALLBACK_STATUSES and new_status == lead.status and callback_at is None and (not lead.callback_at or lead.callback_at <= now):
        raise ValidationError({"callback_at": "Keyingi qayta bog'lanish vaqtini belgilang"})
    validate_callback(lead, new_status, attrs)
    before = audit.snapshot(lead)
    old_status = lead.status
    lead.status = new_status
    for k, v in attrs.items():
        setattr(lead, k, v)
    lead.callback_talked_at = None
    lead.updated_by = user
    lead.save()
    c = LeadComment.objects.create(lead=lead, comment=f"📞 {text}", created_by=user, updated_by=user)
    audit.log_create(user, c)
    audit.log_update(user, lead, before)
    if old_status != new_status:
        notif.lead_changed(lead, old_status, user)
    return lead


# ------------------------------------------------------------------ voronka va statistika

STATUSES = [s for s, _ in Lead.LeadStatus.choices]


def _plain(qs):
    """Izohlar soni kabi annotatsiyalarsiz toza so'rov — aks holda JOIN tufayli lidlar bir necha marta sanaladi."""
    return Lead.objects.filter(pk__in=qs.values("pk"))


def board(qs, per_column=40):
    """Voronka: har statusdagi soni, oxirgi N ta lid va o'tish foizlari — hammasi bazada hisoblanadi."""
    counts = dict(_plain(qs).values_list("status").annotate(n=Count("id")).order_by())
    total = sum(counts.values())

    def reached(k):  # k-bosqichga yetganlar (k..5)
        return sum(n for s, n in counts.items() if int(k) <= int(s) <= 5)

    columns = {s: list(qs.filter(status=s).order_by("-created_at")[:per_column]) for s in STATUSES}
    conv = {k: (reached(k) / total if total else 0) for k in ("3", "4", "5")}
    with_contract = _plain(qs).filter(contract_exists()).count()
    return {"total": total, "counts": {s: counts.get(s, 0) for s in STATUSES}, "columns": columns, "reached": conv,
            "contract_rate": with_contract / total if total else 0}


def stats(qs):
    qs = _plain(qs)
    by_source = list(qs.annotate(hc=contract_exists()).values("source").annotate(n=Count("id"), contracts=Count("id", filter=Q(hc=True))).order_by("-n"))
    by_status = dict(qs.values_list("status").annotate(n=Count("id")).order_by())
    by_month = [
        {"month": r["m"].strftime("%Y-%m"), "source": str(r["source"]), "n": r["n"]}
        for r in qs.annotate(m=TruncMonth("created_at")).values("m", "source").annotate(n=Count("id")).order_by("m")
    ]
    by_age = dict(qs.exclude(age_group="").values_list("age_group").annotate(n=Count("id")).order_by())
    by_social = dict(qs.exclude(social_status="").values_list("social_status").annotate(n=Count("id")).order_by())
    return {
        "total": sum(by_status.values()),
        "by_source": [{"source": str(r["source"]), "n": r["n"], "contracts": r["contracts"]} for r in by_source],
        "by_status": {s: by_status.get(s, 0) for s in STATUSES},
        "by_month": by_month,
        "by_age": by_age,
        "by_social": by_social,
    }


@transaction.atomic
def merge_students(user, keep, drop):
    """AppSheet'dan ikki marta ko'chgan talaba: `drop` dagi shartnoma, qo'ng'iroq va SMS `keep` ga o'tadi, lidlar bitta bo'ladi
    (izohlar asosiy lidga ko'chadi), bo'sh maydonlar to'ldiriladi, `drop` o'chiriladi (soft delete)."""
    from apps.core.services import soft_delete

    if keep.pk == drop.pk or keep.branch_id != drop.branch_id:
        raise ValidationError({"detail": "Bir filialdagi ikki xil talabani birlashtirish mumkin"})
    before = audit.snapshot(keep)
    for f in ("father_name", "gender", "phone2", "birth_date", "parent"):
        if not getattr(keep, f) and getattr(drop, f):
            setattr(keep, f, getattr(drop, f))
    keep.updated_by = user
    keep.save()
    audit.log_update(user, keep, before, detail=f"Birlashtirildi: {drop.pk}")

    main_lead = keep.leads.first()
    for lead in drop.leads.all():
        if main_lead is None:  # asosiy talabada lid yo'q — lid o'zi ko'chadi
            lead.student = keep
            lead.save(update_fields=["student", "updated_at"])
            main_lead = lead
            continue
        lead.comments.update(lead=main_lead)
        soft_delete(lead, user, check_usage=False)
    drop.contracts.update(student=keep)
    drop.calls.update(student=keep)
    if hasattr(drop, "sms_messages"):  # SMS jurnali talabaga bog'langan bo'lsa
        drop.sms_messages.update(student=keep)
    soft_delete(drop, user)
    return keep

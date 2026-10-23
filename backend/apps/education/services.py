"""O'quv jarayoni servislari: guruh va shartnoma qoidalari, davomat olish, kelmaganlar, qoldirilgan darslar (CLAUDE.md 7.4, 9)."""

import datetime

from django.db import transaction
from django.db.models import Count, DecimalField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.models import Status
from apps.core.permissions import can, check_edit_window, is_top, role_code, today
from apps.core.roles import RoleCode
from apps.notifications import services as notif
from apps.references.models import AttendanceStatus

from . import calc
from .models import Attendance, Contract, Group, MakeupRequest

TEACHERS = {RoleCode.USTOZ, RoleCode.USTOZ_YORDAMCHI}
SUPPORTERS = {RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI}
SUBSTITUTE_SETTERS = {RoleCode.ADMIN, RoleCode.BOSH_MENEJER, RoleCode.ADMINISTRATOR, RoleCode.ADMINISTRATOR_HISOBCHI}
FAOL, REJADA, NOFAOL = "Faol", "Rejada", "Nofaol"
ZERO = Value(0, output_field=DecimalField(max_digits=14, decimal_places=0))


# ------------------------------------------------------------------ statuslar (sanadan hisoblanadi)

def period_status(start, end, on=None):
    """Guruh va shartnoma: tugagan → Nofaol, boshlanmagan → Rejada, aks holda Faol (18-bo'lim 1-savol taxmini)."""
    on = on or today()
    if end and end < on:
        return NOFAOL
    if start > on:
        return REJADA
    return FAOL


def status_q(status, on=None, start="start_date", end="end_date"):
    on = on or today()
    if status == FAOL:
        return Q(**{f"{start}__lte": on}) & (Q(**{f"{end}__isnull": True}) | Q(**{f"{end}__gte": on}))
    if status == REJADA:
        return Q(**{f"{start}__gt": on})
    if status == NOFAOL:
        return Q(**{f"{end}__lt": on})
    raise ValidationError({"status": "Status: Faol, Rejada yoki Nofaol"})


def active_on(d, prefix=""):
    """Shu sanada amalda: start ≤ sana va (end bo'sh yoki end ≥ sana)."""
    return Q(**{f"{prefix}start_date__lte": d}) & (Q(**{f"{prefix}end_date__isnull": True}) | Q(**{f"{prefix}end_date__gte": d}))


def has_lesson(group, d):
    return d.isoweekday() in group.day_pattern.weekdays and group.start_date <= d and (not group.end_date or group.end_date >= d)


# ------------------------------------------------------------------ ma'lumot doirasi (6.3)

def teacher_scope(qs, user, group_field="group", extra=()):
    """Ustoz — o'zi ustoz bo'lgan guruhlar, yordamchi — o'zi yordamchi bo'lganlari, Ustoz+Yordamchi — ikkalasi.
    `extra` — qo'shimcha maydonlar (masalan davomatdagi teacher/supporter)."""
    code = role_code(user)
    if code not in (TEACHERS | SUPPORTERS):
        return qs
    p = f"{group_field}__" if group_field else ""
    q = Q()
    if code in TEACHERS:
        q |= Q(**{f"{p}teacher": user})
    if code in SUPPORTERS:
        q |= Q(**{f"{p}supporter": user})
    for f in extra:
        q |= Q(**{f: user})
    return qs.filter(q)


# ------------------------------------------------------------------ guruh

def fill_of(n, capacity):
    """To'lish holati: 0 → Bo'sh, ≤50% → Yomon, ≤75% → O'rtacha, ≤85% → Yaxshi, >85% → Zo'r. Sig'im 0 bo'lsa foiz yo'q («—»)."""
    pct = n / capacity if capacity else None
    if n == 0:
        label, cls = "Bo'sh", "red"
    elif pct is None or pct <= 0.5:
        label, cls = "Yomon", "red"
    elif pct <= 0.75:
        label, cls = "O'rtacha", "orange"
    elif pct <= 0.85:
        label, cls = "Yaxshi", "blue"
    else:
        label, cls = "Zo'r", "green"
    return {"n": n, "cap": capacity, "pct": pct, "free": capacity - n, "label": label, "cls": cls}


def with_fill(qs, on=None):
    """Faol shartnomalar soni va oxirgi davomat sanasi — subquery bilan (JOIN ko'paytmasisiz)."""
    on = on or today()
    active = Contract.objects.filter(group=OuterRef("pk")).filter(active_on(on)).order_by().values("group").annotate(n=Count("id")).values("n")
    last = Attendance.objects.filter(group=OuterRef("pk")).order_by("-date").values("date")[:1]
    return qs.annotate(active_count=Coalesce(Subquery(active), 0), last_att=Subquery(last))


def next_group_number(branch, course):
    return (Group.all_objects.filter(branch=branch, course=course).aggregate(m=Max("number"))["m"] or 0) + 1


def _changed(instance, field, value):
    return instance is None or getattr(instance, f"{field}_id") != getattr(value, "pk", None)


def validate_group(user, d, instance=None):
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    branch, course, pattern, time = get("branch"), get("course"), get("day_pattern"), get("time")
    teacher, supporter, room = get("teacher"), get("supporter"), get("room")
    start, end = get("start_date"), get("end_date")
    if instance is not None and "course" in d and course.pk != instance.course_id:
        if role_code(user) != RoleCode.ADMIN:
            raise PermissionDenied("Guruh kursini faqat Admin o'zgartiradi")
        if instance.contracts.exists():
            raise ValidationError({"course": "Guruhda shartnomalar bor — kursni o'zgartirib bo'lmaydi"})
    if _changed(instance, "course", course) and (course.status != Status.ACTIVE or not course.branches.filter(pk=branch.pk).exists()):
        raise ValidationError({"course": "Bu kurs filialda faol emas"})
    if _changed(instance, "day_pattern", pattern) and pattern.status != Status.ACTIVE:
        raise ValidationError({"pattern": "Bu dars kunlari nofaol"})
    if time.branch_id != branch.pk:
        raise ValidationError({"time": "Dars vaqti boshqa filialdan"})
    if _changed(instance, "time", time) and time.status != Status.ACTIVE:
        raise ValidationError({"time": "Bu dars vaqti nofaol"})
    if room.branch_id != branch.pk:
        raise ValidationError({"room": "Xona boshqa filialdan"})
    if _changed(instance, "room", room) and room.status != Status.ACTIVE:
        raise ValidationError({"room": "Bu xona nofaol"})
    for u, roles, field, label in ((teacher, TEACHERS, "teacher", "Ustoz"), (supporter, SUPPORTERS, "supporter", "Yordamchi")):
        if u is None:
            continue
        if role_code(u) not in roles or u.employment_status != u.Employment.ACTIVE:
            raise ValidationError({field: f"{label} roli va faol holati mos emas"})
        if not u.branches.filter(pk=branch.pk).exists():
            raise ValidationError({field: f"{label} bu filialda ishlamaydi"})
    if supporter and supporter.pk == teacher.pk:
        raise ValidationError({"supporter": "Yordamchi ustozdan farq qilsin"})
    if end and end <= start:
        raise ValidationError({"end": "Boshlanish sanadan kichik bo'lolmaydi!"})


@transaction.atomic
def save_group(user, d, instance=None):
    validate_group(user, d, instance)
    if instance is None:
        g = Group(**d, number=next_group_number(d["branch"], d["course"]), created_by=user, updated_by=user)
        g.save()
        audit.log_create(user, g)
        return g
    before = audit.snapshot(instance)
    for k, v in d.items():
        setattr(instance, k, v)
    instance.updated_by = user
    instance.save()
    audit.log_update(user, instance, before)
    return instance


# ------------------------------------------------------------------ shartnoma

def charged_subquery():
    return Coalesce(Subquery(
        Attendance.objects.filter(contract=OuterRef("pk"), is_deleted=False).order_by().values("contract").annotate(s=Sum("student_debt")).values("s")
    ), ZERO)


def _payments_sum(field):
    from apps.finance.models import Payment

    return Coalesce(Subquery(
        Payment.objects.filter(contract=OuterRef("pk"), is_deleted=False).order_by().values("contract").annotate(s=Sum(field)).values("s")
    ), ZERO)


def with_balance(qs):
    """Balans = boshlang'ich qoldiq + Σ dars narxi − Σ to'lov − Σ chegirma (7.4). To'lov va chegirma kiritilgan zahoti hisobga olinadi
    (tasdiq g'azna balansiga ta'sir qiladi, talaba qarziga emas — docs/decisions.md)."""
    qs = qs.annotate(charged=charged_subquery(), paid=_payments_sum("amount"), discount_sum=_payments_sum("discount"))
    return qs.annotate(balance=Coalesce("opening_balance", ZERO) + Coalesce("charged", ZERO) - Coalesce("paid", ZERO) - Coalesce("discount_sum", ZERO))


def next_contract_number(branch):
    return (Contract.all_objects.filter(branch=branch).aggregate(m=Max("number"))["m"] or 0) + 1


def validate_contract(user, d, instance=None):
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    branch, student, course, group = get("branch"), get("student"), get("course"), get("group")
    start, end = get("start_date"), get("end_date")
    if instance is not None:
        if "course" in d and course.pk != instance.course_id and role_code(user) != RoleCode.ADMIN:
            raise PermissionDenied("Shartnoma kursini faqat Admin o'zgartiradi")
        if "student" in d and student.pk != instance.student_id:
            raise ValidationError({"student": "Talabani o'zgartirib bo'lmaydi"})
    new_type = d.get("type")
    if new_type and new_type != (instance.type if instance else Contract.Type.PAID) and not is_top(user):
        raise PermissionDenied("Shartnoma turini faqat Admin va Bosh menejer o'zgartiradi")
    if student.branch_id != branch.pk:
        raise ValidationError({"student": "Talaba boshqa filialdan"})
    if _changed(instance, "course", course) and (course.status != Status.ACTIVE or not course.branches.filter(pk=branch.pk).exists()):
        raise ValidationError({"course": "Bu kurs filialda faol emas"})
    if group.branch_id != branch.pk or group.course_id != course.pk:
        raise ValidationError({"group": "Guruh shu filial va kursdan bo'lsin"})
    if _changed(instance, "group", group) and period_status(group.start_date, group.end_date) == NOFAOL:
        raise ValidationError({"group": "Guruh nofaol"})
    if end and end < start:
        raise ValidationError({"end": "Boshlanish sanadan kichik bo'lolmaydi"})
    if end and not get("stop_reason"):
        raise ValidationError({"stop_reason": "Tugash sana kiritilsa, to'xtatish sababi majburiy"})
    if period_status(start, end) != NOFAOL:
        dup = Contract.objects.filter(student=student, group=group).exclude(pk=getattr(instance, "pk", None)).exclude(end_date__lt=today())
        if dup.exists():
            raise ValidationError({"group": "Bu talabaning shu guruhda faol shartnomasi bor"})


STOP_FIELDS = {"end", "stop_reason", "comment"}
STOP_DAYS = 30


def check_contract_edit(user, c, fields, end_date=None):
    """Tahrirlash muddati boshlanish sanasi bo'yicha (6.4). Istisno (buyurtmachi qarori 2026-10-13): faqat to'xtatish
    (tugash sanasi, sabab, izoh) — muddatdan qat'i nazar, lekin tugash sanasi oxirgi 30 kun ichida bo'lsin."""
    if is_top(user):
        return
    if fields and set(fields) <= STOP_FIELDS:
        if not can(user, "contracts", "e"):
            raise PermissionDenied("Sizning rolingizda bu amalga ruxsat yo'q")
        if end_date and (today() - end_date).days > STOP_DAYS:
            raise ValidationError({"end": f"Tugash sanasini oxirgi {STOP_DAYS} kun ichida qo'yish mumkin"})
        return
    check_edit_window(user, "contracts", c.start_date)


@transaction.atomic
def save_contract(user, d, instance=None):
    d = dict(d)
    if not d.get("end_date", getattr(instance, "end_date", None)):
        d["stop_reason"] = ""
    validate_contract(user, d, instance)
    if instance is None:
        c = Contract(**d, number=next_contract_number(d["branch"]), created_by=user, updated_by=user)
        c.save()
        audit.log_create(user, c)
        notif.contract_saved(c, user, True)
        from apps.calls import auto_sms

        auto_sms.contract_created(c)  # avtomatik SMS (qoida yoqilgan bo'lsa); xato shartnoma saqlanishini buzmaydi
        return c
    before = audit.snapshot(instance)
    type_changed = "type" in d and d["type"] != instance.type
    for k, v in d.items():
        setattr(instance, k, v)
    instance.updated_by = user
    instance.save()
    n = calc.recalculate(instance.attendance.all()) if type_changed else 0
    audit.log_update(user, instance, before, detail=f"Turi o'zgardi — {n} ta davomat qatori qayta hisoblandi" if type_changed else "")
    notes = []
    if type_changed:
        notes.append(f"Turi: {instance.type}")
    if instance.end_date and str(instance.end_date) != str(before.get("end_date") or ""):
        notes.append(f"Tugadi: {instance.end_date:%d.%m.%Y}" + (f" ({instance.stop_reason})" if instance.stop_reason else ""))
    if notes:
        notif.contract_saved(instance, user, False, "; ".join(notes))
    return instance


# ------------------------------------------------------------------ davomat olish

def is_teacher_mode(user):
    """Ustoz o'z guruhida faqat bugungi davomatni oladi; menejer va administratorlar o'tgan sanani tuzatadi."""
    return role_code(user) in TEACHERS


def check_take(user, group, d):
    if not can(user, "attendance", "a"):
        raise PermissionDenied("Davomatni faqat ustoz oladi")
    if is_teacher_mode(user) and group.teacher_id != user.pk:
        raise PermissionDenied("Bu guruh davomatini uning ustozi oladi")
    if d > today():
        raise ValidationError({"date": "Kelajak sana bilan davomat olib bo'lmaydi"})
    if is_teacher_mode(user) and d != today():
        raise ValidationError({"date": "Faqat bugunga davomat olish mumkin, xolos"})
    if not has_lesson(group, d):
        raise ValidationError({"date": f"Guruhning bu sanaga darsi yo'q ({group.day_pattern})"})


def roster(group, d):
    """Shu sanada guruhda faol shartnomalar."""
    return Contract.objects.filter(group=group).filter(active_on(d)).select_related("student").order_by("student__first_name", "student__last_name")


def allowed_statuses(user):
    return set(AttendanceStatus.objects.filter(roles=user.role_id).values_list("code", flat=True)) if user.role_id else set()


def nearest_lesson(group, d, back=14):
    for i in range(back):
        x = d - datetime.timedelta(days=i)
        if has_lesson(group, x):
            return x
    return None


def _check_substitute(user, group, sub_teacher, sub_supporter):
    if not (sub_teacher or sub_supporter):
        return
    if role_code(user) not in SUBSTITUTE_SETTERS:
        raise PermissionDenied("O'rindoshni Admin, Bosh menejer va administratorlar belgilaydi")
    if sub_teacher and (role_code(sub_teacher) not in TEACHERS or sub_teacher.pk == group.teacher_id):
        raise ValidationError({"sub_teacher": "O'rindosh ustoz guruhning o'z ustozidan farq qiladigan ustoz bo'lsin"})
    if sub_supporter and (role_code(sub_supporter) not in SUPPORTERS or sub_supporter.pk == group.supporter_id):
        raise ValidationError({"sub_supporter": "O'rindosh yordamchi guruhning o'z yordamchisidan farq qilsin"})


def _contact_for(status, current):
    if status in (calc.KELDI, calc.NOFAOL):
        return ""
    return current or Attendance.Contact.TO_CALL


@transaction.atomic
def mark(user, group, d, marks, sub_teacher=None, sub_supporter=None):
    """marks: [{contract, status, comment?}]. Bor qator yangilanadi, yo'g'i yaratiladi; qarz va KPI darhol hisoblanadi.
    O'tgan sanadagi qatorni yaratish va o'zgartirish rol muddati bo'yicha (6.4). Qaytaradi: saqlangan qatorlar."""
    check_take(user, group, d)
    check_edit_window(user, "attendance", d, op="a")
    _check_substitute(user, group, sub_teacher, sub_supporter)
    allowed = allowed_statuses(user)
    active = {c.pk: c for c in roster(group, d)}
    existing = {a.contract_id: a for a in Attendance.objects.filter(group=group, date=d).select_related("contract")}
    names = dict(AttendanceStatus.objects.values_list("code", "name"))
    c_calc = calc.Calculator()
    out = []
    for m in marks:
        contract = active.get(m["contract"].pk if hasattr(m["contract"], "pk") else m["contract"])
        if contract is None:
            raise ValidationError({"contract": "Bu talaba shu sanada guruhda faol emas"})
        st, comment = m["status"], (m.get("comment") or "").strip()
        if st not in allowed:
            raise PermissionDenied(f"Sizning rolingiz «{names.get(st, st)}» statusini qo'ya olmaydi")
        a = existing.get(contract.pk)
        if st == calc.SABABLI and not (comment or (a and a.status == st and a.comment)):
            raise ValidationError({"comment": "Sababli bo'lsa, sababini yozing"})
        if a is None:
            a = Attendance(branch=group.branch, group=group, course=group.course, contract=contract, day_pattern=group.day_pattern, date=d, status=st,
                           teacher=sub_teacher or group.teacher, supporter=sub_supporter or group.supporter, comment=comment,
                           contact_status=_contact_for(st, ""), created_by=user, updated_by=user)
            c_calc.apply(a, contract.type)
            a.save()
            audit.log_create(user, a)
        else:
            before = audit.snapshot(a)
            a.status = st
            if comment:
                a.comment = comment
            a.contact_status = _contact_for(st, a.contact_status)
            if sub_teacher:
                a.teacher = sub_teacher
            if sub_supporter:
                a.supporter = sub_supporter
            a.updated_by = user
            c_calc.apply(a, contract.type)
            a.save()
            audit.log_update(user, a, before)
        out.append(a)
    return out


@transaction.atomic
def mark_all_present(user, group, d, **sub):
    marked = set(Attendance.objects.filter(group=group, date=d).values_list("contract_id", flat=True))
    todo = [{"contract": c, "status": calc.KELDI} for c in roster(group, d) if c.pk not in marked]
    return mark(user, group, d, todo, **sub) if todo else []


@transaction.atomic
def set_contact(user, a, contact, comment=None):
    """Kelmaganlar: bog'lanish holati. «Gaplashildi» bo'lsa izoh majburiy (19-bo'lim 13-xato tuzatilgan)."""
    if not (can(user, "attendance", "e") or can(user, "attendance", "a")):
        raise PermissionDenied("Sizning rolingizda bu amalga ruxsat yo'q")
    if a.status not in (calc.BESABAB, calc.SABABLI):
        raise ValidationError({"contact": "Bog'lanish holati faqat kelmaganlar uchun"})
    if contact not in Attendance.Contact.values:
        raise ValidationError({"contact": "Noto'g'ri qiymat"})
    text = (comment if comment is not None else a.comment or "").strip()
    if contact == Attendance.Contact.TALKED and not text:
        raise ValidationError({"comment": "«Gaplashildi» bo'lsa izoh majburiy"})
    before = audit.snapshot(a)
    a.contact_status, a.comment, a.updated_by = contact, text, user
    a.save(update_fields=["contact_status", "comment", "updated_by", "updated_at"])
    audit.log_update(user, a, before)
    return a


# ------------------------------------------------------------------ qoldirilgan darslar (9-bo'lim)

@transaction.atomic
def request_makeup(user, a, makeup_date, comment):
    if role_code(user) not in TEACHERS or a.teacher_id != user.pk:
        raise PermissionDenied("So'rovni darsni o'tgan ustoz yuboradi")
    if a.status != calc.BESABAB:
        raise ValidationError({"detail": "Faqat besabab (X) qatorga so'rov yuboriladi"})
    if a.makeups.filter(status__in=[MakeupRequest.Status.PENDING, MakeupRequest.Status.APPROVED]).exists():
        raise ValidationError({"detail": "Bu dars uchun so'rov allaqachon yuborilgan"})
    if makeup_date < a.date:
        raise ValidationError({"makeup_date": "Qoldirilgan sanadan oldin bo'lishi mumkin emas"})
    if makeup_date > today():
        raise ValidationError({"makeup_date": "Kelajak sana bo'lishi mumkin emas"})
    if not (comment or "").strip():
        raise ValidationError({"comment": "Izoh majburiy"})
    m = MakeupRequest.objects.create(attendance=a, teacher=user, makeup_date=makeup_date, comment=comment.strip(), created_by=user, updated_by=user)
    audit.log_create(user, m)
    notif.makeup_requested(m)
    return m


def _review(user, m):
    if not can(user, "attendance", "p"):
        raise PermissionDenied("So'rovni Bosh menejer, Filial menejeri va administratorlar ko'rib chiqadi")
    if m.status != MakeupRequest.Status.PENDING:
        raise ValidationError({"detail": "So'rov allaqachon ko'rib chiqilgan"})


@transaction.atomic
def approve_makeup(user, m):
    _review(user, m)
    a = Attendance.objects.select_related("contract").select_for_update().get(pk=m.attendance_id)
    before = audit.snapshot(a)
    a.status = calc.SABABLI
    a.comment = f"Dars yetkazildi ({m.makeup_date:%d.%m.%Y}): {m.comment}"
    a.contact_status = a.contact_status or Attendance.Contact.TALKED
    a.updated_by = user
    calc.calculate(a)
    a.save()
    audit.log_update(user, a, before, detail="X → 0 (dars yetkazildi)")
    before_m = audit.snapshot(m)
    m.status, m.reviewed_by, m.reviewed_at, m.updated_by = MakeupRequest.Status.APPROVED, user, timezone.now(), user
    m.save()
    audit.log_update(user, m, before_m)
    return m


@transaction.atomic
def reject_makeup(user, m, reason):
    _review(user, m)
    if not (reason or "").strip():
        raise ValidationError({"reason": "Sababini yozing"})
    before = audit.snapshot(m)
    m.status, m.reviewed_by, m.reviewed_at, m.reject_reason, m.updated_by = MakeupRequest.Status.REJECTED, user, timezone.now(), reason.strip(), user
    m.save()
    audit.log_update(user, m, before)
    return m


# ------------------------------------------------------------------ statistika

def attendance_stats(qs):
    """Guruh va ustoz bo'yicha: qatorlar, keldi, sababli, besabab (Nofaol hisobga olinmaydi)."""
    qs = qs.exclude(status=calc.NOFAOL)
    agg = dict(n=Count("id"), came=Count("id", filter=Q(status=calc.KELDI)), sab=Count("id", filter=Q(status=calc.SABABLI)),
               bes=Count("id", filter=Q(status=calc.BESABAB)))
    return {
        "by_group": list(qs.values("group").annotate(**agg).order_by()),
        "by_teacher": list(qs.values("teacher").annotate(**agg).order_by()),
    }


# ------------------------------------------------------------------ M6: baholash (talaba → ustoz), ota-onalar bilan aloqa

def _active_contract(contract, on, field="contract"):
    if contract.start_date > on or (contract.end_date and contract.end_date < on):
        raise ValidationError({field: "Shartnoma shu sanada faol emas"})


@transaction.atomic
def save_evaluation(user, d):
    """Talaba ustozni baholaydi: guruh va ustoz shartnomadan, 5 mezon 0–10 (CLAUDE.md 7.4)."""
    c = d["contract"]
    d = dict(d, branch=c.branch, group=c.group, teacher=c.group.teacher)
    d.setdefault("date", today())
    if d["date"] > today():
        raise ValidationError({"date": "Kelajak sana bo'lishi mumkin emas"})
    _active_contract(c, d["date"])
    for i in range(1, 6):
        if not 0 <= int(d.get(f"s{i}", -1)) <= 10:
            raise ValidationError({f"s{i}": "0 dan 10 gacha baho"})
    from .models import TeacherEvaluation

    e = TeacherEvaluation.objects.create(**d, created_by=user, updated_by=user)
    audit.log_create(user, e)
    return e


@transaction.atomic
def save_parent_call(user, d, instance=None):
    """Ota-ona bilan aloqa: kurs va guruh shartnomadan; yaratilgandan keyin faqat sana va izoh o'zgaradi (7.4)."""
    from .models import ParentCall

    d = dict(d)
    if instance is not None:
        check_edit_window(user, "parentCalls", instance.date)
        d = {k: v for k, v in d.items() if k in ("date", "comment")}
    else:
        c = d["contract"]
        d.update(branch=c.branch, course=c.course, group=c.group)
    when = d.get("date", getattr(instance, "date", None)) or today()
    d["date"] = when
    if when > today():
        raise ValidationError({"date": "Kelajak sana bilan kiritib bo'lmaydi"})
    if "comment" in d and not (d["comment"] or "").strip():
        raise ValidationError({"comment": "Izoh majburiy"})
    if instance is None:
        p = ParentCall.objects.create(**d, created_by=user, updated_by=user)
        audit.log_create(user, p)
        return p
    before = audit.snapshot(instance)
    for k, v in d.items():
        setattr(instance, k, v)
    instance.updated_by = user
    instance.save()
    audit.log_update(user, instance, before)
    return instance

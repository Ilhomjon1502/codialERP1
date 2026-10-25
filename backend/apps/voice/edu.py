"""Ovozli buyruq: lidlar, shartnomalar va davomat (2026-10-25). Moslash — `actions` dagi kabi (`pick`, `Need`, `Bad`), bajarish — saytdagi servislar:
`crm.services.create_lead / update_lead / add_comment`, `education.services.save_contract / check_contract_edit / mark / set_contact`."""

import datetime
import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Status
from apps.core.permissions import NO_PERMISSION, can, check_edit_window
from apps.core.services import soft_delete
from apps.crm import services as crm
from apps.crm.models import AGE_GROUPS, LAPTOP_CHOICES, SOCIAL_STATUSES, Lead, Student
from apps.education import calc
from apps.education import services as edu
from apps.education.models import Attendance, Contract, Group
from apps.references.models import Course, LeadSource

from . import match
from .actions import Bad, Need, Resolved, branch_of, day_line, escape, parse_date, pick
from .records import best, similar

LS = Lead.LeadStatus
STATUS_NAMES = {s.value: f"{s.value}. {s.label}" for s in LS}
MARKS = {"keldi": calc.KELDI, "sababli": calc.SABABLI, "besabab": calc.BESABAB, "kelmadi": calc.BESABAB, "1": calc.KELDI, "0": calc.SABABLI, "x": calc.BESABAB}
MARK_NAMES = {calc.KELDI: "Keldi", calc.SABABLI: "Sababli", calc.BESABAB: "Besabab"}


def phone9(v):
    digits = re.sub(r"\D", "", str(v or ""))
    return digits[-9:] if len(digits) >= 9 else ""


def lead_status(v):
    """«5», 5, «5. O'qishni boshladi», «o'qishni boshladi» → «5»."""
    s = str(v or "").strip()
    if s[:1].isdigit() and s[:1] in STATUS_NAMES:
        return s[:1]
    obj, _ = match.find(s, [(k, label) for k, label in STATUS_NAMES.items()])
    return obj


def parse_dt(v):
    if not v:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(v)[:16])
    except ValueError:
        return None
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def group_label(g):
    return f"{g.course.name} {g.number} ({g.teacher.full_name if g.teacher_id else '—'}, {g.time.start_time:%H:%M})"


def open_groups(branch, course=None):
    qs = Group.objects.filter(branch=branch).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())).select_related("course", "teacher", "time")
    if course is not None:
        qs = qs.filter(course=course)
    return qs.order_by("course__name", "number")


def pick_group(item, field, value, branch, course=None, required=True):
    groups = list(open_groups(branch, course))
    # «Frontend 3», «3-guruh», «#3» — raqam bo'yicha ham
    num = re.findall(r"\d+", str(value or ""))
    if value and num:
        exact = [g for g in groups if str(g.number) == num[-1] and (course is not None or similar(re.sub(r"\d+|#", "", str(value)), g.course.name))]
        if len(exact) == 1 and not (item.get("picked") or {}).get(field):
            return exact[0]
    return pick(item, field, "Guruh", value, [(g, group_label(g)) for g in groups], required=required)


def find_student(item, value, branch, qs=None):
    qs = qs if qs is not None else Student.objects.filter(branch=branch)
    p = phone9(value)
    if p:
        hits = list(qs.filter(Q(phone1=p) | Q(phone2=p) | Q(parent__phone=p)))
        if len(hits) == 1:
            return hits[0]
    rows = best(qs.order_by("first_name"), value, str)
    chosen = (item.get("picked") or {}).get("student")
    s = next((x for x in rows if str(x.pk) == str(chosen)), None) or (rows[0] if len(rows) == 1 else None)
    if chosen and s is None:
        s = qs.filter(pk=chosen).first()
    if s is None:
        if not rows:
            raise Bad(f"O'quvchi topilmadi: «{value}»")
        raise Need("student", f"«{value}» — qaysi o'quvchi?", [(str(x.pk), f"{x} · {x.phone1}"[:58]) for x in rows[:match.MAX_OPTIONS]])
    item.setdefault("picked", {})["student"] = str(s.pk)
    return s


def _choice(value, options):
    obj, _ = match.find(value, [(o, o) for o in options]) if value else (None, [])
    return obj


# ------------------------------------------------------------------ yangi lid

def r_lead_create(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    first, last = str(raw.get("first_name") or "").strip(), str(raw.get("last_name") or "").strip()
    try:
        first, last = crm.validate_name(first, "first_name"), crm.validate_name(last, "last_name")
        p1, p2 = crm.validate_phones(phone9(raw.get("phone1")), phone9(raw.get("phone2")), phone2_required=True)
    except Exception as e:  # noqa: BLE001 — DRF ValidationError: kartada sababi
        from .actions import error_text

        raise Bad(f"Talaba: {error_text(e)} (ism, familiya va 2 ta telefon kerak)") from None
    dup = crm.find_duplicate(branch, first, last, [p1, p2])
    if dup:
        raise Bad(f"{dup} avval kiritilgan — lidlar yoki shartnomalardan qidiring")
    src = pick(item, "source", "Manba", raw.get("source"), [(s, s.name) for s in LeadSource.objects.filter(status=Status.ACTIVE).order_by("name")])
    course = pick(item, "course", "Kurs", raw.get("course"), [(c, c.name) for c in Course.objects.filter(status=Status.ACTIVE, branches=branch).order_by("name")])
    status = lead_status(raw.get("status")) or LS.WAITING_GROUP
    data = {"source": src, "course": course, "status": status}
    lines = [f"Talaba: <b>{escape(first)} {escape(last)}</b>", f"Telefon: {p1}, {p2}", f"Manba: {escape(src.name)}", f"Kurs: {escape(course.name)}",
             f"Holat: {escape(STATUS_NAMES[status])}"]
    if status in (LS.CALL_BACK, LS.LATER):
        at = parse_dt(raw.get("callback_at"))
        if at is None:
            raise Bad("1- va 8-holatda qayta bog'lanish sanasi va vaqtini ayting")
        data["callback_at"] = at
        lines.append(f"Qayta bog'lanish: {timezone.localtime(at):%d.%m.%Y %H:%M}")
    if raw.get("group"):
        g = pick_group(item, "group", raw["group"], branch, course)
        data["group"] = g
        lines.append(f"Guruh: {escape(group_label(g))}")
    if raw.get("demo_date"):
        data["demo_date"] = parse_date(raw["demo_date"], None)
        if data["demo_date"]:
            lines.append(f"Sinov darsi: {data['demo_date']:%d.%m.%Y}")
    for key, field, options in (("age_group", "age_group", AGE_GROUPS), ("social", "social_status", SOCIAL_STATUSES), ("laptop", "laptop", LAPTOP_CHOICES)):
        v = _choice(raw.get(key), options)
        if v:
            data[field] = v
            lines.append(f"{dict(age_group='Yosh', social_status='Ijtimoiy holat', laptop='Noutbuk')[field]}: {escape(v)}")
    comment = str(raw.get("comment") or "")
    if comment:
        lines.append(f"Izoh: {escape(comment)}")
    student = {"first_name": first, "last_name": last, "phone1": p1, "phone2": p2, "gender": raw.get("gender") if raw.get("gender") in ("Erkak", "Ayol") else ""}
    return Resolved("🧲 Yangi lid", lines, {"branch": branch, "data": data, "student": student, "comment": comment})


def x_lead_create(ctx, d):
    if not can(ctx.user, "leads", "a"):
        raise Bad(NO_PERMISSION)
    lead = crm.create_lead(ctx.user, d["branch"], dict(d["data"]), new_student=d["student"], comment=d["comment"])
    return f"✅ Lid qo'shildi: {escape(str(lead.student))} — {escape(STATUS_NAMES[lead.status])}"


# ------------------------------------------------------------------ lidni o'zgartirish / izoh / o'chirish

def find_lead(item, value):
    qs = Lead.objects.select_related("student", "course", "source", "group__course")
    p = phone9(value)
    if p:
        hits = list(qs.filter(Q(student__phone1=p) | Q(student__phone2=p) | Q(student__parent__phone=p)))
        if len(hits) == 1:
            return hits[0]
    chosen = (item.get("picked") or {}).get("lead")
    if chosen:
        lead = qs.filter(pk=chosen).first()
        if lead:
            return lead
    rows = best(qs.order_by("-created_at"), value, lambda x: str(x.student))
    if len(rows) == 1:
        item.setdefault("picked", {})["lead"] = str(rows[0].pk)
        return rows[0]
    if not rows:
        raise Bad(f"Lid topilmadi: «{value}»")
    raise Need("lead", f"«{value}» — qaysi lid?", [(str(x.pk), f"{x.student} · {x.course.name} · {x.status}-holat"[:58]) for x in rows[:match.MAX_OPTIONS]])


def r_lead_update(ctx, item):
    raw = item["raw"]
    if not raw.get("student"):
        raise Bad("Qaysi lid — ism yoki telefon aytilmadi")
    lead = find_lead(item, raw["student"])
    head = f"Lid: <b>{escape(str(lead.student))}</b> · {escape(lead.course.name)} · {escape(STATUS_NAMES[lead.status])}"
    if raw.get("delete"):
        return Resolved("🗑 Lidni o'chirish", [head, "<b>O'chiriladi</b> (arxivda qoladi)"], {"lead": lead.pk, "delete": True})
    s, data, lines = raw.get("set") or {}, {}, [head]
    st = lead_status(s.get("status")) if s.get("status") else None
    if st and st != lead.status:
        data["status"] = st
        lines.append(f"Holat: {escape(STATUS_NAMES[lead.status])} → <b>{escape(STATUS_NAMES[st])}</b>")
    new_status = data.get("status", lead.status)
    if s.get("callback_at") or (st in (LS.CALL_BACK, LS.LATER) and st != lead.status):
        at = parse_dt(s.get("callback_at"))
        if at is None:
            raise Bad("1- va 8-holatda qayta bog'lanish sanasi va vaqtini ayting")
        data["callback_at"] = at
        lines.append(f"Qayta bog'lanish: <b>{timezone.localtime(at):%d.%m.%Y %H:%M}</b>")
    course = lead.course
    if s.get("course"):
        course = pick(item, "course", "Kurs", s["course"], [(c, c.name) for c in Course.objects.filter(status=Status.ACTIVE, branches=lead.branch).order_by("name")])
        if course.pk != lead.course_id:
            data["course"] = course
            lines.append(f"Kurs: {escape(lead.course.name)} → <b>{escape(course.name)}</b>")
    if s.get("source"):
        src = pick(item, "source", "Manba", s["source"], [(x, x.name) for x in LeadSource.objects.filter(status=Status.ACTIVE).order_by("name")])
        if src.pk != lead.source_id:
            data["source"] = src
            lines.append(f"Manba: {escape(lead.source.name)} → <b>{escape(src.name)}</b>")
    if s.get("group"):
        g = pick_group(item, "group", s["group"], lead.branch, course)
        if g.pk != lead.group_id:
            data["group"] = g
            lines.append(f"Guruh: <b>{escape(group_label(g))}</b>")
    if s.get("demo_date"):
        dd = parse_date(s["demo_date"], None)
        if dd and dd != lead.demo_date:
            data["demo_date"] = dd
            lines.append(f"Sinov darsi: <b>{dd:%d.%m.%Y}</b>")
    if s.get("demo_attended") in (True, False):
        data["demo_attended"] = s["demo_attended"]
        lines.append(f"Sinov darsiga: <b>{'keldi' if s['demo_attended'] else 'kelmadi'}</b>")
    comment = str(raw.get("comment") or "").strip()
    if comment:
        lines.append(f"Izoh qo'shiladi: {escape(comment)}")
    if not data and not comment:
        raise Bad(f"{lead.student}: nimani o'zgartirish aytilmadi")
    if new_status == LS.STARTED and not crm.has_contract(lead.student):
        lines.append("ℹ️ Shartnoma tuzish uchun: «… shartnoma tuz» deng")
    return Resolved("🧲 Lidni o'zgartirish" if data else "💬 Lidga izoh", lines, {"lead": lead.pk, "data": data, "comment": comment})


def x_lead_update(ctx, d):
    lead = Lead.objects.select_related("student", "branch").get(pk=d["lead"])
    if d.get("delete"):
        if not can(ctx.user, "leads", "d"):
            raise Bad(NO_PERMISSION)
        check_edit_window(ctx.user, "leads", lead.created_at, op="d")
        soft_delete(lead, ctx.user, check_usage=False)
        return f"✅ Lid o'chirildi: {escape(str(lead.student))}"
    if d["data"]:
        crm.update_lead(ctx.user, lead, d["data"], comment=d["comment"])
    else:
        crm.add_comment(ctx.user, lead, d["comment"])
    return f"✅ Lid saqlandi: {escape(str(lead.student))}"


# ------------------------------------------------------------------ shartnomalar

def r_contract_create(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    if not raw.get("student"):
        raise Bad("Kimga shartnoma — ism aytilmadi")
    st = find_student(item, raw["student"], branch)
    lead = Lead.objects.filter(student=st).select_related("course", "group").first()
    courses = [(c, c.name) for c in Course.objects.filter(status=Status.ACTIVE, branches=branch).order_by("name")]
    course = pick(item, "course", "Kurs", raw["course"], courses) if raw.get("course") else (lead.course if lead else pick(item, "course", "Kurs", "", courses))
    group = pick_group(item, "group", raw.get("group") or (str(lead.group.number) if lead and lead.group_id and lead.course_id == course.pk else ""), branch, course)
    start = parse_date(raw.get("start_date"), None) or (lead.demo_date if lead and lead.demo_date else ctx.day)
    ctype = Contract.Type.GRANT if str(raw.get("type") or "").lower().startswith("grant") else Contract.Type.PAID
    lines = [f"Talaba: <b>{escape(str(st))}</b>", f"Kurs: {escape(course.name)}", f"Guruh: <b>{escape(group_label(group))}</b>",
             f"Boshlanish: {start:%d.%m.%Y}", f"Turi: {ctype}"]
    if lead and lead.status != LS.STARTED:
        lines.append(f"Lid holati: {escape(STATUS_NAMES[lead.status])} → <b>{escape(STATUS_NAMES[LS.STARTED])}</b>")
    return Resolved("📄 Yangi shartnoma", lines, {"branch": branch, "student": st, "course": course, "group": group, "start_date": start, "type": ctype,
                                                 "lead": lead.pk if lead and lead.status != LS.STARTED else None})


@transaction.atomic
def x_contract_create(ctx, d):
    if not can(ctx.user, "contracts", "a"):
        raise Bad(NO_PERMISSION)
    c = edu.save_contract(ctx.user, {k: d[k] for k in ("branch", "student", "course", "group", "start_date", "type")})
    if d.get("lead"):
        lead = Lead.objects.get(pk=d["lead"])
        crm.update_lead(ctx.user, lead, {"status": LS.STARTED, "group": d["group"], "course": d["course"]})
    return f"✅ Shartnoma tuzildi: {escape(str(c))}"


def find_contract(item, value):
    qs = Contract.objects.select_related("student", "course", "group__course", "branch")
    chosen = (item.get("picked") or {}).get("contract")
    if chosen:
        c = qs.filter(pk=chosen).first()
        if c:
            return c
    p = phone9(value)
    rows = list(qs.filter(Q(student__phone1=p) | Q(student__phone2=p))) if p else best(qs, value, lambda c: str(c.student))
    active = [c for c in rows if not c.end_date or c.end_date >= timezone.localdate()]
    rows = active or rows
    if len(rows) == 1:
        item.setdefault("picked", {})["contract"] = str(rows[0].pk)
        return rows[0]
    if not rows:
        raise Bad(f"Shartnoma topilmadi: «{value}»")
    raise Need("contract", f"«{value}» — qaysi shartnoma?", [(str(c.pk), f"{c} · {c.course.name} {c.group.number}"[:58]) for c in rows[:match.MAX_OPTIONS]])


def r_contract_update(ctx, item):
    raw = item["raw"]
    if not raw.get("student"):
        raise Bad("Qaysi shartnoma — ism aytilmadi")
    c = find_contract(item, raw["student"])
    s, data = raw.get("set") or {}, {}
    lines = [f"Shartnoma: <b>{escape(str(c))}</b> · {escape(c.course.name)} {c.group.number} · {c.start_date:%d.%m.%Y} dan"]
    if s.get("stop") or s.get("end_date") or s.get("stop_reason"):
        end = parse_date(s.get("end_date"), ctx.day)
        reasons = [(r, r) for r in Contract.StopReason.values]
        reason = pick(item, "stop_reason", "To'xtatish sababi", s.get("stop_reason"), reasons)
        data.update(end_date=end, stop_reason=reason)
        lines += [f"Tugash sanasi: <b>{end:%d.%m.%Y}</b>", f"Sabab: <b>{escape(reason)}</b>"]
    if s.get("group"):
        g = pick_group(item, "group", s["group"], c.branch, c.course)
        if g.pk != c.group_id:
            data["group"] = g
            lines.append(f"Guruh: {escape(str(c.group))} → <b>{escape(group_label(g))}</b>")
    if s.get("start_date"):
        sd = parse_date(s["start_date"], None)
        if sd and sd != c.start_date:
            data["start_date"] = sd
            lines.append(f"Boshlanish: {c.start_date:%d.%m.%Y} → <b>{sd:%d.%m.%Y}</b>")
    if s.get("type"):
        t = Contract.Type.GRANT if str(s["type"]).lower().startswith("grant") else Contract.Type.PAID
        if t != c.type:
            data["type"] = t
            lines.append(f"Turi: {c.type} → <b>{t}</b> (qarz qayta hisoblanadi)")
    if s.get("resume"):  # to'xtatilganni qayta tiklash
        data.update(end_date=None, stop_reason="")
        lines.append("<b>Qayta faollashtiriladi</b> (tugash sanasi olib tashlanadi)")
    if s.get("comment"):
        data["comment"] = str(s["comment"])
        lines.append(f"Izoh: {escape(data['comment'])}")
    if not data:
        raise Bad(f"{c}: nimani o'zgartirish aytilmadi")
    return Resolved("📄 Shartnomani o'zgartirish", lines, {"contract": c.pk, "data": data})


def x_contract_update(ctx, d):
    c = Contract.objects.select_related("student", "course", "group", "branch").get(pk=d["contract"])
    data = dict(d["data"])
    fields = {"end" if k == "end_date" else k for k in data}
    edu.check_contract_edit(ctx.user, c, fields, data.get("end_date"))
    edu.save_contract(ctx.user, data, instance=c)
    return f"✅ Shartnoma saqlandi: {escape(str(c))}"


# ------------------------------------------------------------------ davomat

def r_attendance(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    d = parse_date(raw.get("date"), ctx.day)
    g = pick_group(item, "group", raw.get("group"), branch)
    try:
        edu.check_take(ctx.user, g, d)
    except Exception as e:  # noqa: BLE001
        from .actions import error_text

        raise Bad(error_text(e)) from None
    roster = list(edu.roster(g, d))
    if not roster:
        raise Bad(f"{group_label(g)}: {d:%d.%m.%Y} da faol o'quvchi yo'q")
    marks, lines = {}, [f"Guruh: <b>{escape(group_label(g))}</b>", day_line(d, ctx)]
    for i, m in enumerate(raw.get("marks") or []):
        st = MARKS.get(match.norm(m.get("status")).replace("'", ""))
        if st is None:
            raise Bad(f"«{m.get('status')}» — Keldi, Sababli yoki Besabab bo'lsin")
        sub = {"raw": {}, "picked": item.setdefault("picked", {})}
        c = pick(sub, f"m{i}", f"«{m.get('student')}»", m.get("student"), [(c, str(c.student)) for c in roster])
        comment = str(m.get("comment") or "").strip()
        if st == calc.SABABLI and not comment:
            raise Bad(f"{c.student}: sababli bo'lsa sababini ayting")
        marks[c.pk] = {"contract": c.pk, "status": st, "comment": comment}
    marked = set(Attendance.objects.filter(group=g, date=d).values_list("contract_id", flat=True))
    rest = [c for c in roster if c.pk not in marks and c.pk not in marked] if raw.get("all_present", True) else []
    for c in rest:
        marks[c.pk] = {"contract": c.pk, "status": calc.KELDI, "comment": ""}
    if not marks:
        raise Bad("Davomat allaqachon olingan — kimni o'zgartirish kerakligini ayting")
    names = {c.pk: str(c.student) for c in roster}
    for st in (calc.KELDI, calc.SABABLI, calc.BESABAB):
        who = [names[k] for k, m in marks.items() if m["status"] == st]
        if who:
            lines.append(f"{MARK_NAMES[st]} ({len(who)}): " + escape(", ".join(who) if len(who) <= 8 or st != calc.KELDI else f"{', '.join(who[:6])} va yana {len(who) - 6} ta"))
    if marked:
        lines.append(f"Avval belgilangan: {len(marked)} ta")
    return Resolved("📋 Davomat", lines, {"group": g.pk, "date": d, "marks": list(marks.values())})


def x_attendance(ctx, d):
    g = Group.objects.select_related("branch", "course", "teacher", "supporter", "day_pattern").get(pk=d["group"])
    rows = edu.mark(ctx.user, g, d["date"], d["marks"])
    return f"✅ Davomat saqlandi: {len(rows)} ta o'quvchi"


CONTACTS = [(v, v) for v in Attendance.Contact.values]


def r_attendance_contact(ctx, item):
    raw = item["raw"]
    if not raw.get("student"):
        raise Bad("Qaysi o'quvchi — ism aytilmadi")
    since = timezone.localdate() - datetime.timedelta(days=14)
    qs = Attendance.objects.filter(status__in=[calc.BESABAB, calc.SABABLI], date__gte=since).select_related("contract__student", "group__course").order_by("-date")
    d = parse_date(raw.get("date"), None)
    if d:
        qs = qs.filter(date=d)
    rows = best(qs, raw["student"], lambda a: str(a.contract.student))
    chosen = (item.get("picked") or {}).get("attendance")
    a = next((x for x in rows if str(x.pk) == str(chosen)), None) or (rows[0] if len(rows) == 1 else None)
    if a is None:
        if not rows:
            raise Bad(f"Oxirgi 14 kunda kelmaganlar orasida «{raw['student']}» topilmadi")
        raise Need("attendance", "Qaysi dars?", [(str(x.pk), f"{x.contract.student} · {x.date:%d.%m} · {x.group}"[:58]) for x in rows[:match.MAX_OPTIONS]])
    item.setdefault("picked", {})["attendance"] = str(a.pk)
    contact = pick(item, "contact", "Bog'lanish holati", raw.get("contact") or "Gaplashildi", CONTACTS)
    comment = str(raw.get("comment") or "").strip()
    lines = [f"O'quvchi: <b>{escape(str(a.contract.student))}</b> · {a.date:%d.%m} · {escape(str(a.group))} ({MARK_NAMES.get(a.status, a.status)})",
             f"Bog'lanish: {escape(a.contact_status or '—')} → <b>{escape(contact)}</b>"]
    if comment:
        lines.append(f"Izoh: {escape(comment)}")
    return Resolved("📞 Kelmagan o'quvchi bilan bog'lanish", lines, {"attendance": a.pk, "contact": contact, "comment": comment or None})


def x_attendance_contact(ctx, d):
    a = Attendance.objects.select_related("contract__student").get(pk=d["attendance"])
    edu.set_contact(ctx.user, a, d["contact"], d["comment"])
    return f"✅ Saqlandi: {escape(str(a.contract.student))} — {escape(d['contact'])}"


HANDLERS = {
    "lead_create": (r_lead_create, x_lead_create),
    "lead_update": (r_lead_update, x_lead_update),
    "contract_create": (r_contract_create, x_contract_create),
    "contract_update": (r_contract_update, x_contract_update),
    "attendance": (r_attendance, x_attendance),
    "attendance_contact": (r_attendance_contact, x_attendance_contact),
}

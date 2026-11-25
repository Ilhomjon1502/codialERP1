"""Qo'ng'iroq qilayotgan odam haqida qisqa karta — qabul telefonidagi ilova qo'ng'iroq ekranida ko'rsatadi (buyurtmachi so'rovi 2026-11-25).

Matn serverda tuziladi (ilovani yangilamasdan o'zgartirish uchun): {found, title, badge, lines: [...]}.
Qarz summasi ko'rsatilmaydi — faqat «Qarzi bor» belgisi (telefon ekranini boshqalar ham ko'rishi mumkin).
"""

from django.utils import timezone

from apps.core.permissions import today
from apps.crm.models import InboxLead
from apps.education import services as edu
from apps.education.models import Attendance, Contract

from . import services
from .models import CallRecord

MAX_COMMENT = 140


def _dt(value):
    return timezone.localtime(value).strftime("%d.%m %H:%M")


def _d(value):
    return value.strftime("%d.%m")


def _cut(text):
    text = " ".join((text or "").split())
    return text if len(text) <= MAX_COMMENT else text[: MAX_COMMENT - 1] + "…"


def _history(branch_id, phone, now):
    """«3-marta bog'lanish» va oldingi gaplashilgan qo'ng'iroq (hozirgi qo'ng'iroq jurnalda hali yo'q)."""
    qs = CallRecord.objects.filter(branch_id=branch_id, phone=phone, started_at__lt=now)
    n = qs.count()
    if not n:
        return ["Birinchi qo'ng'iroq"]
    line = f"{n + 1}-marta bog'lanish"
    last = qs.filter(duration__gt=0).order_by("-started_at").first()
    if last:
        line += f" · oxirgi suhbat {_dt(last.started_at)} ({last.duration // 60}:{last.duration % 60:02d})"
    else:
        line += " · oldin gaplashilmagan"
    return [line]


def _group_line(group):
    return f"{group} · {group.day_pattern.name} {group.time} · ustoz {group.teacher.full_name}"


def _contracts(student):
    on = today()
    qs = Contract.objects.filter(student=student).filter(edu.active_on(on))
    return list(edu.with_balance(qs).select_related("group__course", "group__day_pattern", "group__time", "group__teacher"))


def _student_lines(student):
    lines = []
    contracts = _contracts(student)
    for c in contracts[:2]:
        lines.append(_group_line(c.group))
    last = Attendance.objects.filter(contract__student=student).order_by("-date").first()
    if last:
        lines.append(f"Oxirgi dars {_d(last.date)}: {last.get_status_display()}")
    if any((c.balance or 0) > 0 for c in contracts):
        lines.append("💰 Qarzi bor")
    return lines, bool(contracts)


def _lead_lines(lead):
    lines = [f"{lead.course.name} · {lead.source.name}", f"Holat: {lead.get_status_display()}"]
    if lead.demo_date:
        demo = f"Sinov darsi: {_d(lead.demo_date)}"
        if lead.group_id:
            demo += f" · {lead.group} · {lead.group.time}"
        if lead.demo_attended is not None:
            demo += " · keldi" if lead.demo_attended else " · kelmadi"
        lines.append(demo)
    if lead.callback_at:
        lines.append(f"Qayta bog'lanish: {_dt(lead.callback_at)}")
    comment = lead.comments.filter(is_deleted=False).order_by("-created_at").first()
    if comment:
        lines.append(f"Izoh: {_cut(comment.comment)}")
    return lines


def _inbox_card(item):
    lines = [f"Tushgan: {_dt(item.received_at)}" + (f" · {item.course_name}" if item.course_name else "")]
    if item.info:
        lines.append(_cut(item.info))
    note = item.notes.order_by("-created_at").first()
    if note:
        lines.append(f"Izoh: {_cut(note.comment)}")
    return {"title": item.name or "Ism ko'rsatilmagan", "badge": f"{item.kind} lidi (navbatda)", "lines": lines}


def card(device, raw_phone, now=None):
    now = now or timezone.now()
    phone = services.normalize(raw_phone or "")
    if not phone:
        return {"found": False, "title": raw_phone or "Yashirin raqam", "badge": "Raqam aniqlanmadi", "lines": []}
    branch_id = device.branch_id
    student, parent, lead = services.match(branch_id, {phone}).get(phone, (None, None, None))
    inbox = InboxLead.objects.filter(branch_id=branch_id, phone=phone, lead__isnull=True).order_by("-received_at").first()
    out = None
    if parent and (not student or parent.phone == phone and phone not in (student.phone1, student.phone2)):
        children = [c.full_name for c in parent.children.filter(is_deleted=False)[:3]]
        name = " ".join(x for x in (parent.first_name, parent.last_name) if x) or "Ota-ona"
        lines = [f"Farzandi: {', '.join(children)}"] if children else []
        if student:
            more, _ = _student_lines(student)
            lines += more
        out = {"title": name, "badge": parent.relation or "Ota-ona", "lines": lines}
    elif student:
        lines, active = _student_lines(student)
        if active:
            out = {"title": student.full_name, "badge": "O'quvchi", "lines": lines}
        elif lead:
            out = {"title": student.full_name, "badge": "Lid", "lines": _lead_lines(lead) + lines}
        else:
            out = {"title": student.full_name, "badge": "Sobiq o'quvchi", "lines": lines}
    elif inbox:
        out = _inbox_card(inbox)
    if out is None:
        out = {"title": "Yangi raqam", "badge": "Bazada yo'q", "lines": []}
        found = False
    else:
        found = True
    if inbox and student:  # bazada bor, lekin Instagram/saytdan yana yozgan
        out["lines"].append(f"{inbox.kind} orqali murojaat: {_dt(inbox.received_at)}")
    out["lines"] = out["lines"][:6] + _history(branch_id, phone, now)
    return {"found": found, **out}

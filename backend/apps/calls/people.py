"""Qabul telefonidagi ilova uchun (2026-11-27): qo'ng'iroqlar ro'yxatidagi raqamlarga ERP ismlari va ism/raqam bo'yicha qidiruv.

Faqat qurilma filiali; telefon ekranida ism, kimligi va raqam ko'rinadi (qarz va izohlar — faqat `lookup.card` da).
"""

import re

from django.db.models import Q

from apps.core.permissions import today
from apps.crm.models import InboxLead, Parent, Student
from apps.education import services as edu
from apps.education.models import Contract

from . import services

MAX_NUMBERS = 300  # bitta so'rovdagi raqamlar
MIN_QUERY = 3      # qidiruv uchun eng kam belgi — butun bazani varaqlab chiqib bo'lmasin
MAX_RESULTS = 20


def _active_students(student_ids):
    qs = Contract.objects.filter(student_id__in=student_ids).filter(edu.active_on(today()))
    return set(qs.values_list("student_id", flat=True))


def _parent_name(parent):
    return " ".join(x for x in (parent.first_name, parent.last_name) if x) or "Ota-ona"


def _student_badge(student, active, lead=None):
    if student.pk in active:
        return "O'quvchi"
    return "Lid" if lead else "Sobiq o'quvchi"


def names(device, raw_numbers):
    """{9 xonali raqam: {title, badge}} — bazada topilganlar."""
    phones = {services.normalize(str(n)) for n in list(raw_numbers or [])[:MAX_NUMBERS]}
    phones.discard("")
    found = services.match(device.branch_id, phones)
    active = _active_students({v[0].pk for v in found.values() if v[0]})
    out = {}
    for phone, (student, parent, lead) in found.items():
        if parent and (not student or parent.phone == phone and phone not in (student.phone1, student.phone2)):
            badge = parent.relation or "Ota-ona"
            if student:
                badge += f" · {student.full_name}"
            out[phone] = {"title": _parent_name(parent), "badge": badge}
        elif student:
            out[phone] = {"title": student.full_name, "badge": _student_badge(student, active, lead)}
    rest = phones - set(out)
    if rest:
        for item in InboxLead.objects.filter(branch_id=device.branch_id, phone__in=rest, lead__isnull=True).order_by("received_at"):
            out[item.phone] = {"title": item.name or "Ism ko'rsatilmagan", "badge": f"{item.kind} lidi"}
    return out


def _words_q(words, *fields):
    q = Q()
    for word in words:
        one = Q()
        for f in fields:
            one |= Q(**{f"{f}__icontains": word})
        q &= one
    return q


def search(device, raw_query):
    """[{title, badge, phone}] — talaba, ota-ona va navbatdagi lidlar; ism yoki raqam bo'laklari bo'yicha, ko'pi MAX_RESULTS."""
    query = " ".join(str(raw_query or "").split())
    digits = re.sub(r"[\s+()-]", "", query)
    by_number = digits.isdigit()
    if by_number and digits.startswith("998") and (query.startswith("+") or len(digits) > 9):
        digits = digits[3:]  # mamlakat kodi — bazada 9 xonali raqam
    if len(digits if by_number else query) < MIN_QUERY:
        return []
    if by_number:
        s_q = Q(phone1__contains=digits) | Q(phone2__contains=digits)
        p_q = i_q = Q(phone__contains=digits)
    else:
        words = query.split()
        s_q = _words_q(words, "first_name", "last_name", "father_name")
        p_q = _words_q(words, "first_name", "last_name")
        i_q = _words_q(words, "name")
    branch = device.branch_id
    students = list(Student.objects.filter(branch_id=branch).filter(s_q).prefetch_related("leads").order_by("first_name", "last_name")[:MAX_RESULTS])
    active = _active_students({s.pk for s in students})
    rows, seen = [], set()

    def add(title, badge, phone):
        if phone and phone not in seen and len(rows) < MAX_RESULTS:
            seen.add(phone)
            rows.append({"title": title, "badge": badge, "phone": phone})

    # faol o'quvchilar tepada
    for s in sorted(students, key=lambda x: x.pk not in active):
        badge = _student_badge(s, active, any(not x.is_deleted for x in s.leads.all()))
        for i, phone in enumerate((s.phone1, s.phone2), start=1):
            if not by_number or digits in (phone or ""):
                add(s.full_name, f"{badge} · {i}-telefon" if i == 2 else badge, phone)
    for p in Parent.objects.filter(branch_id=branch).filter(p_q).order_by("first_name", "last_name")[:MAX_RESULTS]:
        add(_parent_name(p), p.relation or "Ota-ona", p.phone)
    for item in InboxLead.objects.filter(branch_id=branch, lead__isnull=True).filter(i_q).order_by("-received_at")[:MAX_RESULTS]:
        add(item.name or "Ism ko'rsatilmagan", f"{item.kind} lidi", item.phone)
    return rows

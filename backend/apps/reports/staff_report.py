"""Xodimlar ish sifati hisoboti (PDF) — Administrator+Hisobchi va boshqa qabul xodimlari (2026-10-28, buyurtmachi so'rovi).

`collect(date_from, date_to)` — davr ko'rsatkichlari (audit, lid, shartnoma, to'lov, topshiriq, qo'ng'iroq, SMS);
`grade(...)` — 100 ballik baho va sabablar (mezonlar `CRITERIA`); `build_pdf(data)` — A4 PDF (reportlab).
Hisobotga faqat yig'ma raqamlar va xodim ismlari kiradi — talaba ismi va telefoni yo'q.
"""

import datetime as dt
import io
from collections import Counter, defaultdict
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Circle, Drawing, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.accounts.models import User
from apps.calls.models import CallRecord, SmsMessage
from apps.core.models import AuditLog
from apps.core.roles import RoleCode
from apps.crm.models import Lead, LeadComment, Student
from apps.education.models import Attendance, Contract, DueDismissal
from apps.finance.models import Payment
from apps.tasks.models import StaffTask

ROLES = (RoleCode.ADMINISTRATOR_HISOBCHI,)
ACTIVE_DAY_MIN = 5  # kuniga kamida shuncha amal (kirish/chiqishdan tashqari) — «ishlagan kun»
LATE_HOUR = 15  # oxirgi amal odatda shu soatdan oldin bo'lsa — eslatiladi
DISCOUNT_SHARE_WARN = Decimal("0.05")

# (kalit, nomi, maksimal ball)
CRITERIA = [
    ("activity", "Faollik (ishlagan kunlar)", 10),
    ("sales", "Sotuv (lid, shartnoma)", 25),
    ("money", "To'lov va undirish", 20),
    ("tasks", "Topshiriqlar muddatida", 15),
    ("quality", "Ma'lumot sifati", 15),
    ("follow", "Kelmaganlar va qayta bog'lanish", 15),
]
GRADES = [(80, "A'lo", "#1e9e57"), (55, "Yaxshi", "#2f73da"), (0, "Qoniqarsiz", "#d93b3b")]
SKIP_ACTIONS = ("login", "logout")
STEP = {"2": 2, "3": 3, "4": 4, "5": 5}  # lid voronkasi tartibi; orqaga qaytish — xato tuzatilgani


def _grade(score):
    for low, name, color in GRADES:
        if score >= low:
            return name, color
    return GRADES[-1][1:]


def fmt(n):
    return f"{int(n or 0):,}".replace(",", " ")


def _phones(st):
    ps = {st.phone1, st.phone2}
    if st.parent_id:
        ps.add(st.parent.phone)
    return {p for p in ps if p}


# ------------------------------------------------------------------ ma'lumot yig'ish

def collect(date_from, date_to, roles=ROLES, now=None):
    """[date_from, date_to] (ikkalasi ham kiradi) davr ko'rsatkichlari."""
    tz = timezone.get_current_timezone()
    now = now or timezone.localtime()
    t0 = dt.datetime.combine(date_from, dt.time(0), tzinfo=tz)
    t1 = dt.datetime.combine(date_to + dt.timedelta(days=1), dt.time(0), tzinfo=tz)
    workdays = [date_from + dt.timedelta(days=i) for i in range((date_to - date_from).days + 1)]
    workdays = [d for d in workdays if d.isoweekday() != 7]

    users = (User.objects.filter(role__code__in=roles, is_active=True).select_related("role").order_by("full_name"))
    staff = []
    for u in users:
        al = AuditLog.objects.filter(user=u, at__gte=t0, at__lt=t1)
        if not al.exists() and not u.last_login:
            continue  # tizimga hech kirmagan (masalan, import uchun yaratilgan) akkaunt
        staff.append(_person(u, al, t0, t1, workdays, now))

    return {"from": date_from, "to": date_to, "workdays": workdays, "now": now, "staff": staff,
            "team": _team(t0, t1, date_from, date_to, now, tz)}


def _person(u, al, t0, t1, workdays, now):
    days = defaultdict(list)
    lead_moves, reversals, contact_marks, callback_sets = Counter(), 0, 0, 0
    for a in al.exclude(action__in=SKIP_ACTIONS).only("at", "model", "action", "changes"):
        days[timezone.localtime(a.at).date()].append(timezone.localtime(a.at))
        for ch in a.changes or []:
            if not ch:
                continue
            if a.model == "Lid" and ch[0] == "status":
                lead_moves[(ch[1], ch[2])] += 1
                if ch[1] in STEP and ch[2] in STEP and STEP[ch[2]] < STEP[ch[1]]:
                    reversals += 1
            elif a.model == "Lid" and ch[0] == "callback_at":
                callback_sets += 1
            elif a.model == "Davomat" and ch[0] == "contact_status" and ch[2] and ch[2] != "Bog'lanishga":
                contact_marks += 1
    per_day = {d: len(days.get(d, [])) for d in workdays}
    active = [d for d in workdays if per_day[d] >= ACTIVE_DAY_MIN]
    last_times = sorted(max(ts).time() for d, ts in days.items() if len(ts) >= ACTIVE_DAY_MIN)
    first_times = sorted(min(ts).time() for d, ts in days.items() if len(ts) >= ACTIVE_DAY_MIN)

    leads = Lead.all_objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1, is_deleted=False)
    students = Student.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1)
    pays = Payment.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1)
    pagg = pays.aggregate(n=Count("id"), s=Sum("amount"), d=Sum("discount"))
    comments = LeadComment.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1)

    tasks = StaffTask.objects.filter(assignee=u, created_at__lt=t1).filter(Q(due_at__gte=t0, due_at__lt=t1) | Q(status=StaffTask.Status.OPEN, due_at__lt=t1))
    on_time = list(tasks.filter(done_at__isnull=False, done_at__lte=F("due_at")).values_list("title", flat=True))
    late = list(tasks.filter(done_at__isnull=False, done_at__gt=F("due_at")).values_list("title", "due_at", "done_at"))
    overdue = list(tasks.filter(status=StaffTask.Status.OPEN, due_at__lt=min(now, t1)).values_list("title", "due_at"))

    return {
        "user": u,
        "name": u.full_name,
        "role": u.role.name if u.role else "",
        "actions": sum(per_day.values()),
        "per_day": per_day,
        "active_days": len(active),
        "inactive_days": [d for d in workdays if d not in active and d < now.date()],
        "first_time": first_times[len(first_times) // 2] if first_times else None,
        "last_time": last_times[len(last_times) // 2] if last_times else None,
        "leads": leads.count(),
        "leads_commented": leads.filter(comments__isnull=False).distinct().count(),
        "lead_comments": comments.count(),
        "followup_comments": comments.filter(lead__status__in=["1", "8"]).count(),
        "lead_to_5": sum(n for (a, b), n in lead_moves.items() if b == "5"),
        "reversals": reversals,
        "callback_sets": callback_sets,
        "contact_marks": contact_marks,
        "demo_unfilled": Lead.objects.filter(created_by=u, status="3", demo_date__lt=now.date(), demo_attended__isnull=True).count(),
        "contracts": Contract.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1).count(),
        "students": students.count(),
        "students_no_parent": students.filter(parent__isnull=True).count(),
        "payments": pagg["n"] or 0,
        "paid_sum": pagg["s"] or Decimal(0),
        "discount_sum": pagg["d"] or Decimal(0),
        "discount_n": pays.filter(discount__gt=0).count(),
        "dues_dismissed": DueDismissal.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1).count(),
        "sms_manual": SmsMessage.objects.filter(created_by=u, created_at__gte=t0, created_at__lt=t1, direction=SmsMessage.Direction.OUT).count(),
        "tasks_on_time": on_time,
        "tasks_late": late,
        "tasks_overdue": overdue,
    }


def _team(t0, t1, date_from, date_to, now, tz):
    calls = list(CallRecord.objects.filter(started_at__gte=t0 - dt.timedelta(days=1), started_at__lt=t1 + dt.timedelta(days=3))
                 .values("phone", "started_at", "direction", "duration", "callback_at", "comment"))
    in_period = [c for c in calls if t0 <= c["started_at"] < t1]
    by_phone = defaultdict(list)
    for c in calls:
        by_phone[c["phone"]].append(c)

    def reached(ps, frm, to, talked):
        return any(frm <= c["started_at"] <= to and c["direction"] in ("Chiquvchi", "Kiruvchi") and (not talked or (c["duration"] or 0) > 0)
                   for p in ps for c in by_phone.get(p, []))

    missed = [c for c in in_period if c["direction"] in ("Javobsiz", "Rad etilgan") and 9 <= timezone.localtime(c["started_at"]).hour < 19]
    back = sorted((c["callback_at"] - c["started_at"]).total_seconds() / 60 for c in missed if c["callback_at"])
    out = [c for c in in_period if c["direction"] == "Chiquvchi"]

    ab = list(Attendance.objects.filter(date__gte=date_from, date__lte=min(date_to, now.date() - dt.timedelta(days=1)), status__in=["X", "0"])
              .select_related("contract__student__parent"))
    ab_called = ab_recorded = 0
    for a in ab:
        frm = dt.datetime.combine(a.date, dt.time(8), tzinfo=tz)
        ab_called += reached(_phones(a.contract.student), frm, frm + dt.timedelta(days=2, hours=12), True)
        ab_recorded += bool(a.contact_status) and a.contact_status != Attendance.Contact.TO_CALL

    follow = list(Lead.objects.filter(status__in=["1", "8"]).select_related("student__parent"))
    touched_ids = set(LeadComment.objects.filter(lead__in=follow, created_at__gte=t0, created_at__lt=t1).values_list("lead_id", flat=True))
    touched_ids |= {str(i) for i in AuditLog.objects.filter(model="Lid", action="update", at__gte=t0, at__lt=t1,
                                                              object_id__in=[str(lead.pk) for lead in follow]).values_list("object_id", flat=True)}
    touched = sum(1 for lead in follow if lead.pk in touched_ids or str(lead.pk) in touched_ids or reached(_phones(lead.student), t0, t1, False))

    return {
        "calls_in": sum(1 for c in in_period if c["direction"] == "Kiruvchi"),
        "calls_out": len(out),
        "calls_out_talked": sum(1 for c in out if (c["duration"] or 0) > 0),
        "calls_commented": sum(1 for c in in_period if c["comment"]),
        "calls_total": len(in_period),
        "missed": len(missed),
        "missed_back": len(back),
        "missed_median": back[len(back) // 2] if back else None,
        "absences": len(ab),
        "absences_called": ab_called,
        "absences_recorded": ab_recorded,
        "follow_leads": len(follow),
        "follow_touched": touched,
        "follow_no_time": sum(1 for lead in follow if not lead.callback_at),
        "new_leads": Lead.all_objects.filter(created_at__gte=t0, created_at__lt=t1, is_deleted=False).count(),
        "new_contracts": Contract.objects.filter(created_at__gte=t0, created_at__lt=t1).count(),
        "payments": Payment.objects.filter(date__gte=date_from, date__lte=date_to).aggregate(n=Count("id"), s=Sum("amount")),
    }


# ------------------------------------------------------------------ baholash

def grade(data):
    """Har xodimga {score, grade, color, parts{kalit: ball}, good[], bad[], tips[]} qo'shadi."""
    staff, team = data["staff"], data["team"]
    n = max(1, len(staff))

    def rel(key_fn, p, mx):
        vals = [key_fn(s) for s in staff]
        avg = sum(vals) / len(vals) if vals else 0
        return mx / 2 if avg == 0 else mx * min(1.0, key_fn(p) / avg)

    sales = lambda s: s["leads"] + 2 * s["contracts"]  # noqa: E731
    money = lambda s: s["payments"] + 0.5 * s["dues_dismissed"] + 0.5 * s["sms_manual"]  # noqa: E731
    follow = lambda s: s["contact_marks"] + s["followup_comments"] + s["callback_sets"]  # noqa: E731
    need = (team["absences"] + team["follow_leads"]) / n or 1

    for p in staff:
        wd = max(1, len([d for d in data["workdays"] if d < data["now"].date()]))
        t_all = len(p["tasks_on_time"]) + len(p["tasks_late"]) + len(p["tasks_overdue"])
        lead_ratio = p["leads_commented"] / p["leads"] if p["leads"] else 1
        parent_ratio = 1 - p["students_no_parent"] / p["students"] if p["students"] else 1
        parts = {
            "activity": 10 * min(1.0, p["active_days"] / wd),
            "sales": rel(sales, p, 25),
            "money": rel(money, p, 20),
            "tasks": 15 if not t_all else 15 * (len(p["tasks_on_time"]) + 0.5 * len(p["tasks_late"])) / t_all,
            "quality": 5 * lead_ratio + 4 * parent_ratio + max(0, 3 - p["demo_unfilled"]) + max(0, 3 - p["reversals"]),
            "follow": 15 * min(1.0, follow(p) / need),
        }
        p["parts"] = {k: round(v, 1) for k, v in parts.items()}
        p["score"] = round(sum(parts.values()))
        p["grade"], p["color"] = _grade(p["score"])
        p["good"], p["bad"], p["tips"] = _reasons(p, staff, wd)
    return data


def _short(title, n=55):
    return title if len(title) <= n else title[: n - 3].rstrip() + "..."


def _reasons(p, staff, wd):
    good, bad, tips = [], [], []
    top_sales = max(staff, key=lambda s: s["leads"] + 2 * s["contracts"])
    if p is top_sales and len(staff) > 1 and p["contracts"]:
        good.append(f"Sotuvda eng yaxshi natija: {p['leads']} ta lid, {p['contracts']} ta shartnoma.")
    elif p["contracts"] or p["leads"]:
        good.append(f"{p['leads']} ta lid ochdi, {p['contracts']} ta shartnoma tuzdi.")
    if p["payments"]:
        good.append(f"{p['payments']} ta to'lov qabul qildi - jami {fmt(p['paid_sum'])} so'm.")
    if p["dues_dismissed"] or p["sms_manual"]:
        good.append(f"«To'lovga tavsiya» bilan ishlaydi: {p['dues_dismissed']} kishini to'lagan deb belgiladi, {p['sms_manual']} ta eslatma SMS yubordi.")
    if p["active_days"] >= wd:
        good.append(f"Davrning hamma ish kunida tizimda faol ishladi ({p['actions']} ta amal).")
    t_all = len(p["tasks_on_time"]) + len(p["tasks_late"]) + len(p["tasks_overdue"])
    if t_all and not p["tasks_late"] and not p["tasks_overdue"]:
        good.append(f"Topshiriqlarning hammasini ({t_all} ta) muddatida bajardi.")
    if p["leads"] and p["leads_commented"] / p["leads"] >= 0.5:
        good.append(f"Lidlarga izoh yozadi: {p['leads_commented']}/{p['leads']} lidda izoh bor.")
    if p["contact_marks"]:
        good.append(f"Kelmagan {p['contact_marks']} talaba bilan bog'lanish natijasini ERP'ga yozdi.")

    for title, due in p["tasks_overdue"]:
        bad.append(f"Topshiriq muddati o'tgan, hali ochiq: «{_short(title)}» ({timezone.localtime(due):%d.%m} dan beri).")
    for title, due, done in p["tasks_late"]:
        days = (done - due).days
        bad.append(f"Kech bajarilgan: «{_short(title)}» ({'1 kundan kam' if days < 1 else f'{days} kun'} kechikib).")
    if p["tasks_overdue"] or p["tasks_late"]:
        tips.append("Topshiriqlarni muddatida bajarsin yoki muddatni oldindan uzaytirishni so'rasin.")
    if p["inactive_days"]:
        ds = ", ".join(f"{d:%d.%m}" for d in p["inactive_days"])
        bad.append(f"Bu kunlarda tizimda deyarli ishlamagan (kuniga {ACTIVE_DAY_MIN} tadan kam amal): {ds}.")
    if p["last_time"] and p["last_time"].hour < LATE_HOUR:
        bad.append(f"Tizimdagi faolligi odatda {p['last_time']:%H:%M} da tugaydi - ish vaqti kechgacha bo'lsa, tekshirish kerak.")
    if p["leads"] and p["leads_commented"] / p["leads"] < 0.5:
        bad.append(f"Lidlarga izoh kam: {p['leads']} ta lidning {p['leads_commented']} tasida izoh bor.")
        tips.append("Har lid bilan suhbatdan keyin qisqa izoh yozsin.")
    if p["students_no_parent"]:
        bad.append(f"Yangi {p['students']} talabadan {p['students_no_parent']} tasida vasiy (ota-ona) kiritilmagan.")
        tips.append("Talaba qo'shilganda vasiy ma'lumotini ham kiritsin.")
    if p["reversals"]:
        bad.append(f"Lid holatini {p['reversals']} marta orqaga qaytargan - xato kiritib, keyin tuzatilgan.")
    if p["demo_unfilled"]:
        bad.append(f"Sinov darsi o'tib ketgan {p['demo_unfilled']} ta lidda qatnashgani belgilanmagan.")
        tips.append("Sinov darsidan keyin lidni «4. Sinov darsga qatnashdi» yoki boshqa holatga o'tkazsin.")
    if p["paid_sum"] and p["discount_sum"] / (p["paid_sum"] + p["discount_sum"]) > DISCOUNT_SHARE_WARN:
        share = p["discount_sum"] * 100 / (p["paid_sum"] + p["discount_sum"])
        bad.append(f"Chegirma ulushi baland: {p['discount_n']} ta to'lovda {fmt(p['discount_sum'])} so'm (~{share:.0f}%).")
    if not (p["contact_marks"] or p["followup_comments"] or p["callback_sets"]):
        bad.append("Kelmagan talabalar va «Qayta bog'lanish» lidlari bo'yicha ERP'da hech narsa belgilamagan.")
        tips.append("Kelmagan talabaga qo'ng'iroqdan keyin «Gaplashildi / Tushib bo'lmadi» ni belgilasin.")
    return good, bad, tips


# ------------------------------------------------------------------ PDF

NAVY, SIDE, BRAND = HexColor("#0c2236"), HexColor("#163550"), HexColor("#f26a1b")
INK, MUTED, LINE, BG = HexColor("#17171a"), HexColor("#6b6b73"), HexColor("#e6e6ea"), HexColor("#f5f5f7")
GREEN, RED, ORANGE, BLUE = HexColor("#1e9e57"), HexColor("#d93b3b"), HexColor("#e07b00"), HexColor("#2f73da")
PALETTE = [HexColor("#f26a1b"), HexColor("#2f73da"), HexColor("#1e9e57"), HexColor("#d6418a")]
REPLACE = str.maketrans({"ʻ": "'", "ʼ": "'", "‘": "'", "’": "'", "№": "N", "—": "-", "–": "-"})


def _t(s):
    return ("" if s is None else str(s)).translate(REPLACE).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles():
    base = dict(fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
    return {
        "h1": ParagraphStyle("h1", **{**base, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24}),
        "sub": ParagraphStyle("sub", **{**base, "fontSize": 10, "textColor": MUTED}),
        "h2": ParagraphStyle("h2", **{**base, "fontName": "Helvetica-Bold", "fontSize": 13, "leading": 17, "spaceBefore": 6, "spaceAfter": 4}),
        "h3": ParagraphStyle("h3", **{**base, "fontName": "Helvetica-Bold", "fontSize": 10, "leading": 14, "spaceBefore": 4, "spaceAfter": 2}),
        "p": ParagraphStyle("p", **base),
        "small": ParagraphStyle("small", **{**base, "fontSize": 7.5, "leading": 10, "textColor": MUTED}),
        "cell": ParagraphStyle("cell", **{**base, "fontSize": 8.5, "leading": 11}),
        "cellb": ParagraphStyle("cellb", **{**base, "fontName": "Helvetica-Bold", "fontSize": 8.5, "leading": 11}),
        "center": ParagraphStyle("center", **{**base, "alignment": TA_CENTER}),
    }


def _page(pdf, doc):
    w, h = A4
    pdf.saveState()
    pdf.setFillColor(NAVY)
    pdf.rect(0, h - 16 * mm, w, 16 * mm, stroke=0, fill=1)
    pdf.setFillColor(BRAND)
    pdf.rect(0, h - 16.8 * mm, w, 0.8 * mm, stroke=0, fill=1)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(white)
    pdf.drawString(15 * mm, h - 10.5 * mm, "codial")
    pdf.setFillColor(BRAND)
    pdf.drawString(15 * mm + pdf.stringWidth("codial", "Helvetica-Bold", 15), h - 10.5 * mm, ".")
    pdf.setFillColor(HexColor("#c9d3de"))
    pdf.setFont("Helvetica", 8.5)
    pdf.drawRightString(w - 15 * mm, h - 10 * mm, doc.codial_title)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(15 * mm, 9 * mm, doc.codial_footer)
    pdf.drawRightString(w - 15 * mm, 9 * mm, f"{doc.page}-sahifa")
    pdf.restoreState()


def _pill(text, color, w=26 * mm, h=7 * mm, size=9):
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, rx=h / 2, ry=h / 2, fillColor=color, strokeColor=None))
    d.add(String(w / 2, h / 2 - size * 0.35, text, fontName="Helvetica-Bold", fontSize=size, fillColor=white, textAnchor="middle"))
    return d


def _bar(value, mx, color, w=34 * mm, h=4 * mm):
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, rx=2, ry=2, fillColor=LINE, strokeColor=None))
    if mx and value > 0:
        d.add(Rect(0, 0, max(2, w * min(1, value / mx)), h, rx=2, ry=2, fillColor=color, strokeColor=None))
    return d


def _dot(color, size=2.6 * mm):
    d = Drawing(size, size)
    d.add(Circle(size / 2, size / 2, size / 2, fillColor=color, strokeColor=None))
    return d


def _status_color(ratio):
    return GREEN if ratio >= 0.8 else ORANGE if ratio >= 0.5 else RED


def _card(p, st, width):
    parts = Table([
        [Paragraph(_t(p["name"]), st["h3"]), _pill(p["grade"], HexColor(p["color"]))],
        [Paragraph(f'<font size="22"><b>{p["score"]}</b></font><font color="#6b6b73" size="10"> / 100</font>', st["p"]), ""],
        [Paragraph(f'{p["contracts"]} shartnoma · {p["payments"]} to\'lov · {fmt(p["paid_sum"])} so\'m', st["small"]), ""],
    ], colWidths=[width - 32 * mm, 28 * mm], rowHeights=[9 * mm, 11 * mm, 6 * mm])
    parts.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    box = Table([[parts]], colWidths=[width])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LINEABOVE", (0, 0), (-1, 0), 2.2, HexColor(p["color"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    return box


def _grid(rows, widths, head=True, zebra=True, pad=2.2 * mm):
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
    ]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), SIDE), ("TEXTCOLOR", (0, 0), (-1, 0), white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8.5)]
    if zebra:
        style += [("BACKGROUND", (0, i), (-1, i), BG) for i in range(2 if head else 1, len(rows), 2)]
    t.setStyle(TableStyle(style))
    return t


def _bullets(items, color, st, width):
    if not items:
        return Paragraph('<font color="#6b6b73">-</font>', st["cell"])
    t = Table([[_dot(color), Paragraph(_t(x), st["cell"])] for x in items], colWidths=[5 * mm, width - 5 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (0, -1), 1.3 * mm), ("TOPPADDING", (1, 0), (1, -1), 0.6 * mm),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm)]))
    return t


def _activity_chart(data, width):
    staff, days = data["staff"], data["workdays"]
    h = 52 * mm
    d = Drawing(width, h)
    ch = VerticalBarChart()
    ch.x, ch.y, ch.width, ch.height = 10 * mm, 8 * mm, width - 14 * mm, h - 16 * mm
    ch.data = [[p["per_day"].get(day, 0) for day in days] for p in staff] or [[0]]
    ch.categoryAxis.categoryNames = [f"{day:%d.%m}" for day in days]
    ch.categoryAxis.labels.fontName = ch.valueAxis.labels.fontName = "Helvetica"
    ch.categoryAxis.labels.fontSize = ch.valueAxis.labels.fontSize = 7
    ch.categoryAxis.labels.fillColor = ch.valueAxis.labels.fillColor = MUTED
    ch.categoryAxis.strokeColor = ch.valueAxis.strokeColor = LINE
    ch.valueAxis.valueMin = 0
    ch.valueAxis.gridStrokeColor = LINE
    ch.valueAxis.visibleGrid = True
    ch.barSpacing, ch.groupSpacing = 1, 6
    for i in range(len(ch.data)):
        ch.bars[i].fillColor = PALETTE[i % len(PALETTE)]
        ch.bars[i].strokeColor = None
    d.add(ch)
    x = 10 * mm
    for i, p in enumerate(staff):
        d.add(Rect(x, h - 5 * mm, 3 * mm, 3 * mm, fillColor=PALETTE[i % len(PALETTE)], strokeColor=None))
        d.add(String(x + 4.5 * mm, h - 4.6 * mm, _t(p["name"]), fontName="Helvetica", fontSize=7.5, fillColor=INK))
        x += 45 * mm
    return d


def build_pdf(data):
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=24 * mm, bottomMargin=16 * mm,
                            title="Xodimlar ish sifati", author="Codial ERP")
    period = f"{data['from']:%d.%m.%Y} - {data['to']:%d.%m.%Y}"
    doc.codial_title = f"Xodimlar ish sifati · {period}"
    doc.codial_footer = f"Codial ERP · {data['now']:%d.%m.%Y %H:%M} da tayyorlandi · faqat Bosh menejer uchun"
    W = A4[0] - 30 * mm
    staff, team = data["staff"], data["team"]
    s = []

    s.append(Paragraph("Xodimlar ish sifati", st["h1"]))
    s.append(Paragraph(f"Administrator+Hisobchi · {period} · {len(data['workdays'])} ish kuni", st["sub"]))
    s.append(Spacer(1, 6 * mm))

    if not staff:
        s.append(Paragraph("Bu davrda tizimda ishlagan xodim yo'q.", st["p"]))
        doc.build(s, onFirstPage=_page, onLaterPages=_page)
        return buf.getvalue()

    # --- kartochkalar
    per_row = 2 if len(staff) != 3 else 3
    cw = (W - (per_row - 1) * 4 * mm) / per_row
    for i in range(0, len(staff), per_row):
        row = [_card(p, st, cw) for p in staff[i:i + per_row]]
        row += [""] * (per_row - len(row))
        cells = []
        for j, c in enumerate(row):
            cells.append(c)
            if j < per_row - 1:
                cells.append("")
        t = Table([cells], colWidths=[w for j in range(per_row) for w in ([cw, 4 * mm] if j < per_row - 1 else [cw])])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        s += [t, Spacer(1, 4 * mm)]

    # --- mezonlar
    s.append(Paragraph("Mezonlar bo'yicha ball", st["h2"]))
    name_w = 52 * mm
    col_w = (W - name_w) / len(staff)
    rows = [[Paragraph("<b>Mezon</b>", ParagraphStyle("hh", parent=st["cellb"], textColor=white))]
            + [Paragraph(f"<b>{_t(p['name'])}</b>", ParagraphStyle("hh", parent=st["cellb"], textColor=white)) for p in staff]]
    for key, label, mx in CRITERIA:
        line = [Paragraph(f"{_t(label)} <font color='#6b6b73'>({mx})</font>", st["cell"])]
        for p in staff:
            v = p["parts"][key]
            cell = Table([[_bar(v, mx, _status_color(v / mx), w=col_w - 18 * mm), Paragraph(f"<b>{v:g}</b>", st["cell"])]],
                         colWidths=[col_w - 16 * mm, 12 * mm])
            cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            line.append(cell)
        rows.append(line)
    rows.append([Paragraph("<b>Jami</b>", st["cellb"])] + [Paragraph(f"<b>{p['score']}</b> / 100 · <font color='{p['color']}'><b>{p['grade']}</b></font>", st["cell"]) for p in staff])
    s.append(_grid(rows, [name_w] + [col_w] * len(staff)))
    s.append(Paragraph("Baho: 80+ - A'lo, 55-79 - Yaxshi, 55 dan past - Qoniqarsiz. Sotuv, to'lov va kuzatish ballari xodimlar o'rtacha natijasiga nisbatan.", st["small"]))
    s.append(Spacer(1, 4 * mm))

    s.append(KeepTogether([Paragraph("Kunlik faollik (tizimdagi amallar soni)", st["h2"]), _activity_chart(data, W)]))
    s.append(Spacer(1, 4 * mm))
    s.append(Paragraph("Baholash usuli", st["h3"]))
    method = (f"Faollik - kuniga kamida {ACTIVE_DAY_MIN} ta amal bo'lgan ish kunlari (yakshanbasiz). Sotuv - lidlar + 2×shartnomalar. "
              "To'lov - to'lovlar soni + «to'lagan» belgisi va eslatma SMS (0,5 dan). Topshiriqlar - muddatida 1, kech 0,5, ochiq 0. "
              "Ma'lumot sifati - lidlarda izoh (5), talabada vasiy (4), sinov darsi natijasi (3), lid holatini orqaga qaytarmaslik (3). "
              "Kuzatish - kelmaganlar natijasi, «Qayta bog'lanish» lidlariga izoh va vaqt. "
              "Ma'lumot faqat ERP'dagi amallardan olinadi: telefondagi yoki yuzma-yuz suhbat, ERP'ga yozilmagan ish ko'rinmaydi.")
    s.append(Paragraph(_t(method), st["small"]))

    # --- har bir xodim
    for p in staff:
        head = Table([[Paragraph(_t(p["name"]), st["h2"]), _pill(f"{p['grade']} · {p['score']}", HexColor(p["color"]), w=34 * mm)]], colWidths=[W - 36 * mm, 36 * mm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm)]))
        times = f"{p['first_time']:%H:%M} - {p['last_time']:%H:%M}" if p["first_time"] else "-"
        t_all = len(p["tasks_on_time"]) + len(p["tasks_late"]) + len(p["tasks_overdue"])
        metrics = [
            ("Ishlagan kunlar", f"{p['active_days']} / {len([d for d in data['workdays'] if d < data['now'].date()])}"),
            ("Tizimdagi amallar", fmt(p["actions"])),
            ("Odatdagi ish vaqti", times),
            ("Yangi lidlar", p["leads"]),
            ("Shartnomalar", p["contracts"]),
            ("Lidlarga yozgan izohlari", p["lead_comments"]),
            ("To'lovlar", f"{p['payments']} ta · {fmt(p['paid_sum'])}"),
            ("Chegirma", f"{p['discount_n']} ta · {fmt(p['discount_sum'])}"),
            ("To'lagan deb belgilangan", p["dues_dismissed"]),
            ("Topshiriqlar (muddatida / kech / ochiq)", f"{len(p['tasks_on_time'])} / {len(p['tasks_late'])} / {len(p['tasks_overdue'])}" if t_all else "-"),
        ]
        mt = _grid([[Paragraph(_t(a), st["cell"]), Paragraph(f"<b>{_t(b)}</b>", st["cell"])] for a, b in metrics], [44 * mm, 30 * mm], head=False)
        rw = W - 78 * mm
        right = [Paragraph('<font color="#1e9e57">Yaxshi tomonlari</font>', st["h3"]), _bullets(p["good"], GREEN, st, rw),
                 Spacer(1, 2 * mm), Paragraph('<font color="#d93b3b">Kamchiliklari</font>', st["h3"]), _bullets(p["bad"], RED, st, rw)]
        if p["tips"]:
            right += [Spacer(1, 2 * mm), Paragraph('<font color="#e07b00">Tavsiya</font>', st["h3"]), _bullets(p["tips"], ORANGE, st, rw)]
        body = Table([[mt, right]], colWidths=[78 * mm, rw])
        body.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm)]))
        s += [KeepTogether([head, Spacer(1, 2 * mm), body]), Spacer(1, 5 * mm)]

    # --- jamoa
    tm = [Paragraph("Jamoa ko'rsatkichlari", st["h2"]),
          Paragraph("Qo'ng'iroqlar bitta umumiy qabul telefonidan bo'ladi, shuning uchun ular xodimlarga bo'linmaydi.", st["small"]), Spacer(1, 2 * mm)]

    def ratio(a, b):
        return a / b if b else 1

    med = team["missed_median"]
    med = f" · o'rtacha {med:.0f} daq." if med is not None else ""
    trows = [
        ("Javobsiz qo'ng'iroqqa qayta qo'ng'iroq (9:00-19:00)", f"{team['missed_back']} / {team['missed']}{med}", ratio(team["missed_back"], team["missed"])),
        ("Chiquvchi qo'ng'iroqlar (javob berilgan)", f"{team['calls_out']} ({team['calls_out_talked']})", 1),
        ("Qo'ng'iroqlarga yozilgan izoh", f"{team['calls_commented']} / {team['calls_total']}", ratio(team["calls_commented"], team["calls_total"]) * 2),
        ("Kelmaganlar bilan gaplashilgan (telefon bo'yicha)", f"{team['absences_called']} / {team['absences']}", ratio(team["absences_called"], team["absences"])),
        ("Kelmaganlar natijasi ERP'da belgilangan", f"{team['absences_recorded']} / {team['absences']}", ratio(team["absences_recorded"], team["absences"])),
        ("«Qayta bog'lanish / Keyinroq» lidlari bilan ishlangan", f"{team['follow_touched']} / {team['follow_leads']}", ratio(team["follow_touched"], team["follow_leads"])),
        ("Yangi lidlar · shartnomalar", f"{team['new_leads']} · {team['new_contracts']}", 1),
        ("To'lovlar (davr sanasi bo'yicha)", f"{team['payments']['n'] or 0} ta · {fmt(team['payments']['s'])} so'm", 1),
    ]
    head_st = ParagraphStyle("hh", parent=st["cellb"], textColor=white)
    rows = [[Paragraph("", head_st), Paragraph("Ko'rsatkich", head_st), Paragraph("Natija", head_st)]]
    rows += [[_dot(_status_color(r)), Paragraph(_t(a), st["cell"]), Paragraph(f"<b>{_t(b)}</b>", st["cell"])] for a, b, r in trows]
    tm += [_grid(rows, [7 * mm, W - 62 * mm, 55 * mm], pad=1.5 * mm), Spacer(1, 3 * mm)]
    team_tips = []
    if team["absences"] and team["absences_recorded"] < team["absences_called"]:
        team_tips.append(f"Kelmaganlarga qo'ng'iroq qilinadi ({team['absences_called']} ta), lekin natija ERP'ga yozilmaydi "
                         f"({team['absences_recorded']} ta) - «Kelmaganlar» sahifasida belgilansin.")
    if team["follow_leads"] and ratio(team["follow_touched"], team["follow_leads"]) < 0.5:
        team_tips.append(f"«Qayta bog'lanish» va «Keyinroq o'qiydi» holatidagi {team['follow_leads']} liddan faqat {team['follow_touched']} tasi bilan ishlangan"
                         + (f"; {team['follow_no_time']} tasida qayta bog'lanish vaqti yo'q" if team["follow_no_time"] else "") + ". Bu lidlarni xodimlar orasida taqsimlash kerak.")
    if team["calls_total"] and not team["calls_commented"]:
        team_tips.append("Qo'ng'iroqlarga izoh yozilmaydi - muhim suhbatlar natijasi yo'qoladi.")
    if team["missed"] and ratio(team["missed_back"], team["missed"]) >= 0.8:
        team_tips.insert(0, "Javobsiz qo'ng'iroqlarga tez qayta qo'ng'iroq qilinadi - bu a'lo darajada.")
    if team_tips:
        tm.append(_bullets(team_tips, BRAND, st, W))
    s.append(KeepTogether(tm))

    doc.build(s, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


def report(date_from, date_to, **kw):
    return build_pdf(grade(collect(date_from, date_to, **kw)))


def caption(data):
    lines = [f"📊 <b>Xodimlar ish sifati</b> · {data['from']:%d.%m} - {data['to']:%d.%m.%Y}"]
    lines += [f"• {_t(p['name'])}: <b>{p['score']}</b> - {p['grade']}" for p in data["staff"]]
    return "\n".join(lines)


def send(data, pdf, sender=None):
    """PDF'ni botga ulangan Bosh menejer(lar)ga yuboradi. sender(chat_id, filename, content, caption) — testlar uchun. Qaytaradi: yuborilganlar soni."""
    from apps.notifications import services as tg
    from apps.notifications.models import TelegramLink

    sender = sender or tg.send_document
    filename = f"xodimlar_{data['from']:%Y-%m-%d}_{data['to']:%Y-%m-%d}.pdf"
    links = TelegramLink.objects.filter(chat_id__isnull=False, user__role__code=RoleCode.BOSH_MENEJER,
                                        user__employment_status=User.Employment.ACTIVE)
    n = 0
    for lk in links:
        sender(lk.chat_id, filename, pdf, caption(data))
        n += 1
    return n

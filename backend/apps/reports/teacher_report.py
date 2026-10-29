"""Ustozlar ish sifati hisoboti (PDF) — oy yakunida Bosh menejerga (2026-10-29, buyurtmachi so'rovi).

`collect(date_from, date_to)` — davr ko'rsatkichlari (davomat, qatnash, ketganlar, sinov darsi, guruh to'lishi, topshiriqlar);
`grade(data)` — 100 ballik baho va sabablar (mezonlar `CRITERIA`); `build_pdf(data)` — A4 PDF (reportlab, ko'rinishi `staff_report` bilan bir xil).
Hisobotga faqat yig'ma raqamlar, ustoz ismlari va guruh raqamlari kiradi — talaba ismi va telefoni yo'q.
"""

import datetime as dt
import io
from collections import Counter, defaultdict
from decimal import Decimal

from django.db.models import F, Q, Sum
from django.utils import timezone
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.accounts.models import User
from apps.core.roles import RoleCode
from apps.crm.models import Lead
from apps.education.models import Attendance, Contract, Group, MakeupRequest, TeacherEvaluation
from apps.education.services import has_lesson
from apps.tasks.models import StaffTask

from .staff_report import BRAND, GREEN, ORANGE, RED, _bar, _bullets, _grade, _grid, _page, _pill, _status_color, _styles, _t, fmt

ROLES = (RoleCode.USTOZ, RoleCode.USTOZ_YORDAMCHI)
LIVE = dt.date(2026, 10, 19)  # ERP ishga tushgan kun: undan oldingi davomat AppSheet'dan ko'chgan — kiritilgan vaqti noma'lum
NOT_CHURN = {Contract.StopReason.FINISHED}
QUALITY_REASONS = {Contract.StopReason.QUALITY, Contract.StopReason.OTHER_COURSE}
RELIABLE_COVERAGE = 0.6  # davomat bundan kam olingan bo'lsa, qatnash va ketganlar bo'yicha maqtov berilmaydi

# (kalit, nomi, maksimal ball)
CRITERIA = [
    ("discipline", "Davomat intizomi", 25),
    ("presence", "O'quvchilar qatnashi", 20),
    ("retention", "O'quvchilarni saqlab qolish", 25),
    ("demo", "Sinov darsidan shartnomaga", 15),
    ("fill", "Guruhlar to'lishi", 10),
    ("tasks", "Topshiriqlar", 5),
]


def _clamp(x):
    return max(0.0, min(1.0, x))


def _active_on(contracts, d):
    return sum(1 for s, e in contracts if s <= d and (e is None or e >= d))


# ------------------------------------------------------------------ ma'lumot yig'ish

def collect(date_from, date_to, roles=ROLES, now=None):
    """[date_from, date_to] (ikkalasi ham kiradi) davr ko'rsatkichlari — davrda guruhi bo'lgan ustozlar."""
    tz = timezone.get_current_timezone()
    now = now or timezone.localtime()
    t0 = dt.datetime.combine(date_from, dt.time(0), tzinfo=tz)
    t1 = dt.datetime.combine(date_to + dt.timedelta(days=1), dt.time(0), tzinfo=tz)
    days = [date_from + dt.timedelta(days=i) for i in range((date_to - date_from).days + 1)]

    att = defaultdict(list)
    for a in Attendance.objects.filter(date__gte=date_from, date__lte=date_to).values(
            "group_id", "date", "status", "created_at", "created_by_id", "legacy_id", "teacher_id"):
        att[(a["group_id"], a["date"])].append(a)
    ctr = defaultdict(list)
    for c in Contract.objects.filter(start_date__lte=date_to).filter(Q(end_date__isnull=True) | Q(end_date__gte=date_from)).values(
            "group_id", "start_date", "end_date"):
        ctr[c["group_id"]].append((c["start_date"], c["end_date"]))

    teachers = []
    for u in User.objects.filter(role__code__in=roles, is_active=True).select_related("role").order_by("full_name"):
        groups = [g for g in Group.objects.filter(teacher=u).select_related("time", "room", "day_pattern")
                  if g.start_date <= date_to and (not g.end_date or g.end_date >= date_from)]
        if groups:
            teachers.append(_teacher(u, groups, days, att, ctr, date_from, date_to, t0, t1, now, tz))
    return {"from": date_from, "to": date_to, "now": now, "teachers": teachers}


def _teacher(u, groups, days, att, ctr, date_from, date_to, t0, t1, now, tz):
    gids = [g.id for g in groups]
    lessons = full = subst = by_other = unmarked = 0
    missing, partial, timing, per_group = [], [], [], []
    for g in groups:
        g_less = g_miss = 0
        for d in days:
            if not has_lesson(g, d) or d > now.date():
                continue
            act = _active_on(ctr[g.id], d)
            if not act:
                continue
            rows = att.get((g.id, d), [])
            lessons += 1
            g_less += 1
            if not rows:
                missing.append((g.number, d))
                g_miss += 1
                continue
            if len(rows) < act:
                partial.append((g.number, d, len(rows), act))
                unmarked += act - len(rows)
            else:
                full += 1
            subst += any(r["teacher_id"] != u.id for r in rows)
            fresh = [r for r in rows if r["legacy_id"] is None]
            if d >= LIVE and fresh:
                first = min(timezone.localtime(r["created_at"]) for r in fresh)
                by_other += not any(r["created_by_id"] == u.id for r in fresh)
                timing.append(((first.date() - d).days, (first - dt.datetime.combine(d, g.time.start_time, tzinfo=tz)).total_seconds() / 60))
        cap = g.room.capacity if g.room_id else 0
        per_group.append({"name": str(g), "time": f"{g.day_pattern.name} {g.time.start_time:%H:%M}", "students": _active_on(ctr[g.id], date_to),
                          "cap": cap, "lessons": g_less, "missing": g_miss, "active": not g.end_date or g.end_date >= date_to})

    st = Counter(r["status"] for (gid, d), rows in att.items() if gid in gids for r in rows)
    marked = st["1"] + st["0"] + st["X"]
    base = Contract.objects.filter(group__in=gids, start_date__lte=date_to).filter(Q(end_date__isnull=True) | Q(end_date__gte=date_from))
    stopped = Counter(base.filter(end_date__gte=date_from, end_date__lte=date_to).values_list("stop_reason", flat=True))
    churn_n = sum(n for r, n in stopped.items() if r not in NOT_CHURN)
    base_n = base.count()

    demos = list(Lead.objects.filter(group__in=gids, demo_date__gte=date_from, demo_date__lte=date_to, demo_attended=True))
    joined_students = set(Contract.objects.filter(group__in=gids, student__in=[x.student_id for x in demos]).values_list("student_id", flat=True))
    demo_conv = sum(1 for x in demos if x.status == "5" or x.student_id in joined_students)

    fill_groups = [p for p in per_group if p["active"] and p["cap"] and p["students"]]  # o'quvchisiz guruh — amalda yopilgan
    tasks = StaffTask.objects.filter(assignee=u, created_at__lt=t1).filter(Q(due_at__gte=t0, due_at__lt=t1) | Q(status=StaffTask.Status.OPEN, due_at__lt=t1))
    evs = list(TeacherEvaluation.objects.filter(teacher=u, date__gte=date_from, date__lte=date_to))
    med = sorted(m for late, m in timing if late == 0)
    return {
        "user": u, "name": u.full_name, "groups": per_group, "lessons": lessons, "full": full, "missing": missing, "partial": partial,
        "unmarked": unmarked, "subst": subst, "by_other": by_other, "timing_n": len(timing), "same_day": sum(1 for late, m in timing if late == 0),
        "med_min": med[len(med) // 2] if med else None,
        "last_att": max((d for (gid, d) in att if gid in gids), default=None),
        "st": st, "presence": st["1"] / marked if marked else None,
        "base": base_n, "stopped": stopped, "finished": stopped[Contract.StopReason.FINISHED], "churn_n": churn_n, "churn": churn_n / base_n if base_n else 0,
        "joined": Contract.objects.filter(group__in=gids, start_date__gte=date_from, start_date__lte=date_to).count(),
        "demo_came": len(demos), "demo_conv": demo_conv,
        "fill": sum(min(1, p["students"] / p["cap"]) for p in fill_groups) / len(fill_groups) if fill_groups else None,
        "t_on": tasks.filter(done_at__isnull=False, done_at__lte=F("due_at")).count(),
        "t_late": tasks.filter(done_at__isnull=False, done_at__gt=F("due_at")).count(),
        "t_open": tasks.filter(status=StaffTask.Status.OPEN, due_at__lt=min(now, t1)).count(),
        "makeups": MakeupRequest.objects.filter(teacher=u, created_at__gte=t0, created_at__lt=t1).count(),
        "kpi": Attendance.objects.filter(teacher=u, date__gte=date_from, date__lte=date_to).aggregate(s=Sum("teacher_kpi"))["s"] or Decimal(0),
        "ev_n": len(evs), "ev_avg": sum(e.total for e in evs) / len(evs) if evs else None,
    }


# ------------------------------------------------------------------ baholash

def grade(data):
    """Har ustozga {score, grade, color, parts{kalit: ball}, cov, good[], bad[], tips[]} qo'shadi va ball bo'yicha tartiblaydi."""
    for p in data["teachers"]:
        cov = (p["full"] + 0.5 * len(p["partial"])) / p["lessons"] if p["lessons"] else 1
        timely = p["same_day"] / p["timing_n"] if p["timing_n"] else cov
        t_all = p["t_on"] + p["t_late"] + p["t_open"]
        parts = {
            "discipline": 15 * cov + 10 * timely,
            # davomat to'liq olinmasa, qatnash va saqlab qolish raqamlari ishonchsiz — davomat olingan darslar ulushiga ko'paytiriladi
            "presence": 20 * _clamp(((p["presence"] if p["presence"] is not None else 0.75) - 0.6) / 0.3) * cov,
            "retention": 25 * (1 - _clamp(p["churn"] / 0.15)) * cov,
            "demo": 7.5 if not p["demo_came"] else 15 * _clamp(p["demo_conv"] / p["demo_came"] / 0.6),
            "fill": 5 if p["fill"] is None else 10 * _clamp(p["fill"] / 0.85),
            "tasks": 5 if not t_all else 5 * (p["t_on"] + 0.5 * p["t_late"]) / t_all,
        }
        p["cov"] = cov
        p["parts"] = {k: round(v, 1) for k, v in parts.items()}
        p["score"] = round(sum(parts.values()))
        p["grade"], p["color"] = _grade(p["score"])
        p["good"], p["bad"], p["tips"] = _reasons(p, data["to"])
    data["teachers"].sort(key=lambda p: -p["score"])
    return data


def _dates(items, n):
    return "; ".join(items[:n]) + ("..." if len(items) > n else "")


def _reasons(p, date_to):
    good, bad, tips = [], [], []
    cov, reliable = p["cov"], p["cov"] >= RELIABLE_COVERAGE
    if not p["missing"] and not p["partial"]:
        good.append(f"Hamma darslarda ({p['lessons']} ta) davomat to'liq olingan.")
    if p["timing_n"] and p["same_day"] == p["timing_n"]:
        good.append(f"Davomatni har doim dars kuni oladi ({p['timing_n']} ta dars).")
    if reliable and p["presence"] is not None and p["presence"] >= 0.85:
        good.append(f"O'quvchilar qatnashi yuqori: {p['presence'] * 100:.0f}% darsga kelgan.")
    if reliable and p["base"] and not p["churn_n"]:
        good.append(f"Kursni tamomlamay ketgan o'quvchi yo'q ({p['base']} ta shartnoma).")
    if p["joined"]:
        good.append(f"Guruhlariga {p['joined']} ta yangi o'quvchi qo'shildi.")
    if p["demo_came"] and p["demo_conv"] / p["demo_came"] >= 0.6:
        good.append(f"Sinov darsiga kelganlarning {p['demo_conv']}/{p['demo_came']} tasi o'qishni boshladi.")
    if p["fill"] is not None and p["fill"] >= 0.85:
        good.append(f"Guruhlari yaxshi to'lgan (o'rtacha {p['fill'] * 100:.0f}%).")

    if p["last_att"] and (date_to - p["last_att"]).days >= 5 and any(d > p["last_att"] for _, d in p["missing"]):
        bad.append(f"Oxirgi davomat {p['last_att']:%d.%m} da olingan - shundan beri guruhlarida davomat yo'q.")
    if cov < 0.8:
        bad.append(f"Davomat faqat darslarning {cov * 100:.0f}% ida olingan - shuning uchun qatnash va saqlab qolish ballari ham shu ulushda kamaytirildi.")
    if p["missing"]:
        bad.append(f"{len(p['missing'])} ta darsda davomat umuman olinmagan: {_dates([f'#{n} {d:%d.%m}' for n, d in p['missing']], 12)}.")
        tips.append("Har dars boshida davomatni olsin - Telegram botdagi «Davomat olish» tugmasi orqali 1 daqiqada.")
    if p["partial"]:
        bad.append(f"{len(p['partial'])} ta darsda ba'zi o'quvchilar belgilanmagan (jami {p['unmarked']} ta belgi yo'q): "
                   f"{_dates([f'#{n} {d:%d.%m} ({k}/{m})' for n, d, k, m in p['partial']], 8)}.")
        tips.append("Davomatda guruhdagi hamma o'quvchi belgilanganini tekshirsin - belgilanmagan o'quvchiga qarz va KPI yozilmaydi.")
    if p["timing_n"] > p["same_day"]:
        bad.append(f"{p['timing_n']} ta darsdan {p['timing_n'] - p['same_day']} tasida davomat keyingi kunlarda kiritilgan.")
    if p["by_other"]:
        bad.append(f"{p['by_other']} ta darsda davomatni ustozning o'zi emas, boshqa xodim kiritgan.")
    if p["presence"] is not None and p["presence"] < 0.75:
        bad.append(f"O'quvchilar qatnashi past: faqat {p['presence'] * 100:.0f}% darsga kelgan (besabab: {p['st']['X']} ta).")
        tips.append("Ketma-ket kelmagan o'quvchining ota-onasi bilan o'zi ham bog'lansin, darsni qiziqarliroq qilish usullarini o'rgansin.")
    if p["churn_n"]:
        reasons = ", ".join(f"{r or 'sababsiz'} - {n}" for r, n in p["stopped"].items() if r not in NOT_CHURN)
        bad.append(f"Davr ichida {p['churn_n']} ta o'quvchi kursni tamomlamay to'xtatgan ({p['churn'] * 100:.0f}%): {reasons}.")
        if any(r in QUALITY_REASONS for r in p["stopped"]):
            tips.append("Ketgan o'quvchilar sababini birga tahlil qilish va darsini kuzatib, fikr berish kerak.")
    if p["demo_came"] and p["demo_conv"] / p["demo_came"] < 0.4:
        bad.append(f"Sinov darsiga kelgan {p['demo_came']} kishidan faqat {p['demo_conv']} tasi o'qishni boshladi.")
        tips.append("Sinov darsini alohida tayyorlasin: qisqa, natijasi ko'rinadigan amaliy topshiriq bilan.")
    if p["fill"] is not None and p["fill"] < 0.5:
        bad.append(f"Guruhlar kam to'lgan: o'rtacha {p['fill'] * 100:.0f}%.")
    if p["t_open"] or p["t_late"]:
        bad.append(f"Topshiriqlar: {p['t_late']} tasi kech bajarilgan, {p['t_open']} tasi muddati o'tib ochiq qolgan.")
    return good, bad, tips


# ------------------------------------------------------------------ PDF

METHOD = ("Davomat intizomi (25): dars bo'lgan kunlarning qanchasida hamma o'quvchi belgilangan (15; qisman belgilangan dars - yarim) va davomat dars kuni "
          "kiritilganmi (10; kiritilgan vaqti 19.10.2026 dan - ERP ishga tushgandan aniq). "
          "Qatnash (20): belgilangan o'quvchilarning «Keldi» ulushi; 60% va undan past - 0, 90% va yuqori - to'liq ball. "
          "Saqlab qolish (25): davr ichida to'xtatgan o'quvchilar (kursni tamomlaganlar hisobga olinmaydi); 15% va undan ko'p - 0. "
          "Davomat to'liq olinmagan bo'lsa, bu ikki ball davomat olingan darslar ulushiga ko'paytiriladi - aks holda ma'lumot yo'qligi yuqori ball berib qo'yadi. "
          "Sinov darsi (15): ustoz guruhiga sinov darsiga kelgan lidlardan o'qishni boshlaganlar; 60% - to'liq; sinov darsi bo'lmasa - 7,5. "
          "To'lish (10): faol guruhlardagi o'quvchilar / xona sig'imi; 85% - to'liq (bu ko'proq markaz va marketingga bog'liq). "
          "Topshiriqlar (5): muddatida bajarilgani. Ma'lumot faqat ERP'dan olinadi; dars sifatini (tushuntirish, metodika) ERP o'lchay olmaydi - "
          "buni darsni kuzatish va o'quvchi bahosi bilan to'ldirish kerak.")


def build_pdf(data):
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=24 * mm, bottomMargin=16 * mm,
                            title="Ustozlar ish sifati", author="Codial ERP")
    period = f"{data['from']:%d.%m.%Y} - {data['to']:%d.%m.%Y}"
    doc.codial_title = f"Ustozlar ish sifati · {period}"
    doc.codial_footer = f"Codial ERP · {data['now']:%d.%m.%Y %H:%M} da tayyorlandi · faqat Bosh menejer uchun"
    W = A4[0] - 30 * mm
    hh = ParagraphStyle("hh", parent=st["cellb"], textColor=white)
    teachers = data["teachers"]
    s = [Paragraph("Ustozlar ish sifati", st["h1"]),
         Paragraph(f"Ustoz va Ustoz+Yordamchi · {period} · {len(teachers)} ustoz", st["sub"]), Spacer(1, 6 * mm)]
    if not teachers:
        s.append(Paragraph("Bu davrda guruhi bo'lgan ustoz yo'q.", st["p"]))
        doc.build(s, onFirstPage=_page, onLaterPages=_page)
        return buf.getvalue()

    # --- umumiy jadval
    rows = [[Paragraph(x, hh) for x in ("Ustoz", "Guruh", "O'quvchi", "Darslar", "Qatnash", "Ketgan", "Ball", "Baho")]]
    for p in teachers:
        act = [g for g in p["groups"] if g["active"]]
        rows.append([Paragraph(f"<b>{_t(p['name'])}</b>", st["cell"]), Paragraph(str(len(act)), st["cell"]),
                     Paragraph(str(sum(g["students"] for g in act)), st["cell"]), Paragraph(str(p["lessons"]), st["cell"]),
                     Paragraph("-" if p["presence"] is None else f"{p['presence'] * 100:.0f}%", st["cell"]), Paragraph(str(p["churn_n"]), st["cell"]),
                     Paragraph(f"<b>{p['score']}</b>", st["cell"]), _pill(p["grade"], HexColor(p["color"]), w=22 * mm, h=6 * mm, size=8)])
    s += [_grid(rows, [46 * mm, 15 * mm, 18 * mm, 17 * mm, 18 * mm, 16 * mm, 14 * mm, W - 144 * mm]), Spacer(1, 6 * mm)]

    # --- mezonlar
    s.append(Paragraph("Mezonlar bo'yicha ball", st["h2"]))
    cw = (W - 40 * mm) / len(CRITERIA)
    rows = [[Paragraph("Ustoz", hh)] + [Paragraph(f"{_t(label)} ({mx})", hh) for _, label, mx in CRITERIA]]
    for p in teachers:
        line = [Paragraph(_t(p["name"]), st["cell"])]
        for key, _, mx in CRITERIA:
            v = p["parts"][key]
            cell = Table([[_bar(v, mx, _status_color(v / mx), w=cw - 13 * mm), Paragraph(f"<b>{v:g}</b>", st["cell"])]], colWidths=[cw - 11 * mm, 9 * mm])
            cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            line.append(cell)
        rows.append(line)
    s += [_grid(rows, [40 * mm] + [cw] * len(CRITERIA)), Paragraph("Baho: 80+ - A'lo, 55-79 - Yaxshi, 55 dan past - Qoniqarsiz.", st["small"]),
          Spacer(1, 3 * mm), Paragraph("Baholash usuli", st["h3"]), Paragraph(_t(METHOD), st["small"])]

    # --- har bir ustoz
    for p in teachers:
        s += _teacher_section(p, st, hh, W)

    doc.build(s, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()


def _teacher_section(p, st, hh, W):
    head = Table([[Paragraph(_t(p["name"]), st["h2"]), _pill(f"{p['grade']} · {p['score']}", HexColor(p["color"]), w=34 * mm)]], colWidths=[W - 36 * mm, 36 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm)]))
    med = p["med_min"]
    t_all = p["t_on"] + p["t_late"] + p["t_open"]
    metrics = [
        ("Darslar (to'liq / qisman / olinmagan)", f"{p['full']} / {len(p['partial'])} / {len(p['missing'])}"),
        ("Dars kuni kiritilgan", f"{p['same_day']} / {p['timing_n']}" if p["timing_n"] else "-"),
        ("Darsdan keyin o'rtacha", "-" if med is None else (f"{med:.0f} daq." if med >= 0 else f"darsdan {-med:.0f} daq. oldin")),
        ("O'rindosh o'tgan darslar", p["subst"]),
        ("Oxirgi davomat", f"{p['last_att']:%d.%m}" if p["last_att"] else "-"),
        ("Keldi / Sababli / Besabab", f"{p['st']['1']} / {p['st']['0']} / {p['st']['X']}"),
        ("Qatnash foizi", "-" if p["presence"] is None else f"{p['presence'] * 100:.0f}%"),
        ("Yangi / kursni tamomlagan / ketgan", f"{p['joined']} / {p['finished']} / {p['churn_n']}"),
        ("Sinov darsi: kelgan / o'qishni boshlagan", f"{p['demo_came']} / {p['demo_conv']}" if p["demo_came"] else "-"),
        ("Guruhlar to'lishi", "-" if p["fill"] is None else f"{p['fill'] * 100:.0f}%"),
        ("Qoldirilgan dars so'rovlari", p["makeups"] or "-"),
        ("Topshiriqlar (muddatida / kech / ochiq)", f"{p['t_on']} / {p['t_late']} / {p['t_open']}" if t_all else "-"),
        ("KPI (davomatdan)", f"{fmt(p['kpi'])} so'm"),
    ]
    if p["ev_n"]:
        metrics.append(("O'quvchi bahosi (50 dan)", f"{p['ev_avg']:.1f} ({p['ev_n']} ta)"))
    mt = _grid([[Paragraph(_t(a), st["cell"]), Paragraph(f"<b>{_t(b)}</b>", st["cell"])] for a, b in metrics], [50 * mm, 28 * mm], head=False, pad=1.6 * mm)
    rw = W - 82 * mm
    right = [Paragraph('<font color="#1e9e57">Yaxshi tomonlari</font>', st["h3"]), _bullets(p["good"], GREEN, st, rw),
             Spacer(1, 2 * mm), Paragraph('<font color="#d93b3b">Kamchiliklari</font>', st["h3"]), _bullets(p["bad"], RED, st, rw)]
    if p["tips"]:
        right += [Spacer(1, 2 * mm), Paragraph('<font color="#e07b00">Tavsiya</font>', st["h3"]), _bullets(p["tips"], ORANGE, st, rw)]
    body = Table([[mt, right]], colWidths=[82 * mm, rw])
    body.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm)]))
    grows = [[Paragraph(x, hh) for x in ("Guruh", "Dars vaqti", "O'quvchi / sig'im", "Darslar", "Olinmagan")]]
    for g in p["groups"]:
        grows.append([Paragraph(_t(g["name"]) + ("" if g["active"] else " <font color='#6b6b73'>(tugagan)</font>"), st["cell"]), Paragraph(_t(g["time"]), st["cell"]),
                      Paragraph(f"{g['students']} / {g['cap'] or '-'}", st["cell"]), Paragraph(str(g["lessons"]), st["cell"]),
                      Paragraph(f"<font color='{'#d93b3b' if g['missing'] else '#17171a'}'><b>{g['missing']}</b></font>", st["cell"])])
    gt = _grid(grows, [W - 118 * mm, 42 * mm, 28 * mm, 22 * mm, 26 * mm], pad=1.3 * mm)
    return [KeepTogether([head, Spacer(1, 2 * mm), body]), Spacer(1, 2 * mm), gt, Spacer(1, 6 * mm)]


def report(date_from, date_to, **kw):
    return build_pdf(grade(collect(date_from, date_to, **kw)))


def caption(data):
    lines = [f"🎓 <b>Ustozlar ish sifati</b> · {data['from']:%d.%m} - {data['to']:%d.%m.%Y}"]
    lines += [f"• {_t(p['name'])}: <b>{p['score']}</b> - {p['grade']}" for p in data["teachers"]]
    return "\n".join(lines)


def send(data, pdf, sender=None):
    """PDF'ni botga ulangan Bosh menejer(lar)ga yuboradi (staff_report.send bilan bir xil). Qaytaradi: yuborilganlar soni."""
    from apps.notifications import services as tg
    from apps.notifications.models import TelegramLink

    sender = sender or tg.send_document
    filename = f"ustozlar_{data['from']:%Y-%m-%d}_{data['to']:%Y-%m-%d}.pdf"
    links = TelegramLink.objects.filter(chat_id__isnull=False, user__role__code=RoleCode.BOSH_MENEJER,
                                        user__employment_status=User.Employment.ACTIVE)
    n = 0
    for lk in links:
        sender(lk.chat_id, filename, pdf, caption(data))
        n += 1
    return n

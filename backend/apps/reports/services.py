"""Hisobotlar (CLAUDE.md 8.6, 11): foyda oyma-oy, oylik statistika, sotuv voronkasi, birinchi marta to'lov qilganlar.
Hammasi bazada aggregatsiya bilan; butun jadvallar Python'da aylanib chiqilmaydi."""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Exists, Min, OuterRef, Q, Sum
from django.db.models.functions import TruncMonth

from apps.core.scoping import scope_branch
from apps.crm.models import Lead
from apps.education.models import Attendance, Contract
from apps.finance.models import Expense, Payment
from apps.payroll import services as payroll
from apps.payroll.models import SalaryAssignment
from apps.references.models import ExpenseCategory

ZERO = Decimal(0)
KINDS = ExpenseCategory.Kind


def ym(d):
    return f"{d:%Y-%m}"


def month_list(end, n):
    """Oxirgi n oy (eski → yangi), end — oy (date)."""
    out, d = [], end.replace(day=1)
    for _ in range(n):
        out.append(d)
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def bounds(start, end):
    """[start oyining 1-kuni, end oyidan keyingi oyning 1-kuni)"""
    nxt = (end.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return start.replace(day=1), nxt


# ------------------------------------------------------------------ foyda (8.6)

def profit(user, months):
    """months — [date(oy 1-kuni)]. Foyda = to'lovlar − xarajatlar («Xarajat» turi) − hisoblangan oyliklar.
    Qayta investitsiya, dividend, tashqi qarz — alohida."""
    if not months:
        return []
    lo, hi = bounds(min(months), max(months))
    keys = {ym(m) for m in months}
    rows = {k: {"ym": k, "payments": ZERO, "expenses": ZERO, "salaries": ZERO, "reinvest": ZERO, "dividend": ZERO, "debt": ZERO} for k in sorted(keys)}
    pays = scope_branch(Payment.objects.filter(date__gte=lo, date__lt=hi), user).annotate(m=TruncMonth("date")).order_by()
    for m, s in pays.values_list("m").annotate(s=Sum("amount")).values_list("m", "s"):
        if ym(m) in rows:
            rows[ym(m)]["payments"] = s or ZERO
    field = {KINDS.EXPENSE: "expenses", KINDS.REINVEST: "reinvest", KINDS.DIVIDEND: "dividend", KINDS.EXTERNAL_DEBT: "debt"}
    exps = scope_branch(Expense.objects.all(), user).order_by()
    for y, m, kind, s in exps.values_list("period_year", "period_month", "category__kind").annotate(s=Sum("total")).values_list("period_year", "period_month", "category__kind", "s"):
        k = f"{y}-{m:02d}"
        if k in rows and kind in field:
            rows[k][field[kind]] += s or ZERO
    q = Q()
    for d in months:
        q |= Q(year=d.year, month=d.month)
    for a in payroll.compute(scope_branch(SalaryAssignment.objects.filter(q), user)):
        rows[f"{a.year}-{a.month:02d}"]["salaries"] += a.total
    out = list(rows.values())
    for r in out:
        r["profit"] = r["payments"] - r["expenses"] - r["salaries"]
    return out


# ------------------------------------------------------------------ oylik statistika (11)

def monthly_stats(user, months):
    lo, hi = bounds(months[0], months[-1])
    keys = [ym(m) for m in months]
    leads = scope_branch(Lead.objects.filter(created_at__date__gte=lo, created_at__date__lt=hi), user).annotate(m=TruncMonth("created_at")).order_by()
    by_source = [{"ym": ym(r["m"]), "source": str(r["source"]), "n": r["n"]} for r in leads.values("m", "source").annotate(n=Count("id"))]
    by_course = [{"ym": ym(r["m"]), "course": str(r["course"]), "n": r["n"]} for r in leads.values("m", "course").annotate(n=Count("id"))]
    contracts = scope_branch(Contract.objects.all(), user).order_by()
    new = {ym(r["m"]): r["n"] for r in contracts.filter(start_date__gte=lo, start_date__lt=hi).annotate(m=TruncMonth("start_date")).values("m").annotate(n=Count("id"))}
    stopped = [{"ym": ym(r["m"]), "reason": r["stop_reason"] or "—", "n": r["n"]}
               for r in contracts.filter(end_date__gte=lo, end_date__lt=hi).annotate(m=TruncMonth("end_date")).values("m", "stop_reason").annotate(n=Count("id"))]
    money = {r["ym"]: r for r in profit(user, months)}
    att = scope_branch(Attendance.objects.filter(date__gte=lo, date__lt=hi).exclude(status="-"), user).annotate(m=TruncMonth("date")).order_by()
    att_pct = {ym(r["m"]): (r["came"] / r["n"] if r["n"] else 0) for r in att.values("m").annotate(n=Count("id"), came=Count("id", filter=Q(status="1")))}
    return {
        "months": keys,
        "leads_by_source": by_source,
        "leads_by_course": by_course,
        "contracts_new": [new.get(k, 0) for k in keys],
        "contracts_stopped": stopped,
        "money": [money[k] for k in keys],
        "attendance_pct": [att_pct.get(k, 0) for k in keys],
    }


# ------------------------------------------------------------------ sotuv voronkasi (11)

STATUSES = [s for s, _ in Lead.LeadStatus.choices]


def funnel(user, date_from=None, date_to=None, source=None, course=None, owner=None):
    qs = scope_branch(Lead.objects.all(), user)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    for k, v in (("source", source), ("course", course), ("created_by", owner)):
        if v:
            qs = qs.filter(**{k: v})
    qs = qs.annotate(
        hc=Exists(Contract.objects.filter(student=OuterRef("student"))),
        hp=Exists(Payment.objects.filter(contract__student=OuterRef("student"), amount__gt=0)),
    ).order_by()
    counts = dict(qs.values_list("status").annotate(n=Count("id")))
    total = sum(counts.values())
    agg = qs.aggregate(c=Count("id", filter=Q(hc=True)), p=Count("id", filter=Q(hp=True)))

    def reached(k):
        return sum(n for s, n in counts.items() if int(k) <= int(s) <= 5)

    steps = [{"status": s, "n": counts.get(s, 0)} for s in STATUSES]
    stages = [{"status": k, "reached": reached(k), "rate": reached(k) / total if total else 0} for k in ("1", "2", "3", "4", "5")]
    by_owner = list(qs.values("created_by").annotate(n=Count("id"), c=Count("id", filter=Q(hc=True)), p=Count("id", filter=Q(hp=True))).order_by("-n"))
    return {"total": total, "steps": steps, "stages": stages, "contracts": agg["c"], "paid": agg["p"],
            "contract_rate": agg["c"] / total if total else 0, "pay_rate": agg["p"] / total if total else 0,
            "by_owner": [{"user": r["created_by"], "n": r["n"], "contracts": r["c"], "paid": r["p"]} for r in by_owner]}


# ------------------------------------------------------------------ birinchi marta to'lov qilganlar (11)

def first_payers(user, month):
    """Tanlangan oyda birinchi marta to'lov qilgan talabalar (barcha shartnomalari bo'yicha eng birinchi to'lov), manba va kurs kesimida."""
    lo, hi = bounds(month, month)
    pays = scope_branch(Payment.objects.filter(amount__gt=0), user).order_by()
    firsts = pays.values("contract__student").annotate(first=Min("date")).filter(first__gte=lo, first__lt=hi)
    students = {r["contract__student"]: r["first"] for r in firsts}
    first_pay = {}
    for p in pays.filter(contract__student__in=students.keys()).select_related("contract__student", "contract__course", "contract__group__course").order_by("date", "created_at"):
        sid = p.contract.student_id
        if sid not in first_pay and p.date == students[sid]:
            first_pay[sid] = p
    leads = {lead.student_id: lead for lead in Lead.objects.filter(student__in=students.keys()).select_related("source")}
    rows, by_source, by_course = [], defaultdict(int), defaultdict(int)
    for sid, p in first_pay.items():
        lead = leads.get(sid)
        src = str(lead.source) if lead else "Lidsiz (manba yo'q)"
        rows.append({"student": str(sid), "student_name": p.contract.student.full_name, "contract": str(p.contract_id), "date": p.date, "amount": p.amount,
                     "course": str(p.contract.course_id), "group": str(p.contract.group_id), "source": str(lead.source_id) if lead else None, "source_name": src})
        by_source[src] += 1
        by_course[str(p.contract.course)] += 1
    rows.sort(key=lambda r: r["date"])
    return {"count": len(rows), "rows": rows, "by_source": dict(by_source), "by_course": dict(by_course)}

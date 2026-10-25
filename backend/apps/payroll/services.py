"""Oyliklar servislari (CLAUDE.md 7.2, 7.5, 8.4).

total = fixed + bonus + kpi + teacher_kpi + supporter_kpi − fine   (jarima ayiriladi — AppSheet xatosi tuzatilgan)
carried(M) = Σ oldingi oylar (boshlang'ich qoldiq + total − berilgan) + shu oy boshlang'ich qoldig'i — yillar oralig'ida ham
final(M) = carried(M) + total(M) − given(M)   (musbat — xodim haqdor, manfiy — ortiqcha olgan)
"""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core import audit
from apps.core.permissions import can, check_edit_window, is_top, role_code, sees_all, today
from apps.core.roles import MANAGER_ROLES, RoleCode
from apps.core.scoping import scope_branch
from apps.core.services import soft_delete
from apps.education import calc
from apps.education.models import Attendance
from apps.finance import services as fin
from apps.finance.models import MONEY_TYPES, CashMovement

from .models import KPIRate, SalaryAssignment, SalaryPayout

ZERO = Decimal(0)
TEACHERS = {RoleCode.USTOZ, RoleCode.USTOZ_YORDAMCHI}
SUPPORTERS = {RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI}


def ym_key(year, month):
    return year * 100 + month


# ------------------------------------------------------------------ doira (6.3)

def scope(qs, user):
    """Admin, Bosh menejer — hammasi; Filial menejeri va oylik beruvchilar (ruxsat «qo'shish») — o'z filiali; boshqalar — faqat o'zi."""
    if sees_all(user):
        return qs
    if role_code(user) == RoleCode.FILIAL_MENEJERI or can(user, "salaries", "a"):
        return scope_branch(qs, user)
    return qs.filter(user=user)


def require_manager(user):
    if role_code(user) not in MANAGER_ROLES or not can(user, "salaries", "e"):
        raise PermissionDenied("Buni Admin, Bosh menejer va Filial menejeri qiladi")


def _check_staff(user_obj, branch, field="user"):
    if role_code(user_obj) == RoleCode.ADMIN:
        raise ValidationError({field: "Admin uchun oylik yuritilmaydi"})
    if not user_obj.branches.filter(pk=branch.pk).exists():
        raise ValidationError({field: "Xodim bu filialda ishlamaydi"})


def _update(obj, user, d):
    before = audit.snapshot(obj)
    for k, v in d.items():
        setattr(obj, k, v)
    obj.updated_by = user
    obj.save()
    audit.log_update(user, obj, before)
    return obj


# ------------------------------------------------------------------ KPI stavkalari

def _recalc_rate(rate):
    """Stavka o'zgarsa: shu oydan boshlab xodim ustoz yoki yordamchi bo'lgan davomat qatorlari (8.5)."""
    who = Q(teacher=rate.user) if rate.role_type == KPIRate.RoleType.TEACHER else Q(supporter=rate.user)
    return calc.recalculate(Attendance.objects.filter(date__gte=rate.effective_from, branch=rate.branch, course=rate.course).filter(who))


def _validate_rate(d, instance=None):
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    u, rt, branch, course = get("user"), get("role_type"), get("branch"), get("course")
    if role_code(u) not in (TEACHERS if rt == KPIRate.RoleType.TEACHER else SUPPORTERS):
        raise ValidationError({"user": "Xodim roli tanlangan stavka turiga mos emas"})
    _check_staff(u, branch)
    if not course.branches.filter(pk=branch.pk).exists():
        raise ValidationError({"course": "Kurs bu filialda yo'q"})
    if get("type") == KPIRate.Kind.PERCENT and not (0 <= Decimal(get("percent") or 0) <= 100):
        raise ValidationError({"percent": "0–100 oralig'ida"})
    dup = KPIRate.objects.filter(branch=branch, user=u, role_type=rt, course=course, effective_from=get("effective_from")).exclude(pk=getattr(instance, "pk", None))
    if dup.exists():
        raise ValidationError({"effective_from": "Shu oy uchun bu stavka mavjud — uni tahrirlang"})


@transaction.atomic
def save_rate(user, d, instance=None):
    require_manager(user)
    d = dict(d)
    if d.get("type") == KPIRate.Kind.FIXED:
        d["percent"] = 0
    elif d.get("type") == KPIRate.Kind.PERCENT:
        d["fixed_amount"] = 0
    _validate_rate(d, instance)
    if instance is None:
        r = KPIRate.objects.create(**d, created_by=user, updated_by=user)
        audit.log_create(user, r)
        n = _recalc_rate(r)
    else:
        old_from = instance.effective_from
        r = _update(instance, user, d)
        r.effective_from = min(old_from, r.effective_from)
        n = _recalc_rate(r)
        r.refresh_from_db()
    return r, n


@transaction.atomic
def delete_rate(user, r):
    require_manager(user)
    soft_delete(r, user, check_usage=False)
    return _recalc_rate(r)


# ------------------------------------------------------------------ oylik hisob-kitobi

def kpi_by_month(pairs):
    """{(branch_id, user_id): {yyyymm: (teacher_kpi, supporter_kpi)}} — ikki aggregatsiya so'rovi."""
    out = defaultdict(lambda: defaultdict(lambda: [ZERO, ZERO]))
    if not pairs:
        return out
    branches = {b for b, _ in pairs}
    users = {u for _, u in pairs}
    base = Attendance.objects.filter(branch__in=branches).annotate(m=TruncMonth("date")).order_by()
    for i, field in enumerate(("teacher", "supporter")):
        kpi = f"{field}_kpi"
        for b, u, m, s in base.filter(**{f"{field}__in": users}).values_list("branch", field, "m").annotate(s=Sum(kpi)).values_list("branch", field, "m", "s"):
            if (b, u) in pairs:
                out[(b, u)][ym_key(m.year, m.month)][i] += s or ZERO
    return out


def payouts_by_month(pairs):
    out = defaultdict(lambda: defaultdict(lambda: ZERO))
    if not pairs:
        return out
    qs = SalaryPayout.objects.filter(branch__in={b for b, _ in pairs}, user__in={u for _, u in pairs}).order_by()
    for b, u, y, m, s in qs.values_list("branch", "user", "year", "month").annotate(s=Sum("amount")).values_list("branch", "user", "year", "month", "s"):
        if (b, u) in pairs:
            out[(b, u)][ym_key(y, m)] += s
    return out


def compute(assignments):
    """Har bir oylik belgilashga hisoblangan maydonlarni qo'shadi: tkpi, skpi, total, given, carried, final.
    Tarix (oldingi oylar) xodim + filial bo'yicha to'liq olinadi — qoldiq yillar oralig'ida ham o'tadi (19-bo'lim 6-xato)."""
    assignments = list(assignments)
    pairs = {(a.branch_id, a.user_id) for a in assignments}
    history = defaultdict(dict)
    for h in SalaryAssignment.objects.filter(branch__in={b for b, _ in pairs}, user__in={u for _, u in pairs}):
        if (h.branch_id, h.user_id) in pairs:
            history[(h.branch_id, h.user_id)][ym_key(h.year, h.month)] = h
    kpis, pays = kpi_by_month(pairs), payouts_by_month(pairs)
    results = {}
    for pair in pairs:
        running = ZERO
        months = sorted(set(history[pair]) | set(pays[pair]))
        for key in months:
            given = pays[pair].get(key, ZERO)
            h = history[pair].get(key)
            if h is None:  # belgilanmagan oy uchun berilgan pul — qoldiqdan ayiriladi
                running -= given
                continue
            tk, sk = kpis[pair].get(key, (ZERO, ZERO))
            total = h.fixed + h.bonus + h.kpi + tk + sk - h.fine
            carried = running + h.opening_balance
            final = carried + total - given
            results[h.pk] = {"tkpi": tk, "skpi": sk, "total": total, "given": given, "carried": carried, "final": final}
            running = final
    for a in assignments:
        for k, v in results.get(a.pk, {}).items():
            setattr(a, k, v)
    return assignments


def latest_per_user(qs):
    """Xodim balansi: har (filial, xodim) uchun eng oxirgi oylik belgilash."""
    best = {}
    for a in qs.select_related("user__role"):
        k = (a.branch_id, a.user_id)
        if k not in best or ym_key(a.year, a.month) > ym_key(best[k].year, best[k].month):
            best[k] = a
    return compute(best.values())


# ------------------------------------------------------------------ oylik belgilash

@transaction.atomic
def save_assignment(user, d, instance=None):
    require_manager(user)
    d = dict(d)
    if instance is not None:
        check_edit_window(user, "salaries", instance.created_at)
        for k in ("branch", "user", "year", "month"):
            if k in d and d[k] != getattr(instance, k):
                raise ValidationError({k: "Xodim va davrni o'zgartirib bo'lmaydi — yangi yozuv qo'shing"})
    else:
        _check_staff(d["user"], d["branch"])
        if SalaryAssignment.objects.filter(branch=d["branch"], user=d["user"], year=d["year"], month=d["month"]).exists():
            raise ValidationError({"month": "Bu xodimga shu oy uchun oylik belgilangan"})
    if "opening_balance" in d and role_code(user) != RoleCode.ADMIN and d["opening_balance"] != getattr(instance, "opening_balance", ZERO):
        raise PermissionDenied("Boshlang'ich qoldiqni faqat Admin o'zgartiradi (AppSheet'dan import)")
    if instance is None:
        a = SalaryAssignment.objects.create(**d, created_by=user, updated_by=user)
        audit.log_create(user, a)
        return a
    return _update(instance, user, d)


@transaction.atomic
def delete_assignment(user, a):
    require_manager(user)
    check_edit_window(user, "salaries", a.created_at, op="d")
    soft_delete(a, user, check_usage=False)


@transaction.atomic
def copy_previous_month(user, branch, year, month):
    """O'tgan oydagi belgilangan oyliklarni (faqat «belgilangan» summa) shu oyga nusxalaydi. Qaytaradi: yaratilganlar soni."""
    require_manager(user)
    prev = (datetime.date(year, month, 1) - datetime.timedelta(days=1))
    n = 0
    existing = set(SalaryAssignment.objects.filter(branch=branch, year=year, month=month).values_list("user_id", flat=True))
    for s in SalaryAssignment.objects.filter(branch=branch, year=prev.year, month=prev.month).select_related("user"):
        if s.user_id in existing or s.user.employment_status != s.user.Employment.ACTIVE:
            continue
        a = SalaryAssignment.objects.create(branch=branch, user=s.user, year=year, month=month, fixed=s.fixed, created_by=user, updated_by=user)
        audit.log_create(user, a, detail=f"{prev:%m.%Y} dan nusxa")
        n += 1
    return n


# ------------------------------------------------------------------ oylik berish

def payout_rows(p):
    return [(p.account, p.cash_type, -p.amount, True, p.user)]


@transaction.atomic
def save_payout(user, d, instance=None):
    if not can(user, "salaries", "a" if instance is None else "e"):
        raise PermissionDenied("Sizning rolingizda bu amalga ruxsat yo'q")
    d = dict(d)
    if instance is not None:
        check_edit_window(user, "salaries", instance.date)
        if any(k in d and d[k] != getattr(instance, k) for k in ("branch", "user")):
            raise ValidationError({"user": "Xodimni o'zgartirib bo'lmaydi"})
    get = lambda k: d.get(k, getattr(instance, k, None))  # noqa: E731
    pay_date = get("date") or today()
    d["date"] = pay_date
    if pay_date > today():
        raise ValidationError({"date": "Kelajak sana bo'lishi mumkin emas"})
    if not is_top(user) and (instance is None or "date" in d) and pay_date != today():
        raise ValidationError({"date": "Faqat bugun bilan kiritish mumkin, xolos"})
    if instance is None:
        _check_staff(d["user"], d["branch"])
    if get("cash_type") not in dict(MONEY_TYPES):
        raise ValidationError({"cash_type": "Pul turini tanlang"})
    acc, amount = get("account"), Decimal(get("amount") or 0)
    if (instance is None or "account" in d) and not fin.my_accounts(user).filter(pk=acc.pk).exists():
        raise ValidationError({"account": "Siz mas'ul bo'lgan faol g'aznani tanlang"})
    fin.check_account_type(acc, get("cash_type"), "account")
    if amount <= 0:
        raise ValidationError({"amount": "0 dan katta bo'lsin"})
    fin.check_funds(user, acc, get("cash_type"), amount, exclude=(CashMovement.Source.SALARY, instance.pk) if instance else None)
    if instance is None:
        p = SalaryPayout.objects.create(**d, cashier=user, created_by=user, updated_by=user)
        audit.log_create(user, p)
    else:
        p = _update(instance, user, d)
    fin.sync_movements(CashMovement.Source.SALARY, p, payout_rows(p))
    return p


@transaction.atomic
def delete_payout(user, p):
    check_edit_window(user, "salaries", p.date, op="d")
    soft_delete(p, user, check_usage=False)
    fin.sync_movements(CashMovement.Source.SALARY, p, [])


# ------------------------------------------------------------------ hisoblangan KPI (daraxt)

def kpi_entries(qs):
    """Oy + xodim + rol + guruh bo'yicha: dars qatorlari, KPI yozilgan qatorlar, hisoblanmaganlar, KPI summasi."""
    out = []
    qs = qs.annotate(m=TruncMonth("date")).order_by()
    for role, field in (("USTOZ", "teacher"), ("YORDAMCHI", "supporter")):
        kpi = f"{field}_kpi"
        rows = (qs.exclude(**{f"{field}__isnull": True}).values("branch", "m", field, "group", "course")
                .annotate(n=Count("id"), paid=Count("id", filter=Q(**{f"{kpi}__gt": 0})), pending=Count("id", filter=Q(**{f"{kpi}__isnull": True})), sum=Sum(kpi)))
        for r in rows:
            out.append({"branch": r["branch"], "ym": f"{r['m']:%Y-%m}", "user": r[field], "role": role, "group": r["group"], "course": r["course"],
                        "n": r["n"], "paid": r["paid"], "pending": r["pending"], "sum": r["sum"] or ZERO})
    return out


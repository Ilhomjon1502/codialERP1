"""Ovozli buyruq bandlari: Gemini qaytargan xom qiymatlarni bazadagi yozuvlarga moslash (`resolve`) va mavjud servislar orqali bajarish.

Har bir band: {"type", "raw" (Gemini), "picked" (menejer tugma bilan tanlagan: maydon → id), "need", "result"}.
`resolve` har safar bazadan qayta o'qiydi (karta chizilganda ham, bajarilganda ham) — eskirgan qiymat saqlanmaydi.
Ruxsat, muddat, g'azna qoldig'i va limitlarni saytdagi kabi servislar tekshiradi."""

import datetime
import html
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.core.models import Status
from apps.core.permissions import role_code
from apps.core.roles import RoleCode
from apps.finance import services as fin
from apps.finance.models import CashType, Confirm, Creditor, Payment, Transfer
from apps.payroll import services as payroll
from apps.payroll.models import SalaryAssignment, SalaryPayout
from apps.references.models import Branch, DiscountType, ExpenseCategory
from apps.tasks import services as tasks

from . import match

MONEY = {"CASH": CashType.CASH, "CARD": CashType.CARD, "BANK": CashType.BANK}
CASH_LABEL = {CashType.CASH: "naqd", CashType.CARD: "karta", CashType.BANK: "bank"}
MAX_LIST = 15
TASK_DEFAULT_HOUR = 18



def escape(s):
    """Telegram HTML uchun (apostrof o'zgarmaydi: «g'azna»)."""
    return html.escape(str(s), quote=False)

class Need(Exception):
    """Menejer tanlashi kerak: maydon, savol, [(id, nomi)]."""

    def __init__(self, field, label, options):
        super().__init__(label)
        self.field, self.label, self.options = field, label, options


class Bad(Exception):
    """Bandni bajarib bo'lmaydi (topilmadi, summa yo'q…) — sababi kartada ko'rinadi."""


class Ctx:
    def __init__(self, user, said_at=None):
        self.user = user
        self.said = timezone.localtime(said_at or timezone.now())
        self.day = self.said.date()


class Resolved:
    def __init__(self, title, lines, data):
        self.title, self.lines, self.data = title, lines, data


# ------------------------------------------------------------------ yordamchilar

def money(v):
    if v in (None, "", 0, "0"):
        return None
    try:
        n = Decimal(str(v).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return n.quantize(Decimal(1)) if n else None


def fmt(n):
    return fin.fmt(n)


def parse_date(v, default):
    if not v:
        return default
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return default


def parse_period(v, default_date):
    try:
        y, m = (int(x) for x in str(v)[:7].split("-"))
        if 1 <= m <= 12 and 2020 <= y <= 2100:
            return y, m
    except (TypeError, ValueError):
        pass
    return default_date.year, default_date.month


def cash_type(v, default=CashType.CASH):
    return MONEY.get(str(v or "").upper(), default)


def pick(item, field, label, value, candidates, required=True):
    """candidates: [(obj, nomi)] yoki [(kalit, nomi)]. Avval menejer tanlagani, keyin nom bo'yicha moslash."""
    candidates = list(candidates)
    chosen = (item.get("picked") or {}).get(field)
    if chosen is not None:
        for obj, _ in candidates:
            if str(getattr(obj, "pk", obj)) == str(chosen):
                return obj
    if not value and not required:
        return None
    obj, options = match.find(value, candidates)
    if obj is not None:
        return obj
    if not options:
        raise Bad(f"{label}: «{value}» topilmadi" if value else f"{label} topilmadi")
    what = f"«{value}» — qaysi biri?" if value else "tanlang"
    raise Need(field, f"{label}: {what}", [(str(getattr(o, "pk", o)), name) for o, name in options])


def branch_of(item):
    active = list(Branch.objects.filter(status=Status.ACTIVE))
    if len(active) == 1:
        return active[0]
    return pick(item, "branch", "Filial", item["raw"].get("branch"), [(b, b.name) for b in active])


def account_of(ctx, item, ct, branch):
    raw = item["raw"].get("account")
    accs = [(a, a.name) for a in fin.my_accounts(ctx.user).order_by("name")]
    if raw or (item.get("picked") or {}).get("account"):
        return pick(item, "account", "G'azna", raw, accs)
    default = branch.default_cashbox if ct == CashType.CASH else branch.noncash_cashbox
    if default is not None and default.status == Status.ACTIVE:
        return default
    return pick(item, "account", "G'azna", "", accs)


def acc_line(acc, ct):
    return f"G'azna: {escape(acc.name)} ({CASH_LABEL.get(ct, ct)})"


def day_line(d, ctx, label="Sana"):
    note = "" if d == timezone.localdate() else " ⚠️ bugun emas"
    return f"{label}: {d:%d.%m.%Y}{note}"


def student_q(name):
    q = Q()
    for t in [t for t in match.norm(name).replace("'", " ").split() if len(t) >= 3][:3]:
        q &= Q(contract__student__first_name__icontains=t) | Q(contract__student__last_name__icontains=t) | Q(contract__student__father_name__icontains=t)
    return q


def pay_label(p):
    parts = [str(p.contract.student), f"{p.date:%d.%m}"]
    if p.amount:
        parts.append(f"{fmt(p.amount)} {CASH_LABEL.get(p.cash_type, '')}".strip())
    if p.discount:
        parts.append(f"chegirma {fmt(p.discount)}")
    return " · ".join(parts)


def short_list(lines):
    return lines[:MAX_LIST] + ([f"… yana {len(lines) - MAX_LIST} ta"] if len(lines) > MAX_LIST else [])


# ------------------------------------------------------------------ xarajat

def r_expense(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    cats = ExpenseCategory.objects.filter(allowed_roles__code=role_code(ctx.user)).distinct().order_by("name")
    cat = pick(item, "category", "Kategoriya", raw.get("category"), [(c, c.name) for c in cats])
    qty = int(raw.get("quantity") or 1) if str(raw.get("quantity") or "1").isdigit() else 1
    price = money(raw.get("price"))
    if price is None:
        raise Bad("Summa aytilmadi")
    ct = cash_type(raw.get("cash_type"))
    acc = account_of(ctx, item, ct, branch)
    d = parse_date(raw.get("date"), ctx.day)
    py, pm = parse_period(raw.get("period"), d)
    name = (raw.get("name") or cat.name).strip()[:150]
    total = qty * price
    lines = [f"Kategoriya: {escape(cat.name)}", f"Nomi: {escape(name)}",
             f"Summa: {qty} × {fmt(price)} = <b>{fmt(total)}</b> so'm" if qty > 1 else f"Summa: <b>{fmt(total)}</b> so'm",
             acc_line(acc, ct), day_line(d, ctx)]
    if (py, pm) != (d.year, d.month):
        lines.append(f"Hisob davri: {pm:02d}.{py}")
    if raw.get("comment"):
        lines.append(f"Izoh: {escape(str(raw['comment']))}")
    data = {"branch": branch, "date": d, "category": cat, "name": name, "quantity": qty, "price": price, "cash_type": ct, "account": acc,
            "period_year": py, "period_month": pm, "comment": str(raw.get("comment") or "")}
    return Resolved("💸 Xarajat", lines, data)


def x_expense(ctx, data):
    e = fin.save_expense(ctx.user, data)
    return f"✅ Xarajat saqlandi: {escape(e.name)} — {fmt(e.total)} so'm"


# ------------------------------------------------------------------ kreditor (tashqi pul oqimi)

DIRECTIONS = [("out", "💸 G'aznadan chiqdi (olib ketdi / qarz qaytarildi)"), ("in", "💰 G'aznaga kirdi (qarz olindi / pul kiritdi)")]


def r_creditor(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    cred = pick(item, "creditor", "Kreditor", raw.get("creditor"), [(c, c.name) for c in Creditor.objects.order_by("name")])
    amount = money(raw.get("amount"))
    if amount is None:
        raise Bad("Summa aytilmadi")
    amount = abs(amount)
    direction = (item.get("picked") or {}).get("direction") or raw.get("direction")
    if direction not in ("out", "in"):
        raise Need("direction", "Pul qaysi tomonga?", DIRECTIONS)
    ct = cash_type(raw.get("cash_type"))
    acc = account_of(ctx, item, ct, branch)
    d = parse_date(raw.get("date"), ctx.day)
    signed = amount if direction == "out" else -amount  # «+» qaytarish (g'aznadan chiqadi), «−» qarz olish (g'aznaga kiradi)
    now = fin.creditor_current(cred)
    lines = [f"Kreditor: <b>{escape(cred.name)}</b>", f"{dict(DIRECTIONS)[direction]}: <b>{fmt(amount)}</b> so'm",
             acc_line(acc, ct), day_line(d, ctx), f"Kreditor haqqi: {fmt(now)} → {fmt(now - signed)}"]
    if raw.get("comment"):
        lines.append(f"Izoh: {escape(str(raw['comment']))}")
    return Resolved("🏦 Tashqi pul oqimi", lines, {"date": d, "creditor": cred, "amount": signed, "cash_type": ct, "account": acc,
                                                  "comment": str(raw.get("comment") or "")})


def x_creditor(ctx, data):
    t = fin.save_creditor_tx(ctx.user, data)
    return f"✅ Kreditor amali saqlandi: {escape(t.creditor.name)} {'+' if t.amount > 0 else '−'}{fmt(abs(t.amount))} so'm"


# ------------------------------------------------------------------ o'tkazmalarni tasdiqlash

def r_confirm_transfer(ctx, item):
    raw = item["raw"]
    qs = Transfer.objects.filter(status=Confirm.PENDING).select_related("sender_account", "receiver_account").order_by("date", "created_at")
    pending = list(qs)
    mine = [t for t in pending if fin.can_confirm_transfer(ctx.user, t)]
    amount, d = money(raw.get("amount")), parse_date(raw.get("date"), None)
    out = []
    for t in mine:
        if raw.get("from_account") and match.norm(raw["from_account"]) not in match.norm(t.sender_account.name):
            continue
        if raw.get("to_account") and match.norm(raw["to_account"]) not in match.norm(t.receiver_account.name):
            continue
        if (amount and t.amount != amount) or (d and t.date != d):
            continue
        out.append(t)
    if not out:
        extra = f" ({len(pending) - len(mine)} tasini qabul qiluvchi g'azna mas'uli tasdiqlaydi)" if len(pending) > len(mine) else ""
        raise Bad(f"Tasdiq kutayotgan o'tkazma topilmadi{extra}")
    lines = short_list([f"{t.date:%d.%m} · {escape(t.sender_account.name)} → {escape(t.receiver_account.name)} · {fmt(t.amount)}" for t in out])
    lines.append(f"Jami: {len(out)} ta, {fmt(sum(t.amount for t in out))} so'm")
    return Resolved("🔁 O'tkazmalarni tasdiqlash", lines, {"ids": [t.pk for t in out]})


def x_confirm_transfer(ctx, data):
    ok, errors = 0, []
    for t in Transfer.objects.filter(pk__in=data["ids"]).select_related("receiver_account"):
        try:
            fin.confirm_transfer(ctx.user, t)
            ok += 1
        except (ValidationError, PermissionDenied) as e:
            errors.append(error_text(e))
    return f"✅ {ok} ta o'tkazma tasdiqlandi" + (f"; ⚠️ {len(errors)} tasi: {escape(errors[0])}" if errors else "")


# ------------------------------------------------------------------ to'lovlarni tasdiqlash

def r_approve_payment(ctx, item):
    raw = item["raw"]
    what = raw.get("what") if raw.get("what") in ("noncash", "discount") else "both"
    qs = Payment.objects.filter(Q(noncash_status=Confirm.PENDING) | Q(discount_status=Confirm.PENDING)).select_related("contract__student", "discount_type")
    if raw.get("student"):
        qs = qs.filter(student_q(raw["student"]))
    amount, d = money(raw.get("amount")), parse_date(raw.get("date"), None)
    if d:
        qs = qs.filter(date=d)
    rows = []
    for p in qs.order_by("date", "number"):
        if what in ("noncash", "both") and p.noncash_status == Confirm.PENDING and fin.can_approve_noncash(ctx.user, p) and (not amount or p.amount == amount):
            rows.append(("n", p, f"💳 {escape(str(p.contract.student))} · {p.date:%d.%m} · {fmt(p.amount)} {CASH_LABEL.get(p.cash_type, '')}"))
        if what in ("discount", "both") and p.discount_status == Confirm.PENDING and fin.can_approve_discount(ctx.user, p) and (not amount or p.discount == amount):
            rows.append(("d", p, f"🏷 {escape(str(p.contract.student))} · {p.date:%d.%m} · chegirma {fmt(p.discount)} ({escape(str(p.discount_type or ''))})"))
    if not rows:
        raise Bad("Tasdiq kutayotgan to'lov yoki chegirma topilmadi")
    title = {"noncash": "💳 Naqdsiz to'lovlarni tasdiqlash", "discount": "🏷 Chegirmalarni tasdiqlash"}.get(what, "✔️ To'lov va chegirmalarni tasdiqlash")
    return Resolved(title, short_list([r[2] for r in rows]) + [f"Jami: {len(rows)} ta"], {"rows": [(k, p.pk) for k, p, _ in rows]})


def x_approve_payment(ctx, data):
    ok, errors = 0, []
    for kind, pk in data["rows"]:
        p = Payment.objects.filter(pk=pk).select_related("contract", "branch").first()
        if p is None:
            continue
        try:
            (fin.approve_noncash if kind == "n" else fin.approve_discount)(ctx.user, p)
            ok += 1
        except (ValidationError, PermissionDenied) as e:
            errors.append(error_text(e))
    return f"✅ {ok} ta tasdiqlandi" + (f"; ⚠️ {len(errors)} tasi: {escape(errors[0])}" if errors else "")


# ------------------------------------------------------------------ to'lovni o'zgartirish

def r_payment_edit(ctx, item):
    raw = item["raw"]
    if not raw.get("student"):
        raise Bad("Qaysi o'quvchining to'lovi — ism aytilmadi")
    qs = Payment.objects.filter(student_q(raw["student"])).select_related("contract__student", "contract__branch", "cashbox", "discount_type")
    d, amount = parse_date(raw.get("date"), None), money(raw.get("amount"))
    if d:
        qs = qs.filter(date=d)
    if amount:
        qs = qs.filter(amount=amount)
    found = list(qs.order_by("-date", "-number")[:match.MAX_OPTIONS])
    if not found:
        raise Bad(f"To'lov topilmadi: «{raw['student']}»")
    chosen = (item.get("picked") or {}).get("payment")
    p = next((x for x in found if str(x.pk) == str(chosen)), None) or (found[0] if len(found) == 1 else None)
    if p is None:
        raise Need("payment", "Qaysi to'lov?", [(str(x.pk), pay_label(x)) for x in found])
    s = raw.get("set") or {}
    d_upd, lines = {}, [f"To'lov №{p.number}: {escape(pay_label(p))}"]
    new_amount = money(s.get("amount"))
    if new_amount is not None and new_amount != p.amount:
        d_upd["amount"] = new_amount
        lines.append(f"Summa: {fmt(p.amount)} → <b>{fmt(new_amount)}</b>")
    new_date = parse_date(s.get("date"), None)
    if new_date and new_date != p.date:
        d_upd["date"] = new_date
        lines.append(f"Sana: {p.date:%d.%m.%Y} → <b>{new_date:%d.%m.%Y}</b>")
    new_ct = MONEY.get(str(s.get("cash_type") or "").upper())
    if new_ct and new_ct != p.cash_type:
        d_upd["cash_type"] = new_ct
        lines.append(f"Turi: {CASH_LABEL.get(p.cash_type, '—')} → <b>{CASH_LABEL[new_ct]}</b>")
    if (d_upd.get("cash_type") or p.cash_type) == CashType.CASH and (new_ct or "amount" in d_upd):
        box = p.cashbox if p.cash_type == CashType.CASH and p.cashbox else account_of(ctx, item, CashType.CASH, p.contract.branch)
        d_upd["cashbox"] = box
    new_disc = money(s.get("discount")) if s.get("discount") not in (None, "") else None
    if s.get("discount") in (0, "0"):
        new_disc = Decimal(0)
    if new_disc is not None and new_disc != p.discount:
        d_upd["discount"] = new_disc
        lines.append(f"Chegirma: {fmt(p.discount)} → <b>{fmt(new_disc)}</b>")
    if s.get("discount_type") or (new_disc and not p.discount_type_id):
        types = [(t, t.name) for t in DiscountType.objects.filter(is_system=False).order_by("name")]
        dt = pick(item, "discount_type", "Chegirma turi", s.get("discount_type"), types)
        if dt.pk != p.discount_type_id:
            d_upd["discount_type"] = dt
            lines.append(f"Chegirma turi: {escape(str(p.discount_type or '—'))} → <b>{escape(dt.name)}</b>")
    if s.get("comment"):
        d_upd["comment"] = str(s["comment"])
        lines.append(f"Izoh: {escape(str(s['comment']))}")
    if not d_upd or set(d_upd) == {"cashbox"}:
        raise Bad(f"{pay_label(p)}: nimani o'zgartirish aytilmadi")
    return Resolved("✏️ To'lovni o'zgartirish", lines, {"payment": p.pk, "set": d_upd})


def x_payment_edit(ctx, data):
    p = Payment.objects.select_related("contract__branch", "contract__group").get(pk=data["payment"])
    fin.save_payment(ctx.user, data["set"], instance=p)
    return f"✅ To'lov №{p.number} o'zgartirildi"


# ------------------------------------------------------------------ oyliklar

def staff(ctx, item, raw_name):
    qs = User.objects.filter(employment_status=User.Employment.ACTIVE).exclude(role__code__in=[RoleCode.BOSHQA, RoleCode.ADMIN]).order_by("full_name")
    return pick(item, "employee", "Xodim", raw_name, [(u, u.full_name) for u in qs])


def r_salary_payout(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    u = staff(ctx, item, raw.get("employee"))
    amount = money(raw.get("amount"))
    if amount is None:
        raise Bad("Summa aytilmadi")
    ct = cash_type(raw.get("cash_type"))
    acc = account_of(ctx, item, ct, branch)
    d = parse_date(raw.get("date"), ctx.day)
    y, m = parse_period(raw.get("period"), d)
    kind = raw.get("kind") if raw.get("kind") in SalaryPayout.Kind.values else SalaryPayout.Kind.FIXED
    lines = [f"Xodim: <b>{escape(u.full_name)}</b>", f"Summa: <b>{fmt(amount)}</b> so'm ({kind})", f"Qaysi oy uchun: {m:02d}.{y}", acc_line(acc, ct), day_line(d, ctx)]
    if raw.get("comment"):
        lines.append(f"Izoh: {escape(str(raw['comment']))}")
    return Resolved("👛 Oylik berish", lines, {"branch": branch, "user": u, "year": y, "month": m, "date": d, "type": kind, "amount": amount,
                                              "cash_type": ct, "account": acc, "comment": str(raw.get("comment") or "")})


def x_salary_payout(ctx, data):
    p = payroll.save_payout(ctx.user, data)
    return f"✅ Oylik berildi: {escape(p.user.full_name)} — {fmt(p.amount)} so'm"


ADJUST = [("fixed", "Belgilangan oylik"), ("bonus", "Bonus"), ("kpi", "KPI (qo'lda)"), ("fine", "Jarima")]


def r_salary_adjust(ctx, item):
    raw = item["raw"]
    branch = branch_of(item)
    u = staff(ctx, item, raw.get("employee"))
    y, m = parse_period(raw.get("period"), ctx.day)
    a = SalaryAssignment.objects.filter(branch=branch, user=u, year=y, month=m).first()
    add = raw.get("mode") != "set"
    d_upd, lines = {}, [f"Xodim: <b>{escape(u.full_name)}</b>", f"Oy: {m:02d}.{y}"]
    for field, label in ADJUST:
        v = money(raw.get(field))
        if v is None:
            continue
        old = getattr(a, field) if a else Decimal(0)
        new = old + v if add and field != "fixed" else v
        if new < 0:
            raise Bad(f"{label} manfiy bo'lib qoladi")
        d_upd[field] = new
        lines.append(f"{label}: {fmt(old)} → <b>{fmt(new)}</b>")
    if not d_upd:
        raise Bad("Bonus, jarima yoki oylik summasi aytilmadi")
    if raw.get("comment"):
        d_upd["comment"] = str(raw["comment"])
        lines.append(f"Izoh: {escape(str(raw['comment']))}")
    if a is None:
        lines.append("⚠️ Shu oyga oylik belgilanmagan — yangi yozuv yaratiladi")
    return Resolved("🧾 Oylik belgilash", lines, {"assignment": a.pk if a else None, "set": d_upd, "branch": branch, "user": u, "year": y, "month": m})


def x_salary_adjust(ctx, data):
    if data["assignment"]:
        a = payroll.save_assignment(ctx.user, data["set"], instance=SalaryAssignment.objects.get(pk=data["assignment"]))
    else:
        a = payroll.save_assignment(ctx.user, {"branch": data["branch"], "user": data["user"], "year": data["year"], "month": data["month"], **data["set"]})
    return f"✅ Oylik belgilash saqlandi: {escape(a.user.full_name)} · {a.month:02d}.{a.year}"


# ------------------------------------------------------------------ topshiriq

def r_task(ctx, item):
    raw = item["raw"]
    people = [(u, u.full_name) for u in tasks.assignable(ctx.user).order_by("full_name")]
    u = pick(item, "assignee", "Bajaruvchi", raw.get("assignee"), people)
    title = str(raw.get("title") or "").strip()[:200]
    if not title:
        raise Bad("Topshiriq mavzusi aytilmadi")
    due, note = None, ""
    if raw.get("due"):
        try:
            due = datetime.datetime.fromisoformat(str(raw["due"])[:16])
        except ValueError:
            due = None
    if due is None:
        base = timezone.localtime()
        due = datetime.datetime.combine(base.date() + datetime.timedelta(days=0 if base.hour < TASK_DEFAULT_HOUR - 2 else 1), datetime.time(TASK_DEFAULT_HOUR))
        note = " (muddat aytilmadi — standart)"
    if timezone.is_naive(due):
        due = timezone.make_aware(due)
    lines = [f"Kimga: <b>{escape(u.full_name)}</b>", f"Mavzu: {escape(title)}", f"Muddat: {timezone.localtime(due):%d.%m.%Y %H:%M}{note}"]
    if raw.get("description"):
        lines.append(f"Batafsil: {escape(str(raw['description']))}")
    if not tasks.linked(u):
        lines.append("⚠️ Xodim botga ulanmagan — xabar bormaydi")
    return Resolved("📌 Topshiriq", lines, {"title": title, "description": str(raw.get("description") or ""), "assignee": u, "due_at": due,
                                          "remind_before": 60, "remind_every": 0})


def x_task(ctx, data):
    t = tasks.create(ctx.user, data)
    return f"✅ Topshiriq berildi: {escape(t.assignee.full_name)} — {escape(t.title)}"


# ------------------------------------------------------------------ ro'yxat

HANDLERS = {
    "expense": (r_expense, x_expense),
    "creditor": (r_creditor, x_creditor),
    "confirm_transfer": (r_confirm_transfer, x_confirm_transfer),
    "approve_payment": (r_approve_payment, x_approve_payment),
    "payment_edit": (r_payment_edit, x_payment_edit),
    "salary_payout": (r_salary_payout, x_salary_payout),
    "salary_adjust": (r_salary_adjust, x_salary_adjust),
    "task": (r_task, x_task),
}


def error_text(e):
    """DRF xatosidan birinchi o'qiladigan matn."""
    detail = getattr(e, "detail", None)
    if detail is None:
        return str(e)
    while isinstance(detail, (dict, list)) and detail:
        detail = next(iter(detail.values())) if isinstance(detail, dict) else detail[0]
    return str(detail)


def resolve(ctx, item):
    """Qaytaradi: (Resolved | None, need: Need | None, error: str | None)."""
    handler = HANDLERS.get(item.get("type"))
    if handler is None:
        return None, None, None
    try:
        return handler[0](ctx, item), None, None
    except Need as n:
        return None, n, None
    except Bad as b:
        return None, None, str(b)
    except (ValidationError, PermissionDenied, APIException) as e:
        return None, None, error_text(e)


def execute(ctx, item):
    r, need, err = resolve(ctx, item)
    if r is None:
        return f"⚠️ {escape(err or (need.label if need else 'Bajarib bo`lmadi'))}"
    try:
        return HANDLERS[item["type"]][1](ctx, r.data)
    except (ValidationError, PermissionDenied, APIException) as e:
        return f"⚠️ {escape(error_text(e))}"

"""Mavjud yozuvni ovoz bo'yicha topish, o'zgartirish va o'chirish: xarajat, kreditor amali, to'lov, oylik berish, o'tkazma, ayirboshlash.

Gemini `find` (qidiruv belgilari: sana, summa, kategoriya, nomi, g'azna, kreditor, xodim, o'quvchi…) va `set` (yangi qiymatlar) qaytaradi.
Server avval sana/summa/pul turi bo'yicha bazadan, keyin matnli belgilar bo'yicha o'xshashlik bilan saralaydi; bittadan ko'p chiqsa —
tanlash tugmalari. O'chirish va saqlash saytdagi servislar orqali (muddat, ruxsat, qoldiq tekshiruvi)."""

import datetime
import difflib

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.models import Status
from apps.finance import services as fin
from apps.finance.models import Account, CreditorTransaction, Exchange, Expense, Payment, Transfer
from apps.payroll import services as payroll
from apps.payroll.models import SalaryPayout
from apps.references.models import ExpenseCategory

from . import match
from .actions import CASH_LABEL, MONEY, Bad, Need, Resolved, account_of, escape, fmt, money, parse_date, parse_period, pick

LOOKBACK_DAYS = 90
SCAN = 300


def similar(said, text):
    a, b = match.norm(said).replace("'", ""), match.norm(text).replace("'", "")
    if not a:
        return True
    if not b:
        return False
    if a in b or b in a:
        return True
    toks_b = b.split()
    if all(any(t[:4] == u[:4] for u in toks_b) for t in a.split() if len(t) >= 3):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def cash_of(v):
    return MONEY.get(str(v or "").upper())


# ------------------------------------------------------------------ yozuv turlari

def _expense_texts(e):
    return {"category": e.category.name, "name": e.name, "account": e.account.name, "comment": e.comment}


def _expense_label(e):
    return f"{e.date:%d.%m} · {e.category.name} · {e.name} · {fmt(e.total)} {CASH_LABEL.get(e.cash_type, '')}"


def _creditor_label(t):
    return f"{t.date:%d.%m} · {t.creditor.name} · {'+' if t.amount > 0 else '−'}{fmt(abs(t.amount))} {CASH_LABEL.get(t.cash_type, '')} · {t.account.name}"


def _payment_label(p):
    parts = [f"№{p.number}", f"{p.date:%d.%m}", str(p.contract.student)]
    if p.amount:
        parts.append(f"{fmt(p.amount)} {CASH_LABEL.get(p.cash_type, '')}".strip())
    if p.discount:
        parts.append(f"chegirma {fmt(p.discount)}")
    return " · ".join(parts)


ENTITIES = {
    "expense": {
        "title": "Xarajat", "qs": lambda: Expense.objects.select_related("category", "account"), "amount": "total",
        "texts": _expense_texts, "label": _expense_label, "delete": fin.delete_expense,
    },
    "creditor": {
        "title": "Kreditor amali", "qs": lambda: CreditorTransaction.objects.select_related("creditor", "account"), "amount": "amount", "signed": True,
        "texts": lambda t: {"creditor": t.creditor.name, "account": t.account.name, "comment": t.comment}, "label": _creditor_label,
        "delete": fin.delete_creditor_tx,
    },
    "payment": {
        "title": "To'lov", "qs": lambda: Payment.objects.select_related("contract__student", "contract__branch", "cashbox", "discount_type"), "amount": "amount",
        "texts": lambda p: {"student": str(p.contract.student), "account": p.cashbox.name if p.cashbox else "", "comment": p.comment}, "label": _payment_label,
        "delete": fin.delete_payment,
    },
    "salary_payout": {
        "title": "Oylik berish", "qs": lambda: SalaryPayout.objects.select_related("user", "account"), "amount": "amount",
        "texts": lambda p: {"employee": p.user.full_name, "account": p.account.name, "comment": p.comment},
        "label": lambda p: f"{p.date:%d.%m} · {p.user.full_name} · {fmt(p.amount)} ({p.type}, {p.month:02d}.{p.year}) · {p.account.name}",
        "delete": payroll.delete_payout,
    },
    "transfer": {
        "title": "O'tkazma", "qs": lambda: Transfer.objects.select_related("sender_account", "receiver_account"), "amount": "amount",
        "texts": lambda t: {"from_account": t.sender_account.name, "to_account": t.receiver_account.name, "account": f"{t.sender_account.name} {t.receiver_account.name}",
                            "comment": t.comment},
        "label": lambda t: f"{t.date:%d.%m} · {t.sender_account.name} → {t.receiver_account.name} · {fmt(t.amount)} · {t.status}",
        "delete": fin.delete_transfer,
    },
    "exchange": {
        "title": "Pul ayirboshlash", "qs": lambda: Exchange.objects.select_related("account"), "amount": "amount",
        "texts": lambda x: {"account": x.account.name, "comment": x.comment},
        "label": lambda x: f"{x.date:%d.%m} · {x.account.name} · {fmt(x.amount)} {CASH_LABEL.get(x.from_type, '')} → {fmt(x.amount_to)} {CASH_LABEL.get(x.to_type, '')}",
        "delete": fin.delete_exchange,
    },
}

TEXT_KEYS = ("category", "name", "account", "creditor", "employee", "student", "from_account", "to_account", "comment")


def find_record(ctx, item, entity):
    """Qaytaradi: yozuv. Bir nechta bo'lsa — Need (tanlash), hech biri — Bad."""
    ent = ENTITIES[entity]
    f = item["raw"].get("find") or {}
    qs = ent["qs"]()
    chosen = (item.get("picked") or {}).get("record")
    if chosen:
        obj = qs.filter(pk=chosen).first()
        if obj is not None:
            return obj
    obj = _search(ent, entity, f, qs)
    item.setdefault("picked", {})["record"] = str(obj.pk)  # tasdiqlanganda aynan shu yozuv (karta saqlanadi)
    return obj


def _search(ent, entity, f, qs):
    d = parse_date(f.get("date"), None)
    qs = qs.filter(date=d) if d else qs.filter(date__gte=timezone.localdate() - datetime.timedelta(days=LOOKBACK_DAYS))
    amount = money(f.get("amount"))
    if amount is not None:
        a = abs(amount)
        qs = qs.filter(Q(**{ent["amount"]: a}) | Q(**{ent["amount"]: -a})) if ent.get("signed") else qs.filter(**{ent["amount"]: a})
    ct = cash_of(f.get("cash_type"))
    if ct and entity in ("expense", "creditor", "payment", "salary_payout"):
        qs = qs.filter(cash_type=ct)
    rows = list(qs.order_by("-date", "-created_at")[:SCAN])
    said = {k: f[k] for k in TEXT_KEYS if f.get(k)}
    fits = [r for r in rows if all(similar(v, ent["texts"](r).get(k, "")) for k, v in said.items())]
    if f.get("latest") and (fits or rows):
        return max(fits or rows, key=lambda r: r.created_at)
    if len(fits) == 1:
        return fits[0]
    pool = fits or rows
    if not pool:
        raise Bad(f"{ent['title']} topilmadi ({_describe(f)})" if f else f"{ent['title']} topilmadi")
    label = f"{ent['title']}: qaysi biri?" if fits else f"{ent['title']}: aniq mos topilmadi — tanlang"
    raise Need("record", label, [(str(r.pk), ent["label"](r)) for r in pool[:match.MAX_OPTIONS]])


def _describe(f):
    parts = [str(f[k]) for k in ("date", "category", "name", "creditor", "employee", "student", "account") if f.get(k)]
    if money(f.get("amount")):
        parts.append(f"{fmt(abs(money(f['amount'])))} so'm")
    return ", ".join(parts)


# ------------------------------------------------------------------ o'chirish

def r_delete(ctx, item):
    entity = item["raw"].get("entity")
    if entity not in ENTITIES:
        raise Bad("Nimani o'chirish kerakligi tushunilmadi (xarajat, to'lov, kreditor amali, oylik, o'tkazma, ayirboshlash)")
    obj = find_record(ctx, item, entity)
    ent = ENTITIES[entity]
    return Resolved(f"🗑 {ent['title']}ni o'chirish", [escape(ent["label"](obj)), "<b>O'chiriladi</b> (bazada arxivda qoladi, g'azna qoldig'i qaytadi)"],
                    {"entity": entity, "pk": obj.pk})


def x_delete(ctx, data):
    ent = ENTITIES[data["entity"]]
    obj = ent["qs"]().get(pk=data["pk"])
    ent["delete"](ctx.user, obj)
    return f"✅ O'chirildi: {escape(ent['label'](obj))}"


# ------------------------------------------------------------------ o'zgartirish

def _cat(ctx, item, value):
    from apps.core.permissions import role_code

    cats = ExpenseCategory.objects.filter(allowed_roles__code=role_code(ctx.user)).distinct().order_by("name")
    return pick(item, "category", "Kategoriya", value, [(c, c.name) for c in cats])


def _acc(ctx, item, value):
    return pick(item, "account", "G'azna", value, [(a, a.name) for a in fin.my_accounts(ctx.user).order_by("name")])


def _change(lines, label, old, new, show=str):
    lines.append(f"{label}: {escape(show(old))} → <b>{escape(show(new))}</b>")


def edit_expense(ctx, item, e, s):
    d, lines = {}, []
    if s.get("category"):
        c = _cat(ctx, item, s["category"])
        if c.pk != e.category_id:
            d["category"] = c
            _change(lines, "Kategoriya", e.category.name, c.name)
    if s.get("name") and s["name"].strip() != e.name:
        d["name"] = s["name"].strip()[:150]
        _change(lines, "Nomi", e.name, d["name"])
    qty = int(s["quantity"]) if str(s.get("quantity") or "").isdigit() and int(s["quantity"]) > 0 else None
    price = money(s.get("price") or s.get("amount"))
    if qty and qty != e.quantity:
        d["quantity"] = qty
    if price is not None and price != e.price:
        d["price"] = abs(price)
    if "quantity" in d or "price" in d:
        _change(lines, "Summa", e.total, d.get("quantity", e.quantity) * d.get("price", e.price), fmt)
    ct = cash_of(s.get("cash_type"))
    if ct and ct != e.cash_type:
        d["cash_type"] = ct
        _change(lines, "Pul turi", CASH_LABEL[e.cash_type], CASH_LABEL[ct])
    if s.get("account"):
        a = _acc(ctx, item, s["account"])
        if a.pk != e.account_id:
            d["account"] = a
            _change(lines, "G'azna", e.account.name, a.name)
    elif ct and ct != e.cash_type and e.account.cash_type not in ("ALL", ct):
        a = account_of(ctx, {"raw": {}, "picked": item.get("picked") or {}}, ct, e.branch)
        d["account"] = a
        _change(lines, "G'azna", e.account.name, a.name)
    nd = parse_date(s.get("date"), None)
    if nd and nd != e.date:
        d["date"] = nd
        _change(lines, "Sana", f"{e.date:%d.%m.%Y}", f"{nd:%d.%m.%Y}")
    if s.get("period"):
        y, m = parse_period(s["period"], e.date)
        if (y, m) != (e.period_year, e.period_month):
            d["period_year"], d["period_month"] = y, m
            _change(lines, "Hisob davri", f"{e.period_month:02d}.{e.period_year}", f"{m:02d}.{y}")
    if s.get("comment") is not None and str(s["comment"]) != e.comment:
        d["comment"] = str(s["comment"])
        _change(lines, "Izoh", e.comment or "—", d["comment"])
    return d, lines, lambda: fin.save_expense(ctx.user, d, instance=e)


def edit_creditor(ctx, item, t, s):
    """Saytda kreditor amali tahrirlanmaydi (o'chirib qayta kiritiladi) — bu yerda ham shunday, bitta tranzaksiyada."""
    new = {"date": t.date, "creditor": t.creditor, "amount": t.amount, "cash_type": t.cash_type, "account": t.account, "comment": t.comment}
    lines = []
    amount = money(s.get("amount"))
    direction = s.get("direction")
    if amount is not None or direction in ("out", "in"):
        a = abs(amount) if amount is not None else abs(t.amount)
        sign = 1 if (direction == "out" or (direction is None and t.amount > 0)) else -1
        if a * sign != t.amount:
            new["amount"] = a * sign
            _change(lines, "Summa", t.amount, new["amount"], lambda v: f"{'+' if v > 0 else '−'}{fmt(abs(v))}")
    ct = cash_of(s.get("cash_type"))
    if ct and ct != t.cash_type:
        new["cash_type"] = ct
        _change(lines, "Pul turi", CASH_LABEL[t.cash_type], CASH_LABEL[ct])
    if s.get("account"):
        a = _acc(ctx, item, s["account"])
        if a.pk != t.account_id:
            new["account"] = a
            _change(lines, "G'azna", t.account.name, a.name)
    nd = parse_date(s.get("date"), None)
    if nd and nd != t.date:
        new["date"] = nd
        _change(lines, "Sana", f"{t.date:%d.%m.%Y}", f"{nd:%d.%m.%Y}")
    if s.get("comment") is not None and str(s["comment"]) != t.comment:
        new["comment"] = str(s["comment"])
        _change(lines, "Izoh", t.comment or "—", new["comment"])

    @transaction.atomic
    def save():
        fin.delete_creditor_tx(ctx.user, t)
        return fin.save_creditor_tx(ctx.user, new)

    return (new if lines else {}), lines, save


def edit_salary_payout(ctx, item, p, s):
    d, lines = {}, []
    amount = money(s.get("amount"))
    if amount is not None and abs(amount) != p.amount:
        d["amount"] = abs(amount)
        _change(lines, "Summa", p.amount, d["amount"], fmt)
    ct = cash_of(s.get("cash_type"))
    if ct and ct != p.cash_type:
        d["cash_type"] = ct
        _change(lines, "Pul turi", CASH_LABEL.get(p.cash_type, p.cash_type), CASH_LABEL[ct])
    if s.get("account"):
        a = _acc(ctx, item, s["account"])
        if a.pk != p.account_id:
            d["account"] = a
            _change(lines, "G'azna", p.account.name, a.name)
    nd = parse_date(s.get("date"), None)
    if nd and nd != p.date:
        d["date"] = nd
        _change(lines, "Sana", f"{p.date:%d.%m.%Y}", f"{nd:%d.%m.%Y}")
    if s.get("period"):
        y, m = parse_period(s["period"], p.date)
        if (y, m) != (p.year, p.month):
            d["year"], d["month"] = y, m
            _change(lines, "Qaysi oy uchun", f"{p.month:02d}.{p.year}", f"{m:02d}.{y}")
    if s.get("kind") in SalaryPayout.Kind.values and s["kind"] != p.type:
        d["type"] = s["kind"]
        _change(lines, "Turi", p.type, s["kind"])
    if s.get("comment") is not None and str(s["comment"]) != p.comment:
        d["comment"] = str(s["comment"])
        _change(lines, "Izoh", p.comment or "—", d["comment"])
    return d, lines, lambda: payroll.save_payout(ctx.user, d, instance=p)


def edit_transfer(ctx, item, t, s):
    d, lines = {}, []
    amount = money(s.get("amount"))
    if amount is not None and abs(amount) != t.amount:
        d["amount"] = abs(amount)
        _change(lines, "Summa", t.amount, d["amount"], fmt)
    nd = parse_date(s.get("date"), None)
    if nd and nd != t.date:
        d["date"] = nd
        _change(lines, "Sana", f"{t.date:%d.%m.%Y}", f"{nd:%d.%m.%Y}")
    if s.get("to_account"):
        a = pick(item, "to_account", "Qabul qiluvchi g'azna", s["to_account"], [(x, x.name) for x in Account.objects.filter(status=Status.ACTIVE).order_by("name")])
        if a.pk != t.receiver_account_id:
            d["receiver_account"] = a
            _change(lines, "Qayerga", t.receiver_account.name, a.name)
    if s.get("comment") is not None and str(s["comment"]) != t.comment:
        d["comment"] = str(s["comment"])
        _change(lines, "Izoh", t.comment or "—", d["comment"])
    return d, lines, lambda: fin.save_transfer(ctx.user, d, instance=t)


EDITORS = {"expense": edit_expense, "creditor": edit_creditor, "salary_payout": edit_salary_payout, "transfer": edit_transfer}


def r_edit(ctx, item):
    raw = item["raw"]
    entity = raw.get("entity")
    if entity == "payment":  # to'lov — alohida (chegirma, g'azna, qayta tasdiq qoidalari bilan)
        from .actions import r_payment_edit

        f = raw.get("find") or {}
        item.setdefault("picked", {})
        return r_payment_edit(ctx, {**item, "raw": {"student": f.get("student"), "date": f.get("date"), "amount": f.get("amount"), "set": raw.get("set") or {}}})
    if entity not in EDITORS:
        raise Bad("Nimani o'zgartirish kerakligi tushunilmadi (xarajat, to'lov, kreditor amali, oylik berish, o'tkazma)")
    obj = find_record(ctx, item, entity)
    d, lines, _ = EDITORS[entity](ctx, item, obj, raw.get("set") or {})
    if not d:
        raise Bad(f"{ENTITIES[entity]['label'](obj)}: nimani o'zgartirish aytilmadi")
    return Resolved(f"✏️ {ENTITIES[entity]['title']}ni o'zgartirish", [escape(ENTITIES[entity]["label"](obj)), *lines],
                    {"entity": entity, "pk": obj.pk, "item": item})


def x_edit(ctx, data):
    if "payment" in data:  # to'lov (r_payment_edit natijasi)
        from .actions import x_payment_edit

        return x_payment_edit(ctx, data)
    ent, item = ENTITIES[data["entity"]], data["item"]
    obj = ent["qs"]().get(pk=data["pk"])
    _, _, save = EDITORS[data["entity"]](ctx, item, obj, item["raw"].get("set") or {})
    saved = save()
    return f"✅ O'zgartirildi: {escape(ent['label'](saved if isinstance(saved, type(obj)) else obj))}"

"""Oylik moliyaviy hisobot — Google Sheets (buyurtmachi namunasi «Codial moliyaviy hisobot.xlsx»).
Bitta doimiy fayl, har oy yangi varaq. Qayta bosilsa shu oy varag'idagi raqamlar yangilanadi; qo'lda yozilganlar (O16:O17 «avvalgi oydan»
qoldiq va A:B, K:L, Q+ ustunlaridagi izohlar) saqlanadi. Foyda sahifasi (`services.profit`) bilan bir xil manbalar."""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.scoping import scope_branch
from apps.finance.models import CreditorTransaction, Expense, Payment
from apps.payroll import services as payroll
from apps.payroll.models import SalaryAssignment
from apps.references.models import ExpenseCategory

from . import gsheets as gs
from .services import bounds

UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
TEACHER_ROLES = {"USTOZ", "USTOZ_YORDAMCHI", "YORDAMCHI"}
# Namunadagi qator tartibi; qolgan kategoriyalar alifbo bo'yicha keyin
EXPENSE_ORDER = ["ijara", "internet", "komunal", "marketing", "jamoani rivojlantirish", "oziq-ovqat", "xizmat ko'rsatish", "xo'jalik xarajatlari", "boshqa", "auksion"]
MIN_ROWS = 13  # ro'yxatlarda kamida shuncha qator (namunadagidek); ko'p bo'lsa jadval cho'ziladi
NOTE_LINES = 40
GRID_ROWS = 60

# 0-based ustunlar (A=0)
C, D, E, F, CX, J, M, N, CP, P = 2, 3, 4, 5, 8, 9, 12, 13, 14, 15

COLORS = {
    "oyliklar": "00FFFF", "ustozlar": "00FF00", "xodimlar": "FF9900", "t_row": "93C47D", "s_row": "A4C2F4", "total": "B4A7D6",
    "xarajat": "B6D7A8", "e_row": "A4C2F4", "tushum": "E6B8AF", "prev": "FFF2CC", "share": "FCE5CD", "pct": "EAD1DC",
    "taken": "D9EAD3", "end": "C9DAF8",
}


def tab_title(month):
    return f"{UZ_MONTHS[month.month - 1]} {month.year}"


def _norm(s):
    return " ".join(str(s).lower().replace("’", "'").replace("ʻ", "'").replace("`", "'").split())


def _num(x):
    return int(Decimal(x or 0))


def _sp(n):
    return f"{n:,}".replace(",", " ")


def _col(c):
    return chr(ord("A") + c)


def _safe(text):
    """Foydalanuvchi matni Sheets'da formula bo'lib qolmasin."""
    text = str(text)
    return "'" + text if text[:1] in "=+-@" else text


def _a1(r, c):
    return f"{_col(c)}{r + 1}"  # r — 0-based


# ------------------------------------------------------------------ ma'lumot

def collect(user, month):
    """Foyda sahifasi bilan bir xil manbalar: to'lovlar (sana), xarajatlar («Xarajat» turi, hisob davri), hisoblangan oyliklar,
    kreditorlar (MNSH/Ilhomjon) bo'yicha olingan pullar."""
    lo, hi = bounds(month, month)
    income = scope_branch(Payment.objects.filter(date__gte=lo, date__lt=hi), user).aggregate(s=Sum("amount"))["s"]

    groups = defaultdict(list)
    exps = scope_branch(Expense.objects.filter(period_year=month.year, period_month=month.month, category__kind=ExpenseCategory.Kind.EXPENSE), user)
    for e in exps.select_related("category").order_by("date", "created_at"):
        groups[e.category.name].append(e)
    rank = {n: i for i, n in enumerate(EXPENSE_ORDER)}
    expenses = []
    for name in sorted(groups, key=lambda n: (rank.get(_norm(n), len(rank)), _norm(n))):
        items = groups[name]
        lines = [f"{e.date:%d.%m} · {e.name} — {e.quantity} × {_sp(_num(e.price))} = {_sp(_num(e.total))}" + (f" · {e.comment.strip()}" if e.comment.strip() else "") for e in items]
        if len(lines) > NOTE_LINES:
            lines = lines[:NOTE_LINES] + [f"… yana {len(lines) - NOTE_LINES} ta"]
        expenses.append({"name": name, "total": sum(_num(e.total) for e in items), "note": "\n".join(lines)})

    teachers, staff = defaultdict(int), defaultdict(int)
    assignments = scope_branch(SalaryAssignment.objects.filter(year=month.year, month=month.month), user).select_related("user__role")
    for a in payroll.compute(assignments):
        (teachers if a.user.role and a.user.role.code in TEACHER_ROLES else staff)[a.user.full_name] += _num(a.total)
    teachers = sorted(((n, v) for n, v in teachers.items() if v), key=lambda x: -x[1])
    staff = sorted(((n, v) for n, v in staff.items() if v), key=lambda x: -x[1])

    taken_by = defaultdict(Decimal)
    for name, s in CreditorTransaction.objects.filter(date__gte=lo, date__lt=hi).values_list("creditor__name").annotate(s=Sum("amount")):
        taken_by[_norm(name)] += s or 0
    holders = []
    for label, key, pct in settings.PROFIT_SHARE_HOLDERS:
        # «−» qarz olish (olingan pul), «+» qaytarish: olingan = −Σ
        holders.append({"label": label, "pct": pct, "taken": -_num(sum(v for n, v in taken_by.items() if _norm(key) in n))})
    return {"month": month, "income": _num(income), "teachers": teachers, "staff": staff, "expenses": expenses, "holders": holders}


# ------------------------------------------------------------------ jadval tuzilishi

def layout(data, prev=None, partial=False, now=None, who=""):
    """data → {cells: {(r, c): qiymat}, notes: {(r, c): matn}, merges, fmts, list_end, total}; r/c 0-based.
    prev — oldingi oy varag'idan {tushum, pct: {qator: %}} (yo'q bo'lsa P ustuni bo'sh)."""
    cells, notes, merges, fmts = {}, {}, [], []
    n_rows = max(MIN_ROWS, len(data["teachers"]), len(data["staff"]), len(data["expenses"]))
    list_end = 4 + n_rows  # 1-based so'nggi ro'yxat qatori (namunada 17)
    t = list_end + 2  # «Jami:» qatori (namunada 19)

    def put(a, v):
        cells[a] = v

    def fmt(r1, c1, r2, c2, bg=None, bold=None, h=None, num=None, size=None, color=None, italic=None):
        fmts.append({"r1": r1, "c1": c1, "r2": r2, "c2": c2, "bg": bg, "bold": bold, "h": h, "num": num, "size": size, "color": color, "italic": italic})

    month = data["month"]
    cap = f"{UZ_MONTHS[month.month - 1].capitalize()} {month.year}"
    stamp = (now or timezone.localtime()).strftime("%d.%m.%Y")
    put((0, C), cap + (f" — hozirgacha ({stamp} holatiga, oy tugamagan)" if partial else ""))
    put((1, C), f"Yangilandi: {(now or timezone.localtime()):%d.%m.%Y %H:%M}" + (f" · {who}" if who else "") + " · tizimdan avtomatik (O16:O17 «avvalgi oydan» — qo'lda)")
    fmt(0, C, 0, C, bold=True, size=14)
    fmt(1, C, 1, C, italic=True, size=9, color="808080")

    # sarlavhalar (1-qator indekslari 0-based: 3-qator → 2)
    put((2, C), "Oyliklar")
    merges.append((2, C, 2, F))
    fmt(2, C, 2, F, bg=COLORS["oyliklar"], bold=True, h="CENTER")
    put((3, C), "Ustozlar")
    merges.append((3, C, 3, D))
    fmt(3, C, 3, D, bg=COLORS["ustozlar"], bold=True, h="CENTER")
    put((3, E), "Xodimlar")
    merges.append((3, E, 3, F))
    fmt(3, E, 3, F, bg=COLORS["xodimlar"], bold=True, h="CENTER")
    put((2, CX), "Xarajatlar")
    merges.append((2, CX, 2, J))
    fmt(2, CX, 2, J, bg=COLORS["xarajat"], bold=True, h="CENTER")

    # ro'yxatlar: oyliklar 5-qatordan (index 4), xarajatlar 4-qatordan (index 3)
    for i, (name, v) in enumerate(data["teachers"]):
        put((4 + i, C), _safe(name))
        put((4 + i, D), v)
    for i, (name, v) in enumerate(data["staff"]):
        put((4 + i, E), _safe(name))
        put((4 + i, F), v)
    for i, e in enumerate(data["expenses"]):
        put((3 + i, CX), _safe(e["name"]))
        put((3 + i, J), e["total"])
        if e["note"]:
            notes[(3 + i, J)] = e["note"]
    fmt(4, C, list_end - 1, D, bg=COLORS["t_row"])
    fmt(4, E, list_end - 1, F, bg=COLORS["s_row"])
    fmt(3, CX, list_end - 1, J, bg=COLORS["e_row"])

    # jami qatorlari
    tr = t - 1  # 0-based
    for c, label in ((C, "Jami:"), (E, "Jami:"), (CX, "Jami:")):
        put((tr, c), label)
    put((tr, D), f"=SUM(D5:D{list_end})")
    put((tr, F), f"=SUM(F5:F{list_end})")
    put((tr, J), f"=SUM(J4:J{list_end})")
    put((tr + 1, C), "Jami:")
    put((tr + 1, D), f"=D{t}+F{t}")
    merges.append((tr + 1, D, tr + 1, E))
    fmt(tr, C, tr + 1, F, bg=COLORS["total"], bold=True)
    fmt(tr, CX, tr, J, bg=COLORS["total"], bold=True)
    fmt(2, D, tr + 1, D, num="#,##0")
    fmt(2, F, tr + 1, F, num="#,##0")
    fmt(2, J, tr, J, num="#,##0")

    # o'ng blok
    prev = prev or {}
    pct = prev.get("pct", {})

    def pct_cells(row, formula_src):  # row — 1-based
        put((row - 1, CP), f'=IF($N$3=0,0,{formula_src}/$N$3*100)')
        put((row - 1, P), pct.get(row, ""))

    put((2, M), "Tushum:")
    put((2, N), data["income"])
    put((2, CP), "Tushumdan qismi %")
    put((2, P), prev.get("income", ""))
    put((3, P), "Avvalgi oyda" if prev else "")
    put((4, M), "Ustozlar oyliklari:")
    put((4, N), f"=D{t}")
    pct_cells(5, "N5")
    put((5, M), "Xodimlar oyliklari:")
    put((5, N), f"=F{t}")
    pct_cells(6, "N6")
    put((6, M), "Xarajatlar:")
    put((6, N), f"=J{t}")
    pct_cells(7, "N7")
    put((8, M), "Foyda:")
    put((8, N), "=N3-N5-N6-N7")
    pct_cells(9, "N9")
    fmt(2, M, 2, N, bg=COLORS["tushum"], bold=True)
    fmt(4, M, 6, N, bg=COLORS["tushum"])
    fmt(8, M, 8, N, bg=COLORS["tushum"], bold=True)
    fmt(2, P, 12, P, bg=COLORS["prev"], num="0.0")
    fmt(2, P, 2, P, num="#,##0")
    fmt(4, CP, 12, CP, num="0.0")
    fmt(8, CP, 8, CP, bg=COLORS["pct"])
    fmt(2, N, 8, N, num="#,##0")

    holders = data["holders"]
    k = len(holders)
    put((10, M), "Foyda taqsimoti")
    merges.append((10, M, 10, N))
    put((10, CP), "Tushumdan %")
    fmt(10, M, 10, N, bg=COLORS["share"], bold=True, h="CENTER")
    fmt(10, CP, 10, CP, bg=COLORS["pct"])
    for i, h in enumerate(holders):
        r = 12 + i  # 1-based
        put((r - 1, M), f"{h['label']}:")
        put((r - 1, N), f"=N9*{h['pct'] / 100:g}")
        pct_cells(r, f"N{r}")
    fmt(11, M, 10 + k, N, bg=COLORS["share"], num="#,##0")
    fmt(11, CP, 10 + k, CP, bg=COLORS["pct"], num="0.0")

    hdr = 12 + k + 1  # «Olingan pullar» sarlavhasi, 1-based (k=2 → 15)
    put((hdr - 1, M), "Olingan pullar")
    merges.append((hdr - 1, M, hdr - 1, N))
    put((hdr - 1, CP), "avvalgi oydan")
    put((hdr - 1, P), "Oy yakunida")
    fmt(hdr - 1, M, hdr - 1, N, bg=COLORS["taken"], bold=True, h="CENTER")
    for i, h in enumerate(holders):
        r = hdr + 1 + i  # 1-based
        put((r - 1, M), f"{h['label']}: ")
        put((r - 1, N), h["taken"])
        put((r - 1, P), f"=N{12 + i}-N{r}+O{r}")
    last = hdr + k
    fmt(hdr, M, last - 1, N, bg=COLORS["taken"], num="#,##0")
    fmt(hdr - 1, CP, last - 1, CP, bg=COLORS["pct"], num="#,##0")
    fmt(hdr - 1, P, last - 1, P, bg=COLORS["end"], num="#,##0")
    manual = {(r - 1, CP) for r in range(hdr + 1, last + 1)}  # qo'lda yoziladigan «avvalgi oydan» — tegmaymiz
    return {"cells": cells, "notes": notes, "merges": merges, "fmts": fmts, "list_end": list_end, "total": t, "manual": manual,
            "unmerge": (0, M, hdr + k + 1, P)}


# ------------------------------------------------------------------ Google so'rovlari

def _gr(sid, r1, c1, r2, c2):
    return {"sheetId": sid, "startRowIndex": r1, "endRowIndex": r2 + 1, "startColumnIndex": c1, "endColumnIndex": c2 + 1}


def _rgb(hexcolor):
    return {"red": int(hexcolor[0:2], 16) / 255, "green": int(hexcolor[2:4], 16) / 255, "blue": int(hexcolor[4:6], 16) / 255}


def requests_for(sid, plan):
    """batchUpdate so'rovlari: C:J tozalanadi (qiymat, format, izoh, birlashma), keyin format, birlashma, izohlar, ustun kengligi."""
    out = [
        {"unmergeCells": {"range": _gr(sid, 0, C, GRID_ROWS, J)}},
        {"unmergeCells": {"range": _gr(sid, *plan["unmerge"])}},
        {"updateCells": {"range": _gr(sid, 0, C, GRID_ROWS, J), "fields": "userEnteredValue,userEnteredFormat,note"}},
    ]
    for f in plan["fmts"]:
        cell, fields = {}, []
        fm = {}
        if f["bg"]:
            fm["backgroundColor"] = _rgb(f["bg"])
            fields.append("userEnteredFormat.backgroundColor")
        if f["h"]:
            fm["horizontalAlignment"] = f["h"]
            fields.append("userEnteredFormat.horizontalAlignment")
        if f["num"]:
            fm["numberFormat"] = {"type": "NUMBER", "pattern": f["num"]}
            fields.append("userEnteredFormat.numberFormat")
        tf = {}
        if f["bold"] is not None:
            tf["bold"] = f["bold"]
            fields.append("userEnteredFormat.textFormat.bold")
        if f["size"]:
            tf["fontSize"] = f["size"]
            fields.append("userEnteredFormat.textFormat.fontSize")
        if f["italic"]:
            tf["italic"] = True
            fields.append("userEnteredFormat.textFormat.italic")
        if f["color"]:
            tf["foregroundColor"] = _rgb(f["color"])
            fields.append("userEnteredFormat.textFormat.foregroundColor")
        if tf:
            fm["textFormat"] = tf
        cell["userEnteredFormat"] = fm
        out.append({"repeatCell": {"range": _gr(sid, f["r1"], f["c1"], f["r2"], f["c2"]), "cell": cell, "fields": ",".join(fields)}})
    out += [{"mergeCells": {"range": _gr(sid, *m), "mergeType": "MERGE_ALL"}} for m in plan["merges"]]
    for (r, c), text in plan["notes"].items():
        out.append({"updateCells": {"range": _gr(sid, r, c, r, c), "rows": [{"values": [{"note": text}]}], "fields": "note"}})
    widths = {C: 150, D: 110, E: 190, F: 110, 6: 24, 7: 24, CX: 200, J: 110, 10: 24, 11: 24, M: 190, N: 120, CP: 140, P: 120}
    for c, px in widths.items():
        out.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c, "endIndex": c + 1},
                                                  "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    return out


def _value_data(title, plan):
    q = "'" + title.replace("'", "''") + "'"
    return [{"range": f"{q}!{_a1(r, c)}", "values": [[v]]} for (r, c), v in plan["cells"].items() if (r, c) not in plan["manual"]]


# ------------------------------------------------------------------ oldingi oy

def read_prev(title, existing):
    """Oldingi oy varag'idan (shu generator yaratgan) tushum va foizlar → «Avvalgi oyda» ustuni. Varaq bo'lmasa — bo'sh."""
    if title.lower() not in {s["title"].lower() for s in existing}:
        return {}
    name = next(s["title"] for s in existing if s["title"].lower() == title.lower())
    q = "'" + name.replace("'", "''") + "'"
    inc, pcts = gs.values_get([f"{q}!N3", f"{q}!O3:O13"])
    num = lambda v: v if isinstance(v, (int, float)) else ""  # noqa: E731
    income = num(inc[0][0]) if inc and inc[0] else ""
    col = [row[0] if row else "" for row in pcts]
    col += [""] * (11 - len(col))
    return {"income": income, "pct": {r: num(col[r - 3]) for r in (5, 6, 7, 9, 12, 13)}}


# ------------------------------------------------------------------ asosiy

DEFAULT_SHEET_NAMES = {"sheet1", "sheet 1", "лист1", "лист 1", "varaq1", "varaq 1"}


def _drop_default_tab(sheets):
    """Yangi (bo'sh) faylning avtomatik «Sheet1» varag'i: faqat bo'sh bo'lsa va boshqa varaq bor bo'lsa o'chiriladi."""
    if len(sheets) < 2:
        return
    for s in sheets:
        if s["sheetId"] == 0 and s["title"].strip().lower() in DEFAULT_SHEET_NAMES:
            q = "'" + s["title"].replace("'", "''") + "'"
            if not any(row for row in gs.values_get([f"{q}!A1:Z100"])[0]):
                gs.batch_update([{"deleteSheet": {"sheetId": 0}}])
            return


def generate(user, month, today=None):
    """Hisobotni yaratadi/yangilaydi. → {url, title, created, partial}."""
    today = today or timezone.localdate()
    if month > today.replace(day=1):
        raise ValidationError({"month": "Kelajak oy uchun hisobot yo'q"})
    if not gs.configured():
        raise gs.SheetsError("Google Sheets ulanmagan: administrator serverda `bash deploy/set-google.sh` ni ishga tushirishi kerak")
    title = tab_title(month)
    partial = (month.year, month.month) == (today.year, today.month)
    data = collect(user, month)

    meta = gs.tabs()
    sheets = meta["sheets"]
    found = next((s for s in sheets if s["title"].lower() == title.lower()), None)
    created = found is None
    prev_month = (month - datetime.timedelta(days=1)).replace(day=1)
    prev = read_prev(tab_title(prev_month), sheets)
    plan = layout(data, prev, partial=partial, who=user.full_name)
    if created:
        r = gs.batch_update([{"addSheet": {"properties": {"title": title, "gridProperties": {"rowCount": max(100, plan["total"] + 20), "columnCount": 20}}}}])
        found = r["replies"][0]["addSheet"]["properties"]
    sid = found["sheetId"]
    gs.batch_update(requests_for(sid, plan))
    gs.values_update(_value_data(found["title"], plan))
    if created:
        _drop_default_tab([*sheets, found])
    return {"url": gs.sheet_url(sid), "title": found["title"], "created": created, "partial": partial}

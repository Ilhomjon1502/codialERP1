"""AI yordamchi sifati uchun: bazaning holati (LLM'ga) va bo'sh natijaning sababi (Bosh menejerga).

`data_context()` — LLM'ga boradi: yozuvlar soni va sanalar oralig'i, ma'lumotnoma nomlari (kurslar, guruhlar, ustozlar, lid manbalari,
g'aznalar, xarajat kategoriyalari). Talaba/ota-ona ma'lumoti (ism, telefon, qarz) bormaydi — buyurtmachi qarori 2026-10-16
(`docs/decisions.md`): «flutter14» → 'Flutter / #14' kabi nomlarni to'g'ri topishi va bo'sh jadvalni bilishi uchun.

`diagnose(sql)` — natija bo'sh bo'lsa: qaysi view'da yozuv yo'q yoki WHERE dagi qaysi shartga hech narsa mos kelmadi.
So'rovlar `guard.execute` orqali (faqat o'qish, codial_ai roli). Natija faqat ekranda; qayta so'rashda LLM'ga faqat shart va
shu ustunning shaxsiy bo'lmagan qiymatlari boradi."""

import sqlglot
from django.db import connection
from django.utils import timezone
from sqlglot import exp

from apps.references.models import ExpenseCategory, LeadSource, LessonFrequency

from . import guard
from .analytics import PII_COLUMNS, VIEW_NAMES

LABELS = {
    "analytics_payments": "To'lovlar", "analytics_contracts": "Shartnomalar", "analytics_attendance": "Davomat",
    "analytics_lessons": "Dars jadvali", "analytics_leads": "Lidlar", "analytics_groups": "Guruhlar", "analytics_expenses": "Xarajatlar",
    "analytics_salaries": "Oylik belgilash", "analytics_salary_payouts": "Oylik berish", "analytics_accounts": "G'aznalar",
    "analytics_cash_movements": "G'azna harakatlari", "analytics_evaluations": "Ustozni baholash", "analytics_creditors": "Kreditorlar",
    "analytics_course_prices": "Kurs narxlari", "analytics_staff": "Xodimlar", "analytics_calls": "Qo'ng'iroqlar",
}
EMPTY_HINTS = {
    "analytics_payments": "Tizimga hali to'lov kiritilmagan.",
    "analytics_leads": "Tizimda hali lid yo'q: AppSheet'dan faqat faol shartnomalar ko'chirilgan, yangi lidlar shu tizimda kiritiladi.",
    "analytics_course_prices": "Kurs narxlari kiritilmagan (Sozlamalar → Kurs narxlari).",
}
MONEY_COLS = {"debt", "charged", "student_debt", "paid", "teacher_kpi", "supporter_kpi"}
MAX_VALUES = 40


def _rows(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchall()


def _d(v):
    return str(v)[:10] if v else "—"


def facts():
    """Yozuvlar soni (shaxsiy ma'lumotsiz)."""
    count = {v: _rows(f"SELECT COUNT(*) FROM {v}")[0][0] for v in VIEW_NAMES if v not in ("analytics_lessons",)}
    today = timezone.localdate()
    count["freq_ok"] = LessonFrequency.objects.filter(year=today.year, month=today.month, status=LessonFrequency.FreqStatus.APPROVED).exists()
    return count


def data_context():
    """LLM uchun «MA'LUMOTLAR HOLATI» bloki."""
    n = facts()
    (pay_n, pay_from, pay_to), = _rows("SELECT COUNT(*), MIN(date), MAX(date) FROM analytics_payments")
    (att_n, att_from, att_to), = _rows("SELECT COUNT(*), MIN(date), MAX(date) FROM analytics_attendance")
    (active,), = _rows("SELECT COUNT(*) FROM analytics_contracts WHERE status = 'Faol'")
    (debtors,), = _rows("SELECT COUNT(*) FROM analytics_contracts WHERE debt > 0")
    lines = [
        f"- Shartnomalar: {n['analytics_contracts']} ta (faol {active}, qarzdor (debt > 0) {debtors}).",
        f"- To'lovlar: {pay_n} ta" + (f" ({_d(pay_from)} … {_d(pay_to)})." if pay_n else " — hali kiritilmagan."),
        f"- Davomat qatorlari: {att_n} ta" + (f" ({_d(att_from)} … {_d(att_to)})." if att_n else " — hali olinmagan."),
        f"- Lidlar: {n['analytics_leads']} ta; xarajatlar: {n['analytics_expenses']} ta; oylik belgilash: {n['analytics_salaries']} ta; "
        f"baholashlar: {n['analytics_evaluations']} ta.",
        f"- Kurs narxlari: {n['analytics_course_prices'] or 'kiritilmagan — qarz (debt, charged, student_debt) hamma joyda 0'}; "
        f"shu oy dars soni: {'tasdiqlangan' if n['freq_ok'] else 'tasdiqlanmagan — shu oy qarz va KPI hisoblanmaydi'}.",
    ]
    groups = _rows("SELECT group_name, teacher_name, day_pattern, lesson_time, status, active_contracts FROM analytics_groups "
                   "WHERE status <> 'Nofaol' ORDER BY course, group_name")
    if groups:
        lines.append("- Guruhlar (group_name aynan shunday yoziladi):\n" + "\n".join(
            f"  {g} — ustoz {t or '—'}, {dp or '—'} {lt or ''}, {st}, {k} talaba" for g, t, dp, lt, st, k in groups[:120]))
    courses = [c for (c,) in _rows("SELECT DISTINCT course FROM analytics_groups ORDER BY course")]
    if courses:
        lines.append(f"- Kurslar: {', '.join(courses)}.")
    staff = _rows("SELECT user_name, role FROM analytics_staff WHERE employment_status = 'Faol' ORDER BY role, user_name")
    if staff:
        lines.append("- Xodimlar: " + "; ".join(f"{u} ({r or '—'})" for u, r in staff[:80]) + ".")
    sources = list(LeadSource.objects.order_by("name").values_list("name", flat=True))
    if sources:
        lines.append(f"- Lid manbalari: {', '.join(sources)}.")
    accounts = [a for (a,) in _rows("SELECT account FROM analytics_accounts ORDER BY account")]
    if accounts:
        lines.append(f"- G'aznalar: {', '.join(accounts)}.")
    cats = list(ExpenseCategory.objects.order_by("name").values_list("name", flat=True))
    if cats:
        lines.append(f"- Xarajat kategoriyalari: {', '.join(cats)}.")
    return "\n".join(lines)


# ------------------------------------------------------------------ bo'sh natija

def _conditions(tree, ctes):
    """[(jadval, shart)] — bitta view'dan (JOIN'siz) o'qiydigan SELECT'larning WHERE dagi AND qismlari."""
    out = []
    for sel in tree.find_all(exp.Select):
        frm, where = sel.args.get("from"), sel.args.get("where")
        if not frm or not where or sel.args.get("joins") or not isinstance(frm.this, exp.Table):
            continue
        t = frm.this
        if t.name.lower() in ctes or t.name.lower() not in VIEW_NAMES:
            continue
        parts = list(where.this.flatten()) if isinstance(where.this, exp.And) else [where.this]
        out += [(t, p) for p in parts if not p.find(exp.Select)]
    return out[:8]


def _text_column(cond):
    """`ustun = 'matn'` yoki `ustun LIKE '%matn%'` bo'lsa — ustun nomi (shaxsiy bo'lmagan)."""
    if isinstance(cond, (exp.EQ, exp.Like, exp.ILike)) and isinstance(cond.left, exp.Column) and isinstance(cond.right, exp.Literal) \
            and cond.right.is_string and cond.left.name.lower() not in PII_COLUMNS:
        return cond.left.name
    return None


def diagnose(sql):
    """Bo'sh natija sababi: {"lines": [ekran uchun izohlar], "retry": "LLM'ga qayta so'rash matni" yoki ""}."""
    out = {"lines": [], "retry": ""}
    try:
        d = guard.dialect()
        tree = sqlglot.parse_one(sql, read=d)
        ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
        views = sorted({t.name.lower() for t in tree.find_all(exp.Table)} - ctes)
        cols = {c.name.lower() for c in tree.find_all(exp.Column)}
        n = facts()
        empty = [v for v in views if v in n and n[v] == 0]
        for v in empty:
            out["lines"].append(EMPTY_HINTS.get(v) or f"«{LABELS.get(v, v)}» bo'yicha tizimda hali yozuv yo'q.")
        if cols & MONEY_COLS and set(views) & {"analytics_contracts", "analytics_attendance"}:
            if not n["analytics_course_prices"]:
                out["lines"].append("Kurs narxlari kiritilmagan — darslar uchun summa yozilmaydi, shuning uchun hamma talabaning qarzi 0. "
                                    "Sozlamalar → Kurs narxlari'da narx kiriting (qarz davomatdan avtomatik qayta hisoblanadi).")
            elif not n["freq_ok"]:
                out["lines"].append("Shu oy uchun oydagi dars soni tasdiqlanmagan — qarz va KPI hisoblanmaydi (Tasdiqlashlar → Oydagi dars soni).")
        if empty:
            return out
        retry = []
        for t, cond in _conditions(tree, ctes):
            total = n.get(t.name.lower())
            (k,), = guard.execute(f"SELECT COUNT(*) AS n FROM {t.sql(dialect=d)} WHERE {cond.sql(dialect=d)}")["rows"]
            if k:
                continue
            out["lines"].append(f"«{cond.sql(dialect=d)}» shartiga mos yozuv yo'q ({LABELS.get(t.name.lower(), t.name)}: jami {total} ta).")
            col = _text_column(cond)
            if col:
                vals = [r[0] for r in guard.execute(f"SELECT DISTINCT {col} FROM {t.name} WHERE {col} IS NOT NULL ORDER BY 1")["rows"][:MAX_VALUES]]
                if vals:
                    retry.append(f"«{cond.sql(dialect=d)}» shartiga hech narsa mos kelmadi. {col} ustunidagi mavjud qiymatlar: "
                                 + ", ".join(f"'{v}'" for v in vals))
        if not out["lines"]:
            out["lines"].append("Shartlarning har biriga mos yozuvlar bor, lekin hammasiga birdaniga mos keladigan yozuv yo'q.")
        out["retry"] = "\n".join(retry)
    except Exception:  # noqa: BLE001 — izoh yordamchi narsa, asosiy javobni buzmasin
        pass
    return out

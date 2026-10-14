"""AI yordamchi oqimi (CLAUDE.md 13, buyurtmachi tasdiqlagan variant 2026-10-13):

savol + view'lar sxemasi → LLM → SQL → server tekshiradi va bajaradi → natija faqat Bosh menejer ekranida.
LLM'ga natija qatorlari yuborilmaydi. «Tahlil» qadamida: shaxsiy ma'lumot ustunlari ishlatilmagan bo'lsa — natija jadvali
(ko'pi bilan 40 qator), aks holda faqat yig'ma raqamlar (qatorlar soni, sonli ustunlar yig'indisi/o'rtachasi)."""

import json
import time

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from . import analytics, guard, providers
from .models import AIQuery

CHART_TYPES = {"bar", "line", "pie", "doughnut", "none"}

EXAMPLES = [
    ("Shu oyda qaysi kurs eng ko'p to'lov keltirdi?",
     "SELECT course, SUM(amount) AS tolovlar, COUNT(*) AS soni FROM analytics_payments WHERE ym = '{ym}' GROUP BY course ORDER BY tolovlar DESC",
     {"type": "bar", "x": "course", "y": ["tolovlar"]}),
    ("Manbalar bo'yicha lid konversiyasi",
     "SELECT source, COUNT(*) AS lidlar, SUM(has_contract) AS shartnoma, ROUND(100.0 * SUM(has_contract) / COUNT(*), 1) AS konversiya_foiz "
     "FROM analytics_leads GROUP BY source ORDER BY lidlar DESC",
     {"type": "bar", "x": "source", "y": ["lidlar", "shartnoma"]}),
    ("Qaysi guruhda qarzdorlik eng ko'p?",
     "SELECT group_name, COUNT(*) AS qarzdorlar, SUM(debt) AS jami_qarz FROM analytics_contracts WHERE status = 'Faol' AND debt > 0 GROUP BY group_name ORDER BY jami_qarz DESC",
     {"type": "bar", "x": "group_name", "y": ["jami_qarz"]}),
    ("Eng ko'p qarzi bor 10 ta talaba va telefonlari",
     "SELECT student_name, group_name, phone1, parent_phone, debt FROM analytics_contracts WHERE status = 'Faol' AND debt > 0 ORDER BY debt DESC LIMIT 10",
     {"type": "none"}),
    ("Oxirgi 6 oyda foyda oyma-oy",
     "WITH p AS (SELECT ym, SUM(amount) AS s FROM analytics_payments GROUP BY ym), "
     "e AS (SELECT period_ym AS ym, SUM(total) AS s FROM analytics_expenses WHERE kind = 'Xarajat' GROUP BY period_ym), "
     "o AS (SELECT ym, SUM(total) AS s FROM analytics_salaries GROUP BY ym) "
     "SELECT p.ym, p.s AS tolovlar, COALESCE(e.s, 0) AS xarajatlar, COALESCE(o.s, 0) AS oyliklar, p.s - COALESCE(e.s, 0) - COALESCE(o.s, 0) AS foyda "
     "FROM p LEFT JOIN e ON e.ym = p.ym LEFT JOIN o ON o.ym = p.ym WHERE p.ym >= '{ym6}' ORDER BY p.ym",
     {"type": "line", "x": "ym", "y": ["tolovlar", "xarajatlar", "foyda"]}),
    ("Ustozlar bo'yicha shu oy davomat foizi",
     "SELECT teacher_name, COUNT(*) AS qatorlar, ROUND(100.0 * SUM(CASE WHEN status = '1' THEN 1 ELSE 0 END) / COUNT(*), 1) AS davomat_foiz "
     "FROM analytics_attendance WHERE ym = '{ym}' AND status <> '-' GROUP BY teacher_name ORDER BY davomat_foiz DESC",
     {"type": "bar", "x": "teacher_name", "y": ["davomat_foiz"]}),
]


def _months_back(d, n):
    y, m = d.year, d.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return f"{y}-{m:02d}"


def examples():
    today = timezone.localdate()
    ym, ym6 = f"{today:%Y-%m}", _months_back(today, 5)
    return [(q, sql.format(ym=ym, ym6=ym6), chart) for q, sql, chart in EXAMPLES]


def system_prompt():
    today = timezone.localdate()
    dialect = "PostgreSQL 16" if guard.dialect() == "postgres" else "SQLite"
    ex = "\n\n".join(f"Savol: {q}\nJavob: {json.dumps({'sql': sql, 'title': q, 'chart': chart, 'note': ''}, ensure_ascii=False)}" for q, sql, chart in examples())
    return f"""Siz Codial IT o'quv markazi (Farg'ona) ERP tizimining ma'lumotlar tahlilchisisiz. Bosh menejer o'zbek tilida savol beradi.
Vazifangiz — savolga javob beradigan BITTA SQL SELECT so'rovini yozish. So'rovni server bajaradi va natijani menejerga o'zi ko'rsatadi; siz ma'lumotni ko'rmaysiz.

Bugun: {today:%Y-%m-%d} (joriy oy '{today:%Y-%m}'). Dialekt: {dialect}. Pul — so'mda, butun son.

Qoidalar:
- Faqat quyidagi view'lardan o'qing. Boshqa jadval, sxema yoki tizim funksiyasi ishlatilmaydi. Faqat SELECT (WITH ruxsat).
- Oy bo'yicha filtr va guruhlash uchun ym ('YYYY-MM'), year, month ustunlarini ishlating; sanaga funksiya kerak bo'lmasin.
- "Shu oy" — '{today:%Y-%m}', "o'tgan oy" — '{_months_back(today, 1)}'. Yil aytilmasa — joriy yil.
- Ustun nomlarini tushunarli o'zbekcha snake_case aliaslar bilan bering (tolovlar, soni, foiz ...). ORDER BY qo'ying. Ro'yxat so'ralsa LIMIT 100 dan oshmasin.
- Foiz hisoblashda 100.0 ga ko'paytiring (butun bo'linish bo'lmasin) va ROUND(..., 1).
- Faol talabalar/shartnomalar: analytics_contracts.status = 'Faol'. Qarzdor: debt > 0.
- Foyda = to'lovlar (analytics_payments.amount) − xarajatlar (analytics_expenses, kind = 'Xarajat', period_ym bo'yicha) − hisoblangan oyliklar (analytics_salaries.total).
- Savol tushunarsiz yoki ma'lumotlarda javob yo'q bo'lsa sql bo'sh bo'lsin va note da sababini o'zbekcha yozing.

Javobni faqat JSON ko'rinishida qaytaring:
{{"sql": "...", "title": "natija sarlavhasi (o'zbekcha, qisqa)", "chart": {{"type": "bar|line|pie|doughnut|none", "x": "ustun", "y": ["sonli ustun", ...]}}, "note": "ixtiyoriy qisqa izoh"}}
Diagramma: vaqt (oy) bo'yicha — line, toifalar bo'yicha taqqoslash — bar, ulushlar (≤ 8 toifa) — doughnut, ro'yxat yoki bitta raqam — none.

VIEW'LAR:
{analytics.schema_text()}

NAMUNALAR:
{ex}"""


def _history(user, limit=3):
    """Oldingi savollar va SQL (davomiy savollar uchun: «endi o'tgan oy uchun»). Natijalar yuborilmaydi."""
    qs = AIQuery.objects.filter(user=user, kind=AIQuery.Kind.ASK, status=AIQuery.Status.OK, created_at__date=timezone.localdate()).order_by("-created_at")[:limit]
    items = list(reversed(qs))
    if not items:
        return ""
    return "Oldingi savollar (kontekst uchun):\n" + "\n".join(f"- {q.question}\n  SQL: {q.sql}" for q in items) + "\n\n"


def used_today(user):
    return AIQuery.objects.filter(user=user, created_at__date=timezone.localdate()).exclude(llm_calls=0).count()


def check_limit(user):
    if used_today(user) >= settings.AI_DAILY_LIMIT:
        raise Throttled(detail=f"Bugungi limit tugadi ({settings.AI_DAILY_LIMIT} ta so'rov). Ertaga yana foydalanish mumkin")


def _chart(raw, columns):
    if not isinstance(raw, dict) or raw.get("type") not in CHART_TYPES or raw.get("type") == "none":
        return {"type": "none"}
    x = raw.get("x")
    ys = [y for y in (raw.get("y") or []) if y in columns and y != x]
    if x not in columns or not ys:
        return {"type": "none"}
    return {"type": raw["type"], "x": x, "y": ys[:4]}


def _result(q, data):
    return {
        "id": q.id, "question": q.question, "sql": q.sql, "title": q.title, "note": q.note, "status": q.status, "error": q.error,
        "chart": q.chart or {"type": "none"}, "uses_pii": q.uses_pii, "created_at": q.created_at,
        "columns": data["columns"] if data else [], "rows": data["rows"] if data else [], "truncated": bool(data and data["truncated"]),
        "row_count": q.row_count, "ms": {"llm": q.llm_ms, "db": q.db_ms},
    }


def ask(user, question):
    question = (question or "").strip()
    if not question:
        raise ValidationError({"question": "Savol yozing"})
    if len(question) > 1000:
        raise ValidationError({"question": "Savol juda uzun (1000 belgigacha)"})
    check_limit(user)
    q = AIQuery(user=user, question=question, provider=settings.AI_PROVIDER, model=providers.model_name())
    system, prompt = system_prompt(), f"{_history(user)}Savol: {question}"
    data, t0 = None, time.monotonic()
    try:
        for attempt in range(2):  # xato bo'lsa — xato matni bilan bir marta qayta so'raladi
            q.llm_calls += 1
            out = providers.complete_json(system, prompt)
            q.sql, q.title, q.note = (out.get("sql") or "").strip(), str(out.get("title") or "")[:200], str(out.get("note") or "")[:2000]
            if not q.sql:
                q.status = AIQuery.Status.NO_SQL
                break
            try:
                sql, q.uses_pii = guard.validate(q.sql)
                q.sql = sql
                data = guard.execute(sql)
                q.status, q.error = AIQuery.Status.OK, ""
                break
            except guard.Blocked as e:
                q.status, q.error = (AIQuery.Status.ERROR if str(e).startswith("Bajarishda") else AIQuery.Status.BLOCKED), str(e)[:400]
                if attempt == 0 and time.monotonic() - t0 < 15:  # qayta so'rashga vaqt bo'lsa (sahifa 60 s dan oshmasin)
                    prompt = f"{prompt}\n\nSizning SQL'ingiz:\n{q.sql}\nXato: {e}\nTuzatilgan SQL'ni xuddi shu JSON ko'rinishida qaytaring."
    except providers.ProviderError as e:
        q.status, q.error = AIQuery.Status.ERROR, str(e)[:400]
    q.model = providers.used_model()
    q.llm_ms = int((time.monotonic() - t0) * 1000) - (data["ms"] if data else 0)
    if data:
        q.db_ms, q.row_count, q.truncated = data["ms"], len(data["rows"]), data["truncated"]
        q.chart = _chart(out.get("chart"), data["columns"])
    q.save()
    return _result(q, data)


def rerun(user, q):
    """Saqlangan SQL'ni LLM'siz qayta bajarish (limitga kirmaydi)."""
    if not q.sql or q.status != AIQuery.Status.OK:
        raise ValidationError({"detail": "Bu savolda bajariladigan SQL yo'q"})
    sql, _ = guard.validate(q.sql)
    try:
        data = guard.execute(sql)
    except guard.Blocked as e:
        raise ValidationError({"detail": str(e)}) from None
    return _result(q, data)


def summary_for_llm(columns, rows, uses_pii):
    """LLM'ga boradigan narsa. Shaxsiy ma'lumot ustunlari ishlatilgan bo'lsa — faqat yig'ma raqamlar."""
    if not uses_pii:
        lines = [" | ".join(columns)] + [" | ".join("" if v is None else str(v) for v in r) for r in rows[:40]]
        more = f"\n(jami {len(rows)} qator, birinchi 40 tasi ko'rsatildi)" if len(rows) > 40 else ""
        return "Natija jadvali:\n" + "\n".join(lines) + more
    out = [f"Natijada {len(rows)} qator bor. Shaxsiy ma'lumot himoyasi uchun faqat yig'ma raqamlar:"]
    for i, c in enumerate(columns):
        nums = [r[i] for r in rows if isinstance(r[i], (int, float)) and not isinstance(r[i], bool)]
        if nums and len(nums) >= len(rows) / 2 and c not in analytics.PII_COLUMNS:
            out.append(f"- {c}: yig'indi {sum(nums):g}, o'rtacha {sum(nums) / len(nums):.1f}, eng kichik {min(nums):g}, eng katta {max(nums):g}")
    return "\n".join(out)


def analyze(user, q):
    check_limit(user)
    if q.status != AIQuery.Status.OK:
        raise ValidationError({"detail": "Avval savolga natija olinsin"})
    sql, uses_pii = guard.validate(q.sql)
    try:
        data = guard.execute(sql)
    except guard.Blocked as e:
        raise ValidationError({"detail": str(e)}) from None
    system = ("Siz Codial o'quv markazi Bosh menejeriga yordam beradigan tahlilchisiz. Berilgan natija asosida o'zbek tilida 3–6 gapdan iborat qisqa, "
              "aniq tahlil yozing: asosiy xulosa, e'tiborga loyiq farqlar, amaliy tavsiya. Raqamlarni o'ylab topmang. "
              'Javob JSON: {"analysis": "..."}')
    prompt = f"Savol: {q.question}\nSQL: {sql}\n\n{summary_for_llm(data['columns'], data['rows'], uses_pii)}"
    a = AIQuery(user=user, kind=AIQuery.Kind.ANALYZE, parent=q, question=q.question, sql=sql, uses_pii=uses_pii,
                provider=settings.AI_PROVIDER, model=providers.model_name(), row_count=len(data["rows"]), db_ms=data["ms"], llm_calls=1)
    t0 = time.monotonic()
    try:
        a.note = str(providers.complete_json(system, prompt).get("analysis") or "")[:4000]
    except providers.ProviderError as e:
        a.status, a.error = AIQuery.Status.ERROR, str(e)[:400]
    a.model = providers.used_model()
    a.llm_ms = int((time.monotonic() - t0) * 1000)
    a.save()
    if a.status != AIQuery.Status.OK:
        raise ValidationError({"detail": a.error})
    return {"id": a.id, "analysis": a.note, "aggregated_only": uses_pii}


def history(user, limit=30):
    qs = AIQuery.objects.filter(user=user, kind=AIQuery.Kind.ASK).order_by("-created_at")[:limit]
    return [{"id": q.id, "question": q.question, "title": q.title, "status": q.status, "row_count": q.row_count, "created_at": q.created_at} for q in qs]

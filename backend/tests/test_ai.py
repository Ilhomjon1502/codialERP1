"""M9: AI yordamchi — analytics view'lar, SQL tekshiruvi, xavfsiz bajarish, LLM'ga shaxsiy ma'lumot ketmasligi, limit va ruxsatlar."""

import pytest
from django.db import connection

from apps.ai_assistant import analytics, guard, providers, services
from apps.ai_assistant.models import AIQuery
from apps.education.models import Contract
from apps.education.services import with_balance
from tests.test_finance import fin, pay  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db


@pytest.fixture
def llm(monkeypatch, settings):
    """Soxta LLM: navbatdagi javoblarni qaytaradi va unga nima yuborilganini yozib boradi."""
    settings.AI_API_KEY = "test-key"
    sent, answers = [], []

    def fake(system, user, strong=False):
        sent.append((system, user))
        return answers.pop(0)

    monkeypatch.setattr(providers, "complete_json", fake)
    return {"sent": sent, "answers": answers}


def _rows(sql):
    with connection.cursor() as c:
        c.execute(sql)
        return c.fetchall()


def test_views_have_declared_columns_and_match_services(api, fin):  # noqa: F811
    pay(api(fin["cashier"]), fin, amount=250_000)
    for name, _, cols, _ in analytics.views():
        with connection.cursor() as c:
            c.execute(f"SELECT * FROM {name} LIMIT 1")
            assert [d[0] for d in c.description] == [x[0] for x in cols], name  # LLM'ga berilgan sxema haqiqiy ustunlarga mos
    c = with_balance(Contract.objects.filter(pk=fin["contract"].pk)).get()
    (debt, paid, status, name), = _rows("SELECT debt, paid, status, student_name FROM analytics_contracts")
    assert debt == c.balance == 350_000 and paid == 250_000 and status == "Faol" and name == "Ali Valiyev"
    assert _rows("SELECT SUM(amount), COUNT(*) FROM analytics_payments")[0] == (250_000, 1)
    assert _rows("SELECT active_contracts, fill_pct FROM analytics_groups")[0] == (1, 10.0)
    assert "phone" not in {c for c, _, _ in dict((v[0], v) for v in analytics.views())["analytics_staff"][2]}


@pytest.mark.parametrize("sql", [
    "DELETE FROM analytics_payments",
    "UPDATE analytics_payments SET amount = 0",
    "SELECT * FROM accounts_user",
    "SELECT * FROM crm_student",
    "SELECT 1; DROP TABLE crm_student",
    "SELECT * FROM main.analytics_payments",
    "SELECT * FROM sqlite_master",
    "WITH x AS (SELECT * FROM finance_payment) SELECT * FROM x",
    "SELECT pg_sleep(30) FROM analytics_staff",
    "SELECT 1",
    "",
])
def test_guard_blocks(sql):
    with pytest.raises(guard.Blocked):
        guard.validate(sql)


def test_guard_allows_and_detects_pii():
    assert guard.validate("WITH p AS (SELECT ym, SUM(amount) s FROM analytics_payments GROUP BY ym) SELECT * FROM p ORDER BY ym;")[0].endswith("ym")
    assert guard.validate("SELECT course, COUNT(*) FROM analytics_contracts GROUP BY course")[1] is False
    assert guard.validate("SELECT student_name AS ism, debt FROM analytics_contracts")[1] is True  # alias bilan yashirsa ham
    assert guard.validate("SELECT * FROM analytics_contracts")[1] is True
    assert guard.validate("SELECT * FROM analytics_groups")[1] is False  # guruhlarda shaxsiy ma'lumot yo'q
    assert guard.validate("WITH p AS (SELECT course, COUNT(*) n FROM analytics_contracts GROUP BY course) SELECT * FROM p")[1] is False


def test_execute_limit_and_read_only(settings, fin):  # noqa: F811
    settings.AI_MAX_ROWS = 2
    r = guard.execute("SELECT user_name FROM analytics_staff")
    assert len(r["rows"]) == 2 and r["truncated"] is True
    with pytest.raises(guard.Blocked):
        guard.execute("SELECT * FROM analytics_staff WHERE 1 = (SELECT 1 FROM nonexistent)")
    with connection.cursor() as c:  # bazaning o'zi yozish rejimiga qaytgan
        c.execute("PRAGMA query_only")
        assert c.fetchone()[0] == 0


def test_ask_flow_logs_and_never_sends_rows(api, fin, llm):  # noqa: F811
    pay(api(fin["cashier"]), fin, amount=400_000)
    llm["answers"].append({"sql": "SELECT course, SUM(amount) AS tolovlar FROM analytics_payments GROUP BY course",
                           "title": "Kurslar bo'yicha", "chart": {"type": "bar", "x": "course", "y": ["tolovlar", "yoq"]}})
    r = api(fin["boss"]).post("/api/v1/ai/ask/", {"question": "Kurslar bo'yicha to'lovlar"}, format="json")
    assert r.status_code == 200, r.content
    d = r.json()
    assert d["status"] == "ok" and d["columns"] == ["course", "tolovlar"] and d["rows"] == [["Frontend", 400000]]
    assert d["chart"] == {"type": "bar", "x": "course", "y": ["tolovlar"]}  # mavjud bo'lmagan ustun tashlab yuborildi
    system, user = llm["sent"][0]
    assert "analytics_contracts" in system and "debt" in system  # sxema boradi
    assert "Ali Valiyev" not in system + user and "901112233" not in system + user  # ma'lumot bormaydi
    q = AIQuery.objects.get()
    assert q.row_count == 1 and q.sql.startswith("SELECT course") and q.llm_calls == 1 and q.user == fin["boss"]


def test_ask_retries_with_error(api, fin, llm):  # noqa: F811
    llm["answers"] += [{"sql": "SELECT * FROM crm_student"}, {"sql": "SELECT COUNT(*) AS soni FROM analytics_contracts"}]
    d = api(fin["boss"]).post("/api/v1/ai/ask/", {"question": "Nechta talaba bor?"}, format="json").json()
    assert d["status"] == "ok" and d["rows"] == [[1]]
    assert "Ruxsat etilmagan jadval" in llm["sent"][1][1]
    assert AIQuery.objects.get().llm_calls == 2


def test_ask_no_sql_and_not_configured(api, fin, llm, settings):  # noqa: F811
    llm["answers"].append({"sql": "", "note": "Bunday ma'lumot yo'q"})
    d = api(fin["boss"]).post("/api/v1/ai/ask/", {"question": "Ob-havo qanday?"}, format="json").json()
    assert d["status"] == "no_sql" and d["note"] == "Bunday ma'lumot yo'q"
    settings.AI_API_KEY = ""
    assert providers.configured() is False
    with pytest.raises(providers.ProviderError, match="set-ai.sh"):
        providers.complete("s", "u")


def test_analyze_sends_only_aggregates_for_pii(api, fin, llm):  # noqa: F811
    bm = api(fin["boss"])
    llm["answers"].append({"sql": "SELECT student_name, phone1, debt FROM analytics_contracts"})
    q = bm.post("/api/v1/ai/ask/", {"question": "Qarzdorlar"}, format="json").json()
    assert q["uses_pii"] is True and q["rows"] == [["Ali Valiyev", "901112233", 600000]]  # BM ekranida hammasi ko'rinadi
    llm["answers"].append({"analysis": "Bitta qarzdor bor."})
    r = bm.post(f"/api/v1/ai/{q['id']}/analyze/", format="json")
    assert r.status_code == 200 and r.json() == {"id": r.json()["id"], "analysis": "Bitta qarzdor bor.", "aggregated_only": True}
    sent = llm["sent"][-1][1]
    assert "Ali Valiyev" not in sent and "901112233" not in sent and "debt: yig'indi 600000" in sent

    llm["answers"].append({"sql": "SELECT course, SUM(debt) AS qarz FROM analytics_contracts GROUP BY course"})
    q2 = bm.post("/api/v1/ai/ask/", {"question": "Kurslar bo'yicha qarz"}, format="json").json()
    llm["answers"].append({"analysis": "ok"})
    assert bm.post(f"/api/v1/ai/{q2['id']}/analyze/", format="json").json()["aggregated_only"] is False
    assert "Frontend | 600000" in llm["sent"][-1][1]  # shaxsiy ma'lumotsiz natija jadval sifatida boradi


def test_rerun_without_llm_and_history(api, fin, llm):  # noqa: F811
    bm = api(fin["boss"])
    llm["answers"].append({"sql": "SELECT COUNT(*) AS n FROM analytics_groups"})
    q = bm.post("/api/v1/ai/ask/", {"question": "Guruhlar soni"}, format="json").json()
    calls = len(llm["sent"])
    assert bm.post(f"/api/v1/ai/{q['id']}/run/").json()["rows"] == [[1]] and len(llm["sent"]) == calls
    info = bm.get("/api/v1/ai/").json()
    assert info["used"] == 1 and info["history"][0]["question"] == "Guruhlar soni" and info["configured"] is True and len(info["examples"]) >= 5


def test_permissions_and_daily_limit(api, make_user, fin, llm, settings):  # noqa: F811
    for role in ("ADMIN", "FILIAL_MENEJERI", "ADMINISTRATOR", "USTOZ"):
        assert api(make_user(role)).post("/api/v1/ai/ask/", {"question": "x"}, format="json").status_code == 403
    settings.AI_DAILY_LIMIT = 1
    bm = api(fin["boss"])
    llm["answers"].append({"sql": "SELECT COUNT(*) AS n FROM analytics_staff"})
    assert bm.post("/api/v1/ai/ask/", {"question": "Xodimlar soni"}, format="json").status_code == 200
    assert bm.post("/api/v1/ai/ask/", {"question": "Yana"}, format="json").status_code == 429
    other = make_user("BOSH_MENEJER")
    q = AIQuery.objects.get()
    assert api(other).post(f"/api/v1/ai/{q.pk}/run/").status_code == 404  # boshqa xodimning savoli


def test_system_prompt_has_no_data(fin):  # noqa: F811
    p = services.system_prompt()
    assert "Ali Valiyev" not in p and "analytics_payments" in p and "Bugun:" in p


def test_examples_are_valid(fin):  # noqa: F811
    for q, sql, chart in services.examples():  # namunalar LLM'ga «to'g'ri javob» sifatida boradi — o'zi xatosiz bo'lsin
        clean, _ = guard.validate(sql)
        r = guard.execute(clean)
        assert chart["type"] == "none" or {chart["x"], *chart["y"]} <= set(r["columns"]), q


def test_provider_retries_when_busy(monkeypatch, settings):
    import io
    import urllib.error

    settings.AI_API_KEY = "k"
    calls = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b"{}"))
        return Resp(b'{"candidates": [{"content": {"parts": [{"text": "{\\"sql\\": \\"\\"}"}]}}]}')

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    assert providers.complete_json("s", "u") == {"sql": ""} and len(calls) == 3
    calls.clear()
    monkeypatch.setattr(providers.urllib.request, "urlopen", lambda req, timeout: (_ for _ in ()).throw(urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b""))))
    with pytest.raises(providers.ProviderError, match="band"):
        providers.complete("s", "u")


def test_model_chain_strong_first_on_retry(settings):
    settings.AI_PROVIDER, settings.AI_MODEL, settings.AI_MODEL_FALLBACKS, settings.AI_MODEL_STRONG = "gemini", "", None, []
    assert providers.model_chain()[0] == "gemini-3.5-flash-lite"
    assert providers.model_chain(strong=True)[:2] == ["gemini-3.7-flash", "gemini-3.8-flash"]
    assert len(set(providers.model_chain(strong=True))) == len(providers.model_chain(strong=True))  # takrorsiz


# ------------------------------------------------------------------ sifat: dars jadvali, bo'sh natija izohi, ma'lumotlar holati

def test_lessons_view_shows_missing_attendance(fin):  # noqa: F811
    import datetime

    from django.utils import timezone

    from apps.education.models import Attendance, Group
    from apps.references.models import DayPattern

    today = timezone.localdate()
    g0 = fin["contract"].group
    g = Group.objects.create(branch=fin["branch"], course=g0.course, day_pattern=DayPattern.objects.create(name="", weekdays=[1, 2, 3, 4, 5, 6, 7]),
                             time=g0.time, room=g0.room, teacher=fin["teacher"], start_date=today - datetime.timedelta(days=6), number=2)
    c = fin["contract"]
    c.group, c.start_date = g, today - datetime.timedelta(days=6)
    c.save()
    Attendance.objects.create(branch=fin["branch"], group=g, course=g.course, contract=c, day_pattern=g.day_pattern,
                              date=today - datetime.timedelta(days=2), status="1", teacher=fin["teacher"])
    rows = _rows("SELECT date, weekday, taken, came, students, started FROM analytics_lessons WHERE group_name = 'Frontend / #2' ORDER BY date")
    assert len(rows) == 3 and [r[2] for r in rows].count(1) == 1  # tizimdagi birinchi davomat kunidan: 3 kun, bittasida olingan
    taken = next(r for r in rows if r[2] == 1)
    assert str(taken[0])[:10] == str(today - datetime.timedelta(days=2)) and taken[3] == 1 and taken[4] == 1
    assert rows[0][5] == 1 and rows[0][1] == (today - datetime.timedelta(days=2)).isoweekday()
    # Dush/Chor/Jum guruhida faqat shu kunlar
    wd = {r[0] for r in _rows("SELECT weekday FROM analytics_lessons WHERE group_name = 'Frontend / #1'")}
    assert wd <= {1, 3, 5}


def test_empty_result_is_explained_and_retried_with_values(api, fin, llm):  # noqa: F811
    bm = api(fin["boss"])
    # 1) Nom noto'g'ri: «flutter14» → bo'sh → mavjud guruh nomlari bilan qayta so'raladi
    llm["answers"] += [{"sql": "SELECT student_name FROM analytics_contracts WHERE group_name LIKE '%frontend1%'"},
                       {"sql": "SELECT student_name FROM analytics_contracts WHERE group_name = 'Frontend / #1'", "title": "Guruh talabalari"}]
    d = bm.post("/api/v1/ai/ask/", {"question": "frontend1 guruhida kimlar bor"}, format="json").json()
    assert d["status"] == "ok" and d["rows"] == [["Ali Valiyev"]] and d["explain"] == []
    retry = llm["sent"][1][1]
    assert "Natija bo'sh" in retry and "'Frontend / #1'" in retry and "Ali Valiyev" not in retry  # faqat guruh nomlari, talaba emas
    assert AIQuery.objects.latest("created_at").llm_calls == 2
    # 2) Ma'lumot haqiqatan yo'q: to'lovlar kiritilmagan — qayta so'ralmaydi, sababi ekranda
    llm["answers"].append({"sql": "SELECT course, SUM(amount) AS s FROM analytics_payments GROUP BY course"})
    d = bm.post("/api/v1/ai/ask/", {"question": "To'lovlar kurslar bo'yicha"}, format="json").json()
    assert d["rows"] == [] and any("to'lov kiritilmagan" in x for x in d["explain"]) and AIQuery.objects.latest("created_at").llm_calls == 1
    assert bm.post(f"/api/v1/ai/{d['id']}/analyze/").status_code == 400  # bo'sh natijani tahlil qilish — LLM chaqirilmaydi
    # 3) Qarz 0: kurs narxi kiritilmagan
    Contract.objects.filter(pk=fin["contract"].pk).update(opening_balance=0)
    llm["answers"].append({"sql": "SELECT student_name, debt FROM analytics_contracts WHERE status = 'Faol' AND debt > 0 ORDER BY debt DESC LIMIT 5"})
    d = bm.post("/api/v1/ai/ask/", {"question": "eng ko'p qarzi bor o'quvchi kim"}, format="json").json()
    assert d["rows"] == [] and any("debt > 0" in x for x in d["explain"]) and any("Kurs narxlari kiritilmagan" in x for x in d["explain"])
    assert bm.post(f"/api/v1/ai/{d['id']}/run/").json()["explain"] == d["explain"]  # qayta bajarishda ham


def test_data_context_has_names_but_no_student_data(fin):  # noqa: F811
    p = services.system_prompt()
    assert "Frontend / #1" in p and "Emirat g'azna" in p and "Shartnomalar: 1 ta" in p and "analytics_lessons" in p
    assert "Ali Valiyev" not in p and "901112233" not in p

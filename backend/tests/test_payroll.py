"""M5: KPI stavkalari, oylik belgilash va berish, xodim balansi (CLAUDE.md 7.2, 7.5, 8.4)."""

import datetime
from decimal import Decimal

import pytest

from apps.education.models import Attendance
from apps.finance import services as fin
from apps.finance.models import Account, CashMovement
from apps.payroll.models import KPIRate, SalaryAssignment, SalaryPayout
from tests.test_education import MONTH, PREV, TODAY, take, world  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db


@pytest.fixture
def pw(world, make_user):  # noqa: F811
    acc = Account.objects.create(name="Emirat g'azna", cash_type="ALL", initial_balance=5_000_000)
    hisobchi = make_user("HISOBCHI")
    acc.responsible.set([hisobchi])
    return {**world, "acc": acc, "hisobchi": hisobchi, "fm": make_user("FILIAL_MENEJERI"), "bm": make_user("BOSH_MENEJER")}


def rate_body(w, **kw):
    return {"user": str(w["teacher"].pk), "role_type": "USTOZ", "course": str(w["course"].pk), "effective_from": f"{PREV:%Y-%m}", "type": "O'zgarmas", "fixed": 120000, **kw}


def test_rate_create_recalculates_and_validates(api, pw):
    take(api(pw["teacher"]), pw, [(c, "1", "") for c in pw["contracts"]])
    assert set(Attendance.objects.values_list("teacher_kpi", flat=True)) == {Decimal(0)}  # stavka yo'q
    fm = api(pw["fm"])
    r = fm.post("/api/v1/kpi-rates/", rate_body(pw), format="json")
    assert r.status_code == 201, r.content
    assert r.json()["recalculated"] == 3 and set(Attendance.objects.values_list("teacher_kpi", flat=True)) == {Decimal(10000)}
    assert fm.post("/api/v1/kpi-rates/", rate_body(pw), format="json").json()["effective_from"] == ["Shu oy uchun bu stavka mavjud — uni tahrirlang"]
    assert fm.post("/api/v1/kpi-rates/", rate_body(pw, user=str(pw["supporter"].pk)), format="json").json()["user"] == ["Xodim roli tanlangan stavka turiga mos emas"]
    assert api(pw["hisobchi"]).post("/api/v1/kpi-rates/", rate_body(pw, effective_from=f"{MONTH:%Y-%m}"), format="json").status_code == 403
    # Foiz stavka — yangi oydan
    rid = r.json()["id"]
    assert fm.patch(f"/api/v1/kpi-rates/{rid}/", {"type": "Foiz", "percent": 50}, format="json").status_code == 200
    assert set(Attendance.objects.values_list("teacher_kpi", flat=True)) == {Decimal(25000)}  # 50% × 600 000 / 12
    assert fm.delete(f"/api/v1/kpi-rates/{rid}/").status_code == 204
    assert set(Attendance.objects.values_list("teacher_kpi", flat=True)) == {Decimal(0)}


def test_salary_total_fine_and_carry_across_years(api, pw):
    KPIRate.objects.create(branch=pw["branch"], user=pw["teacher"], role_type="USTOZ", course=pw["course"], effective_from=PREV, type="O'zgarmas", fixed_amount=120000)
    take(api(pw["teacher"]), pw, [(c, "1", "") for c in pw["contracts"]])  # bugun: 3 × 10 000 KPI
    bm = api(pw["bm"])
    # O'tgan yil dekabri — 100 000 qoldiq (berilmagan)
    old = SalaryAssignment.objects.create(branch=pw["branch"], user=pw["teacher"], year=TODAY.year - 1, month=12, fixed=100000)
    body = {"user": str(pw["teacher"].pk), "year": TODAY.year, "month": TODAY.month, "fixed": 1_000_000, "bonus": 50000, "kpi": 20000, "fine": 70000}
    r = bm.post("/api/v1/salary-assignments/", body, format="json")
    assert r.status_code == 201, r.content
    d = r.json()
    assert d["tkpi"] == 30000 and d["total"] == 1_030_000  # 1 000 000 + 50 000 + 20 000 + 30 000 − 70 000
    assert d["carried"] == 100000 and d["final"] == 1_130_000  # yil oralig'idan o'tdi
    assert bm.post("/api/v1/salary-assignments/", body, format="json").json()["month"] == ["Bu xodimga shu oy uchun oylik belgilangan"]
    # Oylik berish → g'azna balansi kamayadi, xodim balansi kamayadi
    h = api(pw["hisobchi"])
    p = h.post("/api/v1/salary-payouts/", {"user": str(pw["teacher"].pk), "year": TODAY.year, "month": TODAY.month, "type": "O'zgarmas", "amount": 400000,
                                           "cash_type": "CASH", "account": str(pw["acc"].pk)}, format="json")
    assert p.status_code == 201, p.content
    assert fin.balance(pw["acc"]) == 4_600_000 and CashMovement.objects.get(source_type="salary").amount == -400000
    a = h.get(f"/api/v1/salary-assignments/{d['id']}/").json()
    assert a["given"] == 400000 and a["final"] == 730000
    assert old.pk  # tarixdagi yozuv qoldi
    bal = bm.get("/api/v1/salary-assignments/balances/").json()
    assert len(bal) == 1 and bal[0]["final"] == 730000
    br = bm.get(f"/api/v1/salary-assignments/{d['id']}/breakdown/").json()
    assert len(br["history"]) == 2 and len(br["payouts"]) == 1


def test_payout_rules_and_scope(api, make_user, pw):
    h = api(pw["hisobchi"])
    body = {"user": str(pw["teacher"].pk), "year": TODAY.year, "month": TODAY.month, "amount": 6_000_000, "cash_type": "CASH", "account": str(pw["acc"].pk)}
    assert h.post("/api/v1/salary-payouts/", body, format="json").json()["amount"] == ["G'aznada 5 000 000 so'm pul bor"]
    yesterday = (TODAY - datetime.timedelta(days=1)).isoformat()
    assert h.post("/api/v1/salary-payouts/", {**body, "amount": 100, "date": yesterday}, format="json").json()["date"] == ["Faqat bugun bilan kiritish mumkin, xolos"]
    assert h.post("/api/v1/salary-payouts/", {**body, "amount": 100, "user": str(make_user("ADMIN").pk)}, format="json").status_code == 400
    pid = h.post("/api/v1/salary-payouts/", {**body, "amount": 100000}, format="json").json()["id"]
    # Ustoz faqat o'zini ko'radi; boshqa ustoz — hech narsa
    assert api(pw["teacher"]).get("/api/v1/salary-payouts/").json()["count"] == 1
    assert api(make_user("USTOZ")).get("/api/v1/salary-payouts/").json()["count"] == 0
    assert api(pw["teacher"]).post("/api/v1/salary-payouts/", body, format="json").status_code == 403
    assert h.delete(f"/api/v1/salary-payouts/{pid}/").status_code == 403  # hisobchida o'chirish ruxsati yo'q (6.2)
    assert api(pw["bm"]).delete(f"/api/v1/salary-payouts/{pid}/").status_code == 204
    assert fin.balance(pw["acc"]) == 5_000_000 and SalaryPayout.all_objects.get(pk=pid).is_deleted


def test_payout_edit_moves_account(api, pw):
    """Berilgan oylikni tahrirlash: g'azna, pul turi, summa, davr — g'azna jurnali ko'chadi."""
    bosh = Account.objects.create(name="Bosh g'azna", cash_type="CARD", initial_balance=1_000_000)
    bm = api(pw["bm"])
    body = {"user": str(pw["teacher"].pk), "year": TODAY.year, "month": TODAY.month, "type": "O'zgarmas", "amount": 300000, "cash_type": "CASH", "account": str(pw["acc"].pk)}
    pid = bm.post("/api/v1/salary-payouts/", body, format="json").json()["id"]
    assert fin.balance(pw["acc"]) == 4_700_000
    r = bm.patch(f"/api/v1/salary-payouts/{pid}/", {"account": str(bosh.pk), "cash_type": "CARD", "amount": 250000, "type": "KPI", "month": PREV.month, "year": PREV.year}, format="json")
    assert r.status_code == 200, r.content
    assert fin.balance(pw["acc"]) == 5_000_000 and fin.balance(bosh) == 750_000
    p = SalaryPayout.objects.get(pk=pid)
    assert (p.type, p.month, p.amount) == ("KPI", PREV.month, 250000) and p.user == pw["teacher"]
    # Karta g'aznaga naqd pul turi to'g'ri kelmaydi; xodimni o'zgartirib bo'lmaydi
    assert bm.patch(f"/api/v1/salary-payouts/{pid}/", {"cash_type": "CASH"}, format="json").status_code == 400
    assert bm.patch(f"/api/v1/salary-payouts/{pid}/", {"user": str(pw["supporter"].pk)}, format="json").json()["user"] == ["Xodimni o'zgartirib bo'lmaydi"]
    # Hisobchida standart holda tahrirlash ruxsati yo'q (faqat qo'shish), FM — bor
    h = api(pw["hisobchi"])
    hid = h.post("/api/v1/salary-payouts/", {**body, "amount": 100000}, format="json").json()["id"]
    assert h.patch(f"/api/v1/salary-payouts/{hid}/", {"amount": 120000}, format="json").status_code == 403
    assert api(pw["fm"]).patch(f"/api/v1/salary-payouts/{hid}/", {"amount": 120000, "comment": "tuzatildi"}, format="json").status_code == 200
    assert fin.balance(pw["acc"]) == 4_880_000


def test_assignment_permissions_and_copy(api, pw):
    body = {"user": str(pw["teacher"].pk), "year": PREV.year, "month": PREV.month, "fixed": 900000}
    assert api(pw["hisobchi"]).post("/api/v1/salary-assignments/", body, format="json").status_code == 403  # faqat menejerlar
    fm = api(pw["fm"])
    assert fm.post("/api/v1/salary-assignments/", body, format="json").status_code == 201
    assert fm.post("/api/v1/salary-assignments/", {**body, "opening": 5}, format="json").status_code in (400, 403)
    r = fm.post("/api/v1/salary-assignments/copy/", {"month": f"{MONTH:%Y-%m}"}, format="json")
    assert r.json()["created"] == 1
    assert SalaryAssignment.objects.get(year=MONTH.year, month=MONTH.month).fixed == 900000
    assert fm.post("/api/v1/salary-assignments/copy/", {"month": f"{MONTH:%Y-%m}"}, format="json").json()["created"] == 0
    assert api(pw["teacher"]).get(f"/api/v1/salary-assignments/?month={MONTH:%Y-%m}").json()[0]["fixed"] == 900000  # o'zinikini ko'radi


def test_kpi_tree_and_rows(api, pw):
    KPIRate.objects.create(branch=pw["branch"], user=pw["teacher"], role_type="USTOZ", course=pw["course"], effective_from=PREV, type="O'zgarmas", fixed_amount=120000)
    take(api(pw["teacher"]), pw, [(pw["contracts"][0], "1", ""), (pw["contracts"][1], "X", "")])
    t = api(pw["teacher"]).get("/api/v1/kpi/").json()
    mine = [e for e in t if e["role"] == "USTOZ"]
    assert len(t) == len(mine) == 1 and mine[0]["n"] == 2 and mine[0]["paid"] == 1 and mine[0]["sum"] == 10000
    assert all(e["user"] == str(pw["teacher"].pk) for e in t)
    sup = api(pw["supporter"]).get("/api/v1/kpi/").json()
    assert len(sup) == 1 and sup[0]["role"] == "YORDAMCHI"
    rows = api(pw["bm"]).get(f"/api/v1/kpi/rows/?month={TODAY:%Y-%m}&user={pw['teacher'].pk}&role=USTOZ&group={pw['group'].pk}").json()
    assert len(rows) == 2
    assert api(pw["supporter"]).get(f"/api/v1/kpi/rows/?month={TODAY:%Y-%m}&user={pw['teacher'].pk}&role=USTOZ&group={pw['group'].pk}").status_code == 403


def test_query_counts(api, pw, django_assert_max_num_queries):
    for i in range(1, 6):
        SalaryAssignment.objects.create(branch=pw["branch"], user=pw["teacher"], year=2025, month=i, fixed=100)
    bm = api(pw["bm"])
    with django_assert_max_num_queries(12):
        assert len(bm.get("/api/v1/salary-assignments/").json()) == 5
    with django_assert_max_num_queries(12):
        bm.get("/api/v1/salary-assignments/balances/")

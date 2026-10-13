"""M7: foyda (8.6), oylik statistika, sotuv voronkasi, birinchi to'lovchilar (CLAUDE.md 11)."""

import pytest
from django.utils import timezone

from apps.crm.models import Lead
from apps.finance.models import Expense
from apps.payroll.models import SalaryAssignment
from apps.references.models import ExpenseCategory, LeadSource
from tests.test_finance import fin, pay  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()
YM = f"{TODAY:%Y-%m}"


def test_profit(api, make_user, fin):  # noqa: F811
    pay(api(fin["cashier"]), fin, amount=1_000_000)
    div = ExpenseCategory.objects.create(name="Dividend", kind="Dividend")
    for cat, total in ((fin["cat"], 200_000), (div, 300_000)):
        Expense.objects.create(branch=fin["branch"], date=TODAY, category=cat, name="x", quantity=1, price=total, total=total, cash_type="CASH",
                               account=fin["cash"], period_year=TODAY.year, period_month=TODAY.month)
    SalaryAssignment.objects.create(branch=fin["branch"], user=fin["teacher"], year=TODAY.year, month=TODAY.month, fixed=150_000, fine=50_000)
    r = api(fin["boss"]).get(f"/api/v1/reports/profit/?months={YM}")
    assert r.status_code == 200, r.content
    row = r.json()[0]
    assert row["payments"] == 1_000_000 and row["expenses"] == 200_000 and row["dividend"] == 300_000 and row["salaries"] == 100_000
    assert row["profit"] == 700_000  # dividend foydaga kirmaydi; jarima oylikdan ayirilgan
    assert api(make_user("FILIAL_MENEJERI")).get("/api/v1/reports/profit/").status_code == 403  # foyda — faqat Admin va BM


def test_stats_funnel_first_payers(api, make_user, fin):  # noqa: F811
    c = fin["contract"]
    src = LeadSource.objects.create(name="Instagram")
    Lead.objects.create(branch=fin["branch"], student=c.student, source=src, course=c.course, status="5", created_by=fin["cashier"])
    pay(api(fin["cashier"]), fin, amount=500_000)
    bm = api(fin["boss"])
    s = bm.get("/api/v1/reports/stats/?count=3").json()
    assert s["months"][-1] == YM and s["contracts_new"][-1] == 1 and s["money"][-1]["payments"] == 500_000
    assert sum(x["n"] for x in s["leads_by_source"]) == 1
    fm_stats = api(make_user("FILIAL_MENEJERI")).get("/api/v1/reports/stats/").json()
    assert fm_stats["money"] is None  # pul ko'rsatkichlari — faqat «Foyda» ruxsati bilan
    f = bm.get("/api/v1/reports/funnel/").json()
    assert f["total"] == 1 and f["contracts"] == 1 and f["paid"] == 1 and f["pay_rate"] == 1
    assert bm.get(f"/api/v1/reports/funnel/?source={src.pk}&owner={fin['boss'].pk}").json()["total"] == 0
    fp = bm.get(f"/api/v1/reports/first-payers/?month={YM}").json()
    assert fp["count"] == 1 and fp["rows"][0]["amount"] == 500_000 and fp["by_source"] == {"Instagram": 1}
    pay(api(fin["cashier"]), fin, amount=100_000)
    assert bm.get(f"/api/v1/reports/first-payers/?month={YM}").json()["count"] == 1  # ikkinchi to'lov «birinchi» emas
    assert api(make_user("HISOBCHI")).get("/api/v1/reports/funnel/").status_code == 403

"""M4: ledger, g'azna balansi, to'lovlar (chegirma limiti, tasdiqlar, chek), o'tkazmalar, ayirboshlash, xarajatlar, kreditorlar (CLAUDE.md 7.5)."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.crm.models import Student
from apps.education.models import Contract, Group
from apps.finance import services
from apps.finance.models import Account, CashMovement, Payment, Transfer
from apps.references.models import Course, DayPattern, DiscountType, ExpenseCategory, LessonTime, Room

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()


@pytest.fixture
def fin(branch, make_user):
    cashier = make_user("ADMINISTRATOR_HISOBCHI")
    accountant = make_user("HISOBCHI")
    cash = Account.objects.create(name="Emirat g'azna", cash_type="ALL", initial_balance=1_000_000)
    cash.responsible.set([cashier, accountant])
    card = Account.objects.create(name="Bosh g'azna", cash_type="CARD", initial_balance=0)
    boss = make_user("BOSH_MENEJER")
    card.responsible.set([boss])
    branch.default_cashbox, branch.noncash_cashbox = cash, card
    branch.save()
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    teacher = make_user("USTOZ")
    g = Group.objects.create(branch=branch, course=course, day_pattern=DayPattern.objects.create(name="", weekdays=[1, 3, 5]),
                             time=LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"), teacher=teacher,
                             room=Room.objects.create(branch=branch, name="1", capacity=10), start_date=TODAY, number=1)
    st = Student.objects.create(branch=branch, first_name="Ali", last_name="Valiyev", phone1="901112233")
    c = Contract.objects.create(branch=branch, student=st, course=course, group=g, number=1, start_date=TODAY, opening_balance=600000)
    d = DiscountType.objects.create(name="Rag'batlantiruvchi", max_amount=350000)
    system = DiscountType.objects.create(name="Boshlang'ich balansga", max_amount=500000, is_system=True)
    cat = ExpenseCategory.objects.create(name="Kommunal")
    cat.allowed_roles.set(Role.objects.filter(code__in=["ADMIN", "BOSH_MENEJER", "HISOBCHI", "ADMINISTRATOR_HISOBCHI"]))
    return {"cashier": cashier, "accountant": accountant, "boss": boss, "cash": cash, "card": card, "contract": c, "discount": d, "system": system,
            "cat": cat, "branch": branch, "teacher": teacher}


def pay(client, f, **kw):
    body = {"contract": str(f["contract"].pk), "amount": 300000, "cash_type": "CASH", "cashbox": str(f["cash"].pk), **kw}
    return client.post("/api/v1/payments/", body, format="json")


def bal(acc, t=None):
    return services.balance(Account.objects.get(pk=acc.pk), t)


# ------------------------------------------------------------------ to'lovlar

def test_cash_payment_updates_balance_and_contract(api, fin):
    c = api(fin["cashier"])
    r = pay(c, fin)
    assert r.status_code == 201, r.content
    d = r.json()
    assert d["number"] == 1 and d["nc_status"] == "" and d["accountant"] == str(fin["cashier"].pk)
    assert bal(fin["cash"]) == 1_300_000 and bal(fin["cash"], "CASH") == 1_300_000
    detail = c.get(f"/api/v1/contracts/{fin['contract'].pk}/").json()
    assert detail["paid"] == 300000 and detail["balance"] == 300000 and len(detail["payments"]) == 1
    lst = c.get(f"/api/v1/payments/?month={TODAY:%Y-%m}").json()
    assert lst["total"] == 300000 and lst["by_day"][TODAY.isoformat()] == 300000


def test_payment_rules(api, make_user, fin):
    c = api(fin["cashier"])
    assert pay(c, fin, date=(TODAY - datetime.timedelta(days=1)).isoformat()).json()["date"] == ["Faqat bugun bilan kiritish mumkin, xolos"]
    assert pay(c, fin, date=(TODAY + datetime.timedelta(days=1)).isoformat()).json()["date"] == ["Kelasi davr bilan kiritib bo'lmaydi"]
    assert pay(c, fin, amount=0).json()["amount"] == ["To'lov summasi yoki chegirma kiritilishi kerak"]
    assert pay(c, fin, cashbox=str(fin["card"].pk)).json()["cashbox"] == ["Siz mas'ul bo'lgan faol g'aznani tanlang"]
    assert pay(c, fin, amount=-5).status_code == 400
    # Administrator to'lov qabul qilmaydi (18-bo'lim 10-savol taklifi), ustoz ham
    assert pay(api(make_user("ADMINISTRATOR")), fin).status_code == 403
    assert pay(api(fin["teacher"]), fin).status_code == 403
    # Bosh menejer o'tgan sana bilan kirita oladi
    r = pay(api(fin["boss"]), fin, cash_type="CARD", cashbox=None, date=(TODAY - datetime.timedelta(days=3)).isoformat())
    assert r.status_code == 201, r.content


def test_discount_limit_and_approval(api, make_user, fin):
    c = api(fin["cashier"])
    r = pay(c, fin, discount_type=str(fin["discount"].pk), discount=400000)
    assert r.json()["discount"] == ["Bu chegirma turiga 350 000 so'mdan ortiqcha chegirma kiritib bo'lmaydi"]
    assert pay(c, fin, discount_type=str(fin["system"].pk), discount=100000).json()["discount_type"] == ["Bu chegirma turini faqat Admin va Bosh menejer qo'llaydi"]
    r = pay(c, fin, discount_type=str(fin["discount"].pk), discount=100000)
    assert r.status_code == 201 and r.json()["disc_status"] == "Tasdiqlashga"
    pid = r.json()["id"]
    assert api(fin["cashier"]).post(f"/api/v1/payments/{pid}/approve_discount/").status_code == 403
    assert api(make_user("FILIAL_MENEJERI")).post(f"/api/v1/payments/{pid}/approve_discount/").status_code == 403
    bm = api(fin["boss"])
    Payment.objects.filter(pk=pid).update(created_at=timezone.now() - datetime.timedelta(days=31))
    assert bm.post(f"/api/v1/payments/{pid}/approve_discount/").status_code == 403  # Bosh menejer — 30 kun
    assert api(make_user("ADMIN")).post(f"/api/v1/payments/{pid}/approve_discount/").json()["disc_status"] == "Tasdiqlandi"
    # tasdiqlangan to'lovni hisobchi o'zgartira olmaydi
    assert c.patch(f"/api/v1/payments/{pid}/", {"comment": "x"}, format="json").status_code == 403
    assert c.get(f"/api/v1/contracts/{fin['contract'].pk}/").json()["discount"] == 100000


def test_noncash_pending_until_approved(api, make_user, fin):
    c = api(fin["cashier"])
    r = pay(c, fin, cash_type="CARD", cashbox=None)
    assert r.status_code == 201 and r.json()["nc_status"] == "Tasdiqlashga" and r.json()["cashbox"] == str(fin["card"].pk)
    card = Account.objects.get(pk=fin["card"].pk)
    assert services.balance(card) == 0 and services.balances([card.pk])[card.pk]["pending"] == 300000
    assert c.get(f"/api/v1/payments/{r.json()['id']}/receipt/").status_code == 403  # tasdiqlanmagan chek
    fm = api(make_user("FILIAL_MENEJERI"))
    Payment.objects.filter(pk=r.json()["id"]).update(created_at=timezone.now() - datetime.timedelta(days=8))
    assert fm.post(f"/api/v1/payments/{r.json()['id']}/approve_noncash/").status_code == 403  # filial menejeri — 7 kun
    assert api(fin["boss"]).post(f"/api/v1/payments/{r.json()['id']}/approve_noncash/").status_code == 200
    assert services.balance(card, "CARD") == 300000
    pdf = c.get(f"/api/v1/payments/{r.json()['id']}/receipt/")
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf" and pdf.content[:4] == b"%PDF"


def test_payment_edit_delete_and_ledger_sync(api, fin):
    c = api(fin["cashier"])
    pid = pay(c, fin).json()["id"]
    assert c.patch(f"/api/v1/payments/{pid}/", {"amount": 250000}, format="json").status_code == 200
    assert bal(fin["cash"]) == 1_250_000
    Payment.objects.filter(pk=pid).update(date=TODAY - datetime.timedelta(days=1))
    assert c.patch(f"/api/v1/payments/{pid}/", {"amount": 200000}, format="json").status_code == 403  # faqat bugun
    assert api(fin["boss"]).delete(f"/api/v1/payments/{pid}/").status_code == 204
    assert bal(fin["cash"]) == 1_000_000 and Payment.all_objects.get(pk=pid).is_deleted
    assert not CashMovement.objects.filter(source_id=pid).exists()


def test_accounts_balances_and_ledger_api(api, fin):
    c = api(fin["cashier"])
    pay(c, fin)
    accs = {a["name"]: a for a in api(fin["boss"]).get("/api/v1/accounts/").json()}
    assert accs["Emirat g'azna"]["balance"] == 1_300_000 and accs["Emirat g'azna"]["by_type"]["CASH"] == 1_300_000
    led = c.get(f"/api/v1/accounts/{fin['cash'].pk}/ledger/").json()
    assert led["count"] == 1 and led["results"][0]["src"] == "To'lov" and led["results"][0]["amount"] == 300000


# ------------------------------------------------------------------ o'tkazma, ayirboshlash, xarajat, kreditor

def test_transfer_flow(api, make_user, fin):
    c = api(fin["cashier"])
    body = {"sender": str(fin["cash"].pk), "receiver": str(fin["card"].pk), "amount": 2_000_000}
    assert c.post("/api/v1/transfers/", body, format="json").json()["amount"] == ["G'aznada 1 000 000 so'm pul bor"]
    r = c.post("/api/v1/transfers/", {**body, "amount": 400000}, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "Tasdiqlashga" and r.json()["direction"] == "Chiquvchi" and r.json()["cash_type"] == "CASH"
    assert bal(fin["cash"]) == 1_000_000  # tasdiqlanmaguncha hisobga olinmaydi
    tid = r.json()["id"]
    assert c.post(f"/api/v1/transfers/{tid}/confirm/").status_code == 403  # yuboruvchi o'zi tasdiqlamaydi
    r = c.patch(f"/api/v1/transfers/{tid}/", {"amount": 300000}, format="json")  # tasdiqlanmaguncha yuboruvchi o'zgartira oladi
    assert r.status_code == 200 and r.json()["amount"] == 300000
    assert api(fin["boss"]).post(f"/api/v1/transfers/{tid}/confirm/").status_code == 200
    assert bal(fin["cash"]) == 700000 and bal(fin["card"], "CASH") == 300000
    assert Transfer.objects.get().confirmed_by == fin["boss"]
    assert c.patch(f"/api/v1/transfers/{tid}/", {"amount": 100}, format="json").status_code == 403  # tasdiqlangach — faqat Admin / Bosh menejer
    assert c.delete(f"/api/v1/transfers/{tid}/").status_code == 403


def test_pending_transfer_edit_delete(api, make_user, fin):
    ah = api(fin["cashier"])  # Administrator+Hisobchi, jo'natuvchi g'azna mas'uli
    old = TODAY - datetime.timedelta(days=5)
    t = Transfer.objects.create(date=old, sender_account=fin["cash"], sender_cashier=fin["cashier"], amount=100000, receiver_account=fin["card"],
                                receiver_cashier=fin["boss"], created_by=make_user("ADMINISTRATOR_HISOBCHI"))
    # sana o'tgan bo'lsa ham, tasdiqlanmaguncha sender g'azna mas'uli o'zgartiradi va o'chiradi
    r = ah.patch(f"/api/v1/transfers/{t.pk}/", {"amount": 250000, "date": old.isoformat(), "comment": "tuzatildi"}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["amount"] == 250000 and r.json()["comment"] == "tuzatildi" and r.json()["can_modify"] is True
    # begona (g'azna mas'uli ham, yaratuvchi ham emas) — o'zgartira olmaydi
    stranger = api(make_user("ADMINISTRATOR_HISOBCHI"))
    assert stranger.patch(f"/api/v1/transfers/{t.pk}/", {"comment": "x"}, format="json").status_code in (403, 404)
    assert stranger.delete(f"/api/v1/transfers/{t.pk}/").status_code in (403, 404)
    assert ah.delete(f"/api/v1/transfers/{t.pk}/").status_code == 204
    assert not Transfer.objects.filter(pk=t.pk).exists() and bal(fin["cash"]) == 1_000_000


def test_exchange_only_top(api, make_user, fin):
    body = {"account": str(fin["cash"].pk), "from_type": "CASH", "amount": 100000, "to_type": "CARD", "amount_to": 98000}
    assert api(fin["cashier"]).post("/api/v1/exchanges/", body, format="json").status_code == 403
    adm = api(make_user("ADMIN"))
    assert adm.post("/api/v1/exchanges/", {**body, "amount_to": 120000}, format="json").json()["amount_to"] == ["100 000 dan katta bo'lolmaydi"]
    r = adm.post("/api/v1/exchanges/", body, format="json")
    assert r.status_code == 201 and r.json()["loss"] == 2000
    assert bal(fin["cash"], "CASH") == 900000 and bal(fin["cash"], "CARD") == 98000


def test_expense_rules(api, make_user, fin):
    c = api(fin["accountant"])
    body = {"date": TODAY.isoformat(), "category": str(fin["cat"].pk), "name": "Svet", "quantity": 2, "price": 300000, "cash_type": "CASH", "account": str(fin["cash"].pk)}
    r = c.post("/api/v1/expenses/", body, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["total"] == 600000 and r.json()["period_month"] == TODAY.month
    assert bal(fin["cash"]) == 400000
    assert c.post("/api/v1/expenses/", {**body, "quantity": 1, "price": 500000}, format="json").json()["price"] == ["G'aznada 400 000 so'm pul bor"]
    assert c.post("/api/v1/expenses/", {**body, "date": (TODAY - datetime.timedelta(days=1)).isoformat()}, format="json").status_code == 403  # hisobchi — faqat bugun
    other = ExpenseCategory.objects.create(name="Dividend", kind="Dividend")
    other.allowed_roles.set(Role.objects.filter(code="ADMIN"))
    assert c.post("/api/v1/expenses/", {**body, "category": str(other.pk)}, format="json").json()["category"] == ["Bu kategoriyaga sizning rolingiz xarajat kirita olmaydi"]
    # Bosh menejer hisob davrini o'zgartiradi, qoldiqdan oshsa ham ruxsat
    bm = api(fin["boss"])
    fin["cash"].responsible.add(fin["boss"])
    r = bm.post("/api/v1/expenses/", {**body, "price": 5_000_000, "period_year": 2026, "period_month": 1}, format="json")
    assert r.status_code == 201 and r.json()["period_month"] == 1
    assert c.get("/api/v1/expenses/names/?category=" + str(fin["cat"].pk)).json() == ["Svet"]
    s = bm.get("/api/v1/expenses/summary/").json()
    assert sum(x["sum"] for x in s) == 10_600_000


def test_creditors(api, make_user, fin):
    bm = api(fin["boss"])
    fin["cash"].responsible.add(fin["boss"])
    cid = bm.post("/api/v1/creditors/", {"name": "Bank krediti", "initial": 0}, format="json").json()["id"]
    assert bm.post("/api/v1/creditor-transactions/", {"creditor": cid, "amount": -5_000_000, "cash_type": "CASH", "account": str(fin["cash"].pk)}, format="json").status_code == 201
    assert bal(fin["cash"]) == 6_000_000  # qarz olindi — g'aznaga kirdi
    assert bm.post("/api/v1/creditor-transactions/", {"creditor": cid, "amount": 1_000_000, "cash_type": "CASH", "account": str(fin["cash"].pk)}, format="json").status_code == 201
    d = bm.get(f"/api/v1/creditors/{cid}/").json()
    assert d["current"] == 4_000_000 and len(d["transactions"]) == 2
    assert bal(fin["cash"]) == 5_000_000
    assert bm.patch(f"/api/v1/creditors/{cid}/", {"initial": 100}, format="json").status_code == 403  # faqat Admin
    assert api(fin["cashier"]).get("/api/v1/creditors/").status_code == 403


def test_approvals_count_and_lead_paid(api, make_user, fin):
    c = api(fin["cashier"])
    pay(c, fin, cash_type="CARD", cashbox=None, discount_type=str(fin["discount"].pk), discount=50000)
    c.post("/api/v1/transfers/", {"sender": str(fin["cash"].pk), "receiver": str(fin["card"].pk), "amount": 100}, format="json")
    n = api(fin["boss"]).get("/api/v1/approvals/").json()
    assert n["discounts"] == 1 and n["noncash"] == 1 and n["transfers"] == 1
    assert api(fin["cashier"]).get("/api/v1/approvals/").json()["total"] == 0
    s = api(fin["boss"]).get("/api/v1/payments/summary/").json()
    assert s["noncash"] == 300000 and s["cash"] == 0


def test_query_counts(api, fin, django_assert_max_num_queries):
    c = api(fin["cashier"])
    for _ in range(5):
        pay(c, fin, amount=1000)
    with django_assert_max_num_queries(14):
        assert c.get("/api/v1/payments/").json()["count"] == 5
    bm = api(fin["boss"])
    with django_assert_max_num_queries(10):
        bm.get("/api/v1/accounts/")


def test_balance_helper_matches_ledger(fin):
    acc = fin["cash"]
    assert services.balance(acc) == Decimal(1_000_000)


def test_leads_paid_tab(api, fin):
    from apps.crm.models import Lead
    from apps.references.models import LeadSource

    c = fin["contract"]
    Lead.objects.create(branch=fin["branch"], student=c.student, source=LeadSource.objects.create(name="Instagram"), course=c.course, status="5")
    bm = api(fin["boss"])
    assert bm.get("/api/v1/leads/?paid=1").json()["count"] == 0
    pay(api(fin["cashier"]), fin)
    r = bm.get("/api/v1/leads/?paid=1").json()
    assert r["count"] == 1 and r["results"][0]["paid_total"] == 300000 and r["results"][0]["first_paid"] == TODAY.isoformat()


def test_boss_can_use_any_cashbox(api, fin):
    assert not fin["cash"].responsible.filter(pk=fin["boss"].pk).exists()
    r = pay(api(fin["boss"]), fin)
    assert r.status_code == 201, r.content
    assert r.json()["cashbox"] == str(fin["cash"].pk) and r.json()["accountant"] in (str(fin["cashier"].pk), str(fin["accountant"].pk))

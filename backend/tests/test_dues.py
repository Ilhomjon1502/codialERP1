"""«Shu oy to'lovi» (education/dues.py): oy narxi bo'yicha kutilayotgan to'lov, davomatga bog'liq emas."""

import datetime

import pytest

from apps.crm.models import Student
from apps.education import dues
from apps.education.models import Contract, Group
from apps.finance.models import Payment
from apps.references.models import Course, CoursePrice, DayPattern, LessonTime, Room

pytestmark = pytest.mark.django_db
D = datetime.date
MONTH = D(2026, 11, 1)  # dush/chor/jum: 2,9,16,23,30 · 4,11,18,25 · 6,13,20,27 = 13 dars; narx 1 300 000 → dars 100 000


@pytest.fixture
def setup(branch, make_user):
    course = Course.objects.create(name="Frontend")
    course.branches.set([branch])
    CoursePrice.objects.create(branch=branch, course=course, effective_from=D(2026, 10, 1), price=1_300_000)
    g = Group.objects.create(
        branch=branch, course=course, day_pattern=DayPattern.objects.create(name="Dush,Chor,Jum", weekdays=[1, 3, 5]),
        time=LessonTime.objects.create(branch=branch, start_time="14:00", end_time="16:00"), teacher=make_user("USTOZ"),
        room=Room.objects.create(branch=branch, name="1", capacity=10), start_date=D(2026, 10, 1), number=1)
    n = iter(range(1, 100))

    def contract(**kw):
        i = next(n)
        st = Student.objects.create(branch=branch, first_name=f"Ali{i}", last_name="Valiyev", phone1=f"9011122{i:02d}")
        return Contract.objects.create(branch=branch, student=st, course=course, group=g, number=i, start_date=kw.pop("start_date", D(2026, 10, 1)), **kw)

    def paid(c, date, amount, discount=0):
        return Payment.objects.create(branch=c.branch, contract=c, group=c.group, number=Payment.objects.count() + 1, date=date, amount=amount, discount=discount)

    return {"contract": contract, "paid": paid, "branch": branch, "make_user": make_user}


def run(on=datetime.date(2026, 11, 5)):
    return dues.month_dues(Contract.objects.all(), MONTH, on)


def test_full_month_price_without_attendance(setup):
    c = setup["contract"]()
    r = run()[c.pk]
    assert r["month_price"] == 1_300_000 and r["to_pay"] == 1_300_000 and r["lessons"] == r["lessons_total"] == 13


def test_paid_this_month_drops_out(setup):
    c = setup["contract"]()
    setup["paid"](c, D(2026, 11, 3), 1_300_000)
    assert c.pk not in run()
    d = setup["contract"]()
    setup["paid"](d, D(2026, 11, 3), 800_000, discount=100_000)
    assert run()[d.pk]["to_pay"] == 400_000 and run()[d.pk]["paid_month"] == 900_000


def test_prepaid_credit_covers_month_and_old_debt_adds(setup):
    credit = setup["contract"](opening_balance=-1_300_000)
    debt = setup["contract"](opening_balance=200_000)
    old_paid = setup["contract"](opening_balance=500_000)
    setup["paid"](old_paid, D(2026, 10, 5), 500_000)  # oktyabrdagi to'lov oy boshidagi balansga kiradi
    r = run()
    assert credit.pk not in r
    assert r[debt.pk]["to_pay"] == 1_500_000 and r[debt.pk]["prev_balance"] == 200_000
    assert r[old_paid.pk]["to_pay"] == 1_300_000 and r[old_paid.pk]["prev_balance"] == 0


def test_partial_credit(setup):
    c = setup["contract"](opening_balance=-500_000)
    assert run()[c.pk]["to_pay"] == 800_000


def test_pro_rata_for_mid_month_start(setup):
    c = setup["contract"](start_date=D(2026, 11, 16))  # 16–30 noyabr: 3 dush + 2 chor + 2 jum = 7 dars
    r = run()[c.pk]
    assert r["lessons"] == 7 and r["lessons_total"] == 13 and r["month_price"] == 700_000


def test_grant_and_ended_excluded(setup):
    grant = setup["contract"](type=Contract.Type.GRANT)
    ended = setup["contract"](end_date=D(2026, 11, 2), stop_reason="Kursni tamomladi")
    future = setup["contract"](start_date=D(2026, 12, 1))
    r = run()
    assert not ({grant.pk, ended.pk, future.pk} & set(r))


def test_deadline_from_branch_setting(setup):
    c = setup["contract"]()
    assert run(D(2026, 11, 10))[c.pk]["overdue"] is False
    late = run(D(2026, 11, 12))[c.pk]
    assert late["overdue"] is True and late["days_over"] == 2 and late["deadline"] == D(2026, 11, 10)
    b = setup["branch"]
    b.payment_due_day = 5
    b.save()
    assert run(D(2026, 11, 12))[c.pk]["days_over"] == 7


def test_missing_price_flagged(setup):
    CoursePrice.objects.all().delete()
    c = setup["contract"](opening_balance=100_000)
    r = run()[c.pk]
    assert r["no_price"] is True and r["to_pay"] == 100_000


def test_api_month_list_and_permissions(api, setup):
    c = setup["contract"]()
    setup["paid"](setup["contract"](), D(2026, 11, 2), 1_300_000)
    cl = api(setup["make_user"]("ADMINISTRATOR_HISOBCHI"))
    r = cl.get("/api/v1/debtors/month/?month=2026-11")
    assert r.status_code == 200, r.content
    d = r.json()
    assert d["count"] == 1 and d["total"] == 1_300_000 and d["results"][0]["id"] == str(c.pk)
    assert d["results"][0]["to_pay"] == 1_300_000 and d["results"][0]["deadline"] == "2026-11-10"
    assert api(setup["make_user"]("USTOZ")).get("/api/v1/debtors/month/").status_code == 403
    # eski ro'yxat o'zgarmagan
    assert cl.get("/api/v1/debtors/").status_code == 200


def test_morning_plan_uses_month_dues(setup):
    from apps.notifications import reminders

    c = setup["contract"]()
    on = D(2026, 11, 11)  # chorshanba — guruhning dars kuni, muddat (10) o'tgan
    text = reminders.plan_text(setup["branch"], on)
    assert c.student.full_name in text and "1 300 000" in text and "Muddati o'tgan" in text


def test_dismissed_hidden_and_restorable(setup, api):
    from apps.education.models import DueDismissal

    c = setup["contract"]()
    bm = setup["make_user"]("BOSH_MENEJER")
    assert c.pk in run()
    cl = api(bm)
    assert cl.post(f"/api/v1/debtors/{c.pk}/dismiss/", {"month": "2026-11"}, format="json").status_code == 200
    assert c.pk not in run()
    assert c.pk in dues.month_dues(Contract.objects.all(), MONTH, datetime.date(2026, 11, 5), "only")
    assert DueDismissal.objects.count() == 1
    assert c.pk in dues.month_dues(Contract.objects.all(), datetime.date(2026, 12, 1), datetime.date(2026, 12, 5))  # keyingi oy yana chiqadi
    assert cl.post(f"/api/v1/debtors/{c.pk}/restore/", {"month": "2026-11"}, format="json").status_code == 200
    assert c.pk in run()


def test_dismiss_forbidden_for_teacher(setup, api):
    c = setup["contract"]()
    assert api(setup["make_user"]("USTOZ")).post(f"/api/v1/debtors/{c.pk}/dismiss/", {}, format="json").status_code == 403

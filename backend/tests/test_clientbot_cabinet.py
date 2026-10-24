"""Mijozlar boti B3: o'quvchi va vasiy kabineti — to'lovlar, davomat, dars jadvali, to'lov muddati."""

import datetime

import pytest
from django.utils import timezone

from apps.clientbot import cabinet
from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, BotLink
from apps.education.models import Attendance, Contract, Group
from apps.finance.models import Payment
from tests.test_clientbot import make_lead, on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_sms_auto import env, refs  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
D = datetime.date
PAY, ATT, SCH, DUE = cabinet.ACTIONS["pay"], cabinet.ACTIONS["att"], cabinet.ACTIONS["sch"], cabinet.ACTIONS["due"]


def pay(env, c, number, date, amount, **kw):  # noqa: F811
    return Payment.objects.create(branch=env["branch"], contract=c, group=env["group"], number=number, date=date, amount=amount, **kw)


def att(env, c, date, status, debt=None):  # noqa: F811
    return Attendance.objects.create(branch=env["branch"], group=env["group"], course=env["course"], contract=c, day_pattern=env["group"].day_pattern,
                                     date=date, status=status, teacher=env["group"].teacher, student_debt=debt)


def text(replies):
    assert len(replies) == 1
    return replies[0].text


def test_menu_shown_after_link_and_status(env, on):  # noqa: F811
    st = env["student"](1)
    env["contract"](st)
    inv = bot.invite_for(st, st.phone1)
    r = bot.handle_message(1, f"/start {inv.code}")
    assert r[0].markup["keyboard"][0][0]["text"] == PAY and r[0].markup["resize_keyboard"]
    assert [b["text"] for row in r[0].markup["keyboard"] for b in row] == [PAY, ATT, SCH, DUE]
    s = bot.handle_message(1, "/menu")
    assert "Siz ulangansiz" in s[0].text and s[0].markup["keyboard"]


def test_payments_text_lists_payments_totals_and_balance(env, on):  # noqa: F811
    st = env["student"](1)
    c = env["contract"](st)
    link_phone(st, st.phone1, 1)
    pay(env, c, 1, D(2026, 10, 3), 500_000, cash_type="CASH")
    pay(env, c, 2, D(2026, 10, 20), 300_000, cash_type="CARD", discount=50_000, noncash_status="Tasdiqlashga")
    for d in (D(2026, 10, 1), D(2026, 10, 3), D(2026, 10, 6)):
        att(env, c, d, "1", debt=100_000)
    t = text(bot.handle_message(1, PAY))
    assert "20.10.2026 — <b>300 000</b> so'm (karta) + chegirma 50 000 ⏳ tasdiqlanmoqda" in t
    assert "03.10.2026 — <b>500 000</b> so'm (naqd)" in t and "Jami to'langan: <b>800 000</b>" in t
    assert "Kompyuter savodxonligi: oldindan to'langan <b>550 000</b>" in t  # 300 000 − 800 000 − 50 000
    assert "Muhsinjon" in t


def test_payments_empty_and_debt(env, on):  # noqa: F811
    st = env["student"](2)
    c = env["contract"](st, opening_balance=200_000)
    link_phone(st, st.phone1, 2)
    t = text(bot.handle_message(2, PAY))
    assert "Hali to'lov kiritilmagan" in t and "qarz <b>200 000</b> so'm" in t
    assert Contract.objects.get(pk=c.pk)


def test_attendance_text_month_summary_and_hides_inactive(env, on):  # noqa: F811
    st = env["student"](1)
    c = env["contract"](st)
    link_phone(st, st.phone1, 1)
    today = timezone.localdate()
    att(env, c, today, "1")
    att(env, c, today - datetime.timedelta(days=1), "0")
    att(env, c, today - datetime.timedelta(days=2), "X")
    att(env, c, today - datetime.timedelta(days=3), "-")  # nofaol — ko'rsatilmaydi
    t = text(bot.handle_message(1, ATT))
    assert "✅ Keldi" in t and "🟡 Sababli" in t and "❌ Sababsiz" in t and "Nofaol" not in t
    if today.day > 3:  # oy boshidagi kunlarda summa oldingi oyga ham tushishi mumkin
        assert "✅ 1 · 🟡 1 · ❌ 1 (jami 3 dars)" in t
    assert "KPI" not in t and "qarz" not in t.lower()


def test_next_lesson_and_schedule_text(env, on):  # noqa: F811
    st = env["student"](1)
    c = env["contract"](st)
    g = Group.objects.select_related("day_pattern", "time").get(pk=env["group"].pk)  # vaqt maydonlari bazadan o'qilsin (fixture satr bergan)
    tz = timezone.get_current_timezone()
    at = lambda y, m, d, h: timezone.make_aware(datetime.datetime(y, m, d, h, 0), tz)  # noqa: E731
    assert cabinet.next_lesson(g, at(2026, 10, 26, 10)) == D(2026, 10, 26)  # dushanba, dars hali tugamagan — bugun
    assert cabinet.next_lesson(g, at(2026, 10, 26, 17)) == D(2026, 10, 28)  # dars tugagan — chorshanba
    assert cabinet.next_lesson(g, at(2026, 10, 31, 9)) == D(2026, 11, 2)  # shanba — keyingi dushanba
    g.end_date = D(2026, 10, 27)
    g.save()
    assert cabinet.next_lesson(g, at(2026, 10, 28, 9)) is None
    g.end_date = None
    g.save()
    link_phone(st, st.phone1, 1)
    t = cabinet.schedule_text(st, D(2026, 10, 24))
    assert "Dush, Chor, Jum" in t and "14:00–16:00" in t and "Xona: 1" in t and "Ustoz:" in t and "Keyingi dars:" in t
    assert str(c.group.number) in t


def test_due_text_unpaid_overdue_paid_and_grant(env, on):  # noqa: F811
    st = env["student"](1)
    c = env["contract"](st)
    t = cabinet.due_text(st, D(2026, 11, 5))
    assert "Noyabr oyi uchun to'lash kerak: <b>1 300 000</b>" in t and "Muddat: 10.11.2026" in t and "⚠️" not in t
    assert "⚠️ 2 kun o'tdi" in cabinet.due_text(st, D(2026, 11, 12))
    pay(env, c, 1, D(2026, 11, 3), 1_300_000)
    assert "✅ Noyabr oyi uchun to'lov qilingan" in cabinet.due_text(st, D(2026, 11, 12))
    grant = env["student"](2)
    env["contract"](grant, type="Grant")
    assert "Grant — to'lov talab qilinmaydi" in cabinet.due_text(grant, D(2026, 11, 5))


def test_due_text_via_menu_and_no_active_contract(env, on):  # noqa: F811
    st = env["student"](3)
    env["contract"](st, start_date=D(2026, 1, 1), end_date=D(2026, 2, 1))
    link_phone(st, st.phone1, 3)
    assert "Hozir faol shartnoma yo'q" in text(bot.handle_message(3, DUE))
    assert "Hozir faol shartnoma yo'q" in text(bot.handle_message(3, SCH))
    assert "Hali davomat belgilanmagan" in text(bot.handle_message(3, ATT))


def test_guardian_with_two_children_picks_child(env, on):  # noqa: F811
    a, b = env["student"](1), env["student"](2)
    ca = env["contract"](a)
    env["contract"](b)
    link_phone(a, a.parent.phone, 5)
    link_phone(b, b.parent.phone, 5)
    pay(env, ca, 1, D(2026, 10, 3), 500_000, cash_type="CASH")
    r = bot.handle_message(5, PAY)
    assert "qaysi farzand" in r[0].text
    data = {x["text"]: x["callback_data"] for row in r[0].markup["inline_keyboard"] for x in row}
    assert set(data.values()) == {f"cs:pay:{a.pk}", f"cs:pay:{b.pk}"}
    ans, rep = bot.handle_callback(5, data[f"{a.first_name} {a.last_name}"])
    assert ans == "✅" and "500 000" in rep[0].text and a.last_name in rep[0].text
    _, rep_b = bot.handle_callback(5, data[f"{b.first_name} {b.last_name}"])
    assert "Hali to'lov kiritilmagan" in rep_b[0].text


def test_cannot_see_other_students_or_after_stop(env, on):  # noqa: F811
    a, b = env["student"](1), env["student"](2)
    ca = env["contract"](a)
    env["contract"](b)
    pay(env, ca, 1, D(2026, 10, 3), 777_000, cash_type="CASH")
    link_phone(b, b.phone1, 6)
    assert "777 000" not in text(bot.handle_message(6, PAY))
    ans, rep = bot.handle_callback(6, f"cs:pay:{a.pk}")  # boshqa talabaning id'si bilan urinish
    assert ans == "Topilmadi" and rep == []
    link_phone(a, a.phone1, 7)
    assert "777 000" in text(bot.handle_message(7, PAY))
    bot.handle_message(7, "/stop")
    assert "rasmiy boti" in text(bot.handle_message(7, PAY))  # uzilgach kabinet yopiq
    assert BotLink.objects.get(account__chat_id=7).is_active is False


def test_unlinked_user_gets_help_and_menu_beats_referrer_step(env, api, refs, on):  # noqa: F811
    assert "rasmiy boti" in text(bot.handle_message(8, DUE))
    lead = make_lead(env, refs, api)
    acc = BotAccount.objects.create(chat_id=9, state={"step": "referrer", "lead": str(lead.pk)})
    link_phone(lead.student, "901233323", 9)
    r = bot.handle_message(9, PAY)  # suhbat qadami (ism kutilmoqda) paytida ham menyu tugmasi ishlaydi
    assert "To'lovlar" in text(r)
    acc.refresh_from_db()
    assert acc.state.get("step") == "referrer"

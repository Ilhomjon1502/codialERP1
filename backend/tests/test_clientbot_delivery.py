"""Mijozlar boti B2: bot yoki SMS, sinov darsi xabari, ulanish eslatmasi, qo'lda to'lov eslatmasi botga."""

import datetime

import pytest
from django.utils import timezone

from apps.calls import auto_sms
from apps.calls.models import SmsMessage, SmsRule
from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, BotInvite, BotLink, ClientOutbox
from tests.test_clientbot import make_lead, on  # noqa: F401 — fixtures
from tests.test_sms_auto import env, refs  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
R = SmsRule.Key
Role = BotInvite.Role


def link_phone(student, phone, chat):
    """Talaba + raqamni botga ulangan holatga keltiradi (SMS'dagi kod orqali ulanishning o'zi)."""
    acc, _ = BotAccount.objects.get_or_create(chat_id=chat)
    inv = bot.invite_for(student, phone)
    return BotLink.objects.create(account=acc, student=student, invite=inv, phone=phone, role=inv.role or Role.STUDENT)


def ago(days):
    return timezone.now() - datetime.timedelta(days=days)


def test_linked_numbers_get_bot_message_instead_of_sms(env, on):  # noqa: F811
    env["enable"](R.CONTRACT)
    st = env["student"](1)
    link_phone(st, st.phone1, 10)
    link_phone(st, st.parent.phone, 11)
    c = env["contract"](st)
    auto_sms.contract_created(c)
    sms_rows = SmsMessage.objects.all()
    assert [m.phone for m in sms_rows] == [st.phone2]  # faqat ulanmagan raqamga SMS, oxirida bot havolasi
    assert "t.me/CodialTestBot?start=" in sms_rows[0].text
    out = ClientOutbox.objects.order_by("account__chat_id")
    assert [(o.account.chat_id, o.phone, o.kind) for o in out] == [(10, st.phone1, "Shartnoma"), (11, st.parent.phone, "Shartnoma")]
    assert out[0].text == "Muhsinjon Kompyuter savodxonligi 192 guruhiga qo&#x27;shildingiz." and out[0].contract == c and out[0].student == st
    auto_sms.contract_created(c)  # takror — na SMS, na bot
    assert SmsMessage.objects.count() == 1 and ClientOutbox.objects.count() == 2


def test_no_duplicate_sms_after_bot_delivery_even_if_unlinked(env, on):  # noqa: F811
    env["enable"](R.CONTRACT)
    st = env["student"](2)
    ln = link_phone(st, st.phone1, 20)
    c = env["contract"](st)
    auto_sms.contract_created(c)
    BotLink.objects.filter(pk=ln.pk).update(is_active=False)  # /stop
    auto_sms.contract_created(c)
    assert not SmsMessage.objects.filter(phone=st.phone1).exists()  # bot orqali ketgan voqea SMS bo'lib qayta ketmaydi


def test_no_device_still_delivers_to_linked_numbers(env, on):  # noqa: F811
    env["enable"](R.CONTRACT)
    st = env["student"](3)
    link_phone(st, st.phone1, 30)
    link_phone(st, st.phone2, 31)
    link_phone(st, st.parent.phone, 32)
    env["device"].delete()
    auto_sms.contract_created(env["contract"](st))
    assert ClientOutbox.objects.count() == 3 and not SmsMessage.objects.exists()


def test_blocked_account_falls_back_to_sms(env, on):  # noqa: F811
    env["enable"](R.CONTRACT)
    st = env["student"](4)
    link_phone(st, st.phone1, 40)
    BotAccount.objects.filter(chat_id=40).update(blocked=True)
    auto_sms.contract_created(env["contract"](st))
    assert SmsMessage.objects.filter(phone=st.phone1).exists() and not ClientOutbox.objects.exists()


def test_demo_attended_message_once_per_lead(env, api, refs, on):  # noqa: F811
    env["enable"](R.DEMO)
    lead = make_lead(env, refs, api)
    c = api(env["user"])
    r = c.patch(f"/api/v1/leads/{lead.pk}/", {"status": "4"}, format="json")
    assert r.status_code == 200, r.content
    msgs = SmsMessage.objects.filter(kind="Sinov darsi")
    assert msgs.count() == 2
    assert all(m.text.startswith("Assalomu alaykum! Sinov darsimizga qatnashganingiz uchun rahmat.") and "t.me/" in m.text for m in msgs)
    c.patch(f"/api/v1/leads/{lead.pk}/", {"status": "3"}, format="json")
    c.patch(f"/api/v1/leads/{lead.pk}/", {"status": "4"}, format="json")
    assert SmsMessage.objects.filter(kind="Sinov darsi").count() == 2  # qayta o'tganda takrorlanmaydi


def test_demo_attended_goes_to_bot_for_linked(env, api, refs, on):  # noqa: F811
    env["enable"](R.DEMO)
    lead = make_lead(env, refs, api)
    link_phone(lead.student, "901233323", 50)
    api(env["user"]).patch(f"/api/v1/leads/{lead.pk}/", {"status": "4"}, format="json")
    assert ClientOutbox.objects.filter(kind="Sinov darsi", account__chat_id=50).count() == 1
    assert list(SmsMessage.objects.values_list("phone", flat=True)) == ["911112233"]


def test_bot_reminder_schedule_limit_and_exclusions(env, on):  # noqa: F811
    rule = env["enable"](R.BOT_REMINDER)
    st = env["student"](5)
    env["contract"](st)
    inv = bot.invite_for(st, st.phone1)  # SMS yuborilmagan/ulanmagan taklif
    quiet = env["student"](6)  # faol shartnomasi ham, ochiq lidi ham yo'q
    bot.invite_for(quiet, quiet.phone1)
    today = timezone.localdate()
    assert auto_sms.run_rule(rule, today) == 1
    m = SmsMessage.objects.get(kind="Bot taklifi")
    assert m.phone == st.phone1 and m.text.startswith("Codial o'quv markazi xabarlari Telegram botda ham keladi") and f"start={inv.code}" in m.text
    inv.refresh_from_db()
    assert inv.reminders == 1 and inv.last_reminded_at
    assert auto_sms.run_rule(rule, today) == 0  # 7 kun o'tmagan
    for n in (2, 3):
        BotInvite.objects.filter(pk=inv.pk).update(last_reminded_at=ago(8))
        assert auto_sms.run_rule(rule, today) == 1
        assert BotInvite.objects.get(pk=inv.pk).reminders == n
    BotInvite.objects.filter(pk=inv.pk).update(last_reminded_at=ago(8))
    assert auto_sms.run_rule(rule, today) == 0  # jami 3 marta
    assert SmsMessage.objects.filter(kind="Bot taklifi").count() == 3


def test_bot_reminder_skips_linked_and_inactive(env, on):  # noqa: F811
    rule = env["enable"](R.BOT_REMINDER)
    st = env["student"](7)
    env["contract"](st)
    link_phone(st, st.phone1, 70)
    ended = env["student"](8)
    env["contract"](ended, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1))
    bot.invite_for(ended, ended.phone1)
    assert auto_sms.run_rule(rule, timezone.localdate()) == 0


def test_reminder_counts_open_lead_only(env, api, refs, on):  # noqa: F811
    rule = env["enable"](R.BOT_REMINDER)
    lead = make_lead(env, refs, api)
    inv = bot.invite_for(lead.student, "901233323")
    assert auto_sms.run_rule(rule, timezone.localdate()) == 1 and BotInvite.objects.get(pk=inv.pk).reminders == 1
    api(env["user"]).patch(f"/api/v1/leads/{lead.pk}/", {"status": "6"}, format="json")
    BotInvite.objects.filter(pk=inv.pk).update(last_reminded_at=ago(8))
    assert auto_sms.run_rule(rule, timezone.localdate()) == 0  # lid yopilgan


def test_manual_dues_go_to_bot_for_linked_numbers(env, on, api):  # noqa: F811
    st = env["student"](9)
    c = env["contract"](st)
    link_phone(st, st.phone1, 90)
    body = {"contracts": [str(c.pk)], "month": "2026-11", "text": "{talaba}: {summa} so'm"}
    pv = api(env["user"]).post("/api/v1/sms/dues/", {**body, "preview": True}, format="json").data
    assert pv["messages"] == 2 and pv["bot_messages"] == 1
    r = api(env["user"]).post("/api/v1/sms/dues/", body, format="json")
    assert r.status_code == 201 and r.data["messages"] == 2 and r.data["bot_messages"] == 1
    o = ClientOutbox.objects.get()
    assert o.kind == "To'lov eslatmasi" and o.account.chat_id == 90 and "1 300 000" in o.text
    assert set(SmsMessage.objects.values_list("phone", flat=True)) == {st.phone2, st.parent.phone}
    again = api(env["user"]).post("/api/v1/sms/dues/", body, format="json").data
    assert again["messages"] == 0 and again["bot_messages"] == 0 and again["skipped_sent"] == 3  # botga ketgani ham «olgan» hisoblanadi


def test_bot_messages_api_and_summary(env, api, on):  # noqa: F811
    env["enable"](R.CONTRACT)
    st = env["student"](5)
    link_phone(st, st.phone1, 100)
    auto_sms.contract_created(env["contract"](st))
    bot.send_pending(sender=lambda *a: None)
    c = api(env["user"])
    r = c.get("/api/v1/bot-messages/?status=sent").json()
    assert r["count"] == 1 and r["results"][0]["student_name"] == st.full_name and r["results"][0]["kind"] == "Shartnoma"
    s = c.get("/api/v1/bot-links/summary/").json()
    assert s["messages_sent"] == 1 and s["messages_sent_30d"] == 1 and s["messages_by_kind"] == [{"kind": "Shartnoma", "count": 1}]

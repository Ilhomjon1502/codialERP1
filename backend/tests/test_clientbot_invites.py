"""Hozirgi talabalarni botga ulash: ommaviy taklif SMS'i (administrator tasdig'i bilan) va faol talabalar ro'yxati."""

import datetime

import pytest

from apps.calls.models import SmsMessage
from apps.clientbot import services as bot
from apps.clientbot.models import BotInvite
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
URL = "/api/v1/bot-students/invite/"
TEXT = "Salom {ism}! Codial boti ishga tushdi, ulaning:"


def setup_students(env):  # noqa: F811
    """a: faol (3 raqam), b: faol (1-telefon ulangan), c: shartnomasi tugagan, d: shartnomasiz."""
    a, b, c, d = (env["student"](i) for i in (1, 2, 3, 4))
    env["contract"](a)
    env["contract"](b)
    link_phone(b, b.phone1, 20)
    env["contract"](c, start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 2, 1))
    return a, b, c, d


def test_preview_counts_only_active_students_and_skips_linked(env, api, on):  # noqa: F811
    a, b, c, d = setup_students(env)
    pv = api(env["user"]).post(URL, {"preview": True, "text": TEXT}, format="json").data
    assert pv["students"] == 2 and pv["numbers"] == 6 and pv["skipped_linked"] == 1 and pv["messages"] == 5
    assert pv["sample"].startswith("Salom ") and "t.me/CodialTestBot?start=XXXXXXXX" in pv["sample"] and pv["parts"] == 5 * pv["sample_parts"]
    assert not SmsMessage.objects.exists() and not BotInvite.objects.filter(student=a).exists()  # ko'rib chiqish hech narsa yaratmaydi


def test_send_queues_sms_with_own_code_once(env, api, on):  # noqa: F811
    a, b, c, d = setup_students(env)
    cl = api(env["user"])
    r = cl.post(URL, {"text": TEXT}, format="json")
    assert r.status_code == 201 and r.data["messages"] == 5 and r.data["skipped_linked"] == 1
    msgs = SmsMessage.objects.filter(kind="Bot taklifi")
    assert msgs.count() == 5 and {m.student_id for m in msgs} == {a.pk, b.pk}
    assert not msgs.filter(phone=b.phone1).exists()  # ulangan raqamga ketmaydi
    for m in msgs:
        inv = BotInvite.objects.get(student=m.student, phone=m.phone)
        assert m.text.startswith("Salom Muhsinjon! Codial boti ishga tushdi, ulaning:") and m.text.endswith(f"t.me/CodialTestBot?start={inv.code}")
        assert m.key == f"botinv:{inv.pk}" and m.status == "Navbatda" and inv.reminders == 1 and inv.last_reminded_at
    again = cl.post(URL, {"text": TEXT}, format="json").data
    assert again["messages"] == 0 and again["skipped_sent"] == 5
    assert SmsMessage.objects.filter(kind="Bot taklifi").count() == 5


def test_default_text_and_validation_and_permissions(env, api, make_user, on):  # noqa: F811
    setup_students(env)
    cl = api(env["user"])
    assert cl.post(URL, {"preview": True}, format="json").data["sample"].startswith("Codial o'quv markazining Telegram boti ishga tushdi")
    assert cl.post(URL, {"preview": True, "text": "Salom {foo}"}, format="json").status_code == 400
    assert api(make_user("USTOZ")).post(URL, {"preview": True}, format="json").status_code == 403
    assert api(make_user("MARKETOLOG")).post(URL, {"preview": True}, format="json").status_code == 403  # faqat ko'rish huquqi


def test_bot_not_configured_and_no_device(env, api, settings):  # noqa: F811
    setup_students(env)
    assert api(env["user"]).post(URL, {"preview": True}, format="json").status_code == 400  # token yo'q
    settings.CLIENT_BOT_TOKEN, settings.CLIENT_BOT_USERNAME = "1:T", "CodialTestBot"
    env["device"].delete()
    r = api(env["user"]).post(URL, {"preview": True}, format="json").data
    assert r["messages"] == 0 and r["no_device"] == ["Emirat"]


def test_students_list_and_summary_coverage(env, api, on):  # noqa: F811
    a, b, c, d = setup_students(env)
    cl = api(env["user"])
    r = cl.get("/api/v1/bot-students/").json()
    assert r["count"] == 2  # tugagan va shartnomasiz talabalar yo'q
    row = {x["id"]: x for x in r["results"]}
    assert row[str(a.pk)]["linked"] is False and row[str(b.pk)]["linked"] is True and row[str(b.pk)]["linked_roles"] == ["Talaba"]
    assert row[str(a.pk)]["contracts_info"] == ["Kompyuter savodxonligi / #192"] and len(row[str(a.pk)]["phones"]) == 3
    assert cl.get("/api/v1/bot-students/?linked=0").json()["count"] == 1
    assert cl.get("/api/v1/bot-students/?linked=1").json()["count"] == 1
    s = cl.get("/api/v1/bot-links/summary/").json()
    assert s["active_students"] == 2 and s["active_linked"] == 1
    bot.invite_for(a, a.phone1)
    assert cl.get("/api/v1/bot-students/?linked=0").json()["results"][0]["invited_at"]

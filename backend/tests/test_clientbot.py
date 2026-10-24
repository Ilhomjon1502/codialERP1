"""Mijozlar boti (B1): taklif kodlari, SMS'dagi havola, ulash, manba va tavsiya so'rovi, API."""

import pytest

from apps.calls import auto_sms
from apps.calls.models import SmsMessage, SmsRule
from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, BotConfig, BotInvite, BotLink, ClientOutbox, LeadSurvey, Referral
from apps.crm.models import Lead, Student
from apps.references.models import LeadSource
from tests.test_crm import new_lead
from tests.test_sms_auto import env, refs  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
R = SmsRule.Key
Role = BotInvite.Role


@pytest.fixture
def on(settings):
    settings.CLIENT_BOT_TOKEN, settings.CLIENT_BOT_USERNAME = "123:TEST", "CodialTestBot"


def make_lead(env, refs, api, **kw):  # noqa: F811
    r = api(env["user"]).post("/api/v1/leads/", new_lead(refs, **kw), format="json")
    assert r.status_code == 201, r.content
    return Lead.objects.get(pk=r.json()["id"])


def say(chat, text, **kw):
    return bot.handle_message(chat, text, **kw)


def texts(replies):
    return [r.text for r in replies]


# ---------- taklif ----------


def test_invite_idempotent_and_role_guess(env):  # noqa: F811
    st = env["student"](1)  # phone1 901112231, phone2 911112231, vasiy — st.parent.phone
    a = bot.invite_for(st, "901112231")
    assert bot.invite_for(st, "901112231").pk == a.pk and len(a.code) == 8
    assert a.role == Role.STUDENT
    assert bot.invite_for(st, "911112231").role == ""  # 2-telefon — ulanganda so'raladi
    assert bot.invite_for(st, st.parent.phone).role == Role.GUARDIAN
    assert len({i.code for i in BotInvite.objects.all()}) == 3


def test_sms_gets_own_link_per_number_only_when_bot_configured(env, api, refs, settings):  # noqa: F811
    env["enable"](R.LEAD)
    make_lead(env, refs, api)
    assert set(SmsMessage.objects.values_list("text", flat=True)) == {"Codialga xush kelibsiz, AyTi ta'limini biz bilan o'rganing!"}
    assert not BotInvite.objects.exists()  # bot sozlanmagan — havola ham, kod ham yo'q


def test_lead_sms_contains_link_and_code_per_phone(env, api, refs, on):  # noqa: F811
    env["enable"](R.LEAD)
    make_lead(env, refs, api)
    msgs = {m.phone: m for m in SmsMessage.objects.all()}
    assert set(msgs) == {"901233323", "911112233"}
    for phone, m in msgs.items():
        inv = BotInvite.objects.get(phone=phone)
        assert m.text.endswith(f" Telegram bot: t.me/CodialTestBot?start={inv.code}") and m.parts == 1
    assert len(set(BotInvite.objects.values_list("code", flat=True))) == 2


def test_no_link_when_disabled_or_already_linked(env, api, refs, on):  # noqa: F811
    env["enable"](R.LEAD)
    BotConfig.objects.create(branch=env["branch"], invite_in_sms=False)
    make_lead(env, refs, api)
    assert not any("t.me" in t for t in SmsMessage.objects.values_list("text", flat=True))
    BotConfig.objects.update(invite_in_sms=True)
    st = env["student"](2)
    acc = BotAccount.objects.create(chat_id=1)
    inv = bot.invite_for(st, "901112232")
    BotLink.objects.create(account=acc, student=st, invite=inv, phone="901112232", role=Role.STUDENT)
    assert bot.invite_suffix(st, "901112232", env["branch"]) == ""
    assert "t.me" in bot.invite_suffix(st, "911112232", env["branch"])


def test_contract_sms_gets_link_and_preview_notes_it(env, on):  # noqa: F811
    rule = env["enable"](R.CONTRACT)
    c = env["contract"](env["student"](3))
    auto_sms.contract_created(c)
    assert SmsMessage.objects.count() == 3 and all("t.me/CodialTestBot?start=" in m.text for m in SmsMessage.objects.all())
    pv = auto_sms.preview(rule)
    assert "t.me/CodialTestBot?start=XXXXXXXX" in pv["sample"] and "avtomatik qo'shiladi" in pv["note"]


# ---------- ulash ----------


def test_link_student_asks_source_and_keeps_admin_source(env, api, refs, on):  # noqa: F811
    lead = make_lead(env, refs, api)
    inv = bot.invite_for(lead.student, "901233323")
    r = say(500, f"/start {inv.code}", username="ali", first_name="Ali")
    assert "ulandingiz" in r[0].text and "qayerdan" in r[1].text
    ln = BotLink.objects.get(account__chat_id=500)
    assert ln.student == lead.student and ln.role == Role.STUDENT and ln.is_active
    pairs = [b["text"] for row in r[1].markup["inline_keyboard"] for b in row]
    assert "Instagram" in pairs
    ans, rep = bot.handle_callback(500, f"src:{refs['source'].pk}")
    assert ans == "✅" and "Rahmat" in rep[-1].text
    s = LeadSurvey.objects.get(lead=lead)
    assert s.source == refs["source"] and Lead.objects.get(pk=lead.pk).source == refs["source"]
    assert BotAccount.objects.get(chat_id=500).state == {}
    # ikkinchi marta so'ralmaydi
    inv2 = bot.invite_for(lead.student, "911112233")
    r2 = say(501, inv2.code)  # kod /start siz ham qabul qilinadi; 2-telefon — kimligi so'raladi
    assert "kimsiz" in r2[0].text
    _, rep = bot.handle_callback(501, f"rl:S:{inv2.pk}")
    assert not any("qayerdan" in r.text for r in rep) and BotAccount.objects.get(chat_id=501).state == {}


def test_ambiguous_phone_asks_role(env, api, refs, on):  # noqa: F811
    lead = make_lead(env, refs, api)
    inv = bot.invite_for(lead.student, "911112233")  # 2-telefon
    assert inv.role == ""
    r = say(600, f"/start {inv.code}")
    assert "kimsiz" in r[0].text and BotLink.objects.get(account__chat_id=600).role == ""
    ans, rep = bot.handle_callback(600, f"rl:G:{inv.pk}")
    assert BotLink.objects.get(account__chat_id=600).role == Role.GUARDIAN and rep[0].done
    assert "vasiysi" in rep[1].text and BotInvite.objects.get(pk=inv.pk).role == Role.GUARDIAN


def test_wrong_codes_rate_limited(on, db):
    for _ in range(bot.MAX_FAILS):
        assert "topilmadi" in say(700, "ABCDEFGH")[0].text
    assert "Juda ko'p" in say(700, "ABCDEFGH")[0].text
    assert "tanlanmagan" not in say(701, "salom")[0].text and "8 belgili" in say(701, "salom")[0].text


def test_invite_limited_to_three_accounts_and_stop(env, api, refs, on):  # noqa: F811
    lead = make_lead(env, refs, api)
    inv = bot.invite_for(lead.student, "901233323")
    for chat in (1, 2, 3):
        assert "ulandingiz" in say(chat, f"/start {inv.code}")[0].text
    assert "cheklovga" in say(4, f"/start {inv.code}")[0].text
    assert "ulandingiz" in say(1, f"/start {inv.code}")[0].text  # mavjud akkaunt qayta ulana oladi
    assert "uzildi" in say(1, "/stop")[0].text
    assert not BotLink.objects.get(account__chat_id=1).is_active
    assert "ulandingiz" in say(1, f"/start {inv.code}")[0].text and BotLink.objects.get(account__chat_id=1).is_active


def test_guardian_linked_to_two_children(env, on):  # noqa: F811
    a, b = env["student"](5), env["student"](6)
    for st in (a, b):
        r = say(800, bot.invite_for(st, st.parent.phone).code)
        assert "vasiysi" in r[0].text
    assert BotLink.objects.filter(account__chat_id=800, role=Role.GUARDIAN).count() == 2
    assert "Muhsinjon" in say(800, "salom")[0].text


# ---------- tavsiya ----------


def test_referral_flow_finds_student_with_contract(env, api, refs, on):  # noqa: F811
    friend = Student.objects.get(pk=env["contract"](env["student"](7)).student_id)  # shartnomasi bor
    nocontract = env["student"](8)
    tan = LeadSource.objects.create(name="Tanishlardan eshitdim")
    lead = make_lead(env, refs, api)
    inv = bot.invite_for(lead.student, "901233323")
    say(900, inv.code)
    ans, rep = bot.handle_callback(900, f"src:{tan.pk}")
    assert "ism va familiya" in rep[-1].text
    r = say(900, "muhsinjon karimov7")  # katta-kichik harf farqsiz; ikki so'z bir talabaning ism va familiyasida
    pairs = {b["text"]: b["callback_data"] for row in r[0].markup["inline_keyboard"] for b in row}
    assert pairs[f"{friend.first_name} {friend.last_name}"] == f"rf:{friend.pk}" and pairs["Bu ro'yxatda yo'q"] == "rf:none"
    assert nocontract.last_name not in "".join(pairs)  # shartnomasi yo'q talaba tavsiya qiluvchi bo'la olmaydi
    ans, rep = bot.handle_callback(900, f"rf:{friend.pk}")
    ref = Referral.objects.get(lead=lead)
    assert ref.referrer_student == friend and ref.state == Referral.State.PENDING and ref.referrer_text == "muhsinjon karimov7"
    assert LeadSurvey.objects.get(lead=lead).source == tan and BotAccount.objects.get(chat_id=900).state == {}


def test_referral_not_in_list_stays_unmatched_and_not_self(env, api, refs, on):  # noqa: F811
    tan = LeadSource.objects.create(name="Tanish-bilish")
    lead = make_lead(env, refs, api)
    env["contract"](lead.student)  # lidning o'zi ham shartnomali bo'lsa o'zini tavsiya qila olmaydi
    say(901, bot.invite_for(lead.student, "901233323").code)
    bot.handle_callback(901, f"src:{tan.pk}")
    r = say(901, "Abdusalom")
    assert [b["text"] for row in r[0].markup["inline_keyboard"] for b in row] == ["Bu ro'yxatda yo'q"]
    bot.handle_callback(901, "rf:none")
    ref = Referral.objects.get(lead=lead)
    assert ref.state == Referral.State.UNMATCHED and ref.referrer_student is None and ref.referrer_text == "Abdusalom"


# ---------- navbat ----------


def test_send_pending_marks_sent_and_blocked(db):
    a, b = BotAccount.objects.create(chat_id=1), BotAccount.objects.create(chat_id=2)
    bot.queue(a, "salom", key="k1")
    assert bot.queue(a, "salom", key="k1") is None  # takror yo'q
    bot.queue(b, "salom")
    sent = []

    def sender(chat, text, markup):
        if chat == 2:
            raise RuntimeError("Forbidden: bot was blocked by the user")
        sent.append(chat)

    assert bot.send_pending(sender=sender) == 1 and sent == [1]
    assert ClientOutbox.objects.get(account=b).status == "failed" and BotAccount.objects.get(pk=b.pk).blocked


# ---------- API ----------


def test_api_permissions_summary_and_scope(env, api, refs, make_user, other_branch, on):  # noqa: F811
    lead = make_lead(env, refs, api)
    bot.invite_for(lead.student, "901233323")
    bot.invite_for(lead.student, "911112233")
    say(1000, bot.invite_for(lead.student, "901233323").code)
    bot.handle_callback(1000, f"src:{refs['source'].pk}")
    c = api(env["user"])
    s = c.get("/api/v1/bot-links/summary/").json()
    assert s["configured"] and s["invites"] == 2 and s["linked_invites"] == 1 and s["unlinked_invites"] == 1
    assert s["linked_students"] == 1 and s["students"] == 1 and s["surveys"] == 1 and s["surveys_same"] == 1
    assert s["survey_sources"] == [{"name": "Instagram", "count": 1}]
    assert c.get("/api/v1/bot-links/").json()["count"] == 1
    assert c.get("/api/v1/bot-invites/?linked=0").json()["count"] == 1
    assert c.get("/api/v1/bot-surveys/").json()["results"][0]["source_name"] == "Instagram"
    assert api(make_user("USTOZ")).get("/api/v1/bot-links/summary/").status_code == 403
    # boshqa filial xodimi hech narsani ko'rmaydi
    other = make_user("ADMINISTRATOR", branches=[other_branch])
    assert api(other).get("/api/v1/bot-links/").json()["count"] == 0 and api(other).get("/api/v1/bot-links/summary/").json()["invites"] == 0


def test_api_referral_bind_and_config(env, api, refs, make_user, on):  # noqa: F811
    friend = env["student"](9)
    env["contract"](friend)
    lead = make_lead(env, refs, api)
    ref = Referral.objects.create(branch=env["branch"], lead=lead, referrer_text="Muhsin")
    c = api(env["user"])
    r = c.patch(f"/api/v1/bot-referrals/{ref.pk}/", {"referrer_student": str(friend.pk)}, format="json")
    assert r.status_code == 200 and r.json()["state"] == "Kutilmoqda" and r.json()["referrer_name"] == friend.full_name
    assert c.patch(f"/api/v1/bot-referrals/{ref.pk}/", {"state": "Berildi"}, format="json").status_code == 400
    assert c.patch(f"/api/v1/bot-referrals/{ref.pk}/", {"referrer_student": str(lead.student_id)}, format="json").status_code == 400
    assert c.get("/api/v1/bot-referrals/?state=Kutilmoqda").json()["count"] == 1
    # sozlamalar
    cfg = c.get("/api/v1/bot-config/").json()
    assert len(cfg) == 1 and cfg[0]["referral_bonus"] == 75000 and cfg[0]["invite_in_sms"] is True
    assert c.patch(f"/api/v1/bot-config/{cfg[0]['id']}/", {"referral_bonus": 100000, "referral_min_percent": 30}, format="json").status_code == 200
    assert BotConfig.objects.get().referral_bonus == 100000
    assert c.patch(f"/api/v1/bot-config/{cfg[0]['id']}/", {"referral_min_percent": 150}, format="json").status_code == 400


def test_bot_section_in_role_matrix(db, make_user):
    from apps.core.permissions import can

    assert can(make_user("BOSH_MENEJER"), "clientbot", "e") and can(make_user("ADMINISTRATOR"), "clientbot", "v")
    assert not can(make_user("USTOZ"), "clientbot", "v") and not can(make_user("HISOBCHI"), "clientbot", "v")


def test_referral_source_detection_matches_real_names(db):
    def src(n):
        return LeadSource(name=n)

    assert bot.is_referral_source(src("Do'stlar (o'qiydi)")) and bot.is_referral_source(src("Doʻstlar (oʻqiydi)"))
    assert bot.is_referral_source(src("Tanishlardan eshitdim")) and bot.is_referral_source(src("Tavsiya"))
    assert not bot.is_referral_source(src("Do'stlar (o'qimaydi)")) and not bot.is_referral_source(src("Instagramdan"))

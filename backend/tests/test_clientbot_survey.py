"""Mijozlar boti B4: tamomlash/to'xtatish so'rovnomasi — yuborish, bot suhbati, xodimlarga xabar, savollar va javoblar API'si."""

import datetime

import pytest
from django.utils import timezone

from apps.clientbot import services as bot
from apps.clientbot import survey
from apps.clientbot.models import BotAccount, ClientOutbox, ExitSurvey, SurveyQuestion
from apps.notifications.models import Outbox, TelegramLink
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
D = datetime.date
TODAY = D(2026, 10, 21)


def at(h, m=0, day=TODAY):
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(h, m)), timezone.get_current_timezone())


def ended(env, i=1, reason="Moliyaviy qiyinchilik", end=None):  # noqa: F811
    end = end or D(2026, 10, 20)
    st = env["student"](i)
    return st, env["contract"](st, start_date=D(2026, 9, 1), end_date=end, stop_reason=reason)


def cb(chat, data):
    return bot.handle_callback(chat, data)


def texts(replies):
    return [r.text for r in replies]


def opts(reply):
    return {b["text"]: b["callback_data"] for row in reply.markup["inline_keyboard"] for b in row}


def test_defaults_created_once_and_split_by_flow(env, api, on):  # noqa: F811
    r = api(env["user"]).get("/api/v1/bot-questions/").json()
    assert len(r) == 7 and {q["flow"] for q in r} == {"Hammasiga", "Tamomlaganlarga", "To'xtatganlarga"}
    assert len(api(env["user"]).get("/api/v1/bot-questions/").json()) == 7
    stopped = [q.key for q in survey.questions_for(env["branch"], "To'xtatganlarga")]
    completed = [q.key for q in survey.questions_for(env["branch"], "Tamomlaganlarga")]
    assert stopped == ["reason", "teacher_rating", "return", "improve"]
    assert completed == ["course_rating", "teacher_rating", "recommend", "continue", "improve"]


def test_due_contracts_window_and_linked_only(env, on):  # noqa: F811
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    st2, c2 = ended(env, 2)  # ulanmagan
    st3, c3 = ended(env, 3, end=TODAY)  # bugun tugagan — ertasi kuni
    link_phone(st3, st3.phone1, 3)
    st4, c4 = ended(env, 4, end=TODAY - datetime.timedelta(days=15))  # oyna o'tib ketgan
    link_phone(st4, st4.phone1, 4)
    assert [x.pk for x in survey.due_contracts(TODAY)] == [c.pk]
    tomorrow = TODAY + datetime.timedelta(days=1)
    assert {x.pk for x in survey.due_contracts(tomorrow)} == {c.pk, c3.pk}


def test_tick_sends_only_in_time_window_to_all_linked_accounts(env, on):  # noqa: F811
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    link_phone(st, st.parent.phone, 2)
    assert survey.tick(at(9, 30), TODAY) == 0 and survey.tick(at(21, 0), TODAY) == 0 and not ExitSurvey.objects.exists()
    assert survey.tick(at(10, 30), TODAY) == 1
    sv = ExitSurvey.objects.get()
    assert sv.contract == c and sv.flow == "To'xtatganlarga" and sv.stop_reason == "Moliyaviy qiyinchilik" and sv.state == "Yuborildi"
    out = ClientOutbox.objects.order_by("account__chat_id")
    assert [o.account.chat_id for o in out] == [1, 2] and all(o.kind == "So'rovnoma" and o.key == f"survey:{sv.pk}" for o in out)
    assert "sizning" in out[0].text and "ning" in out[1].text and "Muhsinjon" in out[1].text and "4 ta qisqa savol" in out[0].text
    assert out[0].markup["inline_keyboard"][0][0]["callback_data"] == f"sv:go:{sv.pk}"
    assert survey.tick(at(11, 0), TODAY) == 0 and ClientOutbox.objects.count() == 2  # takror yuborilmaydi


def test_completed_flow_intro_and_questions(env, on):  # noqa: F811
    st, c = ended(env, 1, reason="Kursni tamomladi")
    link_phone(st, st.phone1, 1)
    survey.tick(at(10, 30), TODAY)
    o = ClientOutbox.objects.get()
    assert "Tabriklaymiz" in o.text and "5 ta qisqa savol" in o.text
    _, rep = cb(1, o.markup["inline_keyboard"][0][0]["callback_data"])
    assert "1/5" in rep[1].text and "Kursni 1 dan 5 gacha baholang" in rep[1].text


def test_full_stopped_flow_stores_answers_and_notifies_manager(env, make_user, django_capture_on_commit_callbacks, on):  # noqa: F811
    bm = make_user("BOSH_MENEJER")
    TelegramLink.objects.create(user=bm, chat_id=555)
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    survey.tick(at(10, 30), TODAY)
    sv = ExitSurvey.objects.get()
    ans, rep = cb(1, f"sv:go:{sv.pk}")
    assert ans == "✅" and rep[0].done and "1/4" in rep[1].text and "nima uchun" in rep[1].text
    pairs = opts(rep[1])
    assert "Moliyaviy qiyinchilik" in pairs and "✍️ Boshqa (yozaman)" in pairs and "⏭ O'tkazib yuborish" in pairs
    assert ExitSurvey.objects.get(pk=sv.pk).state == "Jarayonda"
    # 1) tanlov
    ans, rep = cb(1, pairs["Dars sifatidan qoniqmadim"])
    assert rep[0].done and "✅ Dars sifatidan qoniqmadim" in rep[0].text and "2/4" in rep[1].text and "juda yomon" in rep[1].text
    # 2) baho — eskirgan tugma (oldingi savolniki) o'tmaydi
    assert cb(1, pairs["Moliyaviy qiyinchilik"])[0] == "Bu savol allaqachon yopilgan"
    ans, rep = cb(1, "sv:a:1:4")
    assert rep[0].done and "3/4" in rep[1].text
    # 3) tanlovda matn yozish — tugma so'raladi
    assert "tugmalardan" in texts(bot.handle_message(1, "salom"))[0]
    ans, rep = cb(1, "sv:s:2")  # o'tkazib yuborildi
    assert "o'tkazib yuborildi" in rep[0].text and "4/4" in rep[1].text and "yozib yuboring" in rep[1].text
    # 4) matnli javob
    with django_capture_on_commit_callbacks(execute=True):
        done = bot.handle_message(1, "Ustoz ko'proq amaliyot bersa yaxshi bo'lardi")
    assert "Rahmat" in done[0].text
    sv.refresh_from_db()
    assert sv.state == "Tugadi" and sv.completed_at and sv.account.chat_id == 1 and sv.respondent_role == "Talaba"
    assert [(a["key"], a["answer"]) for a in sv.answers] == [("reason", "Dars sifatidan qoniqmadim"), ("teacher_rating", "4"),
                                                             ("improve", "Ustoz ko'proq amaliyot bersa yaxshi bo'lardi")]
    assert BotAccount.objects.get(chat_id=1).state == {}
    note = Outbox.objects.get(event="survey")
    assert note.chat_id == 555 and "Dars sifatidan qoniqmadim" in note.text and "Moliyaviy qiyinchilik" in note.text and "Muhsinjon" in note.text


def test_other_option_free_text_and_second_account_gets_thanks(env, on):  # noqa: F811
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    link_phone(st, st.parent.phone, 2)
    survey.tick(at(10, 30), TODAY)
    sv = ExitSurvey.objects.get()
    _, rep = cb(1, f"sv:go:{sv.pk}")
    _, rep = cb(1, opts(rep[1])["✍️ Boshqa (yozaman)"])
    assert "yozib yuboring" in rep[1].text
    r = bot.handle_message(1, "Boshqa shaharga ko'chib ketdik")
    assert "2/4" in r[0].text
    for data in ("sv:s:1", "sv:s:2", "sv:s:3"):
        cb(1, data)
    sv.refresh_from_db()
    assert sv.state == "Tugadi" and sv.answers == [{"q": str(SurveyQuestion.objects.get(key="reason").pk), "key": "reason", "question": "Kursni nima uchun to'xtatdingiz?",
                                                    "kind": "Tanlov", "answer": "Boshqa shaharga ko'chib ketdik"}]
    ans, rep = cb(2, f"sv:go:{sv.pk}")  # vasiy keyin bosdi — javob allaqachon qabul qilingan
    assert "allaqachon qabul qilingan" in rep[0].text


def test_only_linked_account_can_start_and_html_is_escaped(env, on):  # noqa: F811
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    survey.tick(at(10, 30), TODAY)
    sv = ExitSurvey.objects.get()
    BotAccount.objects.create(chat_id=99)
    assert cb(99, f"sv:go:{sv.pk}") == ("Topilmadi", [])
    cb(1, f"sv:go:{sv.pk}")
    cb(1, "sv:a:0:o")
    bot.handle_message(1, "<b>x</b> & y")
    ExitSurvey.objects.filter(pk=sv.pk).update(state="Jarayonda")
    for data in ("sv:s:1", "sv:s:2", "sv:s:3"):
        cb(1, data)
    assert ExitSurvey.objects.get(pk=sv.pk).answers[0]["answer"] == "<b>x</b> & y"  # bazada asl matn; xodimlarga xabarda escape qilinadi


def test_edited_questions_apply_to_new_surveys_only(env, api, make_user, on):  # noqa: F811
    cl = api(make_user("BOSH_MENEJER"))
    qs = cl.get("/api/v1/bot-questions/").json()
    improve = next(q for q in qs if q["key"] == "improve")
    assert cl.patch(f"/api/v1/bot-questions/{improve['id']}/", {"status": "Nofaol"}, format="json").status_code == 200
    new = cl.post("/api/v1/bot-questions/", {"branch": str(env["branch"].pk), "text": "Dars vaqti sizga qulay edimi?", "kind": "Tanlov",
                                             "options": ["Ha", "Yo'q"], "flow": "Hammasiga", "order": 95}, format="json")
    assert new.status_code == 201, new.content
    st, c = ended(env, 1)
    link_phone(st, st.phone1, 1)
    survey.tick(at(10, 30), TODAY)
    keys = [q.text for q in survey.questions_for(env["branch"], "To'xtatganlarga")]
    assert keys[-1] == "Dars vaqti sizga qulay edimi?" and not any("fikr yoki taklif" in k for k in keys)
    assert "4 ta qisqa savol" in ClientOutbox.objects.get().text


def test_questions_api_validation_and_permissions(env, api, make_user, on):  # noqa: F811
    cl = api(make_user("BOSH_MENEJER"))
    base = {"branch": str(env["branch"].pk), "text": "Yangi savol matni", "flow": "Hammasiga"}
    assert cl.post("/api/v1/bot-questions/", {**base, "kind": "Tanlov", "options": ["Faqat bitta"]}, format="json").status_code == 400
    assert cl.post("/api/v1/bot-questions/", {**base, "kind": "Tanlov", "options": [str(i) * 5 for i in range(9)]}, format="json").status_code == 400
    ok = cl.post("/api/v1/bot-questions/", {**base, "kind": "Matn", "options": ["a", "b"], "allow_other": True}, format="json")
    assert ok.status_code == 201 and ok.json()["options"] == [] and ok.json()["allow_other"] is False
    assert cl.delete(f"/api/v1/bot-questions/{ok.json()['id']}/").status_code == 204
    assert api(make_user("USTOZ")).get("/api/v1/bot-questions/").status_code == 403
    assert api(make_user("MARKETOLOG")).post("/api/v1/bot-questions/", {**base, "kind": "Matn"}, format="json").status_code == 403
    assert api(env["user"]).get("/api/v1/bot-questions/").status_code == 200  # administrator ko'radi va tahrirlaydi, qo'sha olmaydi
    assert api(env["user"]).post("/api/v1/bot-questions/", {**base, "kind": "Matn"}, format="json").status_code == 403


def test_exit_surveys_api_and_stats(env, api, on):  # noqa: F811
    for i, (reason, chat) in enumerate([("Moliyaviy qiyinchilik", 1), ("Moliyaviy qiyinchilik", 2), ("Kursni tamomladi", 3)], start=1):
        st, c = ended(env, i, reason=reason)
        link_phone(st, st.phone1, chat)
    survey.tick(at(10, 30), TODAY)
    assert ExitSurvey.objects.count() == 3
    flows = {sv.stop_reason: sv.flow for sv in ExitSurvey.objects.all()}
    assert flows["Kursni tamomladi"] == "Tamomlaganlarga"
    for chat, ans in ((1, "Moliyaviy qiyinchilik"), (2, "Vaqt to'g'ri kelmadi")):
        sv = ExitSurvey.objects.get(account__isnull=True, contract__student__bot_links__account__chat_id=chat)
        cb(chat, f"sv:go:{sv.pk}")
        opts_ = {o: f"sv:a:0:{n}" for n, o in enumerate(SurveyQuestion.objects.get(key="reason").options)}
        cb(chat, opts_[ans])
        cb(chat, "sv:a:1:4" if chat == 1 else "sv:a:1:2")
        for data in ("sv:s:2", "sv:s:3"):
            cb(chat, data)
    cl = api(env["user"])
    lst = cl.get("/api/v1/bot-exit-surveys/?state=Tugadi").json()
    assert lst["count"] == 2 and lst["results"][0]["answers"] and lst["results"][0]["course"] == "Kompyuter savodxonligi"
    assert cl.get("/api/v1/bot-exit-surveys/?flow=Tamomlaganlarga").json()["count"] == 1
    s = cl.get("/api/v1/bot-exit-surveys/stats/").json()
    assert s["sent"] == 3 and s["done"] == 2 and s["rate"] == 67
    assert {r["label"]: r["n"] for r in s["reasons"]} == {"Moliyaviy qiyinchilik": 1, "Vaqt to'g'ri kelmadi": 1}
    assert s["admin_reasons"] == [{"label": "Moliyaviy qiyinchilik", "n": 2}]
    assert s["scales"] == [{"question": "Ustozingizni 1 dan 5 gacha baholang", "avg": 3.0, "n": 2}]

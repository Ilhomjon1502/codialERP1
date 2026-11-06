"""Mijozlar boti: kurs testi (2026-11-06) — savollar, guruhga yuborish, bot suhbati, natija, vaqt tugashi, qayta topshirish, ERP API."""

import datetime
import random

import pytest
from django.utils import timezone

from apps.clientbot import quiz
from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, ClientOutbox, QuizAttempt, QuizQuestion
from apps.notifications.models import Outbox, TelegramLink
from apps.references.models import Course
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
D = datetime.date


def url(env):  # noqa: F811
    return f"/api/v1/groups/{env['group'].pk}/quiz/"


def students(env, n=2):  # noqa: F811
    out = []
    for i in range(1, n + 1):
        st = env["student"](i)
        out.append((st, env["contract"](st)))
    return out


def sent_one(env, api, chat=1):  # noqa: F811
    (st, c), = students(env, 1)
    link_phone(st, st.phone1, chat)
    r = api(env["group"].teacher).post(url(env), {}, format="json")
    assert r.status_code == 201, r.content
    return st, c, QuizAttempt.objects.get(student=st)


def run(chat, at, wrong=()):
    """Testni boshlaydi va hamma savolga javob beradi (`wrong` — xato javob beriladigan savol raqamlari, 0 dan)."""
    ans, rep = bot.handle_callback(chat, f"qz:go:{at.pk}")
    assert ans == "✅", rep
    at.refresh_from_db()
    for i, q in enumerate(at.questions):
        n = (q["correct"] + 1) % len(q["options"]) if i in wrong else q["correct"]
        ans, rep = bot.handle_callback(chat, f"qz:a:{at.pk}:{i}:{n}")
        assert ans == "✅" and rep[0].done
    at.refresh_from_db()
    return rep


def test_default_questions_seeded_once_for_literacy_course_only(env, api, make_user, on):  # noqa: F811
    cl = api(make_user("BOSH_MENEJER"))
    r = cl.get("/api/v1/bot-quiz-questions/").json()
    assert len(r) == 20 and {q["course_name"] for q in r} == {"Kompyuter savodxonligi"}
    assert {q["lesson"] for q in r} == set(range(1, 12)) and all(len(q["options"]) == 4 and q["explanation"] for q in r)
    QuizQuestion.objects.filter(pk=r[0]["id"]).update(is_deleted=True)
    assert len(cl.get("/api/v1/bot-quiz-questions/").json()) == 19  # o'chirilgani qayta yaratilmaydi
    other = Course.objects.create(name="Frontend")
    quiz.ensure_questions(other)
    assert not QuizQuestion.objects.filter(course=other).exists()


def test_pick_balances_lessons_and_snapshot_shuffles_options(env):  # noqa: F811
    course = env["course"]
    for i in range(30):
        QuizQuestion.objects.create(course=course, lesson=1 if i < 25 else 2, text=f"Savol {i}", options=["a", "b", "c", "d"], correct=i % 4)
    qs = quiz.pick(list(QuizQuestion.objects.filter(course=course)), size=10, rnd=random.Random(1))
    assert len(qs) == 10 and sum(1 for q in qs if q.lesson == 2) == 5  # 2-darsdagi 5 tasi ham kiradi
    q = qs[0]
    s = quiz.snapshot(q, random.Random(3))
    assert sorted(s["options"]) == sorted(q.options) and s["options"][s["correct"]] == q.options[q.correct]


def test_teacher_sends_to_group_only_student_accounts_get_invite(env, api, on):  # noqa: F811
    (s1, c1), (s2, c2) = students(env)
    link_phone(s1, s1.phone1, 1)  # o'quvchi
    link_phone(s1, s1.parent.phone, 2)  # vasiy — taklif olmaydi
    link_phone(s2, s2.parent.phone, 3)  # faqat vasiy ulangan — o'quvchi kutadi
    cl = api(env["group"].teacher)
    g = cl.get(url(env)).json()
    assert g["available"] and g["can_send"] and g["questions"] == 20 and [r["bot"] for r in g["rows"]] == [True, False]
    r = cl.post(url(env), {}, format="json")
    assert r.status_code == 201 and r.json() == {"sent": 1, "waiting": 1, "done": 0, "open": 0}
    out = ClientOutbox.objects.get()
    assert out.account.chat_id == 1 and out.kind == "Test" and "20 ta savol" in out.text
    assert out.markup["inline_keyboard"][0][0]["callback_data"].startswith("qz:go:")
    assert cl.post(url(env), {}, format="json").json() == {"sent": 0, "waiting": 0, "done": 0, "open": 2}  # takror yuborilmaydi
    assert QuizAttempt.objects.count() == 2 and all(a.state == "Yuborildi" for a in QuizAttempt.objects.all())
    assert cl.get(url(env)).json()["rows"][0]["attempt"]["state"] == "Yuborildi"


def test_full_run_score_review_and_notifications(env, api, django_capture_on_commit_callbacks, on):  # noqa: F811
    teacher = env["group"].teacher
    TelegramLink.objects.create(user=teacher, chat_id=777)
    st, c, at = sent_one(env, api)
    link_phone(st, st.parent.phone, 2)
    with django_capture_on_commit_callbacks(execute=True):
        rep = run(1, at, wrong={0, 5})
    assert at.state == "Tugadi" and at.score == 18 and at.total == 20 and at.percent == 90 and quiz.passed(at) and at.finished_at
    text = "\n".join(r.text for r in rep[1:])
    assert "18/20" in text and "o'tdingiz" in text and text.count("✅ ") >= 2 and "💡" in text
    assert BotAccount.objects.get(chat_id=1).state == {}
    note = Outbox.objects.get(event="quiz")
    assert note.chat_id == 777 and "18/20" in note.text and "Karimov1" in note.text
    guardian = ClientOutbox.objects.get(key=f"quiz-result:{at.pk}")
    assert guardian.account.chat_id == 2 and "18/20" in guardian.text
    assert bot.handle_callback(1, f"qz:a:{at.pk}:19:0")[0] == "Bu savol allaqachon yopilgan"
    assert "tugagan" in bot.handle_callback(1, f"qz:go:{at.pk}")[1][0].text


def test_only_student_account_can_start_and_buttons_must_be_in_order(env, api, on):  # noqa: F811
    st, c, at = sent_one(env, api)
    link_phone(st, st.parent.phone, 2)
    assert bot.handle_callback(2, f"qz:go:{at.pk}")[0] == "Topilmadi"  # vasiy topshira olmaydi
    BotAccount.objects.create(chat_id=99)
    assert bot.handle_callback(99, f"qz:go:{at.pk}")[0] == "Topilmadi"
    bot.handle_callback(1, f"qz:go:{at.pk}")
    assert bot.handle_callback(1, f"qz:a:{at.pk}:3:0")[0] == "Bu savol allaqachon yopilgan"  # 1-savolga javob berilmagan
    assert bot.handle_callback(1, f"qz:a:{at.pk}:0:9")[0] == "Bu savol allaqachon yopilgan"  # bunday variant yo'q
    r = bot.handle_message(1, "B")
    assert "harf tugmasi" in r[0].text and "1/20" in r[1].text
    ans, rep = bot.handle_callback(1, f"qz:go:{at.pk}")  # qayta bosilsa — davom etadi
    assert "Davom etamiz" in rep[0].text and "1/20" in rep[1].text


def test_timeout_finishes_with_answered_questions(env, api, django_capture_on_commit_callbacks, on):  # noqa: F811
    st, c, at = sent_one(env, api)
    bot.handle_callback(1, f"qz:go:{at.pk}")
    at.refresh_from_db()
    for i in range(3):
        bot.handle_callback(1, f"qz:a:{at.pk}:{i}:{at.questions[i]['correct']}")
    assert quiz.tick(timezone.now() + datetime.timedelta(minutes=10)) == 0
    with django_capture_on_commit_callbacks(execute=True):
        assert quiz.tick(timezone.now() + datetime.timedelta(minutes=31)) == 1
    at.refresh_from_db()
    assert at.state == "Tugadi" and at.timed_out and at.score == 3 and len(at.answers) == 3
    msgs = ClientOutbox.objects.filter(key__startswith=f"quiz-timeout:{at.pk}")
    assert msgs.exists() and "Vaqt tugadi" in msgs.first().text and "javob berilmadi" in "".join(m.text for m in msgs)
    assert BotAccount.objects.get(chat_id=1).state == {}
    late = timezone.now() + datetime.timedelta(minutes=40)
    assert quiz.answer(BotAccount.objects.get(chat_id=1), f"{at.pk}:3:0", now=late)[0] == "Bu savol allaqachon yopilgan"


def test_retake_and_cancel(env, api, make_user, on):  # noqa: F811
    st, c, at = sent_one(env, api)
    run(1, at)
    cl = api(env["group"].teacher)
    assert cl.post(url(env), {}, format="json").json()["done"] == 1  # topshirganga qayta yuborilmaydi
    r = cl.post(url(env), {"contract": str(c.pk)}, format="json")
    assert r.status_code == 201 and r.json()["sent"] == 1
    new = QuizAttempt.objects.filter(student=st).order_by("-created_at").first()
    assert new.pk != at.pk and new.state == "Yuborildi"
    assert cl.post(url(env), {"contract": str(c.pk)}, format="json").status_code == 400  # tugamagan test bor
    adm = api(env["user"])
    r = adm.post(f"/api/v1/bot-quiz-attempts/{new.pk}/cancel/")
    assert r.status_code == 200 and r.json()["state"] == "Bekor qilindi"
    assert "bekor" in bot.handle_callback(1, f"qz:go:{new.pk}")[1][0].text
    assert adm.post(f"/api/v1/bot-quiz-attempts/{at.pk}/retake/").json()["sent"] == 1


def test_permissions(env, api, make_user, on):  # noqa: F811
    students(env, 1)
    other_teacher = make_user("USTOZ")
    assert api(other_teacher).get(url(env)).status_code == 404  # boshqa ustozning guruhi ko'rinmaydi
    assert api(env["user"]).post(url(env), {}, format="json").status_code == 201  # administrator (guruhlarni tahrirlaydi)
    assert api(make_user("HISOBCHI")).post(url(env), {}, format="json").status_code == 403
    assert api(env["group"].teacher).get("/api/v1/bot-quiz-attempts/").status_code == 403  # umumiy jadval — clientbot bo'limi
    assert api(make_user("MARKETOLOG")).post("/api/v1/bot-quiz-questions/", {}, format="json").status_code == 403


def test_course_without_questions(env, api, on):  # noqa: F811
    QuizQuestion.objects.all().delete()
    env["course"].name = "Frontend"
    env["course"].save()
    students(env, 1)
    assert api(env["group"].teacher).get(url(env)).json()["available"] is False
    r = api(env["group"].teacher).post(url(env), {}, format="json")
    assert r.status_code == 400 and "savollari yo'q" in r.json()["detail"]


def test_menu_button_and_linking_later(env, api, on):  # noqa: F811
    (st, c), = students(env, 1)
    api(env["group"].teacher).post(url(env), {}, format="json")
    at = QuizAttempt.objects.get()
    ln = link_phone(st, st.phone1, 1)
    r = bot.after_link(BotAccount.objects.get(chat_id=1), ln)
    assert any("qz:go:" in str(x.markup) for x in r)  # ulanishi bilan taklif
    labels = [b["text"] for row in r[0].markup["keyboard"] for b in row]
    assert "📝 Test" in labels
    m = bot.handle_message(1, "📝 Test")
    assert m[0].markup["inline_keyboard"][0][0]["callback_data"] == f"qz:go:{at.pk}"
    run(1, at, wrong={1})
    link_phone(st, st.parent.phone, 2)
    g = bot.handle_message(2, "📝 Test")
    assert "19/20" in g[0].text and "natijalari" in g[0].text


def test_attempts_api_filters_and_stats(env, api, on):  # noqa: F811
    (s1, c1), (s2, c2) = students(env)
    link_phone(s1, s1.phone1, 1)
    link_phone(s2, s2.phone1, 2)
    api(env["group"].teacher).post(url(env), {}, format="json")
    a1, a2 = QuizAttempt.objects.get(student=s1), QuizAttempt.objects.get(student=s2)
    run(1, a1, wrong={0})
    run(2, a2, wrong=set(range(10)))
    cl = api(env["user"])
    lst = cl.get("/api/v1/bot-quiz-attempts/?state=Tugadi").json()
    assert lst["count"] == 2 and lst["results"][0]["review"] and lst["results"][0]["group_name"] == "Kompyuter savodxonligi / #192"
    assert [x["score"] for x in cl.get("/api/v1/bot-quiz-attempts/?passed=1").json()["results"]] == [19]
    assert [x["score"] for x in cl.get("/api/v1/bot-quiz-attempts/?passed=0").json()["results"]] == [10]
    s = cl.get("/api/v1/bot-quiz-attempts/stats/").json()
    assert s["sent"] == 2 and s["done"] == 2 and s["passed"] == 1 and s["avg"] == 72 and s["groups"][0]["n"] == 2
    assert s["questions"][0]["wrong"] >= 1 and sum(x["asked"] for x in s["lessons"]) == 40


def test_question_api_validation(env, api, make_user, on):  # noqa: F811
    cl = api(make_user("BOSH_MENEJER"))
    base = {"course": str(env["course"].pk), "lesson": 3, "text": "Yangi savol matni", "order": 500}
    assert cl.post("/api/v1/bot-quiz-questions/", {**base, "options": ["a"], "correct": 0}, format="json").status_code == 400
    assert cl.post("/api/v1/bot-quiz-questions/", {**base, "options": ["a", "b"], "correct": 2}, format="json").status_code == 400
    assert cl.post("/api/v1/bot-quiz-questions/", {**base, "options": ["a", "a"], "correct": 0}, format="json").status_code == 400
    r = cl.post("/api/v1/bot-quiz-questions/", {**base, "options": ["a", "b", "c"], "correct": 2}, format="json")
    assert r.status_code == 201, r.content
    assert cl.delete(f"/api/v1/bot-quiz-questions/{r.json()['id']}/").status_code == 204

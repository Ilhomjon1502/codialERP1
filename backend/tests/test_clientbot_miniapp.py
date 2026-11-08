"""Mijozlar boti Mini App'i («📚 Darslik» ilovasi, 2026-11-08): initData imzosi, ko'rinishlar, vazifa topshirish va baholash, ruxsatlar."""

import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.clientbot import miniapp, textbook
from apps.clientbot import services as bot
from apps.clientbot.models import BotAccount, LessonSubmission
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
TOKEN = "123:TEST"  # `on` fixture


def init_data(chat, token=TOKEN, age=0, tamper=False):
    fields = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": chat, "first_name": "T"}), "query_id": "AAA"}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields["user"] = json.dumps({"id": chat + 1})
    return urllib.parse.urlencode(fields)


def call(method, path, chat=None, data=None, **kw):
    c = APIClient()
    headers = {"HTTP_X_TELEGRAM_INIT_DATA": init_data(chat, **kw)} if chat is not None else {}
    return getattr(c, method)(f"/api/v1/learn/{path}", data, **headers) if method == "get" else getattr(c, method)(f"/api/v1/learn/{path}", data, format="multipart", **headers)


@pytest.fixture(autouse=True)
def sync_eval(monkeypatch):
    monkeypatch.setattr(miniapp, "ASYNC", False)

    def fake(system, prompt, attachment=None, timeout=None, **kw):
        fake.calls.append((prompt, attachment))
        return {"score": 84, "passed": True, "strengths": "Yaxshi", "mistakes": "Jiddiy kamchilik yo'q", "feedback": "Davom eting"}

    fake.calls = []
    monkeypatch.setattr("apps.clientbot.evaluator.providers.complete_json", fake)
    return fake


@pytest.fixture
def setup(env, on):  # noqa: F811
    textbook.ensure_lessons(env["course"])
    st = env["student"](1)
    env["contract"](st)
    link_phone(st, st.phone1, 1)  # o'quvchi
    link_phone(st, st.parent.phone, 2)  # vasiy
    return st


def test_init_data_is_required_valid_and_fresh(setup):  # noqa: F811
    assert call("get", "state/").status_code == 401
    assert call("get", "state/", chat=1, tamper=True).status_code == 401
    assert call("get", "state/", chat=1, age=2 * 24 * 3600).status_code == 401
    assert call("get", "state/", chat=1, token="999:OTHER").status_code == 401  # boshqa bot imzosi
    assert call("get", "state/", chat=77).status_code == 403  # botga ulanmagan akkaunt
    BotAccount.objects.create(chat_id=78)
    assert call("get", "state/", chat=78).status_code == 403
    assert call("get", "state/", chat=1).status_code == 200


def test_state_lists_lessons_and_roles(setup):  # noqa: F811
    r = call("get", "state/", chat=1).json()
    s = r["students"][0]
    assert s["role"] == "Talaba" and s["course"] == "Kompyuter savodxonligi" and len(s["lessons"]) == 12
    assert s["lessons"][0]["unlocked"] and not s["lessons"][1]["unlocked"] and s["stats"]["total"] == 12 and s["stats"]["passed"] == 0
    assert call("get", "state/", chat=2).json()["students"][0]["role"] == "Vasiy"


def test_lesson_content_and_locking(setup):  # noqa: F811
    r = call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": 1})
    j = r.json()
    assert r.status_code == 200 and j["title"] and j["summary"] and j["practice"] and j["can_submit"] and j["submissions"] == []
    locked = call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": 5})
    assert locked.status_code == 403 and locked.json()["locked"]
    assert call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": "x"}).status_code == 400
    assert call("get", "lesson/", chat=1, data={"student": "00000000-0000-0000-0000-000000000000", "n": 1}).status_code == 403
    assert call("get", "lesson/", chat=2, data={"student": str(setup.pk), "n": 1}).json()["can_submit"] is False  # vasiy topshira olmaydi


def test_submit_text_evaluates_and_updates_progress(setup, sync_eval):  # noqa: F811
    r = call("post", "submit/", chat=1, data={"student": str(setup.pk), "lesson": 1, "text": "Bajardim"})
    assert r.status_code == 201, r.content
    sub = LessonSubmission.objects.get()
    assert sub.score == 84 and sub.passed and sub.submission_type == "Matn" and sub.account.chat_id == 1
    j = call("get", f"submission/{sub.pk}/", chat=1).json()
    assert j["pending"] is False and j["final_score"] == 84 and j["strengths"] == "Yaxshi" and j["advice"] == "Davom eting"
    s = call("get", "state/", chat=1).json()["students"][0]
    assert s["lessons"][0]["passed"] and s["lessons"][0]["best"] == 84 and s["stats"]["passed"] == 1 and s["stats"]["avg"] == 84


def test_submit_file_saved_and_sent_to_ai(setup, sync_eval):  # noqa: F811
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
    f = SimpleUploadedFile("shot.png", png, content_type="image/png")
    r = call("post", "submit/", chat=1, data={"student": str(setup.pk), "lesson": 1, "file": f})
    assert r.status_code == 201, r.content
    sub = LessonSubmission.objects.get()
    assert sub.submission_type == "Rasm" and sub.file_name == "shot.png" and sub.file_path
    assert sync_eval.calls[0][1] == (png, "image/png")  # rasm turi (PNG) to'g'ri aniqlandi


def test_submit_validation_and_permissions(setup):  # noqa: F811
    base = {"student": str(setup.pk), "lesson": 1}
    assert call("post", "submit/", chat=2, data={**base, "text": "x"}).status_code == 403  # vasiy
    assert call("post", "submit/", chat=1, data=base).status_code == 400  # bo'sh
    bad = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
    assert call("post", "submit/", chat=1, data={**base, "file": bad}).status_code == 400
    big = SimpleUploadedFile("big.pdf", b"0" * (miniapp.MAX_FILE + 1), content_type="application/pdf")
    assert call("post", "submit/", chat=1, data={**base, "file": big}).status_code == 400
    assert call("post", "submit/", chat=1, data={**base, "lesson": 5, "text": "x"}).status_code == 409  # hali ochilmagan
    assert call("post", "submit/", chat=1, data={**base, "lesson": 99, "text": "x"}).status_code == 404
    assert not LessonSubmission.objects.exists()


def test_attempt_limit_and_foreign_submission_hidden(setup, sync_eval, monkeypatch):  # noqa: F811
    monkeypatch.setattr("apps.clientbot.evaluator.providers.complete_json", lambda *a, **k: {"score": 20, "passed": False, "feedback": "Yana"})
    base = {"student": str(setup.pk), "lesson": 1, "text": "x"}
    for _ in range(3):
        assert call("post", "submit/", chat=1, data=base).status_code == 201
    r = call("post", "submit/", chat=1, data=base)
    assert r.status_code == 409 and "urinish" in r.json()["detail"]
    sub = LessonSubmission.objects.first()
    BotAccount.objects.create(chat_id=50)
    other = call("get", f"submission/{sub.pk}/", chat=50)
    assert other.status_code == 403  # ulanmagan akkaunt
    j = call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": 1}).json()
    assert len(j["submissions"]) == 3 and j["can_submit"] is False


def test_stuck_evaluation_is_retried_on_poll(setup, sync_eval):  # noqa: F811
    st = setup
    lesson = textbook.lessons_for_course(setup.contracts.first().course)[0]
    sub, _ = textbook.submit_lesson_task(st, setup.contracts.first(), lesson, "Matn", content_text="x", account=BotAccount.objects.get(chat_id=1))
    assert sub.evaluated_at is None
    assert call("get", f"submission/{sub.pk}/", chat=1).json()["pending"] is True  # yangi — hali qayta urinilmaydi
    LessonSubmission.objects.filter(pk=sub.pk).update(updated_at=sub.updated_at.replace(year=2020))
    assert call("get", f"submission/{sub.pk}/", chat=1).json()["pending"] is False  # eskirgan — qayta baholandi
    assert LessonSubmission.objects.get(pk=sub.pk).score == 84


def test_bot_menu_opens_mini_app_and_chat_button(setup):  # noqa: F811
    r = bot.handle_message(1, "📚 Darslik")
    btn = r[0].markup["inline_keyboard"][0][0]
    assert btn["web_app"]["url"] == "https://test.example.uz/learn.html?v=" + miniapp.APP_VERSION and "Darslik" in btn["text"]
    assert miniapp.enabled()

"""Mini App: video, uy vazifasi va «Codial Yoz» ulanishi (2026-11-08)."""

import time
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clientbot import miniapp, textbook, yoz
from apps.clientbot.models import BotLink, CourseLesson, LessonSubmission, YozPairing
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_clientbot_delivery import link_phone
from tests.test_clientbot_miniapp import call, sync_eval  # noqa: F401 — fixtures
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
ORIGIN = "https://yoz.codialinfo.uz"


@pytest.fixture
def setup(env, on):  # noqa: F811
    textbook.ensure_lessons(env["course"])
    st = env["student"](1)
    env["contract"](st)
    link_phone(st, st.phone1, 1)  # o'quvchi
    link_phone(st, st.parent.phone, 2)  # vasiy
    return st


def hdr(token, origin=ORIGIN):
    return {"HTTP_X_YOZ_TOKEN": token, "HTTP_ORIGIN": origin}


def link_yoz(st):
    code = call("post", "yoz-code/", chat=1, data={"student": str(st.pk)}).json()["code"]
    return code, APIClient().post("/api/v1/learn/yoz/exchange/", {"code": code}, format="json", HTTP_ORIGIN=ORIGIN)


def send(token, sessions, method="post"):
    c = APIClient()
    if method == "get":
        return c.get("/api/v1/learn/yoz/sessions/", **hdr(token))
    return c.post("/api/v1/learn/yoz/sessions/", {"sessions": sessions}, format="json", **hdr(token))


def test_video_info_variants():
    v = miniapp.video_info
    assert v("") is None
    yt = v("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5")
    assert yt["kind"] == "embed" and "youtube-nocookie.com/embed/dQw4w9WgXcQ" in yt["src"]
    assert "embed/dQw4w9WgXcQ" in v("https://youtu.be/dQw4w9WgXcQ")["src"]
    assert "embed/dQw4w9WgXcQ" in v("https://youtube.com/shorts/dQw4w9WgXcQ")["src"]
    assert v("https://vimeo.com/123456")["src"] == "https://player.vimeo.com/video/123456"
    assert v("https://drive.google.com/file/d/AbC_123/view?usp=sharing")["src"] == "https://drive.google.com/file/d/AbC_123/preview"
    mp4 = "https://cdn.example.uz/videos/l1.mp4?x=1"
    assert v(mp4) == {"kind": "file", "src": mp4, "url": mp4}
    assert v("https://ilhomjon1502.github.io/Ks-darsi/")["kind"] == "link"


def test_lesson_has_video_and_homework_seeded(setup):  # noqa: F811
    CourseLesson.objects.filter(number=1).update(video_url="https://youtu.be/dQw4w9WgXcQ", homework_task="")  # eski dars: uy vazifasi bo'sh
    j = call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": 1}).json()
    assert j["video"]["kind"] == "embed"
    assert "Codial Yoz" in j["homework"]["text"] and j["homework"]["can_submit"] and j["homework"]["submissions"] == []
    assert CourseLesson.objects.exclude(homework_task="").count() == 12  # hamma 12 dars uchun uy vazifasi bor


def test_homework_submission_is_separate_and_gets_yoz_minutes(setup, sync_eval):  # noqa: F811
    base = {"student": str(setup.pk), "lesson": 1}
    assert call("post", "submit/", chat=1, data={**base, "text": "amaliyot"}).status_code == 201
    r = call("post", "submit/", chat=1, data={**base, "task": "homework", "text": "uy vazifasi"})
    assert r.status_code == 201 and r.json()["task"] == "homework" and r.json()["attempt"] == 1  # urinish raqami amaliyotdan alohida
    prompt = sync_eval.calls[-1][0]
    assert "UY VAZIFASI" in prompt and "CODIAL YOZ STATISTIKASI" in prompt and "0 daqiqa" in prompt
    j = call("get", "lesson/", chat=1, data={"student": str(setup.pk), "n": 1}).json()
    assert len(j["submissions"]) == 1 and len(j["homework"]["submissions"]) == 1 and j["homework"]["can_submit"] is False
    s = call("get", "state/", chat=1).json()["students"][0]["lessons"][0]
    assert s["passed"] and s["homework"]["passed"] and s["homework"]["best"] == 84
    assert LessonSubmission.objects.filter(task_type="Uy vazifasi").count() == 1


def test_pairing_code_rules(setup):  # noqa: F811
    r = call("post", "yoz-code/", chat=1, data={"student": str(setup.pk)})
    code = r.json()["code"]
    assert r.status_code == 201 and len(code) == 6 and r.json()["url"].endswith("/?code=" + code)
    assert call("post", "yoz-code/", chat=2, data={"student": str(setup.pk)}).status_code == 403  # vasiy ulay olmaydi
    assert call("post", "yoz-code/", data={"student": str(setup.pk)}).status_code == 401
    code, ex = link_yoz(setup)
    assert ex.status_code == 200 and ex.json()["token"] and ex.json()["name"] == "Muhsinjon" and ex["Access-Control-Allow-Origin"] == ORIGIN
    assert APIClient().post("/api/v1/learn/yoz/exchange/", {"code": code}, format="json").status_code == 400  # bir marta ishlaydi
    assert APIClient().post("/api/v1/learn/yoz/exchange/", {"code": "ZZZZZZ"}, format="json").status_code == 400
    assert APIClient().post("/api/v1/learn/yoz/exchange/", {}, format="json").status_code == 400


def test_pairing_code_expires_and_new_code_replaces_old(setup):  # noqa: F811
    old = call("post", "yoz-code/", chat=1, data={"student": str(setup.pk)}).json()["code"]
    new = call("post", "yoz-code/", chat=1, data={"student": str(setup.pk)}).json()["code"]
    assert old != new and yoz.exchange(old) is None  # yangi kod berilganda eskisi bekor
    YozPairing.objects.filter(code=new).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert yoz.exchange(new) is None


def test_sessions_saved_deduped_validated_and_summarised(setup):  # noqa: F811
    _, ex = link_yoz(setup)
    tok = ex.json()["token"]
    now_ms = int(time.time() * 1000)
    good = [{"id": f"a{i}", "at": now_ms - i * 1000, "ms": 120000, "wpm": 20 + i, "acc": 95, "stars": 2, "l": "1-1"} for i in range(3)]
    bad = [{"id": "x1", "at": now_ms, "ms": 100, "wpm": 20, "acc": 95}, {"id": "x2", "at": now_ms, "ms": 60000, "wpm": 999, "acc": 95},
           {"id": "x3", "at": now_ms, "ms": 60000, "wpm": 20, "acc": 120}, {"id": "", "at": now_ms, "ms": 60000, "wpm": 20, "acc": 90},
           {"id": "x4", "at": now_ms + 10 * 24 * 3600 * 1000, "ms": 60000, "wpm": 20, "acc": 90}, "junk"]
    r = send(tok, good + bad)
    assert r.status_code == 201 and r.json()["saved"] == 3 and r["Access-Control-Allow-Origin"] == ORIGIN
    again = send(tok, good)
    assert again.status_code == 200 and again.json()["saved"] == 0  # dublikat saqlanmaydi
    s = again.json()["summary"]
    assert s["sessions"] == 3 and s["total_min"] == 6 and s["today_min"] == 6 and s["streak"] == 1 and s["best_wpm"] == 22 and s["avg_acc"] == 95
    assert s["first_wpm"] == 22 and len(s["week"]) == 7 and s["week"][-1]["min"] == 6
    assert send(tok, None, "get").json()["summary"]["sessions"] == 3
    st = call("get", "state/", chat=1).json()["students"][0]["typing"]
    assert st["sessions"] == 3 and st["streak"] == 1  # ilovada ham ko'rinadi


def test_homework_prompt_counts_yoz_minutes(setup, sync_eval):  # noqa: F811
    _, ex = link_yoz(setup)
    send(ex.json()["token"], [{"id": "m1", "at": int(time.time() * 1000), "ms": 11 * 60000, "wpm": 25, "acc": 96, "stars": 3}])
    call("post", "submit/", chat=1, data={"student": str(setup.pk), "lesson": 1, "task": "homework", "text": "bajardim"})
    assert "11 daqiqa" in sync_eval.calls[-1][0]


def test_token_and_cors_rules(setup):  # noqa: F811
    c = APIClient()
    assert c.post("/api/v1/learn/yoz/sessions/", {"sessions": []}, format="json").status_code == 401
    assert send("bad.token", []).status_code == 401
    _, ex = link_yoz(setup)
    tok = ex.json()["token"]
    foreign = APIClient().get("/api/v1/learn/yoz/sessions/", **hdr(tok, origin="https://evil.example"))
    assert foreign.status_code == 200 and "Access-Control-Allow-Origin" not in foreign  # boshqa sayt CORS olmaydi
    pre = c.options("/api/v1/learn/yoz/sessions/", HTTP_ORIGIN=ORIGIN, HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST")
    assert pre.status_code == 204 and pre["Access-Control-Allow-Origin"] == ORIGIN and "X-Yoz-Token" in pre["Access-Control-Allow-Headers"]
    BotLink.objects.filter(account__chat_id=1).update(is_active=False)  # akkaunt endi o'quvchi sifatida ulanmagan
    assert send(tok, None, "get").status_code == 401


def test_erp_typing_list_and_detail(setup, api, make_user):  # noqa: F811
    _, ex = link_yoz(setup)
    now_ms = int(time.time() * 1000)
    send(ex.json()["token"], [{"id": "e1", "at": now_ms, "ms": 300000, "wpm": 30, "acc": 97, "stars": 3},
                              {"id": "e2", "at": now_ms - 5000, "ms": 60000, "wpm": 50, "acc": 70, "stars": 0}])
    bm = api(make_user("BOSH_MENEJER"))
    lst = bm.get("/api/v1/bot-typing/").json()
    row = lst["results"][0]
    assert lst["count"] == 1 and row["sessions"] == 2 and row["total_min"] == 6 and row["best_wpm"] == 30 and row["avg_acc"] == 84
    assert row["group"] == "Kompyuter savodxonligi / #192"
    assert bm.get(f"/api/v1/bot-typing/{row['id']}/").json()["sessions"] == 2
    assert bm.get("/api/v1/bot-typing/?q=zzz").json()["count"] == 0
    assert api(make_user("USTOZ")).get("/api/v1/bot-typing/").status_code == 403


# ---- shartnoma raqami + telefon oxirgi 4 raqami bilan kirish (2026-11-11)

def yoz_login(number, password, ip="1.1.1.1"):
    return APIClient().post("/api/v1/learn/yoz/login/", {"number": number, "password": password}, format="json", HTTP_ORIGIN=ORIGIN, REMOTE_ADDR=ip)


@pytest.fixture
def lc(env):  # noqa: F811
    from django.core.cache import cache

    cache.clear()
    st = env["student"](1)
    c = env["contract"](st)
    return st, c


def test_login_by_contract_and_phone_tail_returns_progress(lc):
    st, c = lc
    r = yoz_login(str(c.number), "2231")  # talabaning 1-telefoni; 2-telefon va vasiy ham mos
    assert r.status_code == 200 and r.json()["name"] == "Muhsinjon" and "phone" not in str(r.json())
    token = r.json()["token"]
    assert yoz_login(f" {c.number} ", "6671").status_code == 200  # vasiy telefoni
    sess = [{"id": "a", "at": int(time.time() * 1000), "ms": 5000, "wpm": 20, "acc": 95, "stars": 2, "l": "0-3"},
            {"id": "b", "at": int(time.time() * 1000), "ms": 5000, "wpm": 25, "acc": 91, "stars": 1, "l": "0-3"},
            {"id": "c", "at": int(time.time() * 1000), "ms": 5000, "wpm": 10, "acc": 80, "stars": 0, "l": "1-1"}]
    assert send(token, sess).status_code == 201  # contract tokeni bilan natija yoziladi
    # boshqa qurilmadan qayta kirsa — qayerda to'xtagani qaytadi
    p = yoz_login(str(c.number), "2231").json()["progress"]
    assert p["0-3"] == {"stars": 2, "wpm": 25, "acc": 95, "n": 2} and p["1-1"]["stars"] == 0
    assert send(token, None, "get").json()["progress"].keys() == p.keys()


def test_login_rejects_wrong_ended_and_locks(lc):
    st, c = lc
    assert yoz_login(str(c.number), "0000").status_code == 400
    assert yoz_login("999999", "2231").status_code == 400  # mavjud emas — xuddi shu xabar
    assert yoz_login(str(c.number), "22").status_code == 400
    for _ in range(4):
        yoz_login(str(c.number), "0000")
    assert yoz_login(str(c.number), "2231").status_code == 429  # 5 xatodan keyin to'g'ri parol ham o'tmaydi
    from django.core.cache import cache

    cache.clear()
    c.end_date = timezone.localdate() - timedelta(days=1)
    c.save()
    assert yoz_login(str(c.number), "2231").status_code == 400  # tugagan shartnoma


def test_contract_token_dies_when_contract_ends(lc):
    st, c = lc
    token = yoz_login(str(c.number), "2231").json()["token"]
    assert send(token, None, "get").status_code == 200
    c.end_date = timezone.localdate() - timedelta(days=1)
    c.save()
    assert send(token, None, "get").status_code == 401

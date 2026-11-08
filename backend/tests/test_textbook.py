"""Elektron darslik va amaliyotlar testlari (2026-11-08)."""

import datetime
import io
import zipfile

import openpyxl
import pytest

from apps.clientbot import evaluator, textbook
from apps.clientbot.models import BotAccount, BotInvite, BotLink, CourseLesson, LessonSubmission
from apps.education.models import Attendance
from tests.test_clientbot import on  # noqa: F401 — fixtures
from tests.test_sms_auto import env  # noqa: F401 — fixtures

pytestmark = pytest.mark.django_db
D = datetime.date


def test_default_lessons_seeded(env):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    lessons = textbook.lessons_for_course(course)
    assert len(lessons) == 12
    assert [lsn.number for lsn in lessons] == list(range(1, 13))
    assert all(lsn.title and lsn.summary and lsn.practice_task and lsn.rubric for lsn in lessons)


def test_max_unlocked_lessons_by_attendance(env):  # noqa: F811
    course = env["course"]
    st = env["student"](1)
    contract = env["contract"](st)
    group = env["group"]

    # 1. Davomat hali olinmagan bo'lsa — kamida 1-dars ochiq
    assert textbook.max_unlocked_lesson(st, contract, today=D(2026, 11, 1)) == 1

    # 2. 3 ta har xil sanadagi davomat yozuvi kiritilsa — 3-darsgacha ochiq
    for day in (2, 4, 6):
        Attendance.objects.create(
            branch=contract.branch,
            group=group,
            course=course,
            contract=contract,
            day_pattern=group.day_pattern,
            date=D(2026, 11, day),
            status="1",
            teacher=group.teacher,
        )
    assert textbook.max_unlocked_lesson(st, contract, today=D(2026, 11, 7)) == 3

    # 3. Agar shartnoma tamomlangan bo'lsa — barcha 12 dars ochiq
    contract.end_date = D(2026, 11, 5)
    contract.save(update_fields=["end_date"])
    assert textbook.max_unlocked_lesson(st, contract, today=D(2026, 11, 10)) == 12


def test_submit_lesson_task_and_evaluation(env, monkeypatch):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    st = env["student"](1)
    contract = env["contract"](st)
    lesson1 = CourseLesson.objects.get(course=course, number=1)
    lesson5 = CourseLesson.objects.get(course=course, number=5)

    # 5-dars hali ochilmagan — xato qaytaradi
    sub_fail, err = textbook.submit_lesson_task(st, contract, lesson5, LessonSubmission.SubmissionType.TEXT, content_text="Test")
    assert sub_fail is None
    assert "ochilmagan" in err

    # 1-dars ochiq — muvaffaqiyatli topshiriladi
    sub, err = textbook.submit_lesson_task(
        st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="Kompyuterim ish stoli tayyor"
    )
    assert err == ""
    assert sub.status == LessonSubmission.Status.PENDING
    assert sub.attempt == 1

    # Mock AI evaluator
    def mock_ai(system, user, attachment=None, timeout=None):
        return {
            "score": 85,
            "passed": True,
            "strengths": "Ish stoli tozalangan",
            "mistakes": "yo'q",
            "feedback": "Barakalla!",
        }

    evaluator.evaluate_submission(sub, ai_caller=mock_ai)
    sub.refresh_from_db()
    assert sub.score == 85
    assert sub.passed is True
    assert sub.status == LessonSubmission.Status.EVALUATED
    assert "Ish stoli tozalangan" in sub.feedback


def test_attempt_limits_and_teacher_reset(env):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    st = env["student"](1)
    contract = env["contract"](st)
    lesson1 = CourseLesson.objects.get(course=course, number=1)

    # 3 ta muvaffaqiyatsiz urinish
    for i in range(1, 4):
        sub, err = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text=f"Urinish {i}")
        assert err == ""
        sub.score = 40
        sub.passed = False
        sub.status = LessonSubmission.Status.RETRY if i < 3 else LessonSubmission.Status.REJECTED
        sub.save()

    # 4-urinish bloklanishi kerak
    sub_4, err = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="4-urinish")
    assert sub_4 is None
    assert "to'liq foydalandingiz" in err

    # Ustoz qo'shimcha urinish beradi
    last_sub = LessonSubmission.objects.filter(student=st, lesson=lesson1).order_by("-attempt").first()
    last_sub.max_attempts += 1
    last_sub.save(update_fields=["max_attempts"])

    # Endi 4-urinish qabul qilinadi
    sub_4, err = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="4-urinish")
    assert err == ""
    assert sub_4.attempt == 4


def test_menu_for_student_and_guardian(env):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    st = env["student"](1)
    env["contract"](st)

    acc = BotAccount.objects.create(chat_id=1111)

    # O'quvchi roli bilan ulash
    BotLink.objects.create(account=acc, student=st, role=BotInvite.Role.STUDENT, is_active=True, phone=st.phone1)
    replies_student = textbook.menu(acc, [st])
    assert len(replies_student) == 1
    # Tugmalar bo'lishi kerak
    assert "inline_keyboard" in (replies_student[0].markup or {})

    # Vasiy roli bilan ulash
    BotLink.objects.filter(account=acc, student=st).update(role=BotInvite.Role.GUARDIAN)
    replies_guardian = textbook.menu(acc, [st])
    assert len(replies_guardian) == 1
    # Matnli hisobot
    assert "Elektron darslik natijalari" in replies_guardian[0].text


def test_document_extractors():
    # 1. Word (.docx) extract
    buf_docx = io.BytesIO()
    with zipfile.ZipFile(buf_docx, "w") as z:
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:t>Sarlavha 1</w:t></w:p><w:p><w:t>Matn mazmuni</w:t></w:p></w:body></w:document>",
        )
    docx_summary = evaluator.extract_docx_summary(buf_docx.getvalue())
    assert "Sarlavha 1" in docx_summary and "Matn mazmuni" in docx_summary

    # 2. Excel (.xlsx) extract
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hisob"
    ws["A1"] = "Narx"
    ws["A2"] = 100
    ws["A3"] = 200
    ws["A4"] = "=SUM(A2:A3)"
    buf_xlsx = io.BytesIO()
    wb.save(buf_xlsx)
    xlsx_summary = evaluator.extract_excel_summary(buf_xlsx.getvalue())
    assert "Hisob" in xlsx_summary
    assert "=SUM(A2:A3)" in xlsx_summary


def test_erp_api_endpoints(env, api, make_user):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    st = env["student"](1)
    contract = env["contract"](st)
    lesson1 = CourseLesson.objects.get(course=course, number=1)

    sub, _ = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="Vazifa")
    sub.score = 50
    sub.save(update_fields=["score"])

    client = api(make_user("BOSH_MENEJER"))

    # 1. Darslar ro'yxati
    r_lessons = client.get(f"/api/v1/bot-textbook-lessons/?course={course.pk}").json()
    assert len(r_lessons) == 12

    # 2. Vazifalar ro'yxati
    r_subs = client.get(f"/api/v1/bot-lesson-submissions/?student={st.pk}").json()
    assert r_subs["count"] == 1
    assert r_subs["results"][0]["id"] == str(sub.pk)

    # 3. Ustoz baholashi
    r_grade = client.post(f"/api/v1/bot-lesson-submissions/{sub.pk}/grade/", {"score": 90, "comment": "Tuzatildi"})
    assert r_grade.status_code == 200
    assert r_grade.json()["teacher_score"] == 90
    assert r_grade.json()["final_score"] == 90

    # 4. Urinishlarni tiklash
    r_reset = client.post(f"/api/v1/bot-lesson-submissions/{sub.pk}/reset_attempts/", {"extra": 2})
    assert r_reset.status_code == 200
    assert r_reset.json()["max_attempts"] == 5


def test_extra_attempt_goes_to_latest_submission_and_validates(env, api, make_user):  # noqa: F811
    course = env["course"]
    textbook.ensure_lessons(course)
    st = env["student"](1)
    contract = env["contract"](st)
    lesson1 = CourseLesson.objects.get(course=course, number=1)
    first, _ = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="a")
    second, _ = textbook.submit_lesson_task(st, contract, lesson1, LessonSubmission.SubmissionType.TEXT, content_text="b")
    client = api(make_user("BOSH_MENEJER"))
    r = client.post(f"/api/v1/bot-lesson-submissions/{first.pk}/reset_attempts/", {"extra": 2}, format="json")
    assert r.status_code == 200 and r.json()["id"] == str(second.pk) and r.json()["max_attempts"] == 5
    assert client.post(f"/api/v1/bot-lesson-submissions/{first.pk}/reset_attempts/", {"extra": "x"}, format="json").status_code == 400
    assert client.post(f"/api/v1/bot-lesson-submissions/{first.pk}/grade/", {"score": 101}, format="json").status_code == 400
    assert api(make_user("USTOZ")).post(f"/api/v1/bot-lesson-submissions/{first.pk}/grade/", {"score": 80}, format="json").status_code == 403

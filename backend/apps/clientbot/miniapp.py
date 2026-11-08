"""Mijozlar botining Telegram Mini App'i — «📚 Darslik» ilovasi (2026-11-08, buyurtmachi so'rovi).

O'quvchi (va vasiy) bot menyusidagi tugma yoki chat menyu tugmasi orqali `frontend/learn.html` ni Telegram ichida ochadi.
Kirish parolsiz: Telegram bergan `initData` mijozlar boti tokeni bilan tekshiriladi (xodimlar Mini App'i bilan bir xil usul,
`notifications/webapp.py`), so'ng shu Telegram akkauntga bog'langan talabalar ko'rsatiladi. Sessiya va CSRF yo'q: har so'rov
`X-Telegram-Init-Data` sarlavhasi bilan imzolanadi.

Qoidalar bot bilan bir xil (`textbook.py`): darslar guruh davomatiga qarab ochiladi, 3 ta urinish, 60+ ball — o'tdi. Vazifani faqat
«O'quvchining o'zi» topshiradi, vasiy natijani ko'radi. AI baholash 10–40 soniya oladi, shuning uchun u fon oqimida bajariladi va ilova
natijani so'rab turadi (polling).
"""

import logging
import os
import re
import threading
import uuid
from pathlib import Path

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import webapp

from . import evaluator, textbook
from .models import BotAccount, BotInvite, CourseLesson, LessonSubmission

log = logging.getLogger(__name__)
Role = BotInvite.Role
ASYNC = True  # testlarda False — baholash darhol, shu oqimda bajariladi
MAX_FILE = 8 * 1024 * 1024  # nginx client_max_body_size 10m
ALLOWED = {".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image", ".pdf": "doc", ".docx": "doc", ".xlsx": "doc"}
RETRY_AFTER_S = 120  # baholash shundan ko'p kutib qolsa (jarayon o'lgan) — qayta ishga tushiriladi
APP_VERSION = "1"


def enabled():
    """Mini App faqat HTTPS manzilda ishlaydi (Telegram talabi)."""
    return bool(settings.CLIENT_BOT_TOKEN) and settings.FRONTEND_URL.startswith("https://")


def app_url():
    return f"{settings.FRONTEND_URL.rstrip('/')}/learn.html?v={APP_VERSION}"


def open_button(text="📚 Darslikni ochish"):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": app_url()}}]]}


# ---------- kirish ----------


class Unauthorized(Exception):
    def __init__(self, msg, code=401):
        super().__init__(msg)
        self.code = code


def authenticate(request):
    """Sarlavhadagi initData → BotAccount. Imzo noto'g'ri/eskirgan yoki akkaunt botga ulanmagan bo'lsa — Unauthorized."""
    raw = request.META.get("HTTP_X_TELEGRAM_INIT_DATA", "")
    try:
        user = webapp.validate(raw, token=settings.CLIENT_BOT_TOKEN)
    except webapp.InvalidInitData as e:
        raise Unauthorized(str(e)) from None
    acc = BotAccount.objects.filter(chat_id=user["id"]).first()
    if acc is None or not acc.links.filter(is_active=True).exists():
        raise Unauthorized("Telegram akkauntingiz botga ulanmagan. Botda SMS'dagi kodni yuboring.", 403)
    return acc


def linked(acc):
    """[(Student, role)] — akkauntga faol ulangan talabalar."""
    seen, out = set(), []
    for ln in acc.links.filter(is_active=True, student__is_deleted=False).select_related("student").order_by("linked_at"):
        if ln.student_id not in seen:
            seen.add(ln.student_id)
            out.append((ln.student, ln.role))
    return out


def _student_for(acc, student_id):
    for st, role in linked(acc):
        if str(st.pk) == str(student_id):
            return st, role
    raise Unauthorized("Bu talaba sizga ulanmagan", 403)


class LearnView(APIView):
    """Sessiyasiz, CSRF'siz: har so'rov `X-Telegram-Init-Data` bilan imzolanadi."""

    authentication_classes = []
    permission_classes = []

    def handle_exception(self, exc):
        if isinstance(exc, Unauthorized):
            return Response({"detail": str(exc)}, status=exc.code)
        return super().handle_exception(exc)


# ---------- ko'rinishlar ----------

_TAG = re.compile(r"<[^>]+>")


def _plain(s):
    return _TAG.sub("", s or "").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip()


def sub_payload(sub):
    ai = sub.raw_ai or {}
    pending = sub.evaluated_at is None and sub.teacher_score is None
    return {
        "id": str(sub.pk), "attempt": sub.attempt, "max_attempts": sub.max_attempts, "kind": sub.submission_type, "file_name": sub.file_name,
        "text": sub.content_text, "status": sub.status, "pending": pending, "passed": sub.passed, "score": sub.score,
        "teacher_score": sub.teacher_score, "teacher_comment": sub.teacher_comment, "final_score": sub.final_score,
        "strengths": _plain(ai.get("strengths")), "mistakes": _plain(ai.get("mistakes")), "advice": _plain(ai.get("feedback")) or (_plain(sub.feedback) if not ai else ""),
        "submitted_at": sub.submitted_at.isoformat(),
    }


def _item(p):
    lsn, latest = p["lesson"], p["latest_submission"]
    return {
        "number": lsn.number, "title": lsn.title, "unlocked": p["unlocked"], "passed": p["passed"], "best": p["best_score"],
        "attempts": p["attempts_used"], "max_attempts": p["max_attempts"], "can_submit": p["can_submit"],
        "pending": bool(latest and latest.evaluated_at is None and latest.teacher_score is None),
    }


def student_state(st, role):
    contract = textbook.active_contract_for_student(st)
    if not contract:
        return {"id": str(st.pk), "name": st.full_name, "first_name": st.first_name, "role": role, "course": "", "lessons": [], "stats": None}
    prog = textbook.student_progress(st, contract)
    items = [_item(p) for p in prog]
    scored = [i["best"] for i in items if i["best"] is not None]
    return {
        "id": str(st.pk), "name": st.full_name, "first_name": st.first_name, "role": role, "course": contract.course.name,
        "lessons": items,
        "stats": {"total": len(items), "passed": sum(1 for i in items if i["passed"]), "unlocked": sum(1 for i in items if i["unlocked"]),
                  "avg": round(sum(scored) / len(scored)) if scored else None, "pass_score": textbook.PASS_SCORE},
    }


class StateView(LearnView):
    """GET → akkauntga ulangan hamma talaba va ularning darslar holati."""

    def get(self, request):
        acc = authenticate(request)
        return Response({"name": acc.first_name, "students": [student_state(st, role) for st, role in linked(acc)]})


class LessonView(LearnView):
    """GET ?student=&n= → dars mazmuni, urinishlar tarixi."""

    def get(self, request):
        acc = authenticate(request)
        st, role = _student_for(acc, request.query_params.get("student"))
        contract = textbook.active_contract_for_student(st)
        if not contract:
            return Response({"detail": "Faol shartnoma topilmadi"}, status=404)
        try:
            n = int(request.query_params.get("n"))
        except (TypeError, ValueError):
            return Response({"detail": "Dars raqami noto'g'ri"}, status=400)
        textbook.ensure_lessons(contract.course)
        lsn = CourseLesson.objects.filter(course=contract.course, number=n, is_deleted=False, status="Faol").first()
        if not lsn:
            return Response({"detail": "Dars topilmadi"}, status=404)
        if n > textbook.max_unlocked_lesson(st, contract):
            return Response({"detail": f"{n}-dars hali ochilmagan. Guruhda dars o'tilishini kuting.", "locked": True}, status=403)
        item = next((_item(p) for p in textbook.student_progress(st, contract) if p["lesson"].pk == lsn.pk), None)
        subs = LessonSubmission.objects.filter(student=st, contract=contract, lesson=lsn, is_deleted=False).order_by("attempt")
        for s in subs:
            _maybe_retry(s)
        return Response({
            "student": str(st.pk), "role": role, "number": lsn.number, "title": lsn.title, "summary": lsn.summary, "video_url": lsn.video_url,
            "practice": lsn.practice_task, "progress": item, "can_submit": bool(item and item["can_submit"]) and role == Role.STUDENT,
            "submissions": [sub_payload(s) for s in subs][::-1],
        })


def _save_file(data, name):
    root = Path(settings.MEDIA_ROOT) / "lesson_files"
    root.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80] or "file"
    path = root / f"{uuid.uuid4().hex}_{safe}"
    path.write_bytes(data)
    return str(path)


def _run_eval(sub_id):
    close_old_connections()
    try:
        sub = LessonSubmission.objects.select_related("lesson").get(pk=sub_id)
        data = None
        if sub.file_path and os.path.exists(sub.file_path):
            with open(sub.file_path, "rb") as f:
                data = f.read()
        evaluator.evaluate_submission(sub, file_bytes=data)
    except Exception:  # noqa: BLE001 — fon oqimi yiqilsa ham jarayon to'xtamasin
        log.exception("Mini App: baholash yiqildi %s", sub_id)
    finally:
        close_old_connections()


def start_eval(sub):
    if ASYNC:
        threading.Thread(target=_run_eval, args=(str(sub.pk),), daemon=True).start()
    else:
        _run_eval(str(sub.pk))


def _maybe_retry(sub):
    """Baholash tugamagan va uzoq kutilgan bo'lsa (jarayon qayta ishga tushgan) — yana urinadi."""
    if sub.evaluated_at is None and sub.teacher_score is None and (timezone.now() - sub.updated_at).total_seconds() > RETRY_AFTER_S:
        LessonSubmission.objects.filter(pk=sub.pk).update(updated_at=timezone.now())
        start_eval(sub)


class SubmitView(LearnView):
    """POST (multipart): student, lesson (raqam), text, file → topshiriq yaratadi va baholashni boshlaydi."""

    def post(self, request):
        acc = authenticate(request)
        st, role = _student_for(acc, request.data.get("student"))
        if role != Role.STUDENT:
            return Response({"detail": "Vazifani faqat o'quvchining o'zi topshiradi. Siz natijalarni ko'rishingiz mumkin."}, status=403)
        contract = textbook.active_contract_for_student(st)
        if not contract:
            return Response({"detail": "Faol shartnoma topilmadi"}, status=404)
        try:
            n = int(request.data.get("lesson"))
        except (TypeError, ValueError):
            return Response({"detail": "Dars raqami noto'g'ri"}, status=400)
        lsn = CourseLesson.objects.filter(course=contract.course, number=n, is_deleted=False, status="Faol").first()
        if not lsn:
            return Response({"detail": "Dars topilmadi"}, status=404)
        text = str(request.data.get("text") or "").strip()[:4000]
        upload = request.FILES.get("file")
        data, name, kind = None, "", LessonSubmission.SubmissionType.TEXT
        if upload:
            ext = os.path.splitext(upload.name or "")[1].lower()
            if ext not in ALLOWED:
                return Response({"detail": "Faqat rasm (jpg, png, webp), PDF, Word (.docx) yoki Excel (.xlsx) yuboring"}, status=400)
            if upload.size > MAX_FILE:
                return Response({"detail": "Fayl hajmi 8 MB dan oshmasin"}, status=400)
            data, name = upload.read(), upload.name[:200]
            kind = LessonSubmission.SubmissionType.PHOTO if ALLOWED[ext] == "image" else LessonSubmission.SubmissionType.DOCUMENT
        if not text and data is None:
            return Response({"detail": "Matn yozing yoki fayl biriktiring"}, status=400)
        sub, err = textbook.submit_lesson_task(st, contract, lsn, kind, content_text=text, file_name=name, account=acc,
                                               file_path=_save_file(data, name) if data else "")
        if err:
            return Response({"detail": err}, status=409)
        start_eval(sub)
        return Response(sub_payload(sub), status=status.HTTP_201_CREATED)


class SubmissionView(LearnView):
    """GET <id> → topshiriq holati (natijani so'rab turish uchun)."""

    def get(self, request, pk):
        acc = authenticate(request)
        sub = LessonSubmission.objects.select_related("lesson").filter(pk=pk, is_deleted=False).first()
        if sub is None:
            return Response({"detail": "Topilmadi"}, status=404)
        _student_for(acc, sub.student_id)
        _maybe_retry(sub)
        sub.refresh_from_db()
        return Response(sub_payload(sub))


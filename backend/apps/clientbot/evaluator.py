"""Talabalar vazifalarini AI (Gemini) orqali tekshirish va baholash servisi (2026-11-08).

- Matn, skrinshot (rasm), Word (.docx), Excel (.xlsx) va PDF fayllarni tahlil qiladi.
- 100 ballik tizimda baholaydi (60+ o'tish bali).
- O'quvchiga kuchli tomonlari, xatolari va yo'naltiruvchi xulosani o'zbek tilida beradi.
"""

import io
import json
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from django.conf import settings
from django.utils import timezone

from apps.ai_assistant import providers

from .models import LessonSubmission

log = logging.getLogger(__name__)


def download_telegram_file(file_id, token=None, max_bytes=20 * 1024 * 1024):
    """Clientbot tokeni orqali Telegram'dan yuklangan fayl baytlarini oladi."""
    token = token or settings.CLIENT_BOT_TOKEN
    if not token:
        raise RuntimeError("CLIENT_BOT_TOKEN berilmagan")
    data = urllib.parse.urlencode({"file_id": file_id}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/getFile", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    if not res.get("ok"):
        raise RuntimeError(res.get("description", "Fayl ma'lumotini olib bo'lmadi"))

    path = res["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{token}/{path}"
    with urllib.request.urlopen(file_url, timeout=60) as r:
        content = r.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise RuntimeError("Fayl hajmi 20 MB dan katta")
    return content


def extract_excel_summary(file_bytes, max_cells=150):
    """Excel (.xlsx) faylidan varaqlar, kataklar va formulalarni matn ko'rinishida ajratadi."""
    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
        lines = [f"Excel hujjati: jami {len(wb.sheetnames)} ta varaq ({', '.join(wb.sheetnames)})"]
        cell_count = 0
        for sheetname in wb.sheetnames[:5]:  # ko'pi bilan 5 ta varaq
            sheet = wb[sheetname]
            lines.append(f"\nVaraq: '{sheetname}'")
            formulas = []
            values = []
            for row in sheet.iter_rows(values_only=False):
                for cell in row:
                    if cell.value is not None:
                        val_str = str(cell.value)
                        coord = cell.coordinate
                        if str(cell.value).startswith("="):
                            formulas.append(f"{coord}: {val_str}")
                        else:
                            values.append(f"{coord}={val_str[:30]}")
                        cell_count += 1
                        if cell_count >= max_cells:
                            break
                if cell_count >= max_cells:
                    break
            if formulas:
                lines.append("  Formulalar: " + "; ".join(formulas[:20]))
            if values:
                lines.append("  Qiymatlar: " + "; ".join(values[:30]))
        return "\n".join(lines)
    except Exception as e:
        log.warning("Excel tahlilida xato: %s", e)
        return f"Excel fayli (.xlsx), hajmi: {len(file_bytes)} bayt."


def extract_docx_summary(file_bytes, max_chars=3000):
    """Word (.docx) fayli ichidagi matn va sarlavhalarni ajratadi."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        # XML namespace w:
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for p in tree.findall(".//w:p", ns):
            texts = [t.text for t in p.findall(".//w:t", ns) if t.text]
            p_text = "".join(texts).strip()
            if p_text:
                paragraphs.append(p_text)
        full_text = "\n".join(paragraphs)
        return f"Word hujjati (.docx):\n{full_text[:max_chars]}"
    except Exception as e:
        log.warning("Word tahlilida xato: %s", e)
        return f"Word fayli (.docx), hajmi: {len(file_bytes)} bayt."


def evaluate_submission(submission, *, file_bytes=None, downloader=None, ai_caller=None):
    """LessonSubmission obyektini tekshiradi, ball qo'yadi va xulosa chiqaradi.

    downloader(file_id) -> bytes (testlar uchun almashtirish mumkin)
    ai_caller(system, prompt, attachment=...) -> dict (testlar uchun almashtirish mumkin)
    """
    lesson = submission.lesson
    sub_type = submission.submission_type
    attachment = None
    extracted_text = ""

    # Agar fayl yoki rasm bo'lsa, yuklab olamiz
    if submission.telegram_file_id and file_bytes is None:
        try:
            get_file = downloader or download_telegram_file
            file_bytes = get_file(submission.telegram_file_id)
        except Exception as e:
            log.warning("Faylni yuklab bo'lmadi: %s", e)

    fname = (submission.file_name or "").lower()

    if sub_type == LessonSubmission.SubmissionType.PHOTO and file_bytes:
        attachment = (file_bytes, "image/jpeg")
    elif sub_type == LessonSubmission.SubmissionType.DOCUMENT and file_bytes:
        if fname.endswith(".pdf"):
            attachment = (file_bytes, "application/pdf")
        elif fname.endswith(".xlsx") or fname.endswith(".xls"):
            extracted_text = extract_excel_summary(file_bytes)
        elif fname.endswith(".docx") or fname.endswith(".doc"):
            extracted_text = extract_docx_summary(file_bytes)
        else:
            extracted_text = f"Fayl: {submission.file_name}, hajmi: {len(file_bytes)} bayt."

    system_prompt = (
        "Sen Codial IT akademiyasining Kompyuter savodxonligi o'quv kursi bo'yicha sun'iy intellekt ustozi "
        "va baholovchisisan.\n"
        "Vazifang: O'quvchining berilgan dars mavzusi va topshirig'i bo'yicha topshirgan ishini "
        "(matn, skrinshot yoki fayl ma'lumotlarini) baholash mezonlari (rubrika) asosida tekshirish.\n\n"
        "Baholash qoidalari:\n"
        "- Ball 0 dan 100 gacha butun son.\n"
        "- 60 va undan yuqori ball — topshiriq 'O'tdi' (passed: true).\n"
        "- 60 dan past ball — 'O'tmadi' (passed: false).\n"
        "- Hech qanday boshqa format ishlatma, FAQAT quyidagi JSON formatda javob ber:\n"
        "{\n"
        '  "score": <0 dan 100 gacha butun son>,\n'
        '  "passed": <true yoki false>,\n'
        '  "strengths": "<o\'quvchi to\'g\'ri bajargan asosiy jihatlar (o\'zbek tilida)>",\n'
        '  "mistakes": "<yo\'l qo\'yilgan xatolar yoki kamchiliklar (o\'zbek tilida, bo\'lmasa \'Jiddiy kamchilik yo\'q\')>",\n'
        '  "feedback": "<o\'quvchiga yo\'naltiruvchi, samimiy va rag\'batlantiruvchi xulosa/maslahat (o\'zbek tilida)>"\n'
        "}"
    )

    user_prompt_parts = [
        f"DARS RAQAMI: {lesson.number}",
        f"MAVZU: {lesson.title}",
        f"AMALIYOT TOPSHIRIG'I:\n{lesson.practice_task}",
        f"BAHOLASH MEZONI (RUBRIKA):\n{lesson.rubric}",
        f"\nO'QUVCHINING TOPSHIRIG'I (Urinish {submission.attempt}):",
    ]

    if submission.content_text:
        user_prompt_parts.append(f"O'quvchi yozgan matn/izoh:\n{submission.content_text}")
    if extracted_text:
        user_prompt_parts.append(f"Yuklangan fayl tahlili:\n{extracted_text}")
    if attachment:
        user_prompt_parts.append("[Topshiriqqa biriktirilgan rasm/skrinshot yoki PDF ilova qilingan, uni ko'rib baholang]")

    user_prompt = "\n\n".join(user_prompt_parts)

    caller = ai_caller or providers.complete_json
    try:
        res = caller(system_prompt, user_prompt, attachment=attachment, timeout=35)
    except Exception as e:
        log.error("AI baholashda xatolik: %s", e)
        submission.status = LessonSubmission.Status.PENDING
        submission.feedback = "AI xizmati hozir band bo'lgani sababli baholash kechikmoqda. Qaytadan urinib ko'riladi."
        submission.save(update_fields=["status", "feedback", "updated_at"])
        return submission

    score = int(res.get("score") or 0)
    score = max(0, min(100, score))
    passed = bool(res.get("passed", score >= 60))

    strengths = str(res.get("strengths") or "").strip()
    mistakes = str(res.get("mistakes") or "").strip()
    advice = str(res.get("feedback") or "").strip()

    feedback_parts = []
    if strengths:
        feedback_parts.append(f"✅ <b>Yutuqlar:</b> {strengths}")
    if mistakes and mistakes.lower() != "yo'q":
        feedback_parts.append(f"⚠️ <b>Kamchiliklar:</b> {mistakes}")
    if advice:
        feedback_parts.append(f"💡 <b>Xulosa:</b> {advice}")

    full_feedback = "\n\n".join(feedback_parts) if feedback_parts else advice

    submission.score = score
    submission.passed = passed
    submission.feedback = full_feedback
    submission.raw_ai = res
    submission.evaluated_at = timezone.now()

    if passed:
        submission.status = LessonSubmission.Status.EVALUATED
    else:
        if submission.attempt < submission.max_attempts:
            submission.status = LessonSubmission.Status.RETRY
        else:
            submission.status = LessonSubmission.Status.REJECTED

    submission.save(update_fields=["score", "passed", "feedback", "raw_ai", "evaluated_at", "status", "updated_at"])
    return submission

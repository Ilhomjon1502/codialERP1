"""Kompyuter savodxonligi elektron darsligi va amaliyotlar (2026-11-08).

- 12 ta dars (o'quv reja: https://ilhomjon1502.github.io/Ks-darsi/).
- Darslar ochilishi: guruh davomatiga bog'liq (ustoz o'tgan darslar soni bo'yicha).
- Talaba topshirig'i (matn, skrinshot, fayl) AI tomonidan tekshiriladi va 100 ballik baholanadi.
- Qayta topshirish: 3 marta; undan keyin ustoz ruxsat berishi mumkin.
"""

import logging
from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from apps.education.models import Attendance, Contract
from apps.education.services import NOFAOL, period_status

from .models import CourseLesson, LessonSubmission

log = logging.getLogger(__name__)

LITERACY_COURSE = "Kompyuter savodxonligi"
PASS_SCORE = 60
MAX_ATTEMPTS = 3

KS_LESSONS = [
    (
        1,
        "Kompyuter va Windows",
        "Kompyuterning asosiy qismlari: tizim bloki, monitor, klaviatura, sichqoncha.\n"
        "Operativ xotira (RAM) — dasturlar ishlashi uchun vaqtinchalik xotira; doimiy xotira (HDD/SSD) — ma'lumotlarni doimiy saqlaydi.\n"
        "Ish stoli, vazifalar paneli, ochiq oynalar orasida tez almashish (Alt + Tab), kompyuterni qulflash (Win + L).",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "1. Ish stolidagi keraksiz belgilarni tozalang yoki tartiblang.\n"
        "2. Ish stolida o'z ism-familiyangiz bilan yangi papka oching (masalan: Ali_Valiyev).\n"
        "3. Ochiq oynalar va ish stolingiz ko'ringan skrinshotni (Win + Shift + S) rasm qilib botga yuboring.",
        "O'quvchi Windows ish stoli va oynalar skrinshotini yuborgan bo'lishi kerak. "
        "Ish stoli tartiblanganligi va o'quvchi nomidagi papka borligi tekshiriladi. 60+ ball: topshiriq bajarilgan.",
    ),
    (
        2,
        "Fayl va papkalar",
        "Fayl turlari va kengaytmalari (.docx, .xlsx, .pdf, .jpg).\n"
        "Papkalar iyerarxiyasi va to'g'ri nomlash qoidasi: Sana_Ism_Mavzu (masalan: 2026-11-08_Ali_Referat.docx).\n"
        "Maxsus taqiqlangan belgilar: / \\ ? * : < > | .\n"
        "Shift + Delete xavfi: Savatni chetlab faylni butunlay o'chiradi.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Kompyuteringizda 'Darslar' papkasi ichida 2 ta papka oching va ichiga 'Sana_Ism_Mavzu' qoidasiga mos nomlangan 2 ta fayl yarating. "
        "Papka va fayllar nomi ko'ringan skrinshotni botga yuboring.",
        "Fayl va papka nomlari qoidaga muvofiq bo'lishi kerak (sana, ism, mavzu, taqiqlangan belgilarsiz). 60+ ball: qoidaga mos nomlangan fayllar ko'ringan.",
    ),
    (
        3,
        "Tezkor tugmalar va fleshka",
        "Eng muhim tezkor tugmalar:\n"
        "Ctrl + C (nusxalash), Ctrl + V (joylashtirish), Ctrl + X (qirqish), Ctrl + Z (orqaga qaytarish), Win + Shift + S (ekranni qirqib skrinshot olish).\n"
        "Fleshkani sug'urishdan oldin 'Xavfsiz chiqarish' (Safely Remove Hardware) amalini bajarish shart — bu fayllar buzilishining oldini oladi.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Win + Shift + S orqali kompyuteringizdagi soat va sana qismini skrinshot qilib rasm sifatida yuboring.\n"
        "Xabar matnida: 1) Fleshkani nima uchun to'g'ridan-to'g'ri sug'urib bo'lmasligini; 2) Ctrl+Z nima qilishini yozing.",
        "Skrinshot mavjud bo'lishi va matnda fleshkani xavfsiz chiqarish sababi hamda Ctrl+Z vazifasi to'g'ri tushuntirilgan bo'lishi kerak.",
    ),
    (
        4,
        "Internet va qidiruv",
        "Brauzer (Chrome, Edge). Google qidiruv sirlari:\n"
        "- 'filetype:pdf' (faqat PDF fayllarni qidirish)\n"
        "- 'site:edu.uz' (faqat ma'lum sayt yoki domendan qidirish)\n"
        "- qo'shtirnoq \"aniq ibora\" va minus -so'z.\n"
        "Internetdagi ma'lumotlarning ishonchliligini kamida 2-3 ta manbada solishtirib tekshirish.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Google'da 'filetype:pdf' operatori yordamida o'zingiz xohlagan mavzuda PDF manba toping. "
        "Qidiruv satri va topilgan PDF fayllar ko'ringan skrinshotni yuboring hamda topgan faylingiz nomini matnda yozing.",
        "Google qidiruv satrida filetype:pdf (yoki shunga o'xshash qidiruv operatori) to'g'ri yozilgani va PDF natijalar chiqqani skrinshotda ko'rinishi shart.",
    ),
    (
        5,
        "Prompt va AI",
        "Sun'iy intellekt (ChatGPT, Gemini) bilan muloqot qilish: R-V-K-F formulasi:\n"
        "R — Rol (kim sifatida javob berishi kerak)\n"
        "V — Vazifa (nima qilishi kerak)\n"
        "K — Kontekst (kim uchun, qanday sharoitda)\n"
        "F — Format (jadval, ro'yxat, qisqa xulosa).\n"
        "Xavfsizlik: AI xizmatlariga bank karta raqami, SMS kodlar, shaxsiy parollar va pasport ma'lumotlarini hech qachon yozmaslik.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "R-V-K-F formulasiga amal qilgan holda tuzgan biror prompt matningizni va AI dan olgan javobingizni (matn yoki skrinshot ko'rinishida) botga yuboring.",
        "Promptda Rol, Vazifa, Kontekst va Format elementlari mavjudligi tekshiriladi. Shaxsiy nozik ma'lumotlar bo'lmasligi shart.",
    ),
    (
        6,
        "Word — hujjat yaratish",
        "Microsoft Word: matn terish, shriftlar (Times New Roman, Arial, 12-14 pt), qatorlar oralig'i (1.15).\n"
        "Sarlavhalarga stillar berish (Sarlavha 1, Sarlavha 2).\n"
        "Stillar asosida avtomatik mundarija (Table of Contents) chiqarish.\n"
        "Hujjatni boshqa qurilmalarda bir xil ko'rinishi uchun PDF formatida saqlash.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Word dasturida kamida 2 ta sarlavha va avtomatik mundarijaga ega referat yoki maqola tayyorlang. Faylni .docx yoki .pdf formatida botga yuklang.",
        "Hujjatda avtomatik mundarija (yoki sarlavha stillari qo'llanilgani) va matn to'g'ri formatlangani tekshiriladi.",
    ),
    (
        7,
        "Word + AI",
        "AI yordamida Word hujjatlarini sifatli tayyorlash: reja tuzish, matnni boyitish, imlo xatolarini tekshirish.\n"
        "Muhim qoida: AI bergan har bir fakt va manbani tekshirish (chunki AI mavjud bo'lmagan manbalarni to'qishi mumkin).\n"
        "Hujjatga jadvallar, rasmlar va adabiyotlar ro'yxatini kiritish.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "AI yordamida tayyorlangan, rejasi va jadvallari bo'lgan, rasmiylashtirilgan referat yoki maqolani (.docx fayl) yuboring.",
        "Hujjat shunchaki ko'chirilmagan, chiroyli formatlangan, jadval va tekshirilgan manbalarga ega bo'lishi kerak.",
    ),
    (
        8,
        "Excel — jadvallar va formulalar",
        "Microsoft Excel kataklari (ustun harfi + qator raqami: A1, B3).\n"
        "Ma'lumot turlari (son, matn, sana). Formulalar doim '=' belgisi bilan boshlanadi.\n"
        "Asosiy funksiyalar: =SUM(diapazon) — yig'indi, =AVERAGE(diapazon) — o'rtacha qiymat, =MIN(), =MAX(), =COUNT(). Kataklar chegarasi (Borders).",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Excelda kamida 5 qatorli jadval tuzing (masalan, tovarlar narxi yoki xarajatlar). "
        "Jami qatorida =SUM() va o'rtacha qatorida =AVERAGE() formulasini yozing. .xlsx faylni botga yuboring.",
        "Faylda =SUM va =AVERAGE (yoki boshqa standart formulalar) to'g'ri ishlatilganligi va jadval chiroyli formatlanganligi tekshiriladi.",
    ),
    (
        9,
        "Excel + AI",
        "Excelda shartli funksiyalar: =IF(shart, to'g'ri_qiymat, noto'g'ri_qiymat) (masalan: =IF(C2>=60, \"O'tdi\", \"Yiqildi\")).\n"
        "Mutlaq havola ($ belgisi, $F$1): formulani boshqa kataklarga nusxalagandagi havola o'zgarmasligini ta'minlaydi (F4 tugmasi).",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Excelda o'quvchilar yoki tovarlar ro'yxatini tuzing. =IF() formulasi va kamida bitta $ belgili mutlaq havolani qo'llang. .xlsx faylni yuboring.",
        "Jadvalda =IF sharti va $ mutlaq havola to'g'ri qo'llanilgani tekshiriladi.",
    ),
    (
        10,
        "Taqdimot (PowerPoint)",
        "PowerPoint asoslari. Yaxshi taqdimot qoidalari:\n"
        "- 1 slayd = 1 ta asosiy fikr\n"
        "- 6 qatordan ko'p matn bo'lmasligi\n"
        "- katta o'qiladigan shriftlar, fon va matn kontrasti\n"
        "- ortiqcha animatsiya va noo'rin bezaklardan qochish.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "O'zingiz qiziqqan mavzuda 3-5 slayddan iborat chiroyli va qoidalarga mos taqdimot tayyorlang. .pptx yoki PDF faylni botga yuklang.",
        "Slaydlar soni (kamida 3 ta), matn hajmi qisqaligi, rasmlar va dizayn qoidalariga rioya qilinganligi baholanadi.",
    ),
    (
        11,
        "Bulut va xavfsizlik",
        "Bulutli xizmatlar (Google Drive, OneDrive).\n"
        "Fayllarni ulashish huquqlari (ko'rish, sharhlash, tahrirlash).\n"
        "Kuchli parollar: kamida 12 belgi, so'zlar birikmasi va raqamlar (masalan: Olma-Daryo-Kitob-47).\n"
        "Fishing xabarlari (SMS yoki havolalar orqali aldash) va ikki bosqichli himoya (2FA).",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "1) Google Drive'ga ixtiyoriy fayl yuklab, unga 'Ko'rish huquqi' (Viewer) bilan havola oling va havolani botga yuboring.\n"
        "2) Xavfsiz parol namunasini matnda yozing.",
        "Google Drive havolasi to'g'ri formatda berilgani va xavfsiz parol namunasi kiritilgani tekshiriladi.",
    ),
    (
        12,
        "Yakuniy loyiha",
        "Kurs davomida o'rganilgan barcha amaliy bilimlarni jamlovchi yakuniy loyiha: "
        "kompyuterda fayllarni to'g'ri saqlash, Word'da rasmiylashtirish, Excel'da hisob-kitob qilish "
        "va natijani taqdimot yoki xulosa ko'rinishida topshirish.",
        "https://ilhomjon1502.github.io/Ks-darsi/",
        "Kurs yakuniy loyihasi sifatida o'zingiz tanlagan mavzudagi to'liq Word hujjati, "
        "Excel jadvali yoki Taqdimot faylingizni botga yuklang va qisqa xulosa yozing.",
        "O'quvchining kurs davomida olgan bilimlarini to'liq va mustaqil qo'llay olgani yakuniy kompleks ball bilan baholanadi.",
    ),
]


def ensure_lessons(course):
    """Kurs uchun 12 ta dars mavzusi bo'lmasa — yaratadi."""
    if not course:
        return
    existing = set(CourseLesson.all_objects.filter(course=course).values_list("number", flat=True))
    to_create = []
    for num, title, summary, v_url, task, rubric in KS_LESSONS:
        if num not in existing:
            to_create.append(
                CourseLesson(
                    course=course,
                    number=num,
                    title=title,
                    summary=summary,
                    video_url=v_url,
                    practice_task=task,
                    rubric=rubric,
                    order=num * 10,
                )
            )
    if to_create:
        CourseLesson.objects.bulk_create(to_create)


def lessons_for_course(course):
    ensure_lessons(course)
    return list(CourseLesson.objects.filter(course=course, status="Faol").order_by("number"))


def active_contract_for_student(student, today=None):
    """Talabaning KS kursi bo'yicha faol yoki so'nggi shartnomasi."""
    today = today or timezone.localdate()
    contracts = list(
        Contract.objects.filter(
            student=student,
            course__name__icontains=LITERACY_COURSE,
            is_deleted=False,
        ).select_related("course", "group", "branch").order_by("-start_date")
    )
    if not contracts:
        # kurs nomi aynan mos kelmasa, istalgan faol shartnomasini tekshiramiz
        contracts = list(
            Contract.objects.filter(student=student, is_deleted=False)
            .select_related("course", "group", "branch")
            .order_by("-start_date")
        )
    for c in contracts:
        if period_status(c.start_date, c.end_date, today) != NOFAOL:
            return c
    return contracts[0] if contracts else None


def max_unlocked_lesson(student, contract, today=None):
    """Guruh davomatiga qarab qaysi darsgacha ochiqligini aniqlaydi (C qarori)."""
    if not contract:
        return 1
    today = today or timezone.localdate()

    # Kurs tamomlangan bo'lsa barcha 12 dars ochiq
    if period_status(contract.start_date, contract.end_date, today) == NOFAOL:
        return 12

    if not contract.group_id:
        return 1

    # Guruhda shu kungacha o'tilgan davomat kunlari soni
    taught_dates_count = (
        Attendance.objects.filter(
            group_id=contract.group_id,
            is_deleted=False,
            status__in=["1", "0", "X"],
        )
        .values("date")
        .distinct()
        .count()
    )

    # Kamida 1-dars doim ochiq; eng ko'pi bilan 12
    return max(1, min(taught_dates_count, 12))


def student_progress(student, contract, today=None):
    """Talabaning barcha darslar bo'yicha holati:
    [
      {
        'lesson': CourseLesson,
        'unlocked': bool,
        'passed': bool,
        'best_score': int or None,
        'attempts_used': int,
        'max_attempts': int,
        'can_submit': bool,
        'latest_submission': LessonSubmission or None,
      },
      ...
    ]
    """
    if not contract:
        return []
    course = contract.course
    lessons = lessons_for_course(course)
    unlocked_limit = max_unlocked_lesson(student, contract, today)

    subs = list(
        LessonSubmission.objects.filter(
            student=student,
            contract=contract,
            is_deleted=False,
        ).select_related("lesson").order_by("submitted_at")
    )
    by_lesson = defaultdict(list)
    for s in subs:
        by_lesson[s.lesson_id].append(s)

    out = []
    for lsn in lessons:
        unlocked = lsn.number <= unlocked_limit
        lsn_subs = by_lesson.get(lsn.id, [])
        latest = lsn_subs[-1] if lsn_subs else None
        best = max((s.final_score for s in lsn_subs if s.final_score is not None), default=None)
        passed = any(s.passed for s in lsn_subs)
        attempts = len(lsn_subs)
        allowed = latest.max_attempts if latest else MAX_ATTEMPTS
        can_sub = unlocked and not passed and attempts < allowed

        out.append({
            "lesson": lsn,
            "unlocked": unlocked,
            "passed": passed,
            "best_score": best,
            "attempts_used": attempts,
            "max_attempts": allowed,
            "can_submit": can_sub,
            "latest_submission": latest,
        })
    return out


def submit_lesson_task(
    student,
    contract,
    lesson,
    submission_type,
    *,
    content_text="",
    telegram_file_id="",
    file_name="",
    file_path="",
    account=None,
    today=None,
):
    """Vazifani qabul qilish va yangi LessonSubmission yaratish.
    Qaytaradi: (submission, error_msg)
    """
    unlocked_limit = max_unlocked_lesson(student, contract, today)
    if lesson.number > unlocked_limit:
        return None, f"{lesson.number}-dars hali ochilmagan. Guruhda dars o'tilishini kuting."

    existing_subs = list(
        LessonSubmission.objects.filter(
            student=student,
            contract=contract,
            lesson=lesson,
            is_deleted=False,
        ).order_by("attempt")
    )
    latest = existing_subs[-1] if existing_subs else None
    allowed_attempts = latest.max_attempts if latest else MAX_ATTEMPTS
    next_attempt = len(existing_subs) + 1

    if len(existing_subs) >= allowed_attempts:
        return None, f"Bu dars uchun ruxsat etilgan {allowed_attempts} ta urinishdan to'liq foydalandingiz. Ustozingiz bilan bog'laning."

    with transaction.atomic():
        sub = LessonSubmission.objects.create(
            branch=contract.branch,
            student=student,
            contract=contract,
            lesson=lesson,
            account=account,
            attempt=next_attempt,
            max_attempts=allowed_attempts,
            submission_type=submission_type,
            content_text=content_text,
            telegram_file_id=telegram_file_id,
            file_name=file_name,
            file_path=file_path,
            status=LessonSubmission.Status.PENDING,
        )
    return sub, ""


def menu(acc, students):
    """Menyudagi '📚 Darslik' tugmasi bosilganda:
    - O'quvchiga: 12 ta dars ro'yxati (ochilganlari, ballari, qulflanganlari).
    - Vasiyga: farzandining darslikdagi ballari va o'zlashtirish holati.
    """
    from html import escape

    from . import miniapp
    from .models import BotInvite
    from .services import Reply, buttons

    if miniapp.enabled():  # 2026-11-08: darslik — Telegram Mini App; chat ro'yxati faqat zaxira (HTTPS yoki token yo'q bo'lsa)
        return [Reply("📚 <b>Elektron darslik</b>\nDarslar, amaliyot topshiriqlari va ballaringiz — qulay ilovada. Ochish uchun tugmani bosing 👇",
                      miniapp.open_button())]

    roles = {ln.student_id: ln.role for ln in acc.links.filter(is_active=True)}
    replies = []

    for st in students:
        role = roles.get(st.pk)
        contract = active_contract_for_student(st)
        if not contract:
            replies.append(Reply(f"<b>{escape(st.first_name)}</b> uchun faol shartnoma topilmadi."))
            continue

        prog = student_progress(st, contract)
        if not prog:
            replies.append(Reply(f"<b>{escape(st.first_name)}</b> — darslik mavzulari topilmadi."))
            continue

        name = escape(st.first_name)
        if role == BotInvite.Role.GUARDIAN:
            # Vasiy uchun barcha 12 dars holati
            lines = [f"📚 <b>{name}</b> — Elektron darslik natijalari:\n"]
            for p in prog:
                lsn = p["lesson"]
                if not p["unlocked"]:
                    state_icon = "🔒"
                    extra = "hali dars o'tilmagan"
                elif p["passed"]:
                    state_icon = "✅"
                    extra = f"{p['best_score']} ball"
                elif p["attempts_used"] > 0:
                    state_icon = "🟡"
                    extra = f"{p['best_score'] or 0} ball (qayta topshirish)"
                else:
                    state_icon = "⏳"
                    extra = "topshirilmagan"
                lines.append(f"{state_icon} {lsn.number}. {escape(lsn.title)} — {extra}")
            replies.append(Reply("\n".join(lines)))
        else:
            # O'quvchining o'zi uchun tugmalar bilan
            lines = [
                f"📚 <b>{name}</b>, Kompyuter savodxonligi darsligiga xush kelibsiz!",
                "Darsni o'rganish va amaliyot topshirish uchun quyidagi mavzulardan birini tanlang:\n",
            ]
            btns = []
            for p in prog:
                lsn = p["lesson"]
                if not p["unlocked"]:
                    label = f"🔒 {lsn.number}. {lsn.title}"
                    cb_data = f"bk:lock:{lsn.number}:{st.pk}"
                elif p["passed"]:
                    label = f"✅ {lsn.number}. {lsn.title} ({p['best_score']} ball)"
                    cb_data = f"bk:l:{lsn.number}:{st.pk}"
                elif p["attempts_used"] > 0:
                    label = f"🟡 {lsn.number}. {lsn.title} ({p['best_score'] or 0})"
                    cb_data = f"bk:l:{lsn.number}:{st.pk}"
                else:
                    label = f"📖 {lsn.number}. {lsn.title}"
                    cb_data = f"bk:l:{lsn.number}:{st.pk}"
                btns.append((label, cb_data))

            reply_markup = buttons(*btns, per_row=1)
            replies.append(Reply("\n".join(lines), reply_markup))
    return replies


def lesson_view(acc, student_id, lesson_num):
    """Mavzuni ko'rish: nazariya, havola, amaliyot, holat va vazifa topshirish tugmasi."""
    from html import escape

    from apps.crm.models import Student

    from .services import Reply, buttons

    st = Student.objects.filter(pk=student_id, is_deleted=False).first()
    if not st:
        return "Talaba topilmadi", []
    contract = active_contract_for_student(st)
    if not contract:
        return "Shartnoma topilmadi", []
    course = contract.course
    ensure_lessons(course)
    lesson = CourseLesson.objects.filter(course=course, number=int(lesson_num), is_deleted=False).first()
    if not lesson:
        return "Dars topilmadi", []

    unlocked_limit = max_unlocked_lesson(st, contract)
    if lesson.number > unlocked_limit:
        return f"{lesson.number}-dars hali ochilmagan", []

    subs = list(LessonSubmission.objects.filter(student=st, contract=contract, lesson=lesson, is_deleted=False).order_by("attempt"))
    latest = subs[-1] if subs else None
    best = max((s.final_score for s in subs if s.final_score is not None), default=None)
    allowed = latest.max_attempts if latest else MAX_ATTEMPTS
    attempts_used = len(subs)
    passed = any(s.passed for s in subs)

    status_str = "Topshirilmagan"
    if passed:
        status_str = f"✅ O'tgan (Eng yaxshi ball: <b>{best}</b>/100)"
    elif attempts_used > 0:
        status_str = f"🟡 O'tmagan ({best or 0}/100, qayta urinish mumkin)"

    lines = [
        f"💻 <b>{lesson.number}-dars: {escape(lesson.title)}</b>\n",
        f"📖 <b>Nazariya:</b>\n{escape(lesson.summary)}\n",
    ]
    if lesson.video_url:
        lines.append(f"🔗 <b>Videodars / Sayt:</b> {escape(lesson.video_url)}\n")
    lines.append(f"🛠 <b>Amaliyot topshirig'i:</b>\n{escape(lesson.practice_task)}\n")
    lines.append(f"📊 <b>Holatingiz:</b> {status_str}")
    lines.append(f"Urinishlar: {attempts_used} / {allowed}")

    if latest and latest.feedback:
        lines.append(f"\n💬 <b>So'nggi AI xulosasi:</b>\n{latest.feedback}")

    row_btns = []
    can_sub = not passed and attempts_used < allowed
    if can_sub:
        btn_label = "📤 Qayta topshirish" if attempts_used > 0 else "📤 Vazifa topshirish"
        row_btns.append((btn_label, f"bk:sub:{lesson.number}:{st.pk}"))

    row_btns.append(("⬅️ Darslar ro'yxati", f"bk:list:{st.pk}"))
    return "✅", [Reply("\n".join(lines), buttons(*row_btns, per_row=1))]


def start_submission(acc, student_id, lesson_num):
    """Vazifa topshirish rejimini yoqadi: acc.state ga step='submission' yoziladi."""
    from html import escape

    from apps.crm.models import Student

    from .services import Reply, buttons

    st = Student.objects.filter(pk=student_id, is_deleted=False).first()
    if not st:
        return "Talaba topilmadi", []
    contract = active_contract_for_student(st)
    if not contract:
        return "Shartnoma topilmadi", []
    lesson = CourseLesson.objects.filter(course=contract.course, number=int(lesson_num), is_deleted=False).first()
    if not lesson:
        return "Dars topilmadi", []

    acc.state = {
        "step": "submission",
        "student": str(st.pk),
        "contract": str(contract.pk),
        "lesson": str(lesson.pk),
    }
    acc.save(update_fields=["state"])

    text = (
        f"📤 <b>{lesson.number}-dars vazifasini topshirish:</b>\n"
        f"<i>{escape(lesson.title)}</i>\n\n"
        "Tayyorlagan ishingizni yuboring:\n"
        "• 📷 Skrinshot (rasm)\n"
        "• 📁 Hujjat (.docx, .xlsx, .pdf)\n"
        "• ✍️ Yoki to'g'ridan-to'g'ri matn ko'rinishida yozing.\n\n"
        "AI ishni tekshirib, darhol ball va xulosani beradi."
    )
    return "✅", [Reply(text, buttons(("❌ Bekor qilish", f"bk:l:{lesson.number}:{st.pk}")))]


def handle_submission_message(acc, text="", photo_id="", doc_id="", doc_name="", caption=""):
    """Talaba topshirgan vazifani qabul qilib, AI orqali tekshirish va javob berish."""
    from apps.crm.models import Student

    from . import evaluator
    from .services import Reply, buttons

    st_id = (acc.state or {}).get("student")
    contract_id = (acc.state or {}).get("contract")
    lesson_id = (acc.state or {}).get("lesson")

    student = Student.objects.filter(pk=st_id, is_deleted=False).first()
    contract = Contract.objects.filter(pk=contract_id, is_deleted=False).first()
    lesson = CourseLesson.objects.filter(pk=lesson_id, is_deleted=False).first()

    if not student or not contract or not lesson:
        acc.state = {}
        acc.save(update_fields=["state"])
        return [Reply("Topshiriq jarayoni eskirgan. /menu orqali qayta kiring.")]

    acc.state = {}
    acc.save(update_fields=["state"])

    sub_text = text or caption
    if photo_id:
        sub_type = LessonSubmission.SubmissionType.PHOTO
        file_id = photo_id
        fname = "screenshot.jpg"
    elif doc_id:
        sub_type = LessonSubmission.SubmissionType.DOCUMENT
        file_id = doc_id
        fname = doc_name or "document"
    else:
        sub_type = LessonSubmission.SubmissionType.TEXT
        file_id = ""
        fname = ""

    sub, err = submit_lesson_task(
        student,
        contract,
        lesson,
        sub_type,
        content_text=sub_text,
        telegram_file_id=file_id,
        file_name=fname,
        account=acc,
    )
    if err:
        return [Reply(f"⚠️ {err}", buttons(("⬅️ Darsga qaytish", f"bk:l:{lesson.number}:{student.pk}")))]

    # AI baholash
    evaluator.evaluate_submission(sub)

    if sub.passed:
        head = f"🎉 <b>Tabriklaymiz! {lesson.number}-dars vazifasi qabul qilindi.</b>\n"
        badge = "✅ O'tdi"
    else:
        head = f"⚠️ <b>{lesson.number}-dars vazifasi to'liq bajarilmagan.</b>\n"
        badge = "❌ O'tmadi"

    score_line = f"Ball: <b>{sub.score} / 100</b> ({badge})\nUrinish: {sub.attempt} / {sub.max_attempts}\n"
    body = f"{head}\n{score_line}\n{sub.feedback}"

    row_btns = []
    if not sub.passed and sub.attempt < sub.max_attempts:
        row_btns.append(("🔄 Qayta topshirish", f"bk:sub:{lesson.number}:{student.pk}"))
    row_btns.append(("⬅️ Darsga qaytish", f"bk:l:{lesson.number}:{student.pk}"))
    row_btns.append(("📚 Barcha darslar", f"bk:list:{student.pk}"))

    return [Reply(body, buttons(*row_btns, per_row=1))]


def callback(acc, rest):
    """'bk:' prefiksli callback'larni qayta ishlaydi:
    - bk:lock:<num>:<st_id>
    - bk:l:<num>:<st_id>
    - bk:sub:<num>:<st_id>
    - bk:list:<st_id>
    """
    from apps.crm.models import Student

    parts = rest.split(":")
    cmd = parts[0] if parts else ""

    if cmd == "lock":
        return f"{parts[1]}-dars hali ochilmagan. Guruhda dars o'tilishini kuting.", []

    if cmd == "l" and len(parts) >= 3:
        return lesson_view(acc, parts[2], parts[1])

    if cmd == "sub" and len(parts) >= 3:
        return start_submission(acc, parts[2], parts[1])

    if cmd == "list" and len(parts) >= 2:
        st = Student.objects.filter(pk=parts[1], is_deleted=False).first()
        if st:
            return "✅", menu(acc, [st])
        return "Topilmadi", []

    return "Noma'lum buyruq", []

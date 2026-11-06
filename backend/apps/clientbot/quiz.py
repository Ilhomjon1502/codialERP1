"""Kurs testi (2026-11-06, buyurtmachi so'rovi): o'quvchi mijozlar botida kurs bo'yicha test topshiradi (`docs/ks_test_reja.md`).

- Testni ustoz yoki administrator ochadi: guruh sahifasi → «📝 Test» → «Hammasiga yuborish» (yoki bitta talabaga). Faqat guruhdagi faol shartnomalar.
- Topshiradi faqat o'quvchining o'zi (botga «Talaba» bo'lib ulangan akkaunt). Botga hali ulanmagan bo'lsa test kutib turadi — ulanganda taklif chiqadi.
- Bir marta: tugagan testdan keyin qayta topshirishga ustoz/administrator ruxsat beradi (yangi urinish; eskisi saqlanadi).
- Savollar (`QuizQuestion`) boshlanganda nusxalanadi; savol tartibi va variantlar aralashtiriladi; 20 tadan ko'p bo'lsa — darslar bo'yicha teng tanlanadi.
- To'g'ri javoblar oxirida ko'rsatiladi (xatolar ro'yxati). Vaqt — `MINUTES` daqiqa; tugasa, javob berilganlari bilan yakunlanadi (`tick`).
- Natija: guruh ustozi va yordamchisiga (xodimlar boti, `quiz` xabari) va vasiyga (mijozlar boti).
"""

import datetime
import logging
import random
from collections import Counter, defaultdict
from html import escape

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.permissions import can
from apps.education.models import Contract

from .models import BotInvite, BotLink, QuizAttempt, QuizQuestion

log = logging.getLogger(__name__)
St = QuizAttempt.State
OPEN = (St.SENT, St.STARTED)
SIZE = 20
MINUTES = 30
PASS_PERCENT = 60
LETTERS = "ABCDEF"
LITERACY_COURSE = "Kompyuter savodxonligi"
CHUNK = 3500  # Telegram xabari 4096 belgigacha

# Kompyuter savodxonligi + AI o'quv rejasi (https://ilhomjon1502.github.io/Ks-darsi/), 1–11-darslar.
# (dars, savol, [variantlar], to'g'ri javob raqami, izoh)
LITERACY_QUESTIONS = [
    (1, "Kompyuterni o'chirsak, qaysi xotiradagi narsa yo'qoladi?", ["Disk", "Operativ xotira (RAM)", "Fleshka", "Google Drive"], 1,
     "RAM faqat kompyuter yoniqligida ishlaydi. Shuning uchun ishni diskka saqlash kerak (Ctrl + S)."),
    (1, "Ochiq oynalar orasida tez almashish uchun qaysi tugmalar?", ["Alt + Tab", "Ctrl + C", "Win + L", "Win + D"], 0,
     "Alt ni ushlab turib Tab ni bosing. Win + L esa kompyuterni qulflaydi."),
    (2, "Qaysi fayl nomi eng to'g'ri?", ["yangi document (2).docx", "referat/oxirgi?.docx", "2026-10-20_Ali_Referat.docx", "oxirgi_oxirgi2.docx"], 2,
     "Qoida: Sana_Ism_Mavzu. Nomda / va ? kabi belgilar bo'lmaydi."),
    (2, "Shift + Delete nima qiladi?", ["Faylni Savatga tashlaydi", "Faylni butunlay o'chiradi", "Faylning nusxasini oladi", "Faylni qayta nomlaydi"], 1,
     "Shift + Delete Savatni chetlab o'tadi: fayl qaytmaydi."),
    (3, "Fleshkani sug'urishdan oldin nima qilish kerak?", ["Kompyuterni o'chirish", "Hech narsa", "«Xavfsiz chiqarish»ni bosish", "Ctrl + S ni bosish"], 2,
     "Xavfsiz chiqarish yozish tugaganini tekshiradi, shunda fayllar buzilmaydi."),
    (3, "Ekranning bir qismini rasmga olish (skrinshot) uchun qaysi tugmalar?", ["Win + Shift + S", "Ctrl + Shift + N", "Win + E", "Ctrl + P"], 0,
     "Win + Shift + S — sohani belgilaysiz, keyin Ctrl + V bilan qo'yasiz."),
    (4, "Google'da faqat PDF fayllarni topish uchun nima qo'shamiz?", ["filetype:pdf", "site:pdf", "\"pdf\"", "-pdf"], 0,
     "filetype: fayl turini tanlaydi, site: esa saytni."),
    (4, "Internetdagi ma'lumot to'g'riligini qanday tekshiramiz?",
     ["Birinchi chiqqan saytga ishonamiz", "Kamida 2 ta ishonchli manbada tekshiramiz", "Chiroyli saytga ishonamiz", "Tekshirish shart emas"], 1,
     "Kim va qachon yozganini ko'ring, kamida 2 ta ishonchli manbada solishtiring."),
    (5, "R-V-K-F formulasidagi «K» nimani bildiradi?", ["Kompyuter", "Kod", "Kontekst", "Kitob"], 2,
     "R — rol, V — vazifa, K — kontekst (kim uchun, nima uchun), F — format."),
    (5, "Qaysi ma'lumotni AI ga hech qachon yozmaymiz?", ["Dars mavzusi", "Bank karta raqami va SMS kod", "Umumiy savol", "O'zingiz yozgan matn"], 1,
     "AI bilan suhbat internetga yuboriladi: parol, SMS kod, karta va pasport raqamini yozmang."),
    (6, "Mundarija avtomatik chiqishi uchun sarlavhaga nima qilish kerak?",
     ["Qalin qilish", "«Sarlavha 1» stilini berish", "Shriftni kattalashtirish", "Markazga tekislash"], 1,
     "Mundarija stillardan yasaladi: sarlavhalarga «Sarlavha 1», «Sarlavha 2» bering."),
    (6, "Hujjat hamma kompyuter va telefonda bir xil ko'rinishi uchun qaysi formatda yuboramiz?", [".docx", ".pdf", ".txt", ".zip"], 1,
     "PDF hamma joyda bir xil ko'rinadi — yuborish va chop etish uchun qulay."),
    (7, "AI bergan manbalar ro'yxati bilan nima qilamiz?",
     ["Shundayligicha ko'chirib qo'yamiz", "O'chirib tashlaymiz", "Har birini topib tekshiramiz", "AI dan yana so'raymiz"], 2,
     "AI mavjud bo'lmagan kitob va saytlarni to'qishi mumkin."),
    (8, "=AVERAGE(B2:B5) nima hisoblaydi?", ["Yig'indini", "O'rtachani", "Eng kattasini", "Nechta son borligini"], 1,
     "AVERAGE — o'rtacha, SUM — yig'indi, MAX — eng kattasi."),
    (8, "Excelda formula qaysi belgi bilan boshlanadi?", ["=", "#", "$", "*"], 0, "Formula doim = belgisi bilan boshlanadi: =SUM(B2:B5)."),
    (9, "Formulani pastga tortganda F1 katak o'zgarmasligi uchun nima yozamiz?", ["$F$1", "F1", "\"F1\"", "#F1"], 0,
     "$F$1 — mutlaq havola. F4 tugmasi $ belgisini o'zi qo'yadi."),
    (9, "C2 katakda 60 turibdi. =IF(C2>=60; \"O'tdi\"; \"Yiqildi\") nima chiqaradi?", ["O'tdi", "Yiqildi", "#VALUE!", "60"], 0,
     ">= — «katta yoki teng»: aynan 60 ham shartga mos."),
    (10, "Qaysi slayd yaxshiroq?", ["Katta sarlavha, rasm va 3 qator", "15 qator mayda matn", "Har so'zda animatsiya", "Referat matni to'liq"], 0,
     "1 slayd = 1 fikr, 6 qatordan ko'p emas, katta shrift."),
    (11, "SMS: «Kartangiz bloklandi, kodni shu raqamga yuboring». Nima qilasiz?",
     ["Kodni yuboraman", "Havolani ochib ko'raman", "Bankning rasmiy raqamiga o'zim qo'ng'iroq qilaman", "Javob yozib so'rayman"], 2,
     "Bu fishing: shoshiltiradi va kod so'raydi. Bankka o'zingiz qo'ng'iroq qiling."),
    (11, "Qaysi parol eng kuchli?", ["123456", "ali2012", "qwerty", "Olma-Daryo-Kitob-47"], 3,
     "Uzun, bir necha so'z va raqamdan iborat parol kuchli. Har saytda boshqa parol bo'lsin."),
]


def ensure_questions(course):
    """«Kompyuter savodxonligi» kursida hali savol bo'lmagan bo'lsa (o'chirilganlari ham) — boshlang'ich 20 ta savol."""
    if course.name.strip().lower() != LITERACY_COURSE.lower() or QuizQuestion.all_objects.filter(course=course).exists():
        return
    QuizQuestion.objects.bulk_create([QuizQuestion(course=course, lesson=lesson, text=text, options=opts, correct=ok, explanation=why, order=n * 10)
                                      for n, (lesson, text, opts, ok, why) in enumerate(LITERACY_QUESTIONS, start=1)])


def questions(course):
    ensure_questions(course)
    return list(QuizQuestion.objects.filter(course=course, status="Faol").order_by("order", "created_at"))


def available(course):
    return bool(course) and bool(questions(course))


def pick(qs, size=SIZE, rnd=random):
    """`size` tadan ko'p bo'lsa — darslar bo'yicha navbatma-navbat (har darsdan teng); tartib aralashtiriladi."""
    if len(qs) > size:
        by_lesson = defaultdict(list)
        for q in qs:
            by_lesson[q.lesson].append(q)
        for v in by_lesson.values():
            rnd.shuffle(v)
        chosen, lessons = [], sorted(by_lesson)
        while len(chosen) < size:
            for lesson in lessons:
                if by_lesson[lesson] and len(chosen) < size:
                    chosen.append(by_lesson[lesson].pop())
        qs = chosen
    qs = list(qs)
    rnd.shuffle(qs)
    return qs


def snapshot(q, rnd=random):
    idx = list(range(len(q.options)))
    rnd.shuffle(idx)
    return {"q": str(q.pk), "lesson": q.lesson, "text": q.text, "options": [q.options[i] for i in idx], "correct": idx.index(q.correct),
            "explanation": q.explanation}


# ---------- yuborish (xodim) ----------


def can_send(user, group):
    return can(user, "groups", "e") or user.pk in (group.teacher_id, group.supporter_id)


def _active_contracts(group, today):
    return list(Contract.objects.filter(group=group, is_deleted=False, student__is_deleted=False, start_date__lte=today)
                .filter(Q(end_date__isnull=True) | Q(end_date__gte=today)).select_related("student", "course", "branch")
                .order_by("student__first_name", "student__last_name"))


def student_accounts(student):
    """O'quvchining o'zi ulangan akkauntlar (testni faqat ular topshiradi)."""
    return [ln.account for ln in BotLink.objects.filter(student=student, role=BotInvite.Role.STUDENT, is_active=True, account__blocked=False)
            .select_related("account")]


def _invite_text(at):
    return (f"📝 <b>{escape(at.course.name)}</b> kursi bo'yicha test\n"
            f"{at.total} ta savol, har biriga bir nechta javob varianti — to'g'risini tanlaysiz. Vaqt: {MINUTES} daqiqa.\n"
            f"Testni bir marta topshirasiz, shuning uchun shoshilmang. Natija va xatolaringiz oxirida ko'rsatiladi. Omad! 🍀")


def invite(at):
    """O'quvchi akkauntlariga «Testni boshlash» tugmasi. Qaytaradi: nechta akkauntga ketdi."""
    from . import services as bot

    n = 0
    for acc in student_accounts(at.student):
        if bot.queue(acc, _invite_text(at), kind="Test", key=f"quiz:{at.pk}", markup=bot.buttons(("▶️ Testni boshlash", f"qz:go:{at.pk}"))):
            n += 1
    return n


def create(user, contract, group=None):
    total = min(SIZE, len(questions(contract.course)))
    at = QuizAttempt.objects.create(branch=contract.branch, course=contract.course, student=contract.student, contract=contract,
                                    group=group or contract.group, total=total, created_by=user, updated_by=user)
    return at


def last_attempts(student_ids, course):
    """{student_id: oxirgi urinish} (bekor qilinganlarsiz)."""
    out = {}
    for at in QuizAttempt.objects.filter(student__in=student_ids, course=course).exclude(state=St.CANCELLED).order_by("created_at"):
        out[at.student_id] = at
    return out


@transaction.atomic
def send_to_group(user, group, contract=None, today=None):
    """Guruhga (yoki bitta shartnomaga) test. Topshirgan talabaga — faqat `contract` berilganda (qayta topshirish). Qaytaradi: hisob."""
    if not can_send(user, group):
        raise PermissionDenied("Testni faqat guruh ustozi yoki administrator yuboradi")
    if not available(group.course):
        raise ValidationError({"detail": f"«{group.course.name}» kursi uchun test savollari yo'q"})
    today = today or timezone.localdate()
    contracts = _active_contracts(group, today)
    if contract is not None:
        contracts = [c for c in contracts if c.pk == contract.pk]
        if not contracts:
            raise ValidationError({"detail": "Bu shartnoma guruhda faol emas"})
    last = last_attempts([c.student_id for c in contracts], group.course)
    res = {"sent": 0, "waiting": 0, "done": 0, "open": 0}
    for c in contracts:
        prev = last.get(c.student_id)
        if prev and prev.state in OPEN:
            if contract is not None:
                raise ValidationError({"detail": "Bu talabaga test allaqachon yuborilgan va hali tugamagan"})
            res["open"] += 1
            continue
        if prev and prev.state == St.DONE and contract is None:
            res["done"] += 1
            continue
        at = create(user, c, group)
        if invite(at):
            res["sent"] += 1
        else:
            res["waiting"] += 1
    return res


@transaction.atomic
def cancel(user, at):
    if at.state not in OPEN:
        raise ValidationError({"detail": "Faqat tugamagan testni bekor qilish mumkin"})
    at.state, at.updated_by = St.CANCELLED, user
    at.save(update_fields=["state", "updated_by", "updated_at"])
    return at  # o'quvchi tugmani bossa «bekor qilingan» deyiladi


def on_linked(acc, link):
    """O'quvchi botga endi ulandi: kutib turgan testi bo'lsa — taklif."""
    from .services import Reply, buttons

    if link.role != BotInvite.Role.STUDENT:
        return []
    at = QuizAttempt.objects.filter(student=link.student, state=St.SENT).select_related("course").order_by("-created_at").first()
    if not at:
        return []
    return [Reply(_invite_text(at), buttons(("▶️ Testni boshlash", f"qz:go:{at.pk}")))]


# ---------- bot suhbati ----------


def _deadline(at):
    return at.started_at + datetime.timedelta(minutes=MINUTES)


def _q_text(at, i):
    q = at.questions[i]
    lines = [f"<b>{i + 1}/{len(at.questions)}.</b> {escape(q['text'])}", ""]
    lines += [f"<b>{LETTERS[n]})</b> {escape(o)}" for n, o in enumerate(q["options"])]
    return "\n".join(lines)


def _ask(at):
    from .services import Reply

    i = len(at.answers)
    q = at.questions[i]
    row = [{"text": LETTERS[n], "callback_data": f"qz:a:{at.pk}:{i}:{n}"} for n in range(len(q["options"]))]
    return [Reply(_q_text(at, i), {"inline_keyboard": [row]})]


def _student_link(acc, at):
    return BotLink.objects.filter(account=acc, student=at.student, role=BotInvite.Role.STUDENT, is_active=True).exists()


def start(acc, attempt_id, now=None, rnd=random):
    from .services import Reply

    now = now or timezone.now()
    with transaction.atomic():
        at = QuizAttempt.objects.select_for_update().filter(pk=attempt_id).first()
        if not at or not _student_link(acc, at):
            return "Topilmadi", [Reply("Bu testni faqat o'quvchining o'zi topshiradi (botga o'quvchi sifatida ulangan akkaunt).")]
        if at.state == St.CANCELLED:
            return "Bekor qilingan", [Reply("Bu test bekor qilingan.", done=True)]
        if at.state == St.DONE:
            return "Tugagan", [Reply(f"Bu test tugagan: {at.score}/{at.total}.", done=True)]
        if at.state == St.STARTED:
            if at.account_id and at.account_id != acc.pk:
                return "Boshqa akkauntda", [Reply("Test boshqa Telegram akkauntda boshlangan.")]
            if now >= _deadline(at):
                return "⏰", [Reply("⏰ Vaqt tugadi.", done=True), *finish(at, timed_out=True)]
            acc.state = {"step": "quiz", "attempt": str(at.pk)}
            acc.save(update_fields=["state"])
            return "▶️", [Reply("▶️ Davom etamiz.", done=True), *_ask(at)]
        qs = pick(questions(at.course), rnd=rnd)
        if not qs:
            return "Savol yo'q", [Reply("Hozircha test savollari yo'q. Ustozingizga ayting.")]
        at.questions, at.answers, at.total = [snapshot(q, rnd) for q in qs], [], len(qs)
        at.state, at.started_at, at.account = St.STARTED, now, acc
        at.save(update_fields=["questions", "answers", "total", "state", "started_at", "account", "updated_at"])
    acc.state = {"step": "quiz", "attempt": str(at.pk)}
    acc.save(update_fields=["state"])
    head = f"📝 Boshladik! {at.total} ta savol, vaqt {MINUTES} daqiqa (≈ {timezone.localtime(_deadline(at)):%H:%M} gacha). Har savolga harf tugmasini bosing."
    return "✅", [Reply(head, done=True), *_ask(at)]


def answer(acc, rest, now=None):
    """`<attempt>:<i>:<n>` → (qisqa javob, [Reply])."""
    from .services import Reply

    now = now or timezone.now()
    parts = rest.split(":")
    stale = ("Bu savol allaqachon yopilgan", [Reply("✅", done=True)])
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return "Noma'lum amal", []
    att_id, i, n = parts[0], int(parts[1]), int(parts[2])
    with transaction.atomic():
        at = QuizAttempt.objects.select_for_update().filter(pk=att_id).first()
        if not at or at.account_id != acc.pk:
            return "Topilmadi", []
        if at.state != St.STARTED or i != len(at.answers) or n >= len(at.questions[i]["options"]):
            return stale
        if now >= _deadline(at):
            return "⏰", [Reply(_q_text(at, i) + "\n\n⏰ Vaqt tugadi", done=True), *finish(at, timed_out=True)]
        at.answers = [*at.answers, n]
        at.save(update_fields=["answers", "updated_at"])
    chosen = f"{_q_text(at, i)}\n\n☑️ Javobingiz: <b>{LETTERS[n]}</b>"
    if len(at.answers) < len(at.questions):
        return "✅", [Reply(chosen, done=True), *_ask(at)]
    return "✅", [Reply(chosen, done=True), *finish(at)]


def text_while_quiz(acc):
    from .services import Reply

    at = QuizAttempt.objects.filter(pk=(acc.state or {}).get("attempt"), state=St.STARTED).first()
    if not at:
        acc.state = {}
        acc.save(update_fields=["state"])
        return [Reply("Test yakunlangan.")]
    return [Reply("Javobni savol ostidagi harf tugmasi bilan tanlang 👇"), *_ask(at)]


def review(at):
    """Har savol: {n, lesson, text, chosen, correct, ok, explanation} — ERP va bot uchun."""
    out = []
    for i, q in enumerate(at.questions):
        a = at.answers[i] if i < len(at.answers) else None
        out.append({"n": i + 1, "lesson": q["lesson"], "text": q["text"], "chosen": q["options"][a] if a is not None else None,
                    "correct": q["options"][q["correct"]], "ok": a == q["correct"], "explanation": q.get("explanation", "")})
    return out


def passed(at):
    return at.score is not None and at.total > 0 and at.score * 100 >= at.total * PASS_PERCENT


def passed_q():
    """`passed()` ning so'rov ko'rinishi (filtr uchun)."""
    return Q(state=St.DONE, total__gt=0, score__gte=F("total") * PASS_PERCENT / 100.0)


def result_texts(at):
    """O'quvchiga: ball va xatolar (uzun bo'lsa bir necha xabar)."""
    rows = review(at)
    wrong = [r for r in rows if not r["ok"]]
    head = [("⏰ Vaqt tugadi. " if at.timed_out else "") + "✅ Test tugadi!",
            f"Natija: <b>{at.score}/{at.total}</b> ({at.percent}%)",
            "🎉 Tabriklaymiz, siz testdan o'tdingiz!" if passed(at) else f"Testdan o'tish uchun kamida {PASS_PERCENT}% kerak. Xatolar ustida ishlang 💪"]
    if not wrong:
        return ["\n".join(head + ["", "Hamma javob to'g'ri — a'lo! 🏆"])]
    parts, cur = [], "\n".join(head + ["", "<b>Xatolar ustida ishlash:</b>"])
    for r in wrong:
        block = (f"\n\n<b>{r['n']}.</b> {escape(r['text'])} <i>({r['lesson']}-dars)</i>\n"
                 f"❌ {escape(r['chosen']) if r['chosen'] is not None else 'javob berilmadi'}\n✅ {escape(r['correct'])}"
                 + (f"\n💡 {escape(r['explanation'])}" if r["explanation"] else ""))
        if len(cur) + len(block) > CHUNK:
            parts.append(cur)
            cur = block.lstrip("\n")
        else:
            cur += block
    parts.append(cur)
    return parts


def finish(at, timed_out=False, now=None):
    """Testni yakunlaydi (javob berilmaganlari — xato). Qaytaradi: o'quvchiga [Reply]."""
    from . import services as bot

    now = now or timezone.now()
    with transaction.atomic():
        at = QuizAttempt.objects.select_for_update().select_related("student", "course", "group__course", "branch").get(pk=at.pk)
        if at.state != St.STARTED:
            return []
        at.score = sum(1 for r in review(at) if r["ok"])
        at.state, at.finished_at, at.timed_out = St.DONE, now, timed_out
        at.save(update_fields=["score", "state", "finished_at", "timed_out", "updated_at"])
        acc = bot.BotAccount.objects.filter(pk=at.account_id).first() if at.account_id else None
        if acc and (acc.state or {}).get("attempt") == str(at.pk):
            acc.state = {}
            acc.save(update_fields=["state"])
        _notify(at)
    return [bot.Reply(t) for t in result_texts(at)]


def _notify(at):
    from apps.notifications import services as notif

    from . import services as bot

    mark = "✅" if passed(at) else "⚠️"
    group = f"{at.group.course.name} / #{at.group.number}" if at.group_id else at.course.name
    text = (f"📝 <b>Test natijasi</b>\n{escape(at.student.full_name)} · {escape(group)}\n{mark} <b>{at.score}/{at.total}</b> ({at.percent}%)"
            + (" · vaqt tugadi" if at.timed_out else ""))
    users = [at.group.teacher, at.group.supporter] if at.group_id else []
    notif.notify("quiz", text, branch=at.branch, default_users=users, key=f"quiz:{at.pk}")
    for ln in BotLink.objects.filter(student=at.student, role=BotInvite.Role.GUARDIAN, is_active=True, account__blocked=False).select_related("account"):
        bot.queue(ln.account, f"📝 <b>{escape(at.student.first_name)}</b> «{escape(at.course.name)}» kursi bo'yicha test topshirdi: "
                              f"<b>{at.score}/{at.total}</b> ({at.percent}%).", kind="Test", key=f"quiz-result:{at.pk}")


def tick(now=None):
    """Bot jarayonida har daqiqada: vaqti tugagan testlarni yakunlaydi va o'quvchiga natijani yuboradi."""
    from . import services as bot

    now = now or timezone.now()
    n = 0
    for at in QuizAttempt.objects.filter(state=St.STARTED, started_at__lte=now - datetime.timedelta(minutes=MINUTES)).select_related("account"):
        try:
            replies = finish(at, timed_out=True, now=now)
            if at.account_id:
                for i, r in enumerate(replies):
                    bot.queue(at.account, r.text, kind="Test", key=f"quiz-timeout:{at.pk}:{i}")
            n += 1
        except Exception:  # noqa: BLE001 — bitta test boshqasini to'xtatmasin
            log.exception("Test yakunlanmadi: %s", at.pk)
    return n


def menu(acc, students):
    """Menyudagi «📝 Test»: o'quvchiga — kutib turgan test yoki oxirgi natija; vasiyga — farzandlarining natijalari."""
    from .services import Reply, buttons

    roles = {ln.student_id: ln.role for ln in acc.links.filter(is_active=True)}
    replies = []
    for st in students:
        ats = list(QuizAttempt.objects.filter(student=st).exclude(state=St.CANCELLED).select_related("course").order_by("-created_at")[:5])
        name = escape(st.first_name)
        open_ = next((a for a in ats if a.state in OPEN), None)
        if roles.get(st.pk) == BotInvite.Role.STUDENT and open_:
            label = "▶️ Davom ettirish" if open_.state == St.STARTED else "▶️ Testni boshlash"
            replies.append(Reply(_invite_text(open_), buttons((label, f"qz:go:{open_.pk}"))))
            continue
        done = [a for a in ats if a.state == St.DONE]
        if done:
            lines = [f"📝 <b>{name}</b> — test natijalari:"] + [f"• {escape(a.course.name)}: <b>{a.score}/{a.total}</b> ({a.percent}%) · {timezone.localtime(a.finished_at):%d.%m.%Y}"
                                                              for a in done]
            replies.append(Reply("\n".join(lines)))
        elif open_:
            replies.append(Reply(f"📝 <b>{name}</b>ga test yuborilgan, hali topshirilmagan. Testni o'quvchining o'zi o'z Telegram akkauntidan topshiradi."))
        else:
            replies.append(Reply(f"📝 <b>{name}</b>: hozircha test yo'q. Test kurs oxirida ustoz tomonidan ochiladi."))
    return replies


# ---------- statistika (ERP) ----------


def stats(qs):
    """`qs` — QuizAttempt. Yuborilgan/topshirgan, o'rtacha ball, o'tganlar, eng ko'p xato qilingan savollar va darslar, guruhlar."""
    done = list(qs.filter(state=St.DONE).select_related("group__course"))
    wrong_q, asked_q, wrong_l, asked_l = Counter(), Counter(), Counter(), Counter()
    groups = defaultdict(list)
    for at in done:
        for r in review(at):
            asked_q[r["text"]] += 1
            asked_l[r["lesson"]] += 1
            if not r["ok"]:
                wrong_q[r["text"]] += 1
                wrong_l[r["lesson"]] += 1
        if at.group_id:
            groups[f"{at.group.course.name} / #{at.group.number}"].append(at.percent or 0)
    pcts = [at.percent or 0 for at in done]
    return {
        "sent": qs.exclude(state=St.CANCELLED).count(), "done": len(done), "waiting": qs.filter(state__in=OPEN).count(),
        "avg": round(sum(pcts) / len(pcts)) if pcts else None,
        "passed": sum(1 for at in done if passed(at)), "pass_percent": PASS_PERCENT,
        "questions": sorted(({"text": t, "wrong": wrong_q[t], "asked": n, "rate": round(wrong_q[t] * 100 / n)} for t, n in asked_q.items()),
                            key=lambda x: (-x["rate"], -x["wrong"]))[:10],
        "lessons": [{"lesson": ls, "wrong": wrong_l[ls], "asked": n, "rate": round(wrong_l[ls] * 100 / n)} for ls, n in sorted(asked_l.items())],
        "groups": sorted(({"group": g, "n": len(v), "avg": round(sum(v) / len(v))} for g, v in groups.items()), key=lambda x: x["group"]),
    }

"""Tamomlash/to'xtatish so'rovnomasi (B4): shartnomasi tugagan talabaga (botga ulangan bo'lsa) ertasi kuni 10:00 da bot qisqa savollar yuboradi.

- Kimga: shartnomaning `end_date` si kecha yoki undan oldin (oxirgi `WINDOW_DAYS` kun ichida), botga ulangan faol akkauntlar bor (o'quvchi va vasiy).
  Talaba keyin ulansa ham, oyna ichida yuboriladi. Har shartnomaga bitta so'rovnoma; javobni birinchi javob bergan akkaunt tugatadi.
- Oqim: sabab «Kursni tamomladi» bo'lsa — *tamomlaganlarga*, aks holda — *to'xtatganlarga* savollari (`SurveyQuestion.flow`; «Hammasiga» ikkalasiga).
- Savollar bazada (Bosh menejer qo'shadi/tahrirlaydi): tanlov (variantlar + «Boshqa (yozaman)»), baho (1–5), matn. Har savolni o'tkazib yuborish mumkin.
- Javoblar `ExitSurvey.answers` ga (savol matni nusxasi bilan) va xodimlarga Telegram'da (`survey` xabari, standart — Bosh menejer) boradi.
"""

import datetime
import logging
from collections import Counter, defaultdict
from html import escape

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.education.models import Contract

from .models import BotLink, ExitSurvey, SurveyQuestion

log = logging.getLogger(__name__)
K, F, St = SurveyQuestion.Kind, SurveyQuestion.Flow, ExitSurvey.State
COMPLETED_REASON = "Kursni tamomladi"
WINDOW_DAYS = 14
SEND_FROM, SEND_TO = datetime.time(10, 0), datetime.time(20, 0)
MAX_TEXT = 500

# (kalit, matn, tur, variantlar, boshqa, kimga, tartib)
DEFAULT_QUESTIONS = [
    ("reason", "Kursni nima uchun to'xtatdingiz?", K.CHOICE,
     ["Moliyaviy qiyinchilik", "Dars sifatidan qoniqmadim", "Markaz sharoiti yoqmadi", "Kurs yoqmadi, boshqa kursga o'tyapman", "Vaqt to'g'ri kelmadi"], True, F.STOPPED, 10),
    ("course_rating", "Kursni 1 dan 5 gacha baholang", K.SCALE, [], False, F.COMPLETED, 10),
    ("teacher_rating", "Ustozingizni 1 dan 5 gacha baholang", K.SCALE, [], False, F.BOTH, 20),
    ("recommend", "Do'stlaringizga Codialni tavsiya qilasizmi?", K.CHOICE, ["Albatta", "Balki", "Yo'q"], False, F.COMPLETED, 30),
    ("return", "Kelajakda Codialda qayta o'qishni xohlaysizmi?", K.CHOICE, ["Ha", "Balki", "Yo'q"], False, F.STOPPED, 30),
    ("continue", "Boshqa kursni davom ettirmoqchimisiz?", K.CHOICE, ["Ha", "Balki", "Yo'q"], False, F.COMPLETED, 40),
    ("improve", "Markazni yaxshilash uchun fikr yoki taklifingiz bormi? (yozing)", K.TEXT, [], False, F.BOTH, 90),
]


def ensure_questions(branch):
    """Filialda hali savol yo'q bo'lsa — standart savollar (keyin Bosh menejer o'zgartiradi)."""
    if SurveyQuestion.objects.filter(branch=branch).exists():
        return
    for key, text, kind, options, other, flow, order in DEFAULT_QUESTIONS:
        SurveyQuestion.objects.create(branch=branch, key=key, text=text, kind=kind, options=options, allow_other=other, flow=flow, order=order)


def flow_of(contract):
    return F.COMPLETED if contract.stop_reason == COMPLETED_REASON else F.STOPPED


def questions_for(branch, flow):
    return list(SurveyQuestion.objects.filter(branch=branch, status="Faol", flow__in=[flow, F.BOTH]).order_by("order", "created_at"))


# ---------- yuborish ----------


def due_contracts(today=None):
    today = today or timezone.localdate()
    return (Contract.objects.filter(is_deleted=False, end_date__isnull=False, end_date__lt=today, end_date__gte=today - datetime.timedelta(days=WINDOW_DAYS),
                                    student__is_deleted=False, student__bot_links__is_active=True, student__bot_links__account__blocked=False)
            .exclude(pk__in=ExitSurvey.all_objects.values("contract")).select_related("student", "course", "branch").distinct())


def _intro(contract, role, n):
    st, course = contract.student.first_name, contract.course.name
    who = f"<b>{escape(st)}</b>ning" if role == "Vasiy" else "sizning"
    if flow_of(contract) == F.COMPLETED:
        head = f"🎓 Tabriklaymiz! {who} Codial'dagi «{escape(course)}» kursi tugadi."
    else:
        head = f"Assalomu alaykum! {who} Codial'dagi «{escape(course)}» kursi yakunlandi."
    return f"{head}\nFikringiz biz uchun muhim: {n} ta qisqa savolga javob bering, bu bizga yaxshilanishga yordam beradi. 🙏"


def send(contract):
    """Shartnoma uchun so'rovnomani botga ulangan akkauntlarga yuboradi. Qaytaradi: ExitSurvey yoki None (savol yoki ulangan akkaunt yo'q)."""
    from . import services as bot

    ensure_questions(contract.branch)
    flow = flow_of(contract)
    qs = questions_for(contract.branch, flow)
    links = list(BotLink.objects.filter(student=contract.student, is_active=True, account__blocked=False).select_related("account"))
    if not qs or not links:
        return None
    try:
        with transaction.atomic():
            sv = ExitSurvey.objects.create(branch=contract.branch, contract=contract, student=contract.student, flow=flow, stop_reason=contract.stop_reason)
    except IntegrityError:
        return None
    seen = set()
    for ln in links:
        if ln.account_id in seen:
            continue
        seen.add(ln.account_id)
        bot.queue(ln.account, _intro(contract, ln.role, len(qs)), kind="So'rovnoma", key=f"survey:{sv.pk}",
                  markup=bot.buttons(("📝 Savollarga javob berish", f"sv:go:{sv.pk}")))
    return sv


def tick(now=None, today=None):
    """Bot jarayonida har daqiqada: 10:00–20:00 oralig'ida vaqti kelgan so'rovnomalarni yuboradi."""
    now = now or timezone.localtime()
    if not SEND_FROM <= now.time() <= SEND_TO:
        return 0
    n = 0
    for c in due_contracts(today or now.date()):
        try:
            if send(c):
                n += 1
        except Exception:  # noqa: BLE001 — bitta shartnoma boshqasini to'xtatmasin
            log.exception("So'rovnoma yuborilmadi: %s", c.pk)
    return n


# ---------- bot suhbati ----------


def _current(st):
    """(savol, tartib raqami, jami) — suhbat holatidan."""
    ids = st.get("qs", [])
    i = st.get("i", 0)
    q = SurveyQuestion.objects.filter(pk=ids[i]).first() if i < len(ids) else None
    return q, i, len(ids)


def _ask(acc):
    from .services import Reply, buttons

    st = acc.state
    q, i, total = _current(st)
    if q is None:  # savol o'chirilgan — keyingisiga
        return _advance(acc, None, None)
    head = f"<b>{i + 1}/{total}.</b> {escape(q.text)}"
    skip = ("⏭ O'tkazib yuborish", f"sv:s:{i}")
    if q.kind == K.SCALE:
        row = [{"text": str(n), "callback_data": f"sv:a:{i}:{n}"} for n in range(1, 6)]
        return [Reply(head + "\n1 — juda yomon, 5 — a'lo", {"inline_keyboard": [row, [{"text": skip[0], "callback_data": skip[1]}]]})]
    if q.kind == K.CHOICE:
        pairs = [(o, f"sv:a:{i}:{n}") for n, o in enumerate(q.options)]
        if q.allow_other:
            pairs.append(("✍️ Boshqa (yozaman)", f"sv:a:{i}:o"))
        return [Reply(head, buttons(*pairs, skip))]
    return [Reply(head + "\n✍️ Javobingizni yozib yuboring.", buttons(skip))]


def start(acc, survey_id):
    from .services import Reply

    sv = ExitSurvey.objects.select_related("student", "contract__course").filter(pk=survey_id).first()
    if not sv or not BotLink.objects.filter(account=acc, student=sv.student, is_active=True).exists():
        return "Topilmadi", []
    if sv.state == St.DONE:
        return "Rahmat", [Reply("Rahmat! Javob allaqachon qabul qilingan. 🙏", done=True)]
    qs = questions_for(sv.branch, sv.flow)
    if not qs:
        return "Topilmadi", []
    acc.state = {"step": "survey", "survey": str(sv.pk), "qs": [str(q.pk) for q in qs], "i": 0, "answers": [], "other": False}
    acc.save(update_fields=["state"])
    if sv.state == St.SENT:
        ExitSurvey.objects.filter(pk=sv.pk).update(state=St.STARTED)
    return "✅", [Reply("📝 Boshladik!", done=True), *_ask(acc)]


def callback(acc, rest):
    """`sv:go:<id>` | `sv:a:<i>:<qiymat>` | `sv:s:<i>` → (qisqa javob, [Reply])."""
    from .services import Reply

    kind, _, tail = rest.partition(":")
    if kind == "go":
        return start(acc, tail)
    st = acc.state or {}
    stale = ("Bu savol allaqachon yopilgan", [Reply("✅", done=True)])
    if st.get("step") != "survey":
        return stale
    i_str, _, val = tail.partition(":")
    q, i, total = _current(st)
    if not i_str.isdigit() or int(i_str) != i or q is None:
        return stale
    if kind == "s":
        return "✅", [Reply(f"<b>{i + 1}/{total}.</b> {escape(q.text)}\n⏭ o'tkazib yuborildi", done=True), *_advance(acc, q, None)]
    if kind != "a":
        return "Noma'lum amal", []
    if q.kind == K.SCALE and val in {"1", "2", "3", "4", "5"}:
        answer = val
    elif q.kind == K.CHOICE and val == "o" and q.allow_other:
        acc.state = {**st, "other": True}
        acc.save(update_fields=["state"])
        return "✅", [Reply(f"<b>{i + 1}/{total}.</b> {escape(q.text)}\n✍️ Boshqa", done=True), Reply("Javobingizni yozib yuboring:")]
    elif q.kind == K.CHOICE and val.isdigit() and int(val) < len(q.options):
        answer = q.options[int(val)]
    else:
        return "Noma'lum amal", []
    return "✅", [Reply(f"<b>{i + 1}/{total}.</b> {escape(q.text)}\n✅ {escape(answer)}", done=True), *_advance(acc, q, answer)]


def text_answer(acc, text):
    """So'rovnoma paytida yozilgan matn: matnli savolga yoki «Boshqa (yozaman)» ga javob."""
    from .services import Reply

    st = acc.state
    q, _, _ = _current(st)
    if q is None:
        return _advance(acc, None, None)
    if q.kind == K.TEXT or st.get("other"):
        return _advance(acc, q, text.strip()[:MAX_TEXT])
    return [Reply("Iltimos, yuqoridagi tugmalardan birini tanlang (yoki «O'tkazib yuborish»).")]


def _advance(acc, q, answer):
    st = acc.state
    answers = list(st.get("answers", []))
    if q is not None and answer:
        answers.append({"q": str(q.pk), "key": q.key, "question": q.text, "kind": q.kind, "answer": answer})
    acc.state = {**st, "answers": answers, "i": st.get("i", 0) + 1, "other": False}
    acc.save(update_fields=["state"])
    if acc.state["i"] < len(st.get("qs", [])):
        return _ask(acc)
    return _finish(acc)


def _finish(acc):
    from .services import Reply

    st = acc.state
    sv = ExitSurvey.objects.select_related("student", "contract__course", "branch").filter(pk=st.get("survey")).first()
    acc.state = {}
    acc.save(update_fields=["state"])
    if sv is None or sv.state == St.DONE:
        return [Reply("Rahmat! Javob allaqachon qabul qilingan. 🙏")]
    role = BotLink.objects.filter(account=acc, student=sv.student).values_list("role", flat=True).first() or ""
    sv.answers, sv.state, sv.completed_at, sv.account, sv.respondent_role = st.get("answers", []), St.DONE, timezone.now(), acc, role
    sv.save()
    if sv.answers:
        _notify_staff(sv)
    return [Reply("Rahmat! Fikringiz biz uchun juda muhim. 🙏 Sizga omad tilaymiz!")]


def _notify_staff(sv):
    from apps.notifications import services as notif

    c = sv.contract
    lines = [f"📝 <b>So'rovnoma javobi</b>\n{escape(sv.student.full_name)} · {escape(c.course.name)}" + (f"\nShartnomada: {escape(sv.stop_reason)}" if sv.stop_reason else "")]
    lines += [f"• {escape(a['question'])}: <b>{escape(a['answer'])}</b>" for a in sv.answers]
    notif.notify("survey", "\n".join(lines), branch=sv.branch, key=f"survey:{sv.pk}")


# ---------- statistika ----------


def stats(qs):
    """`qs` — ExitSurvey. Yuborilgan/javob berganlar, sabablar (talaba aytgan va administrator kiritgan), baholar o'rtachasi."""
    done = list(qs.filter(state=St.DONE))
    reasons, admin_reasons, scales = Counter(), Counter(), defaultdict(list)
    for sv in done:
        if sv.stop_reason:
            admin_reasons[sv.stop_reason] += 1
        for a in sv.answers:
            if a.get("key") == "reason":
                reasons[a["answer"]] += 1
            elif a.get("kind") == K.SCALE and str(a.get("answer", "")).isdigit():
                scales[a["question"]].append(int(a["answer"]))
    sent = qs.count()
    return {
        "sent": sent, "done": len(done), "rate": round(len(done) / sent * 100) if sent else 0,
        "reasons": [{"label": k, "n": n} for k, n in reasons.most_common()],
        "admin_reasons": [{"label": k, "n": n} for k, n in admin_reasons.most_common()],
        "scales": [{"question": q, "avg": round(sum(v) / len(v), 2), "n": len(v)} for q, v in scales.items()],
    }


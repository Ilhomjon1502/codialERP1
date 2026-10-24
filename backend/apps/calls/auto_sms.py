"""Avtomatik SMS (buyurtmachi so'rovi 2026-10-23): voqeaga yoki jadvalga qarab SMS navbatiga o'zi tushadi. Beshta qoida (`SmsRule`):

- **lead** — yangi lid yaratilganda, lidning hamma raqamiga (hook: `crm.services.create_lead`);
- **contract** — shartnoma tuzilganda (faol yoki rejadagi), talaba va vasiyning hamma raqamiga (hook: `education.services.save_contract`);
- **month_start** — oyning 1-sanasi 10:00: shu oy narxini hali to'lamagan faol, Grant bo'lmagan shartnomalarga («To'lovga tavsiya» hisobi);
- **prepay_bonus** — oyning 25-sanasi 10:00: kelasi oy uchun hali to'lamaganlarga, «Avvaldan to'lov» chegirmasi bonusi;
- **absence** — har kuni 08:00: oxirgi 3 kunda sababsiz («Besabab») kelmagan, «Gaplashildi» deb belgilanmagan talabalarga; bir talabaga 3 kunda bittadan;
- **demo** — lid «Sinov darsga qatnashdi» holatiga o'tganda (hook: `notifications.services.lead_changed`);
- **bot_reminder** — har kuni 10:00: faol shartnomasi yoki ochiq lidi (1–4) bor, lekin mijozlar botiga ulanmagan raqamlarga ulanish eslatmasi
  (har `reminder_days` kunda, jami `reminder_max` marta — Telegram bot sozlamasi).

**Bot yoki SMS (2026-10-24):** talaba + raqam mijozlar botiga ulangan bo'lsa, xabar SMS o'rniga **botga** ketadi (`enqueue`); ulanmagan raqamga SMS,
lid/shartnoma/sinov darsi/eslatma SMS'lariga bot havolasi va kodi qo'shiladi (`_bot_suffix`).

Qoidalar boshida **o'chiq**; administrator matnni ko'rib, «kimlarga ketadi» ro'yxatini tekshirib yoqadi. Yoqilishdan oldingi voqealarga SMS ketmaydi.
Takrorlanmaslik: `SmsMessage.key` (voqea + raqam) — bitta voqea bitta raqamga ikki marta ketmaydi.
Jadval `tick()` — Telegram bot jarayonida har daqiqada; muammo (telefon aloqasiz, xato, yetkazilmadi) Bosh menejerga botdan: `check_problems()`.
"""

import calendar
import datetime
import logging
from collections import namedtuple

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.education.dues import month_dues
from apps.education.models import Attendance, Contract
from apps.references.models import DiscountType

from . import sms
from .models import CallDevice, SmsMessage, SmsRule

log = logging.getLogger(__name__)
R, K, S = SmsRule.Key, SmsMessage.Kind, SmsMessage.State
T = datetime.time

# Tur: kind — SMS jurnalidagi belgi; ph — matnda ishlatish mumkin bo'lgan o'rinbosarlar; when — administratorga tushuntirish
DEFAULTS = {
    R.LEAD: {
        "kind": K.LEAD, "time": None, "day": None, "ph": ["ism", "talaba", "kurs"],
        "text": "Codialga xush kelibsiz, AyTi ta'limini biz bilan o'rganing!",
        "when": "Yangi lid yaratilganda — lidning hamma raqamiga (har yangi lidga)",
    },
    R.CONTRACT: {
        "kind": K.CONTRACT, "time": None, "day": None, "ph": ["ism", "talaba", "kurs", "guruh"],
        "text": "{ism} {guruh} guruhiga qo'shildingiz.",
        "when": "Shartnoma tuzilganda (faol yoki rejadagi) — talaba va vasiyning hamma raqamiga",
    },
    R.MONTH_START: {
        "kind": K.MONTH, "time": T(10, 0), "day": 1, "ph": ["ism", "talaba", "kurs", "guruh", "oy", "summa", "muddat", "muddat_kun"],
        "text": "Codial ichki tartib qoidalariga ko'ra oylik to'lovlarni shu oyning {muddat_kun}-sanasidan kechiktirmay to'lash kerak.",
        "when": "Har oyning belgilangan kuni — shu oy narxini hali to'lamagan faol (Grant emas) shartnomalarga",
    },
    R.PREPAY_BONUS: {
        "kind": K.BONUS, "time": T(10, 0), "day": 25, "ph": ["ism", "talaba", "kurs", "guruh", "bonus", "kun", "oy", "keyingi_oy", "summa"],
        "text": ("Codialda oldindan to'lov uchun {bonus} so'm bonus bor, oy tugashiga {kun} kun qoldi, ulgirib qoling! "
                 "{keyingi_oy} oyi uchun to'lovni hozir qilsangiz bonus sizniki."),
        "when": "Har oyning belgilangan kuni — kelasi oy uchun hali to'lamagan faol shartnomalarga (bonus «Avvaldan to'lov» chegirmasidan)",
    },
    R.DEMO: {
        "kind": K.DEMO, "time": None, "day": None, "ph": ["ism", "talaba", "kurs", "guruh"],
        "text": "Assalomu alaykum! Sinov darsimizga qatnashganingiz uchun rahmat. Savollaringiz bo'lsa, 998204432 ga murojaat qiling.",
        "when": "Lid «Sinov darsga qatnashdi» holatiga o'tganda — talabaning hamma raqamiga (har lidga bir marta)",
    },
    R.BOT_REMINDER: {
        "kind": K.BOT, "time": T(10, 0), "day": None, "ph": ["ism", "talaba"],
        "text": "Codial o'quv markazi xabarlari Telegram botda ham keladi, ulanib qo'ying.",
        "when": "Har kuni — faol shartnomasi yoki ochiq lidi (1–4) bor, lekin botga ulanmagan raqamlarga; oralig'i va soni «Telegram bot → Sozlamalar»da",
    },
    R.ABSENCE: {
        "kind": K.ABSENCE, "time": T(8, 0), "day": None, "ph": ["ism", "talaba", "kurs", "guruh", "kecha", "sana"],
        "text": "{kecha} {ism} darsga kelmagan ko'rinadi, aniqlik kiritish uchun 998204432 ga telefon qiling.",
        "when": "Har kuni — oxirgi 3 kunda sababsiz kelmagan, «Gaplashildi» belgilanmagan talabalarga (3 kunda bittadan)",
    },
}
SAMPLE_CTX = {
    "ism": "Muhsinjon", "talaba": "Muhsinjon Karimov", "kurs": "Kompyuter savodxonligi", "guruh": "Kompyuter savodxonligi 192",
    "oy": "noyabr", "summa": "450 000", "muddat": "10.11", "muddat_kun": "10", "bonus": "75 000", "kun": "5", "keyingi_oy": "dekabr",
    "kecha": "Kecha", "sana": "21.10",
}
PROBLEM_AFTER = datetime.timedelta(minutes=15)
ABSENCE_WINDOW_DAYS = 3

Plan = namedtuple("Plan", "student contract ctx key month skip invite", defaults=(None,))


def ensure_rules(branches):
    """Filialda yetishmayotgan qoidalarni (o'chiq holda) yaratadi."""
    out = []
    for b in branches:
        have = {r.key: r for r in SmsRule.objects.filter(branch=b, is_deleted=False)}
        for key, d in DEFAULTS.items():
            if key not in have:
                have[key] = SmsRule.objects.create(branch=b, key=key, text=d["text"], send_time=d["time"], day=d["day"])
        out.extend(have[k] for k in DEFAULTS)
    return out


def check_rule_text(key, text):
    text = sms.plain(text)
    if not text:
        raise ValidationError({"text": ["Matn kiriting"]})
    allowed = DEFAULTS[key]["ph"]
    bad = sorted({t for t in sms._TOKEN.findall(text) if t not in allowed})
    if bad:
        raise ValidationError({"text": [f"Bu qoidada ishlatib bo'lmaydigan o'rinbosar: {', '.join('{' + b + '}' for b in bad)}. Mavjud: "
                                        + ", ".join("{" + k + "}" for k in allowed)]})
    return text


# ---------- navbatga qo'yish ----------


def _safe(fn):
    """Avtomatik SMS lid yoki shartnoma saqlanishini hech qachon buzmasin (xato — jurnalga)."""
    try:
        with transaction.atomic():
            fn()
    except Exception:  # noqa: BLE001
        log.exception("Avtomatik SMS navbatga qo'yilmadi")


def alert_no_device(branch):
    from apps.notifications import services as notif

    notif.notify("sms_problem", f"⚠️ <b>SMS yuborilmadi</b>\n«{branch}» filialida SMS yuboradigan telefon ulanmagan "
                 "(Qo'ng'iroqlar va SMS → Qurilmalar).", force=True, key=f"smsnodev:{branch.pk}:{timezone.localdate()}")


def enqueue(rule, student, ctx, key_base, kind, *, contract=None, lead=None, month=None, skip=()):
    """Talabaning hamma raqamiga xabar: botga ulangan raqamga **botga**, qolganiga SMS qatori (Navbatda). Qaytaradi: yaratilganlar soni."""
    from apps.clientbot import services as bot
    from apps.clientbot.models import ClientOutbox

    text = sms.plain(sms.render(sms.plain(rule.text), ctx))
    phones = [(p, who) for p, who in sms.recipients(student) if p not in skip]
    keys = [f"{key_base}:{p}" for p, _ in phones]
    have = set(SmsMessage.all_objects.filter(key__in=keys).values_list("key", flat=True))
    have |= set(ClientOutbox.objects.filter(key__in=keys).values_list("key", flat=True))  # shu voqea allaqachon (SMS yoki bot orqali) ketgan
    todo = [(p, who, k) for (p, who), k in zip(phones, keys, strict=True) if k not in have]
    n, sms_todo = 0, []
    for p, who, k in todo:
        accs = bot.accounts_for(student, p)
        if accs:
            n += bot.deliver(accs, text, kind=kind, key=k, student=student, contract=contract, lead=lead, month=month, phone=p, recipient=who)
        else:
            sms_todo.append((p, who, k))
    if not sms_todo:
        return n
    device = sms.branch_device(rule.branch_id)
    if not device:
        alert_no_device(rule.branch)
        return n
    rows = []
    for p, who, k in sms_todo:
        msg = text + _bot_suffix(rule, student, p)
        rows.append(SmsMessage(branch_id=rule.branch_id, device=device, student=student, contract=contract, lead=lead, kind=kind, month=month,
                               phone=p, recipient=who, text=msg, parts=sms.segments(msg), key=k))
    SmsMessage.objects.bulk_create(rows, ignore_conflicts=True)
    return n + len(rows)


INVITE_RULES = {R.LEAD, R.CONTRACT, R.DEMO, R.BOT_REMINDER}  # shu SMS'larga mijozlar boti havolasi (raqamga xos kod) qo'shiladi


def _bot_suffix(rule, student, phone):
    """Lid va shartnoma SMS'i oxiriga « Telegram bot: t.me/…?start=KOD » (bot sozlangan va raqam hali ulanmagan bo'lsa)."""
    if rule.key not in INVITE_RULES:
        return ""
    from apps.clientbot import services as bot

    try:
        suffix = sms.plain(bot.invite_suffix(student, phone, rule.branch))
        return f" {suffix}" if suffix else ""
    except Exception:  # noqa: BLE001 — havola bo'lmasa ham SMS ketsin
        log.exception("Bot havolasi SMS'ga qo'shilmadi")
        return ""


def _name(st):
    return f"{st.first_name} {st.last_name}".strip()


def _enabled_rule(branch_id, key):
    return SmsRule.objects.filter(branch_id=branch_id, key=key, enabled=True, is_deleted=False).select_related("branch").first()


# ---------- voqeali qoidalar (hook'lar) ----------


def lead_created(lead):
    def run():
        rule = _enabled_rule(lead.branch_id, R.LEAD)
        if rule:
            st = lead.student
            ctx = {"ism": st.first_name, "talaba": _name(st), "kurs": lead.course.name if lead.course_id else ""}
            enqueue(rule, st, ctx, f"lead:{lead.pk}", K.LEAD, lead=lead)

    _safe(run)


def contract_created(contract):
    def run():
        from apps.education.services import NOFAOL, period_status

        rule = _enabled_rule(contract.branch_id, R.CONTRACT)
        if rule and period_status(contract.start_date, contract.end_date) != NOFAOL:
            st = contract.student
            ctx = {"ism": st.first_name, "talaba": _name(st), "kurs": contract.course.name, "guruh": sms.group_label(contract.group)}
            enqueue(rule, st, ctx, f"contract:{contract.pk}", K.CONTRACT, contract=contract)

    _safe(run)


def lead_status_changed(lead, old_status):
    """Lid «Sinov darsga qatnashdi» (4) holatiga o'tdi — rahmat xabari (har lidga bir marta)."""
    from apps.crm.models import Lead

    if lead.status != Lead.LeadStatus.DEMO_ATTENDED or old_status == lead.status:
        return

    def run():
        rule = _enabled_rule(lead.branch_id, R.DEMO)
        if rule:
            st = lead.student
            ctx = {"ism": st.first_name, "talaba": _name(st), "kurs": lead.course.name if lead.course_id else "",
                   "guruh": sms.group_label(lead.group) if lead.group_id else ""}
            enqueue(rule, st, ctx, f"demo:{lead.pk}", K.DEMO, lead=lead)

    _safe(run)


# ---------- jadvalli qoidalar ----------


def _contracts(rule):
    return Contract.objects.filter(branch_id=rule.branch_id, is_deleted=False)


def _month_skip(contract_ids, month):
    """Shu oy uchun «To'lovga tavsiya» yoki oy boshi SMS olgan (shartnoma, raqam) juftlari — qayta yuborilmaydi."""
    q = SmsMessage.objects.filter(contract__in=contract_ids, month=month, kind__in=[K.DUE, K.MONTH], is_deleted=False,
                                  status__in=[S.QUEUED, S.SENDING, S.SENT])
    from apps.clientbot import services as bot

    out = {}
    for cid, phone in set(q.values_list("contract_id", "phone")) | bot.sent_pairs(contract_ids, month, [K.DUE, K.MONTH]):
        out.setdefault(cid, set()).add(phone)
    return out


def plan_month_start(rule, today):
    month = today.replace(day=1)
    dues = month_dues(_contracts(rule), month, today)
    cs = _contracts(rule).filter(pk__in=dues.keys()).select_related("student__parent", "course", "group__course")
    skip = _month_skip(list(dues), month)
    return [Plan(c.student, c, sms.due_context(c, dues[c.pk], month), f"month:{c.pk}:{month:%Y-%m}", month, skip.get(c.pk, set())) for c in cs]


def prepay_bonus_amount():
    d = DiscountType.objects.filter(is_deleted=False, name__icontains="avvaldan").order_by("name").first()
    return d.max_amount if d else None


def plan_prepay_bonus(rule, today):
    bonus = prepay_bonus_amount()
    if not bonus:
        return None  # «Avvaldan to'lov» chegirma turi yo'q — bonus summasi noma'lum
    last = calendar.monthrange(today.year, today.month)[1]
    nxt = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    dues = month_dues(_contracts(rule), nxt, today)
    cs = _contracts(rule).filter(pk__in=dues.keys()).select_related("student__parent", "course", "group__course")
    plans = []
    for c in cs:
        ctx = sms.due_context(c, dues[c.pk], nxt)
        ctx.update(bonus=sms.money(bonus), kun=str(last - today.day), keyingi_oy=sms.MONTHS[nxt.month - 1], oy=sms.MONTHS[today.month - 1])
        plans.append(Plan(c.student, c, ctx, f"bonus:{c.pk}:{nxt:%Y-%m}", nxt, set()))
    return plans


def plan_absence(rule, today):
    lo = today - datetime.timedelta(days=ABSENCE_WINDOW_DAYS)
    if rule.enabled_at:
        lo = max(lo, timezone.localtime(rule.enabled_at).date() - datetime.timedelta(days=1))  # yoqilishdan oldingi voqealarga ketmaydi
    qs = (Attendance.objects.filter(branch_id=rule.branch_id, is_deleted=False, status="X", date__gte=lo, date__lt=today,
                                    contract__is_deleted=False)
          .exclude(contact_status=Attendance.Contact.TALKED)
          .filter(Q(contract__end_date__isnull=True) | Q(contract__end_date__gte=today))
          .select_related("contract__student__parent", "group__course", "course").order_by("-date"))
    latest = {}
    for a in qs:
        latest.setdefault(a.contract.student_id, a)
    recent = set(SmsMessage.objects.filter(kind=K.ABSENCE, student_id__in=list(latest), is_deleted=False,
                                           created_at__gte=timezone.now() - datetime.timedelta(days=ABSENCE_WINDOW_DAYS))
                 .values_list("student_id", flat=True))
    plans = []
    for sid, a in latest.items():
        if sid in recent:
            continue
        st = a.contract.student
        yesterday = a.date == today - datetime.timedelta(days=1)
        ctx = {"ism": st.first_name, "talaba": _name(st), "kurs": a.course.name, "guruh": sms.group_label(a.group),
               "kecha": "Kecha" if yesterday else f"{a.date:%d.%m} kuni", "sana": f"{a.date:%d.%m}"}
        plans.append(Plan(st, a.contract, ctx, f"absent:{a.pk}", None, set()))
    return plans


def plan_bot_reminder(rule, today):
    """Botga ulanmagan raqamlar: faol shartnomali yoki ochiq lidli (1–4) talabalar; har taklifga `reminder_days` kunda bir, jami `reminder_max` marta."""
    from apps.clientbot import services as bot
    from apps.clientbot.models import BotInvite, BotLink
    from apps.crm.models import Student

    if not bot.configured():
        return []
    cfg = bot.get_config(rule.branch)
    if not cfg.reminder_max:
        return []
    cutoff = timezone.now() - datetime.timedelta(days=cfg.reminder_days)
    active = Student.objects.filter(branch_id=rule.branch_id, is_deleted=False).filter(
        Q(contracts__is_deleted=False, contracts__end_date__isnull=True) | Q(contracts__is_deleted=False, contracts__end_date__gte=today)
        | Q(leads__is_deleted=False, leads__status__in=["1", "2", "3", "4"]))
    linked = BotLink.objects.filter(student=OuterRef("student"), phone=OuterRef("phone"), is_active=True)
    invites = (BotInvite.objects.filter(branch_id=rule.branch_id, reminders__lt=cfg.reminder_max, student__in=active.values("pk"))
               .filter(Q(last_reminded_at__isnull=True) | Q(last_reminded_at__lte=cutoff))
               .exclude(Exists(linked)).select_related("student__parent"))
    plans = []
    for inv in invites:
        st = inv.student
        others = {p for p, _ in sms.recipients(st)} - {inv.phone}
        plans.append(Plan(st, None, {"ism": st.first_name, "talaba": _name(st), "kurs": ""}, f"botrem:{inv.pk}:{inv.reminders + 1}", None, others, inv))
    return plans


PLANNERS = {R.MONTH_START: plan_month_start, R.PREPAY_BONUS: plan_prepay_bonus, R.ABSENCE: plan_absence, R.BOT_REMINDER: plan_bot_reminder}


def run_rule(rule, today=None):
    """Jadvalli qoidani bajaradi: SMS'larni navbatga qo'yadi. Qaytaradi: yaratilgan SMS soni."""
    today = today or timezone.localdate()
    plans = PLANNERS[rule.key](rule, today)
    if plans is None:
        from apps.notifications import services as notif

        notif.notify("sms_problem", "⚠️ <b>Oldindan to'lov bonusi SMS ketmadi</b>\nSozlamalarda «Avvaldan to'lov» chegirma turi topilmadi.",
                     force=True, key=f"smsbonus:{today}")
        return 0
    kind = DEFAULTS[rule.key]["kind"]
    total = 0
    for p in plans:
        n = enqueue(rule, p.student, p.ctx, p.key, kind, contract=p.contract, month=p.month, skip=p.skip)
        if n and p.invite:  # eslatma ketdi — keyingisi `reminder_days` kundan keyin, jami `reminder_max` marta
            type(p.invite).objects.filter(pk=p.invite.pk).update(reminders=p.invite.reminders + 1, last_reminded_at=timezone.now())
        total += n
    return total


def tick(now=None):
    """Bot jarayonida har daqiqada: vaqti kelgan jadvalli qoidalarni kuniga bir marta bajaradi."""
    now = now or timezone.localtime()
    today = now.date()
    done = 0
    for rule in SmsRule.objects.filter(enabled=True, is_deleted=False, send_time__isnull=False).select_related("branch"):
        if rule.last_run_on == today or now.time() < rule.send_time or (rule.day and today.day != rule.day):
            continue
        try:
            with transaction.atomic():
                n = run_rule(rule, today)
                SmsRule.objects.filter(pk=rule.pk).update(last_run_on=today)
            log.info("Avtomatik SMS %s (%s): %s ta navbatga qo'yildi", rule.key, rule.branch, n)
            done += n
        except Exception:  # noqa: BLE001 — bitta qoida boshqasini to'xtatmasin
            log.exception("Avtomatik SMS qoidasi bajarilmadi: %s", rule.key)
    return done


# ---------- ko'rib chiqish (yoqishdan oldin) ----------


def preview(rule, today=None):
    """Qoida hozir ishga tushsa nima bo'lardi: namuna matn va kimlarga ketishi (hech narsa yuborilmaydi)."""
    today = today or timezone.localdate()
    out = {"scheduled": rule.key in PLANNERS, "sample": "", "real": False, "students": 0, "messages": 0, "names": [], "note": ""}
    plans = PLANNERS[rule.key](rule, today) if rule.key in PLANNERS else []
    if plans is None:
        out["note"] = "«Avvaldan to'lov» chegirma turi topilmadi (Sozlamalar → Chegirma turlari) — bonus summasi noma'lum, SMS ketmaydi."
        plans = []
    ctx = dict(SAMPLE_CTX)
    if plans:
        ctx = {**SAMPLE_CTX, **plans[0].ctx}
        out["real"] = True
    out["sample"] = sms.plain(sms.render(sms.plain(rule.text), ctx))
    if rule.key in INVITE_RULES:
        from apps.clientbot import services as bot

        if bot.configured() and bot.get_config(rule.branch).invite_in_sms:
            out["sample"] += " " + sms.plain(bot.sample_suffix())
            out["note"] = "Matn oxiriga mijozlar botiga ulanish havolasi (har raqamga alohida kod) avtomatik qo'shiladi; raqam allaqachon ulangan bo'lsa qo'shilmaydi."
    out["parts"] = sms.segments(out["sample"])
    out["students"] = len(plans)
    out["messages"] = sum(len([1 for p, _ in sms.recipients(pl.student) if p not in pl.skip]) for pl in plans)
    out["names"] = [_name(pl.student) for pl in plans[:8]]
    return out


# ---------- muammo haqida Bosh menejerga ----------


def check_problems(now=None):
    """Telefon aloqasiz (navbatda 15 daqiqadan ortiq), SMS xato yoki operator «yetkazilmadi» desa — Bosh menejerga Telegram. Har SMS haqida bir marta."""
    from apps.notifications import services as notif
    from apps.notifications.models import Outbox

    now = now or timezone.now()
    if Outbox.objects.filter(event="sms_problem", created_at__gte=now - PROBLEM_AFTER).exists():
        return 0
    base = SmsMessage.objects.filter(direction=SmsMessage.Direction.OUT, is_deleted=False, problem_alerted_at__isnull=True)
    stuck = list(base.filter(status=S.QUEUED, created_at__lte=now - PROBLEM_AFTER).values_list("pk", "device"))
    failed = list(base.filter(status=S.FAILED, created_at__gte=now - datetime.timedelta(hours=24)).values_list("pk", "error"))
    undelivered = list(base.filter(delivery=sms.UNDELIVERED, created_at__gte=now - datetime.timedelta(hours=24)).values_list("pk", flat=True))
    if not (stuck or failed or undelivered):
        return 0
    lines = ["⚠️ <b>SMS yuborishda muammo</b>"]
    if stuck:
        f = lambda t: timezone.localtime(t).strftime("%H:%M") if t else "hech qachon"  # noqa: E731
        devs = ", ".join(f"{d.name} (oxirgi aloqa {f(d.last_seen_at)})" for d in CallDevice.objects.filter(pk__in={d for _, d in stuck}))
        lines.append(f"⏳ {len(stuck)} ta SMS 15 daqiqadan beri navbatda. Telefon: {devs}. Internet, ilova va batareyani tekshiring.")
    if failed:
        errs = {}
        for _, e in failed:
            errs[e or "noma'lum"] = errs.get(e or "noma'lum", 0) + 1
        top = "; ".join(f"{e} — {n}" for e, n in sorted(errs.items(), key=lambda x: -x[1])[:3])
        lines.append(f"❌ {len(failed)} ta SMS yuborilmadi: {top}")
    if undelivered:
        lines.append(f"📵 {len(undelivered)} ta SMS qabul qiluvchiga yetmadi (operator xabari).")
    lines.append("Qo'ng'iroqlar va SMS → SMS bo'limida «Qayta yuborish» mumkin.")
    ids = [p for p, _ in stuck] + [p for p, _ in failed] + undelivered
    SmsMessage.objects.filter(pk__in=ids).update(problem_alerted_at=now)
    notif.notify("sms_problem", "\n".join(lines), force=True, key=f"smsprob:{now:%Y%m%d%H%M}")
    return len(ids)

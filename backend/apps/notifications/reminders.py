"""Vaqtga bog'liq Telegram eslatmalari (buyurtmachi so'rovi 2026-10-14).

- `lesson_starts()` — dars boshlanganda guruh ustoziga «davomat olish vaqti» (bot jarayoni har daqiqada chaqiradi:
  alohida jarayon ochilmaydi, bitta-ikkita yengil so'rov).
- `morning_plan()` — ertalab 8:30 da administratorlarga bugungi ish rejasi (cron: `morning_plan` buyrug'i).
"""

import datetime
from html import escape

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import role_code
from apps.core.roles import TEACHER_ROLES
from apps.crm.models import Lead
from apps.education.dues import due_map_by_group, month_dues
from apps.education.models import Attendance, Contract, Group
from apps.education.services import FAOL, active_on, has_lesson, status_q
from apps.references.models import Branch

from . import services, webapp

WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
DEBT_BEFORE = 10  # daqiqa: dars boshlanishidan oldin qarzdorlar haqida eslatma
START_WINDOW = 15  # daqiqa: bot qayta ishga tushsa ham shu oraliqda boshlangan dars eslatiladi
PER_GROUP = 12
CALLBACK_WINDOW_H = 12  # soat: bot to'xtab qolgan bo'lsa ham shu oraliqda belgilangan qayta bog'lanish eslatiladi (eskisi — ertalabki rejada)
PER_LIST = 15


def e(s):
    return escape(str(s or "—"), quote=False)


def num(n):
    return f"{int(n or 0):,}".replace(",", " ")


def link(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}/#/{path}"


def phone(p):
    return f"+998{p}" if p else ""


def _lesson_groups(day, branch=None):
    qs = Group.objects.filter(status_q(FAOL, day)).select_related("day_pattern", "time", "teacher", "branch", "course", "room")
    if branch:
        qs = qs.filter(branch=branch)
    return [g for g in qs if has_lesson(g, day)]


# ------------------------------------------------------------------ dars boshlanishi

def lesson_starts(now=None):
    """Hozir boshlangan (oxirgi 15 daqiqada) va hali davomati olinmagan darslar → ustozga bir marta (takrorlanmaslik kaliti)."""
    now = now or timezone.localtime()
    today = now.date()
    taken = set(Attendance.objects.filter(date=today).values_list("group_id", flat=True))
    n = 0
    for g in _lesson_groups(today):
        if g.pk in taken:
            continue
        start = timezone.make_aware(datetime.datetime.combine(today, g.time.start_time))
        if not (start <= now < start + datetime.timedelta(minutes=START_WINDOW)):
            continue
        text = f"🔔 <b>Dars vaqti — davomatni oling</b>\n{e(g.name)} · {g.time.start_time:%H:%M}–{g.time.end_time:%H:%M} · {e(g.room)}"
        if not webapp.enabled():  # Mini App tugmasi bo'lmasa — oddiy havola
            text += f"\n{link(f'attendance?tab=take&group={g.pk}')}"
        services.lesson_started(g, text, key=f"start:{g.pk}:{today}")
        n += 1
    return n


def debt_before_lessons(now=None):
    """Dars boshlanishiga 10 daqiqa qolganda — shu guruhdagi qarzdor talabalar ro'yxati (to'lovni undirish uchun). Har guruhga kuniga bir marta."""
    now = now or timezone.localtime()
    today = now.date()
    n = 0
    for g in _lesson_groups(today):
        start = timezone.make_aware(datetime.datetime.combine(today, g.time.start_time))
        if not (start - datetime.timedelta(minutes=DEBT_BEFORE) <= now < start):
            continue
        debtors = due_map_by_group(Contract.objects.filter(group=g).filter(active_on(today)), today).get(g.pk, [])
        if not debtors:
            continue
        L = [f"💰 <b>{DEBT_BEFORE} daqiqadan keyin dars — to'lovni eslating</b>",
             f"{e(g.name)} · {g.time.start_time:%H:%M}–{g.time.end_time:%H:%M} · {e(g.room)}",
             f"Shu oy to'lamaganlar: {len(debtors)} ta, jami {num(sum(i['to_pay'] for _, i in debtors))} so'm"]
        L += [f"  {'🔴' if i['overdue'] else '•'} {e(c.student.full_name)} — <b>{num(i['to_pay'])}</b> so'm · {phone(c.student.phone1)}" for c, i in debtors[:PER_GROUP]]
        if len(debtors) > PER_GROUP:
            L.append(f"  <i>… yana {len(debtors) - PER_GROUP} ta — Qarzdorlar bo'limi</i>")
        services.notify("debt_lesson", "\n".join(L),branch=g.branch, key=f"debt10:{g.pk}:{today}")
        n += 1
    return n


def demo_before_lessons(now=None):
    """Sinov darsiga yozilgan lid (3-status): dars boshlanishiga 10 daqiqa qolganda Administrator+Hisobchiga (va qo'shimcha qabul qiluvchilarga) hamda
    guruh ustoziga — talaba, telefon, guruh, xona. Har lidga kuniga bir marta."""
    now = now or timezone.localtime()
    today = now.date()
    n = 0
    leads = Lead.objects.filter(demo_date=today, status=Lead.LeadStatus.DEMO_BOOKED).select_related("student", "course", "group__time", "group__room", "group__teacher", "branch")
    for ld in leads:
        g = ld.group
        t = g.time if g else ld.preferred_times.order_by("start_time").first()
        if t is None:
            continue
        start = timezone.make_aware(datetime.datetime.combine(today, t.start_time))
        if not (start - datetime.timedelta(minutes=DEBT_BEFORE) <= now < start):
            continue
        st = ld.student
        where = f"{e(g.name)} · {e(g.room)}" if g else e(ld.course)
        teacher = f"\nUstoz: {e(g.teacher)}" if g else ""
        text = (f"🧪 <b>{DEBT_BEFORE} daqiqadan keyin sinov darsi</b>\n{e(st.full_name)} · {phone(st.phone1)}\n"
                f"{where} · {t.start_time:%H:%M}–{t.end_time:%H:%M}{teacher}")
        mine = {g.teacher_id, g.supporter_id} if g else set()
        services.notify("demo_soon", text, branch=ld.branch, default_users=[g.teacher] if g else [], key=f"demo10:{ld.pk}:{today}",
                        only=lambda u, mine=mine: role_code(u) not in TEACHER_ROLES or u.pk in mine)
        n += 1
    return n


def _talk_line(lead):
    """«Gaplashilgan: 14:05 · chiquvchi · 3 daq» — lidning oxirgi suhbati."""
    rec = lead.calls.filter(duration__gt=0).order_by("-started_at").first()
    if not rec:
        return ""
    m, s = divmod(rec.duration, 60)
    return f"📞 Gaplashilgan: {timezone.localtime(rec.started_at):%d.%m %H:%M} · {rec.direction.lower()} · {m}:{s:02d}"


def _note_markup(lead):
    """Izoh yozish uchun: saytdagi lid kartochkasiga havola (https bo'lsa) va keyingi qayta bog'lanishni tez surish tugmalari."""
    rows = []
    url = link(f"leads?open={lead.pk}")
    if url.startswith("https://"):
        rows.append([{"text": "📝 Izoh yozish va keyingi vaqtni belgilash", "url": url}])
    rows.append([{"text": "📅 Ertaga", "callback_data": f"lc:tm:{lead.pk}"}, {"text": "📅 3 kundan keyin", "callback_data": f"lc:d3:{lead.pk}"}])
    return {"inline_keyboard": rows}


def _note_text(lead, head):
    st = lead.student
    L = [head, f"{e(st.full_name)} · {phone(st.phone1)}", f"{e(lead.course)} · {lead.get_status_display()}", _talk_line(lead),
         "Suhbat haqida <b>izoh yozing</b>; lid qayta bog'lanishda qolsa — keyingi vaqtni belgilang."]
    if not link("x").startswith("https://"):
        L.append(link("leads"))
    return "\n".join(x for x in L if x)


def lead_call_note(lead, rec):
    """Gaplashilgan qo'ng'iroqdan keyin darhol: «izoh yozing» (eslatma allaqachon yuborilgan yoki vaqt belgilanmagan bo'lsa)."""
    services.notify("lead_callback", _note_text(lead, "📞 <b>Suhbat bo'ldi — izoh yozing</b>"), branch=lead.branch, key=f"cnote:{lead.pk}:{rec.pk}", markup=_note_markup(lead))


def lead_callbacks(now=None):
    """Lidning «qayta bog'lanish vaqti» kelganda (1- va 8-statuslar) — Administrator+Hisobchilarga bir marta, tugmalar bilan:
    ✅ Qo'ng'iroq qilindi · ⏰ +1 soat · 📅 Ertaga. Eskirgan (12 soatdan oshgan) eslatmalar ertalabki rejaga tushadi."""
    now = now or timezone.localtime()
    leads = (Lead.objects.filter(status__in=["1", "8"], callback_at__isnull=False, callback_at__lte=now, callback_reminded_at__isnull=True,
                                 callback_at__gte=now - datetime.timedelta(hours=CALLBACK_WINDOW_H))
             .select_related("student", "course", "branch"))
    n = 0
    for ld in leads:
        st = ld.student
        if ld.callback_talked_at:  # vaqt kelguncha allaqachon gaplashilgan — eslatma to'xtamaydi, lekin faqat izoh yozish uchun
            services.notify("lead_callback", _note_text(ld, f"⏰ <b>Qayta bog'lanish vaqti</b> · {timezone.localtime(ld.callback_at):%H:%M} — allaqachon gaplashilgan"),
                            branch=ld.branch, key=f"lcb:{ld.pk}:{int(ld.callback_at.timestamp())}", markup=_note_markup(ld))
            Lead.objects.filter(pk=ld.pk).update(callback_reminded_at=now)
            n += 1
            continue
        last = ld.comments.order_by("-created_at").first()
        L = [f"⏰ <b>Qayta bog'lanish vaqti keldi</b> · {timezone.localtime(ld.callback_at):%H:%M}",
             f"{e(st.full_name)} · {phone(st.phone1)}" + (f" · {phone(st.phone2)}" if st.phone2 else ""),
             f"{e(ld.course)} · {ld.get_status_display()}"]
        if last:
            L.append(f"💬 {e(last.comment[:150])}")
        L.append(link("leads"))
        pk = ld.pk
        markup = {"inline_keyboard": [[{"text": "✅ Qo'ng'iroq qilindi", "callback_data": f"lc:done:{pk}"}],
                                      [{"text": "⏰ +1 soat", "callback_data": f"lc:h1:{pk}"}, {"text": "📅 Ertaga", "callback_data": f"lc:tm:{pk}"}]]}
        services.notify("lead_callback", "\n".join(L), branch=ld.branch, key=f"lcb:{pk}:{int(ld.callback_at.timestamp())}", markup=markup)
        Lead.objects.filter(pk=pk).update(callback_reminded_at=now)
        n += 1
    return n


# ------------------------------------------------------------------ ertalabki reja

NIGHT_FROM = datetime.time(18, 30)  # kechagi ish kuni oxiri
NIGHT_TO = datetime.time(8, 30)     # bugungi reja vaqti


def _night_missed(branch, day):
    """Kecha 18:30 → bugun 8:30 oralig'ida javobsiz (yoki rad etilgan) qo'ng'iroqlar, shu raqamga hali qo'ng'iroq qilinmagan
    (`callback_at` bo'sh — chiquvchi yoki gaplashilgan kiruvchi qo'ng'iroq bo'lsa tizim o'zi yopadi). Raqam bo'yicha jamlanadi."""
    from apps.calls.models import CallRecord

    tz = timezone.get_current_timezone()
    start = datetime.datetime.combine(day - datetime.timedelta(days=1), NIGHT_FROM, tz)
    end = datetime.datetime.combine(day, NIGHT_TO, tz)
    rows = list(CallRecord.objects.filter(branch=branch, direction__in=[CallRecord.Direction.MISSED, CallRecord.Direction.REJECTED],
                                          callback_at__isnull=True, started_at__gte=start, started_at__lt=end)
                .select_related("student", "parent").order_by("started_at"))
    if not rows:
        return []
    groups = {}
    for r in rows:
        key = r.phone or r.number or r.pk
        g = groups.setdefault(key, {"first": r, "n": 0})
        g["n"] += 1
    items = list(groups.values())
    L = [f"\n📵 <b>Tunda javobsiz qo'ng'iroqlar</b> ({start:%d.%m} {NIGHT_FROM:%H:%M} – {NIGHT_TO:%H:%M}) — {len(items)} raqam, qayta qo'ng'iroq qiling"]
    for g in items[:PER_LIST]:
        r = g["first"]
        if r.student_id:
            who = r.student.full_name
        elif r.parent_id:
            who = f"{r.parent} (vasiy)"
        else:
            who = r.contact_name or "noma'lum raqam"
        num_txt = phone(r.phone) if r.phone else e(r.number or "yashirin raqam")
        times = timezone.localtime(r.started_at)
        L.append(f"  • {e(who)} · {num_txt} — {times:%H:%M}" + (f" (×{g['n']})" if g["n"] > 1 else ""))
    if len(items) > PER_LIST:
        L.append(f"  <i>… yana {len(items) - PER_LIST} ta — Qo'ng'iroqlar bo'limi</i>")
    return L


def plan_text(branch, day):
    """Filial uchun bugungi tavsiya etilgan ishlar."""
    L = [f"📋 <b>Bugungi ish rejasi</b> · {day:%d.%m.%Y}, {WEEKDAYS[day.weekday()]}"]
    groups = sorted(_lesson_groups(day, branch), key=lambda g: (g.time.start_time, g.name))
    L.append(f"Bugun {len(groups)} ta dars." if groups else "Bugun dars yo'q.")

    # 0. Kechagi 18:30 dan bugungi 8:30 gacha javobsiz qolgan qo'ng'iroqlar (qayta terilmaganlari)
    L += _night_missed(branch, day)

    # 1. To'lov kutilayotganlar: bugun darsi bor guruhlardagi qarzdorlar, dars vaqti bo'yicha
    # Shu oy kurs narxi bo'yicha (davomatga bog'liq emas) — education/dues.py
    by_group = due_map_by_group(Contract.objects.filter(group__in=groups).filter(active_on(day)), day)
    n_due = sum(len(v) for v in by_group.values())
    total = sum(i["to_pay"] for v in by_group.values() for _, i in v)
    if by_group:
        L.append(f"\n💰 <b>Bugun olinadigan to'lovlar</b> (shu oy uchun) — {n_due} talaba, jami {num(total)} so'm")
        for g in groups:
            cs = by_group.get(g.pk)
            if not cs:
                continue
            L.append(f"⏰ <b>{g.time.start_time:%H:%M}</b> · {e(g.name)} ({e(g.room)})")
            L += [f"  {'🔴' if i['overdue'] else '•'} {e(c.student.full_name)} — <b>{num(i['to_pay'])}</b> so'm · {phone(c.student.phone1)}"
                  for c, i in cs[:PER_GROUP]]
            if len(cs) > PER_GROUP:
                L.append(f"  <i>… yana {len(cs) - PER_GROUP} ta</i>")
    all_due = month_dues(Contract.objects.filter(branch=branch).filter(active_on(day)), day, day)
    over = [i for i in all_due.values() if i["overdue"]]
    if over:
        L.append(f"\n🔴 <b>Muddati o'tgan</b> (shu oy to'lovi) — {len(over)} talaba, jami {num(sum(i['to_pay'] for i in over))} so'm · Qarzdorlar → «Shu oy to'lovi»")

    # 2. Bugungi sinov darslari — qayta aloqa (eslatish)
    demos = (Lead.objects.filter(branch=branch, demo_date=day, status__in=["3", "4"]).select_related("student", "group__time", "group__course", "course")
             .order_by("group__time__start_time"))
    if demos:
        L.append(f"\n🧪 <b>Bugun sinov darsiga keladiganlar</b> — {len(demos)} ta, qo'ng'iroq qilib eslating")
        for ld in demos[:PER_LIST]:
            where = f"{ld.group.time.start_time:%H:%M} · {ld.group.name}" if ld.group_id else e(ld.course)
            L.append(f"  • {e(ld.student.full_name)} — {where} · {phone(ld.student.phone1)}")
        if len(demos) > PER_LIST:
            L.append(f"  <i>… yana {len(demos) - PER_LIST} ta</i>")

    # 3. Kelmaganlar bilan bog'lanish (oxirgi 7 kun, hali bog'lanilmagan)
    absent = (Attendance.objects.filter(branch=branch, status__in=["X", "0"], contact_status=Attendance.Contact.TO_CALL,
                                        date__gte=day - datetime.timedelta(days=7), date__lt=day)
              .filter(Q(contract__end_date__isnull=True) | Q(contract__end_date__gte=day))
              .select_related("contract__student", "group__course").order_by("-date"))
    absent = list(absent[:200])
    if absent:
        L.append(f"\n📞 <b>Kelmaganlar bilan bog'lanish</b> (oxirgi 7 kun) — {len(absent)} ta")
        for a in absent[:PER_LIST]:
            L.append(f"  • {e(a.contract.student.full_name)} — {e(a.group.name)}, {a.date:%d.%m} ({'besabab' if a.status == 'X' else 'sababli'}) · {phone(a.contract.student.phone1)}")
        if len(absent) > PER_LIST:
            L.append(f"  <i>… yana {len(absent) - PER_LIST} ta — Davomatlar → Kelmaganlar</i>")

    # 4. Qayta bog'lanish: muddati o'tganlar (vaqti belgilangan, bog'lanilmagan), bugunga rejalashtirilganlar va vaqti belgilanmagan 1-status lidlar
    start_of_day = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
    end_of_day = start_of_day + datetime.timedelta(days=1)
    base = Lead.objects.filter(branch=branch, status__in=["1", "8"]).select_related("student", "course")
    overdue = list(base.filter(callback_at__lt=start_of_day).order_by("callback_at")[:200])
    today_cb = list(base.filter(callback_at__gte=start_of_day, callback_at__lt=end_of_day).order_by("callback_at"))
    if overdue:
        L.append(f"\n⏰ <b>Muddati o'tgan qayta bog'lanishlar</b> — {len(overdue)} ta (vaqti o'tdi, qo'ng'iroq qilinmadi)")
        L += [f"  • {timezone.localtime(ld.callback_at):%d.%m %H:%M} · {e(ld.student.full_name)} — {e(ld.course)} · {phone(ld.student.phone1)}" for ld in overdue[:PER_LIST]]
        if len(overdue) > PER_LIST:
            L.append(f"  <i>… yana {len(overdue) - PER_LIST} ta</i>")
    if today_cb:
        L.append(f"\n🔁 <b>Bugun qayta bog'lanish rejalashtirilgan</b> — {len(today_cb)} ta (vaqtida bot eslatadi)")
        L += [f"  • {timezone.localtime(ld.callback_at):%H:%M} · {e(ld.student.full_name)} — {e(ld.course)} · {phone(ld.student.phone1)}" for ld in today_cb[:PER_LIST]]
    unnoted = list(base.filter(callback_talked_at__isnull=False).order_by("callback_talked_at")[:200])
    if unnoted:
        L.append(f"\n📝 <b>Gaplashilgan, izoh yozilmagan lidlar</b> — {len(unnoted)} ta")
        L += [f"  • {timezone.localtime(ld.callback_talked_at):%d.%m %H:%M} · {e(ld.student.full_name)} — {e(ld.course)} · {phone(ld.student.phone1)}" for ld in unnoted[:PER_LIST]]
        if len(unnoted) > PER_LIST:
            L.append(f"  <i>… yana {len(unnoted) - PER_LIST} ta</i>")
    callback = Lead.objects.filter(branch=branch, status="1", callback_at__isnull=True).select_related("student", "course").order_by("created_at")
    n_cb = callback.count()
    if n_cb:
        L.append(f"\n🔁 <b>Qayta bog'lanish kerak lidlar</b> — {n_cb} ta (vaqti belgilanmagan, eng eskilari)")
        L += [f"  • {e(ld.student.full_name)} — {e(ld.course)} · {phone(ld.student.phone1)}" for ld in callback[:10]]

    # 5. Kecha davomati olinmagan guruhlar
    y = day - datetime.timedelta(days=1)
    y_groups = _lesson_groups(y, branch)
    y_taken = set(Attendance.objects.filter(date=y, group__in=y_groups).values_list("group_id", flat=True))
    missing = [g for g in y_groups if g.pk not in y_taken]
    if missing:
        L.append(f"\n⚠️ <b>Kecha davomati olinmagan guruhlar</b> — {len(missing)} ta")
        L += [f"  • {e(g.name)} ({g.time.start_time:%H:%M}, {e(g.teacher)})" for g in missing]

    if len(L) <= 2:
        L.append("\nBugun alohida vazifa yo'q ✨")
    L.append(f"\n{link('dashboard')}")
    return "\n".join(L)


def morning_plan(day=None):
    day = day or timezone.localdate()
    n = 0
    for b in Branch.objects.filter(status="Faol"):
        services.notify_chunks("morning_plan", plan_text(b, day), branch=b, key=f"morning:{b.pk}:{day}")
        n += 1
    return n

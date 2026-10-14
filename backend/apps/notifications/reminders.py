"""Vaqtga bog'liq Telegram eslatmalari (buyurtmachi so'rovi 2026-10-14).

- `lesson_starts()` — dars boshlanganda guruh ustoziga «davomat olish vaqti» (bot jarayoni har daqiqada chaqiradi:
  alohida jarayon ochilmaydi, bitta-ikkita yengil so'rov).
- `morning_plan()` — ertalab 8:30 da administratorlarga bugungi ish rejasi (cron: `morning_plan` buyrug'i).
"""

import datetime
from collections import defaultdict
from html import escape

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.crm.models import Lead
from apps.education.models import Attendance, Contract, Group
from apps.education.services import FAOL, active_on, has_lesson, status_q, with_balance
from apps.references.models import Branch

from . import services

WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
START_WINDOW = 15  # daqiqa: bot qayta ishga tushsa ham shu oraliqda boshlangan dars eslatiladi
PER_GROUP = 12
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
        text = (f"🔔 <b>Dars vaqti — davomatni oling</b>\n{e(g.name)} · {g.time.start_time:%H:%M}–{g.time.end_time:%H:%M} · {e(g.room)}\n"
                f"{link(f'attendance?tab=take&group={g.pk}')}")
        services.lesson_started(g, text, key=f"start:{g.pk}:{today}")
        n += 1
    return n


# ------------------------------------------------------------------ ertalabki reja

def plan_text(branch, day):
    """Filial uchun bugungi tavsiya etilgan ishlar."""
    L = [f"📋 <b>Bugungi ish rejasi</b> · {day:%d.%m.%Y}, {WEEKDAYS[day.weekday()]}"]
    groups = sorted(_lesson_groups(day, branch), key=lambda g: (g.time.start_time, g.name))
    L.append(f"Bugun {len(groups)} ta dars." if groups else "Bugun dars yo'q.")

    # 1. To'lov kutilayotganlar: bugun darsi bor guruhlardagi qarzdorlar, dars vaqti bo'yicha
    debt = (with_balance(Contract.objects.filter(group__in=groups).filter(active_on(day))).filter(balance__gt=0)
            .select_related("student").order_by("-balance"))
    by_group = defaultdict(list)
    for c in debt:
        by_group[c.group_id].append(c)
    total = sum(c.balance for c in debt)
    if by_group:
        L.append(f"\n💰 <b>Olinadigan to'lovlar</b> — {len(debt)} talaba, jami {num(total)} so'm")
        for g in groups:
            cs = by_group.get(g.pk)
            if not cs:
                continue
            L.append(f"⏰ <b>{g.time.start_time:%H:%M}</b> · {e(g.name)} ({e(g.room)})")
            L += [f"  • {e(c.student.full_name)} — <b>{num(c.balance)}</b> so'm · {phone(c.student.phone1)}" for c in cs[:PER_GROUP]]
            if len(cs) > PER_GROUP:
                L.append(f"  <i>… yana {len(cs) - PER_GROUP} ta</i>")

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

    # 4. Qayta bog'lanish kerak lidlar
    callback = Lead.objects.filter(branch=branch, status="1").select_related("student", "course").order_by("created_at")
    n_cb = callback.count()
    if n_cb:
        L.append(f"\n🔁 <b>Qayta bog'lanish kerak lidlar</b> — {n_cb} ta (eng eskilari)")
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

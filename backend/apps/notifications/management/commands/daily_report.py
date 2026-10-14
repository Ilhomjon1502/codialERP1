"""Har kuni 19:00 da Bosh menejerga Telegram hisobot (buyurtmachi so'rovi 2026-10-14, CLAUDE.md 12):
to'lovlar, faol shartnomalar (kurslar bo'yicha), lidlar (kurslar va statuslar bo'yicha), bugungi xarajatlar, davomat,
g'azna qoldiqlari va tizim auditi (kim nima qildi). Hammasi aggregatsiya bilan — butun jadvallar aylanib chiqilmaydi.
Cron: 0 19 * * *

    python manage.py daily_report
"""

import html
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.core.models import AuditLog
from apps.crm.models import Lead
from apps.education.models import Attendance, Contract
from apps.education.services import FAOL, status_q
from apps.finance import services as fin
from apps.finance.models import Account, Expense, Payment
from apps.notifications import services

WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
OPEN_LEADS = ["1", "2", "3", "4", "8"]  # hali hal bo'lmagan bosqichlar
TOP = 10
LIMIT = 4000  # Telegram xabari 4096 belgigacha


def e(s):
    return html.escape(str(s or "—"), quote=False)  # Telegram HTML: < > & yetarli, apostrof o'zgarmasin


def num(n):
    return f"{int(n or 0):,}".replace(",", " ")


def ranked(rows, label, value=lambda r: r["n"]):
    """[(nom, son)] → «• nom — son» qatorlari, ko'pi bilan TOP ta + «yana N ta»."""
    rows = list(rows)
    out = [f"  • {e(label(r))} — <b>{num(value(r))}</b>" for r in rows[:TOP]]
    if len(rows) > TOP:
        out.append(f"  <i>… yana {len(rows) - TOP} ta</i>")
    return out


def build(day):
    L = []
    L.append(f"📊 <b>Kunlik hisobot</b> · {day:%d.%m.%Y}, {WEEKDAYS[day.weekday()]}")

    # To'lovlar
    pays = Payment.objects.filter(date=day)
    agg = pays.aggregate(s=Sum("amount"), n=Count("id"), cash=Sum("amount", filter=Q(cash_type="CASH")), d=Sum("discount"))
    total, cash = agg["s"] or 0, agg["cash"] or 0
    L.append(f"\n💰 <b>To'lovlar: {services.money(total)}</b> ({agg['n']} ta)")
    L.append(f"  naqd {num(cash)} · naqdsiz {num(total - cash)}" + (f" · chegirma {num(agg['d'])}" if agg["d"] else ""))

    # Faol shartnomalar — kurslar bo'yicha
    active = Contract.objects.filter(status_q(FAOL, day))
    new = Contract.objects.filter(created_at__date=day).count()
    stopped = Contract.objects.filter(end_date=day).count()
    L.append(f"\n📝 <b>Faol shartnomalar: {num(active.count())}</b> (bugun +{new} yangi, −{stopped} to'xtatildi)")
    L += ranked(active.values("course__name").annotate(n=Count("id")).order_by("-n", "course__name"), lambda r: r["course__name"])

    # Lidlar — statuslar va kurslar bo'yicha
    leads = Lead.objects.all()
    today_new = leads.filter(created_at__date=day).count()
    open_leads = leads.filter(status__in=OPEN_LEADS)
    L.append(f"\n🎯 <b>Lidlar</b>: bugun +{today_new} yangi · ochiq {num(open_leads.count())} · jami {num(leads.count())}")
    by_status = dict(leads.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    L.append("  <i>Holat bo'yicha:</i>")
    L += [f"  {v}. {e(label)} — <b>{num(by_status[v])}</b>" for v, label in Lead.LeadStatus.choices if by_status.get(v)]
    matrix = defaultdict(dict)
    for course, st, n in open_leads.values_list("course__name", "status").annotate(n=Count("id")).values_list("course__name", "status", "n"):
        matrix[course or "Kurssiz"][st] = n
    if matrix:
        L.append("  <i>Ochiq lidlar kurs bo'yicha</i> (holat: soni):")
        rows = sorted(matrix.items(), key=lambda kv: -sum(kv[1].values()))
        for course, sts in rows[:TOP]:
            parts = " · ".join(f"{s}: {sts[s]}" for s in OPEN_LEADS if sts.get(s))
            L.append(f"  • {e(course)} — <b>{sum(sts.values())}</b> ({parts})")
        if len(rows) > TOP:
            L.append(f"  <i>… yana {len(rows) - TOP} ta kurs</i>")

    # Xarajatlar
    exps = Expense.objects.filter(date=day)
    ex = exps.aggregate(s=Sum("total"), n=Count("id"))
    L.append(f"\n💸 <b>Xarajatlar: {services.money(ex['s'])}</b> ({ex['n']} ta)")
    L += ranked(exps.values("category__name").annotate(n=Sum("total")).order_by("-n"), lambda r: r["category__name"])

    # Davomat
    att = Attendance.objects.filter(date=day).aggregate(all=Count("id"), x=Count("id", filter=Q(status="X")), z=Count("id", filter=Q(status="0")),
                                                       k=Count("id", filter=Q(status="1")))
    if att["all"]:
        pct = round(100 * att["k"] / att["all"]) if att["all"] else 0
        L.append(f"\n✅ <b>Davomat</b>: {att['all']} ta belgi · keldi {pct}% · besabab {att['x']} · sababli {att['z']}")

    # G'azna qoldiqlari
    accs = list(Account.objects.filter(status="Faol").order_by("name"))
    if accs:
        bal = fin.balances([a.pk for a in accs])
        L.append("\n🏦 <b>G'azna qoldiqlari</b>")
        L += [f"  • {e(a.name)} — <b>{services.money(bal[a.pk]['balance'])}</b>" for a in accs]

    # Tizim auditi
    logs = AuditLog.objects.filter(at__date=day)
    acts = dict(logs.values_list("action").annotate(n=Count("id")).values_list("action", "n"))
    labels = dict(AuditLog.Action.choices)
    total_acts = sum(acts.values())
    L.append(f"\n🔍 <b>Tizim auditi: {num(total_acts)} amal</b>")
    if total_acts:
        L.append("  " + " · ".join(f"{labels.get(k, k).lower()} {n}" for k, n in sorted(acts.items(), key=lambda kv: -kv[1])))
        per_user = logs.exclude(action__in=["login", "logout"]).values("user__full_name").annotate(
            n=Count("id"), c=Count("id", filter=Q(action="create")), u=Count("id", filter=Q(action="update")), d=Count("id", filter=Q(action="delete"))).order_by("-n")
        if per_user:
            L.append("  <i>Xodimlar bo'yicha</i> (✚ yaratdi · ✎ o'zgartirdi · ✖ o'chirdi):")
            for r in per_user[:TOP]:
                L.append(f"  • {e(r['user__full_name'] or 'Tizim')} — <b>{r['n']}</b> (✚{r['c']} ✎{r['u']} ✖{r['d']})")
        by_model = logs.exclude(action__in=["login", "logout"]).values("model").annotate(n=Count("id")).order_by("-n")[:6]
        if by_model:
            L.append("  <i>Bo'limlar:</i> " + " · ".join(f"{e(r['model'])} {r['n']}" for r in by_model))
        deleted = logs.filter(action="delete").select_related("user").order_by("-at")[:5]
        if deleted:
            L.append("  <i>O'chirilganlar:</i>")
            L += [f"  ✖ {e(d.model)}: {e(d.object_repr)} — {e(d.user.full_name if d.user else 'Tizim')}, {timezone.localtime(d.at):%H:%M}" for d in deleted]
        logins = logs.filter(action="login").values("user").distinct().count()
        if logins:
            L.append(f"  Bugun tizimga kirgan xodimlar: {logins}")

    text = "\n".join(L)
    if len(text) > LIMIT:
        text = text[: LIMIT - 40].rsplit("\n", 1)[0] + "\n<i>… hisobot qisqartirildi</i>"
    return text


class Command(BaseCommand):
    help = "Bosh menejerlarga kunlik Telegram hisobot (19:00)"

    def add_arguments(self, parser):
        parser.add_argument("--print", action="store_true", help="Yubormasdan ekranga chiqarish")

    def handle(self, *args, **opts):
        day = timezone.localdate()
        text = build(day)
        if opts["print"]:
            self.stdout.write(text)
            return
        services.daily_report(text, key=f"daily:{day}")
        self.stdout.write("Kunlik hisobot navbatga qo'yildi (Bosh menejer va hisobotni tanlagan, audit huquqi bor xodimlarga)")

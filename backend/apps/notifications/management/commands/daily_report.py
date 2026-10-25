"""Har kuni 19:00 da Bosh menejerga Telegram hisobot (buyurtmachi so'rovi 2026-10-14, CLAUDE.md 12):
to'lovlar, faol shartnomalar (kurslar bo'yicha), lidlar (kurslar va statuslar bo'yicha), qo'ng'iroqlar, bugungi xarajatlar, davomat,
g'azna qoldiqlari va tizim auditi (kim nima qildi). Hammasi aggregatsiya bilan — butun jadvallar aylanib chiqilmaydi.
Cron: 0 19 * * *

    python manage.py daily_report
"""

import datetime
import html
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.calls import services as call_services
from apps.calls.models import CallDevice, CallRecord
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


def day_updates(day, model):
    """Shu kuni `model` bo'yicha O'ZGARTIRILDI audit yozuvlari: {yozuv_id: [(maydon, eski, yangi), ...]} (vaqt tartibida)."""
    out = defaultdict(list)
    qs = AuditLog.objects.filter(at__date=day, model=model, action=AuditLog.Action.UPDATE).order_by("at").values_list("object_id", "changes")
    for oid, changes in qs:
        for field, old, new in changes or []:
            out[oid].append((field, old, new))
    return out


def stopped_contracts(day):
    """Bugun to'xtatilgan shartnomalar: tugash sanasi bugun kiritilganlar (sanasi qaysi kun bo'lishidan qat'i nazar)."""
    return sum(1 for ch in day_updates(day, "Shartnoma").values() if any(f == "end_date" and not old and new for f, old, new in ch))


def lead_moves(day):
    """Bugun holati o'zgargan lidlar: {yangi holat: soni} (kun ichidagi birinchi eski va oxirgi yangi holat bo'yicha)."""
    moved = Counter()
    for ch in day_updates(day, "Lid").values():
        st = [(old, new) for f, old, new in ch if f == "status"]
        if st and st[0][0] != st[-1][1]:
            moved[st[-1][1]] += 1
    return moved


def calls_section(day, brief=False):
    """Qabul telefonidagi qo'ng'iroqlar (2026-10-19): jami, javobsiz qolganlar (kimga qayta qo'ng'iroq qilish kerak),
    qayta javob vaqti, yangi raqamlar va lid manbalari. Qurilma ulanmagan bo'lsa — bo'lim chiqmaydi.
    `brief` — faqat bitta jamlama qator (asoschi uchun)."""
    devices = list(CallDevice.objects.filter(status="Faol"))
    if not devices:
        return []
    qs = CallRecord.objects.filter(started_at__date=day)
    s = call_services.stats(qs)
    D = CallRecord.Direction
    L = [f"\n📞 <b>Qo'ng'iroqlar: {num(s['total'])}</b> (kiruvchi {s['answered']} · chiquvchi {s['outgoing']} · javobsiz {s['missed']})"
         + (f" · suhbat {num(s['talk'] // 60)} daq, o'rtacha {s['avg_talk'] // 60}:{s['avg_talk'] % 60:02d}, eng uzuni {s['longest'] // 60}:{s['longest'] % 60:02d}"
            if s["talk"] else "")]
    if brief:
        return L
    for title, c in (("Eng uzun", s["longest_call"]), ("Eng qisqa", s["shortest_call"])):
        if c:
            who = c["name"] or (f"+998{c['phone']}" if c["phone"] else c["number"] or "yashirin raqam")
            L.append(f"  {title} suhbat: <b>{c['duration'] // 60}:{c['duration'] % 60:02d}</b> — {e(who)}"
                     + (f" · +998{c['phone']}" if c["name"] and c["phone"] else ""))
    if s["missed"]:
        wait = f", o'rtacha {s['callback_minutes']} daqiqada" if s["callback_minutes"] is not None else ""
        L.append(f"  Javobsizlarga qayta bog'lanildi: {s['missed'] - s['missed_open']} ta{wait}")
    missed = list(qs.filter(direction__in=[D.MISSED, D.REJECTED], callback_at__isnull=True)
                  .select_related("student", "parent").order_by("started_at"))
    if missed:
        L.append(f"  ❗ <b>Javobsiz qoldi: {len(missed)}</b> (qayta qo'ng'iroq qilinmagan)")
        for r in missed[:TOP]:
            who = r.student.full_name if r.student_id else str(r.parent) if r.parent_id else r.contact_name or "noma'lum"
            phone = f"+998{r.phone}" if r.phone else r.number or "yashirin raqam"
            L.append(f"  • {timezone.localtime(r.started_at):%H:%M} {e(phone)} — {e(who)}")
        if len(missed) > TOP:
            L.append(f"  <i>… yana {len(missed) - TOP} ta</i>")
    if s["new_numbers"]:
        L.append(f"  Yangi raqamlar: <b>{s['new_numbers']}</b> (bazada yo'q: {s['unknown']})")
    if s["by_source"]:
        L.append("  <i>Lid manbasi bo'yicha</i> (raqamlar):")
        L += ranked(s["by_source"], lambda r: r["name"], lambda r: r["numbers"])
    now = timezone.now()
    for d in devices:
        if not d.last_seen_at or now - d.last_seen_at > datetime.timedelta(hours=6):
            seen = f"{timezone.localtime(d.last_seen_at):%d.%m %H:%M}" if d.last_seen_at else "hech qachon"
            L.append(f"  ⚠️ {e(d.name)} aloqaga chiqmayapti (oxirgi: {seen}) — telefonda ilova va internetni tekshiring")
    return L


def fit(text):
    if len(text) > LIMIT:
        text = text[: LIMIT - 40].rsplit("\n", 1)[0] + "\n<i>… hisobot qisqartirildi</i>"
    return text


def build(day, short=False):
    """To'liq hisobot (Bosh menejer) yoki `short=True` — asoschi uchun qisqa: lidlarning holat/kurs bo'yicha taqsimoti,
    qo'ng'iroq tafsilotlari va tizim auditi yo'q (2026-10-25)."""
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
    new = Contract.objects.filter(Q(created_at__date=day) | Q(start_date=day)).count()  # bugun qo'shilgan yoki bugun boshlangan
    stopped = stopped_contracts(day)
    L.append(f"\n📝 <b>Faol shartnomalar: {num(active.count())}</b> (bugun +{new} yangi, −{stopped} to'xtatildi)")
    L += ranked(active.values("course__name").annotate(n=Count("id")).order_by("-n", "course__name"), lambda r: r["course__name"])

    # Lidlar — statuslar va kurslar bo'yicha
    leads = Lead.objects.all()
    today_new = leads.filter(created_at__date=day).count()
    open_leads = leads.filter(status__in=OPEN_LEADS)
    L.append(f"\n🎯 <b>Lidlar</b>: bugun +{today_new} yangi · ochiq {num(open_leads.count())} · jami {num(leads.count())}")
    by_status = dict(leads.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    moved = lead_moves(day)
    if moved:
        names = dict(Lead.LeadStatus.choices)
        parts = " · ".join(f"{st}. {e(names.get(st, st))} — {n}" for st, n in sorted(moved.items()))
        L.append(f"  <i>Bugun holati o'zgardi: {sum(moved.values())} ta</i> ({parts})")
    if not short:
        L.append("  <i>Holat bo'yicha:</i>")
        L += [f"  {v}. {e(label)} — <b>{num(by_status[v])}</b>" for v, label in Lead.LeadStatus.choices if by_status.get(v)]
    matrix = defaultdict(dict)
    for course, st, n in open_leads.values_list("course__name", "status").annotate(n=Count("id")).values_list("course__name", "status", "n"):
        matrix[course or "Kurssiz"][st] = n
    if matrix and not short:
        L.append("  <i>Ochiq lidlar kurs bo'yicha</i> (holat: soni):")
        rows = sorted(matrix.items(), key=lambda kv: -sum(kv[1].values()))
        for course, sts in rows[:TOP]:
            parts = " · ".join(f"{s}: {sts[s]}" for s in OPEN_LEADS if sts.get(s))
            L.append(f"  • {e(course)} — <b>{sum(sts.values())}</b> ({parts})")
        if len(rows) > TOP:
            L.append(f"  <i>… yana {len(rows) - TOP} ta kurs</i>")

    L += calls_section(day, brief=short)

    # Xarajatlar
    exps =Expense.objects.filter(date=day)
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

    if short:  # asoschi hisobotida tizim auditi yo'q
        return fit("\n".join(L))

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

    return fit("\n".join(L))


class Command(BaseCommand):
    help = "Bosh menejerlarga kunlik Telegram hisobot (19:00)"

    def add_arguments(self, parser):
        parser.add_argument("--print", action="store_true", help="Yubormasdan ekranga chiqarish")
        parser.add_argument("--short", action="store_true", help="Asoschi uchun qisqa ko'rinish (--print bilan)")

    def handle(self, *args, **opts):
        day = timezone.localdate()
        if opts["print"]:
            self.stdout.write(build(day, short=opts["short"]))
            return
        services.daily_report(build(day), key=f"daily:{day}")
        services.notify("founder_report", build(day, short=True), key=f"founder:{day}")  # asoschiga — faqat shu, qisqa ko'rinishda
        self.stdout.write("Kunlik hisobot navbatga qo'yildi (Bosh menejer va hisobotni tanlagan xodimlarga; asoschiga qisqa ko'rinishda)")

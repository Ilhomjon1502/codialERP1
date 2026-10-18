"""M11 o'tish kuni (buyurtmachi qarori 2026-10-18): faol shartnomalarga qo'shimcha ravishda ko'chiriladi —
boshlang'ich qarz (AppSheet formulasi bo'yicha), ochiq lidlar (1–4, 8) va izohlari, lid manbalari, oktyabr–noyabr kurs narxlari
va oydagi dars soni, oktyabr KPI stavkalari, g'azna qoldiqlari (pul turlari bo'yicha). Yangi tizimda o'tish sanasidan oldin
olingan (AppSheet'da ham bor) davomat qatorlari o'chiriladi — qarz ikki marta hisoblanmasin.

AppSheet formulalari (codial_appdoc.json):
- Attendance.StudentDebt = Status="-" yoki Grant → 0, aks holda CoursePrices[filial+kurs+yil+oy].Price / LessonFrequency(yil, oy, dars kunlari, filial, kurs).Frequency
- Contracts.ContractDebt = Σ StudentDebt − Σ Payments.Summa − Σ Payments.Discount
- Accounts.Now = InitialBalance + to'lovlar + kiruvchi o'tkazmalar (tasdiqlangan) ± ayirboshlash − xarajatlar − oyliklar − chiquvchi o'tkazmalar − kreditor amallari"""

import collections
import datetime
import re
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Status
from apps.crm.models import Lead, LeadComment
from apps.education import calc
from apps.education.models import Attendance, Contract
from apps.finance.models import Account, CashMovement
from apps.payroll.models import KPIRate
from apps.references.models import Course, CoursePrice, LeadSource, LessonFrequency

from . import reader as r

EXTRA_SHEETS = ["Attendance", "Payments", "CoursePrices", "LessonFrequency", "Leads", "LeadSources", "LeadComments", "TeacherKPI",
                "Accounts", "Transactions", "Expenses", "SalaryGiving", "CashFlow", "Exchange"]
MONTHS = [(2026, 10), (2026, 11)]  # narx va dars soni
KPI_MONTHS = [(2026, 10), (2026, 11)]
OPEN_LEADS = {"1", "2", "3", "4", "8"}
TYPES = {"Cash": "CASH", "Card": "CARD", "Bank": "BANK"}
ONE = Decimal(1)


def num(v):
    try:
        return Decimal(str(v)) if v not in (None, "") else Decimal(0)
    except Exception:  # noqa: BLE001
        return Decimal(0)


def ym(row, y="Year", m="Month"):
    return r.integer(row.get(y)), r.integer(row.get(m))


def month_start(y, m):
    return datetime.date(y, m, 1)


def run_all(wb, on, rep, branch, bid, h):
    drop_new_attendance(branch, on, rep)
    opening_balances(wb, branch, rep)
    sources = lead_sources(wb, rep)
    leads(wb, bid, branch, rep, h, sources)
    prices_and_frequencies(wb, bid, branch, rep, h)
    kpi_rates(wb, bid, branch, rep, h)
    accounts(wb, on, rep)


# ------------------------------------------------------------------ davomat (yangi tizimdagi o'tish oldi qatorlari)

def drop_new_attendance(branch, on, rep):
    qs = Attendance.objects.filter(branch=branch, legacy_id=None, date__lt=on)
    n = qs.update(is_deleted=True, updated_at=timezone.now())
    rep.checks["O'chirilgan davomat (yangi tizimda, o'tish sanasidan oldin)"] = n


# ------------------------------------------------------------------ boshlang'ich qarz

def opening_balances(wb, branch, rep):
    contracts = {r.ident(c.get("ContractID")): c for c in wb["Contracts"]}
    prices = {}
    for p in wb["CoursePrices"]:
        prices.setdefault(r.text(p.get("ToExport")), num(p.get("Price")))  # LOOKUP — birinchi mos qator
    freqs = collections.defaultdict(list)
    for f in wb["LessonFrequency"]:
        freqs[(*ym(f), r.ident(f.get("DayID")), r.ident(f.get("BranchID")))].append(f)

    def frequency(a):
        for f in freqs.get((*ym(a), r.ident(a.get("DayID")), r.ident(a.get("BranchID"))), []):
            if r.ident(a.get("CourseID")) in r.ids(f.get("CourceID")):
                return r.integer(f.get("Frequency"))
        return None

    ours = {c.legacy_id: c for c in Contract.objects.filter(branch=branch).exclude(legacy_id=None)}
    charged, missing, fcache = collections.Counter(), collections.Counter(), {}
    for a in wb["Attendance"]:
        cid = r.ident(a.get("ContractID"))
        if cid not in ours or r.text(a.get("Status")) == "-" or r.text((contracts.get(cid) or {}).get("ContractType")) == "Grant":
            continue
        y, m = ym(a)
        price = prices.get(f"{r.ident(a.get('BranchID'))}{r.ident(a.get('CourseID'))}{y}{m}")
        fk = (y, m, r.ident(a.get("DayID")), r.ident(a.get("BranchID")), r.ident(a.get("CourseID")))
        if fk not in fcache:
            fcache[fk] = frequency(a)
        if price is None or not fcache[fk]:
            missing[f"{y}-{m:02d}"] += 1
            continue
        charged[cid] += price / fcache[fk]
    paid = collections.Counter()
    for p in wb["Payments"]:
        cid = r.ident(p.get("ContractID"))
        if cid in ours:
            paid[cid] += num(p.get("Summa")) + num(p.get("Discount"))
    debt, over, n_debt, n_over = Decimal(0), Decimal(0), 0, 0
    for cid, c in ours.items():
        bal = Decimal(charged[cid] - paid[cid]).quantize(ONE, rounding=ROUND_HALF_UP)
        Contract.all_objects.filter(pk=c.pk).update(opening_balance=bal)
        if bal > 0:
            debt, n_debt = debt + bal, n_debt + 1
        elif bal < 0:
            over, n_over = over + bal, n_over + 1
    if missing:
        rep.warn(f"Narx yoki oydagi dars soni topilmagan davomat qatorlari (qarzga kirmadi, AppSheet'da ham bo'sh): {dict(missing)}")
    rep.checks["Boshlang'ich qarz: qarzdorlar"] = f"{n_debt} ta, jami {debt:,.0f} so'm".replace(",", " ")
    rep.checks["Boshlang'ich qarz: oldindan to'laganlar"] = f"{n_over} ta, jami {over:,.0f} so'm".replace(",", " ")


# ------------------------------------------------------------------ lidlar

def lead_sources(wb, rep):
    out = {}
    for s in wb["LeadSources"]:
        sid, name = r.ident(s.get("SourceID")), r.text(s.get("Name"))[:100]
        if not sid or not name:
            continue
        obj = LeadSource.objects.filter(legacy_id=sid).first() or LeadSource.objects.filter(name=name).first()
        created = obj is None
        if created:
            obj = LeadSource.objects.create(legacy_id=sid, name=name, status=Status.ACTIVE)
        elif obj.legacy_id != sid:
            obj.legacy_id = sid
            obj.save(update_fields=["legacy_id"])
        rep.count("Lid manbalari", created)
        out[sid] = obj
    return out


def _by_email(emails):
    users = {u.email.lower(): u for u in User.objects.exclude(email=None).exclude(email="")}
    return lambda v: users.get(r.text(v).lower())


def leads(wb, bid, branch, rep, h, sources):
    from .services import _keep_created

    author = _by_email(None)
    today = timezone.localdate()
    done = {}
    for x in wb["Leads"]:
        if r.ident(x.get("BranchID")) != bid:
            continue
        status = r.text(x.get("Status"))[:1]
        if status not in OPEN_LEADS:
            continue
        lid = r.ident(x.get("LeadID"))
        try:
            with transaction.atomic():
                src = sources.get(r.ident(x.get("SourceID")))
                if src is None:
                    src = LeadSource.objects.get_or_create(name="Noma'lum manba", defaults={"status": Status.INACTIVE})[0]
                    rep.warn(f"Lid {lid}: manbasi topilmadi — «Noma'lum manba»")
                student = h.student(r.ident(x.get("StudentID")))
                group = None
                gid = r.ident(x.get("GroupID"))
                if gid and status in ("3", "4", "5"):
                    group = h.group(gid)
                    if group.end_date and group.end_date < today:
                        group = None
                did = r.ident(x.get("DayID"))
                demo = r.text(x.get("Demo_Come"))
                values = {
                    "branch": branch, "student": student, "source": src, "course": h.course(r.ident(x.get("CourseID"))),
                    "day_pattern": h.pattern(did) if did else None, "status": status, "group": group,
                    "demo_date": r.date(x.get("DemoDate")), "demo_attended": {"True": True, "False": False}.get(demo),
                    "age_group": r.text(x.get("AgeGroup"))[:5], "social_status": r.text(x.get("StudentSocialStatus"))[:32],
                    "laptop": r.text(x.get("Noutbook"))[:12], "tags": [t for t in (p.strip() for p in str(x.get("Tags") or "").split(",")) if t],
                    "created_by": author(x.get("CreatedBy")),
                }
                obj = Lead.objects.filter(legacy_id=lid).first() or Lead.objects.filter(branch=branch, student=student).first()
                created = obj is None
                if created:
                    obj = Lead(legacy_id=lid, **values)
                else:
                    obj.legacy_id = lid
                    for k, v in values.items():
                        setattr(obj, k, v)
                obj.save()
                obj.preferred_times.set([h.lesson_time(t) for t in r.ids(x.get("TimeID"))])
                _keep_created(Lead, obj, x.get("CreatedTime"))
                rep.count("Lidlar (ochiq)", created)
                if student.contracts.filter(end_date__isnull=True).exists():
                    rep.warn(f"Lid {lid} (status {status}): talabaning faol shartnomasi bor — lid baribir ko'chirildi, tekshiring")
                done[lid] = obj
        except Exception as e:  # noqa: BLE001
            h.reset()
            rep.error(f"Lid {lid}: {e}")
    for c in wb["LeadComments"]:
        lead = done.get(r.ident(c.get("LeadID")))
        text = r.text(c.get("Comment"))
        if not lead or not text:
            continue
        cid = r.ident(c.get("CommentID"))
        obj = LeadComment.objects.filter(legacy_id=cid).first()
        created = obj is None
        if created:
            obj = LeadComment.objects.create(legacy_id=cid, lead=lead, comment=text, created_by=author(c.get("CreatedBy")))
        else:
            obj.comment = text
            obj.save(update_fields=["comment"])
        _keep_created(LeadComment, obj, c.get("CreatedTime"))
        rep.count("Lid izohlari", created)
    rep.checks["Ochiq lidlar (Excel)"] = sum(1 for x in wb["Leads"] if r.ident(x.get("BranchID")) == bid and r.text(x.get("Status"))[:1] in OPEN_LEADS)
    rep.checks["Ochiq lidlar (tizimda)"] = Lead.objects.filter(branch=branch, status__in=OPEN_LEADS).count()


# ------------------------------------------------------------------ narxlar, oydagi dars soni, KPI

def _db_course(cid):
    return Course.objects.filter(legacy_id=cid).first()


def prices_and_frequencies(wb, bid, branch, rep, h):
    for p in wb["CoursePrices"]:
        y, m = ym(p)
        if r.ident(p.get("BranchID")) != bid or (y, m) not in MONTHS:
            continue
        course = _db_course(r.ident(p.get("CourseID")))
        if course is None:
            continue  # bu kursda faol guruh/lid yo'q
        eff = month_start(y, m)
        obj = CoursePrice.objects.filter(branch=branch, course=course, effective_from=eff).first()
        created = obj is None
        if created:
            obj = CoursePrice(branch=branch, course=course, effective_from=eff)
        obj.legacy_id, obj.price = r.ident(p.get("PriceID")), num(p.get("Price"))
        obj.save()
        rep.count("Kurs narxlari", created)
    now = timezone.now()
    for f in wb["LessonFrequency"]:
        y, m = ym(f)
        if r.ident(f.get("BranchID")) != bid or (y, m) not in MONTHS:
            continue
        courses = [c for c in (_db_course(x) for x in r.ids(f.get("CourceID"))) if c]
        freq = r.integer(f.get("Frequency"))
        if not courses:
            continue
        if not freq or not 4 <= freq <= 26:
            rep.warn(f"Oydagi dars soni {y}-{m:02d}: {freq} — 4–26 oralig'ida emas, ko'chirilmadi")
            continue
        pattern = h.pattern(r.ident(f.get("DayID")))
        # Yangi tizimda qo'lda kiritilganlari bilan to'qnashmasin: shu kurslar ulardan olib tashlanadi
        for old in LessonFrequency.objects.filter(branch=branch, day_pattern=pattern, year=y, month=m, legacy_id=None):
            old.courses.remove(*courses)
            if not old.courses.exists():
                old.is_deleted = True
                old.save(update_fields=["is_deleted"])
        lid = r.ident(f.get("FrequenceID"))
        obj = LessonFrequency.objects.filter(legacy_id=lid).first()
        created = obj is None
        if created:
            obj = LessonFrequency(legacy_id=lid, branch=branch, day_pattern=pattern, year=y, month=m)
        obj.frequency, obj.status, obj.approved_at = freq, LessonFrequency.FreqStatus.APPROVED, obj.approved_at or now
        obj.save()
        obj.courses.set(courses)
        rep.count("Oydagi dars soni", created)
    first = month_start(*MONTHS[0])
    priced = set(CoursePrice.objects.filter(branch=branch, effective_from__lte=first).values_list("course_id", flat=True))
    for crs in Course.objects.filter(contracts__branch=branch, contracts__end_date__isnull=True, contracts__type=Contract.Type.PAID).exclude(pk__in=priced).distinct():
        rep.warn(f"Kurs «{crs.name}»: {first:%m.%Y} uchun narx yo'q — bu kursda yangi davomatga qarz yozilmaydi. Sozlamalar → Kurs narxlari'da kiriting")
    n = calc.recalculate(Attendance.objects.filter(branch=branch, date__gte=first))
    rep.checks["Kurs narxlari (okt–noy)"] = CoursePrice.objects.filter(branch=branch, effective_from__gte=month_start(*MONTHS[0])).count()
    rep.checks["Oydagi dars soni (okt–noy, tasdiqlangan)"] = LessonFrequency.objects.filter(branch=branch, year=2026, month__gte=10, status="Tasdiqlangan").count()
    rep.checks["Qayta hisoblangan davomat qatorlari"] = n


def kpi_rates(wb, bid, branch, rep, h):
    for k in wb["TeacherKPI"]:
        y, m = ym(k)
        if r.ident(k.get("BranchID")) != bid or (y, m) not in KPI_MONTHS:
            continue
        kid = r.ident(k.get("KPIID"))
        try:
            with transaction.atomic():
                role = KPIRate.RoleType.SUPPORTER if r.text(k.get("Status")) == "Yordamchi" else KPIRate.RoleType.TEACHER
                user = h.user(r.ident(k.get("TeacherSupporter")), "supporter" if role == KPIRate.RoleType.SUPPORTER else "teacher")
                course = h.course(r.ident(k.get("CourseID")))
                kind = KPIRate.Kind.PERCENT if r.text(k.get("Type")) == "Foiz" else KPIRate.Kind.FIXED
                key = {"branch": branch, "user": user, "role_type": role, "course": course, "effective_from": month_start(y, m)}
                obj = KPIRate.objects.filter(legacy_id=kid).first() or KPIRate.objects.filter(**key).first()
                created = obj is None
                if created:
                    obj = KPIRate(**key)
                obj.legacy_id, obj.type, obj.fixed_amount, obj.percent = kid, kind, num(k.get("Fixed")), num(k.get("Percent"))
                obj.save()
                rep.count("KPI stavkalari", created)
        except Exception as e:  # noqa: BLE001
            h.reset()
            rep.error(f"KPI stavkasi {kid}: {e}")
    if KPIRate.objects.filter(branch=branch, effective_from__gte=month_start(*KPI_MONTHS[0])).exists():
        calc.recalc_from(month_start(*KPI_MONTHS[0]), branch=branch)


# ------------------------------------------------------------------ g'azna qoldiqlari

def _norm(name):
    return re.sub(r"[^a-z]", "", r.text(name).lower().replace("g'azna", "").replace("gʻazna", "").replace("kassasi", ""))


def accounts(wb, on, rep):
    """Har bir faol g'azna uchun pul turlari bo'yicha bugungi qoldiq → boshlang'ich jurnal qatorlari (manba «Boshlang'ich qoldiq»)."""
    bal = collections.defaultdict(collections.Counter)  # account → {Cash/Card/Bank/"": summa}
    for p in wb["Payments"]:
        bal[r.ident(p.get("Cashbox"))][r.text(p.get("Type"))] += num(p.get("Summa"))
    for t in wb["Transactions"]:
        if r.text(t.get("ConfirmationStatus")) != "Tasdiqlandi":
            continue
        s, ct = num(t.get("Sum")), r.text(t.get("PaymentType"))
        bal[r.ident(t.get("RecieverCashbox"))][ct] += s
        bal[r.ident(t.get("SenderCashbox"))][ct] -= s
    for x in wb["Exchange"]:
        a = r.ident(x.get("Cashbox"))
        bal[a][r.text(x.get("CashTypeTo"))] += num(x.get("SummaTo"))
        bal[a][r.text(x.get("CashTypeFrom"))] -= num(x.get("Summa"))
    for sheet, acc, ct, amt in (("Expenses", "Cashbox", "TypeID", "Summa"), ("SalaryGiving", "CashBox", "CashType", "Summa"), ("CashFlow", "Cashbox", "CashType", "Summa")):
        for x in wb[sheet]:
            bal[r.ident(x.get(acc))][r.text(x.get(ct))] -= num(x.get(amt))
    ours = list(Account.objects.all())
    for a in wb["Accounts"]:
        aid, name, kind = r.ident(a.get("AccountID")), r.text(a.get("Name")), r.text(a.get("Cashtype"))
        if r.text(a.get("Status")) != "Faol":
            continue
        acc = next((x for x in ours if x.legacy_id == aid), None) or next((x for x in ours if _norm(x.name) == _norm(name)), None)
        if acc is None:
            rep.warn(f"G'azna «{name}» tizimda topilmadi — qoldig'i ko'chirilmadi")
            continue
        b = bal[aid]
        by_type = {code: b[t] for t, code in TYPES.items()} if kind == "All" else {TYPES.get(kind, "CASH"): b[kind]}
        if kind == "All":
            untyped = sum(v for t, v in b.items() if t not in TYPES)  # turi bo'sh eski yozuvlar — naqdga
            by_type["CASH"] += untyped
        by_type["CASH" if kind == "All" else TYPES.get(kind, "CASH")] += num(a.get("InitialBalance"))
        CashMovement.objects.filter(account=acc, source_type=CashMovement.Source.OPENING).delete()
        CashMovement.objects.bulk_create(
            CashMovement(account=acc, cash_type=ct, amount=v.quantize(ONE, rounding=ROUND_HALF_UP), date=on, source_type=CashMovement.Source.OPENING,
                         source_id=acc.pk, is_confirmed=True, note="AppSheet'dan boshlang'ich qoldiq")
            for ct, v in by_type.items() if v)
        if acc.legacy_id != aid:
            acc.legacy_id = aid
            acc.save(update_fields=["legacy_id"])
        parts = ", ".join(f"{ct}: {v:,.0f}".replace(",", " ") for ct, v in by_type.items())
        rep.checks[f"G'azna «{acc.name}»"] = f"jami {sum(by_type.values()):,.0f} so'm ({parts})".replace(",", " ")

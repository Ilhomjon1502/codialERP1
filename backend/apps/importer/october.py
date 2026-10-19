"""2026-10-19: oktyabr oyini ham yangi tizimda yopamiz (oylik, foyda) — AppSheet'dan 01.10.2026 dan boshlab davomat, to'lov, xarajat,
o'tkazma, ayirboshlash, kreditor amallari va oyliklar ko'chiriladi. Qoldiqlar (shartnoma qarzi, g'azna, kreditor, xodim oyligi) — 01.10 holatida.

Qayta ishga tushirilsa xavfsiz: har qator `legacy_id` bilan yangilanadi; yangi tizimda qo'lda kiritilgan (legacy_id yo'q) bir xil qator
(shartnoma+sana+summa va h.k.) topilsa — yangisi yaratilmaydi, mavjudiga AppSheet kaliti yoziladi (ikkala tizimda ishlash davrida dublikat bo'lmasin)."""

import collections
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Max, Q, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.education import calc
from apps.education.models import Attendance, Contract
from apps.finance import services as fin
from apps.finance.models import Account, CashMovement, CashType, Confirm, Creditor, CreditorTransaction, Exchange, Expense, Payment, Transfer
from apps.payroll import services as pay
from apps.payroll.models import SalaryAssignment, SalaryPayout
from apps.references.models import DiscountType, ExpenseCategory

from . import reader as r

CUT = datetime.date(2026, 10, 1)  # shu sanadan boshlab qatorlar ko'chadi, undan oldingisi — qoldiq
FIRST_SALARY = (2026, 9)  # shu oydan boshlab oylik belgilash va berish ko'chadi, oldingilari — boshlang'ich qoldiq
TYPES = {"Cash": CashType.CASH, "Card": CashType.CARD, "Bank": CashType.BANK}
KINDS = {v for v, _ in ExpenseCategory.Kind.choices}
CONTACTS = {v for v, _ in Attendance.Contact.choices}
ONE = Decimal(1)
ZERO = Decimal(0)


def dt(v):
    try:
        return r.date(v)
    except ValueError:
        return None


def num(v):
    try:
        return Decimal(str(v)) if v not in (None, "") else ZERO
    except Exception:  # noqa: BLE001
        return ZERO


def rnd(x):
    return Decimal(x).quantize(ONE, rounding=ROUND_HALF_UP)


def money(x):
    return f"{rnd(x or 0):,.0f}".replace(",", " ")


def pair(excel, db):
    return f"{money(excel)} / {money(db)}"


def author(email_map, v):
    return email_map.get(r.text(v).lower())


class Ctx:
    """Ko'chirish davomida umumiy: filial, yordamchilar, keshlar."""

    def __init__(self, wb, rep, branch, bid, h):
        self.wb, self.rep, self.branch, self.bid, self.h = wb, rep, branch, bid, h
        self.emails = {u.email.lower(): u for u in User.objects.exclude(email=None).exclude(email="")}
        self.accounts = account_map(wb, rep)
        self._cat, self._disc, self._cred = {}, {}, {}
        self.cats_src = wb.by_id("Categories", "CategoryID")
        self.disc_src = wb.by_id("DiscountTypes", "TypeID")
        self.creditors_src = wb.by_id("Creditors", "CreditorID")
        self.users_src = wb.by_id("Users", "UserID")
        self.by_name = {r.text(u.get("FullName")).lower(): uid for uid, u in self.users_src.items() if r.text(u.get("FullName"))}
        self.by_email = {r.text(u.get("Email")).lower(): uid for uid, u in self.users_src.items() if r.text(u.get("Email"))}
        self.unknown = collections.Counter()

    def user(self, ref):
        """Xodim: AppSheet'da bu ustunlarga ba'zan UserID, ba'zan ism yoki pochta yozilgan (19-bo'lim 14-xato). Hammasi taniladi; tanilmaganlari — jamlama ogohlantirish."""
        raw = r.ident(ref)
        if not raw:
            return None
        if raw in self.users_src:
            return self._import_user(raw)
        low = raw.lower()
        if low in self.emails:
            return self.emails[low]
        uid = self.by_name.get(low) or self.by_email.get(low)
        if uid:
            return self._import_user(uid)
        found = User.objects.filter(full_name__iexact=raw).first()
        if found is None:
            self.unknown[raw] += 1
        return found

    def _import_user(self, uid):
        try:
            return self.h.user(uid)
        except Exception as e:  # noqa: BLE001
            self.rep.warn(f"Xodim {uid} ko'chmadi: {e}")
            return None

    def report_unknown(self):
        if self.unknown:
            self.rep.warn(f"Tanilmagan xodim qiymatlari (bo'sh qoldirildi, {sum(self.unknown.values())} marta): " + ", ".join(sorted(self.unknown)[:8]))

    def account(self, aid):
        acc = self.accounts.get(r.ident(aid))
        if acc is None and r.ident(aid):
            self.rep.warn(f"G'azna {r.ident(aid)} tizimda topilmadi")
        return acc

    def category(self, cid):
        if cid not in self._cat:
            src = self.cats_src.get(cid)
            name = r.text(src.get("Name")) if src else "Boshqa"
            kind = r.text(src.get("Status")) if src else "Xarajat"
            obj = ExpenseCategory.objects.filter(legacy_id=cid).first() or ExpenseCategory.objects.filter(name=name).first()
            if obj is None:
                obj = ExpenseCategory.objects.create(legacy_id=cid, name=name, kind=kind if kind in KINDS else "Xarajat")
                self.rep.count("Xarajat kategoriyalari", True)
            elif obj.legacy_id != cid:
                obj.legacy_id = cid
                obj.save(update_fields=["legacy_id"])
            self._cat[cid] = obj
        return self._cat[cid]

    def discount_type(self, tid):
        if not tid:
            return None
        if tid not in self._disc:
            src = self.disc_src.get(tid)
            if not src:
                self.rep.warn(f"Chegirma turi {tid} Excel'da yo'q")
                self._disc[tid] = None
            else:
                name = r.text(src.get("Name")).replace("�", "'")
                obj = DiscountType.objects.filter(legacy_id=tid).first() or DiscountType.objects.filter(name=name).first()
                if obj is None:
                    obj = DiscountType.objects.create(legacy_id=tid, name=name, max_amount=num(src.get("MaxAmount")))
                    self.rep.count("Chegirma turlari", True)
                self._disc[tid] = obj
        return self._disc[tid]


def account_map(wb, rep):
    """AppSheet g'azna kaliti → tizimdagi g'azna (legacy_id yoki nomi bo'yicha). Nofaol g'aznalar ham (oktyabr harakatlari bo'lishi mumkin)."""
    import re

    def norm(name):
        return re.sub(r"[^a-z]", "", r.text(name).lower().replace("g'azna", "").replace("gʻazna", "").replace("kassasi", ""))

    ours = list(Account.objects.all())
    out = {}
    for a in wb["Accounts"]:
        aid, name = r.ident(a.get("AccountID")), r.text(a.get("Name"))
        acc = next((x for x in ours if x.legacy_id == aid), None) or next((x for x in ours if norm(x.name) == norm(name)), None)
        if acc is not None:
            if acc.legacy_id != aid:
                acc.legacy_id = aid
                acc.save(update_fields=["legacy_id"])
            out[aid] = acc
    return out


# ------------------------------------------------------------------ shartnomalar doirasi

def scope_contracts(c):
    """Oktyabrda davomati yoki to'lovi bor shartnomalar. Hozir faol bo'lmaganlari (tugagan) ham ko'chadi — KPI va foyda uchun."""
    wb, h = c.wb, c.h
    need = {r.ident(a.get("ContractID")) for a in wb["Attendance"] if r.ident(a.get("BranchID")) == c.bid and (dt(a.get("Date")) or CUT) >= CUT and dt(a.get("Date"))}
    need |= {r.ident(p.get("ContractID")) for p in wb["Payments"] if r.ident(p.get("BranchID")) == c.bid and dt(p.get("Date")) and dt(p.get("Date")) >= CUT}
    out = {}
    for cid in sorted(need):
        src = h.contracts_src.get(cid)
        if src is None:
            c.rep.error(f"Shartnoma {cid} Excel'da yo'q (oktyabr davomati/to'lovi bor)")
            continue
        obj = Contract.objects.filter(legacy_id=cid).first()
        if obj is None:
            start, end = dt(src.get("StartDate")), dt(src.get("EndDate"))
            obj = h.contract(src, start, end if cid not in h.active_ids else None)
        if obj is not None:
            out[cid] = obj
    c.rep.checks["Oktyabrda davomati/to'lovi bor shartnomalar"] = f"{len(need)} ta, ko'chdi: {len(out)}"
    return out


# ------------------------------------------------------------------ davomat

def drop_new_attendance(c, excel_max):
    """Yangi tizimda AppSheet'ga ham kiritilgan (o'tishdan oldingi) qatorlar: AppSheet tarixi asos — Excel qamrab olgan sanalar uchun o'chiriladi."""
    qs = Attendance.objects.filter(branch=c.branch, legacy_id=None, date__gte=CUT, date__lte=excel_max)
    n = qs.update(is_deleted=True, updated_at=timezone.now())
    c.rep.checks[f"O'chirilgan davomat (yangi tizimda, {CUT:%d.%m}–{excel_max:%d.%m}, AppSheet'da bor)"] = n


def attendance(c, ctr):
    wb, rep, h = c.wb, c.rep, c.h
    rows = [a for a in wb["Attendance"] if r.ident(a.get("BranchID")) == c.bid and dt(a.get("Date")) and dt(a.get("Date")) >= CUT]
    rows.sort(key=lambda a: dt(a.get("Date")))
    skipped = 0
    for a in rows:
        aid, cid = r.ident(a.get("AttendanceID")), r.ident(a.get("ContractID"))
        contract = ctr.get(cid)
        if contract is None:
            skipped += 1
            continue
        try:
            group = h.group(r.ident(a.get("GroupID")))
            teacher = c.user(a.get("TeacherID"))
            sup = c.user(a.get("SupporterID"))
            if teacher is None:
                raise ValueError("ustoz yo'q")
            date = dt(a.get("Date"))
            status = r.text(a.get("Status"))
            if status not in ("1", "0", "X", "-"):
                raise ValueError(f"status tushunarsiz: {status}")
            contact = r.text(a.get("ContactStatus"))
            values = {"branch": c.branch, "group": group, "course": h.course(r.ident(a.get("CourseID"))), "contract": contract,
                      "day_pattern": h.pattern(r.ident(a.get("DayID"))) if r.ident(a.get("DayID")) else group.day_pattern, "date": date, "status": status,
                      "teacher": teacher, "supporter": sup, "contact_status": contact if contact in CONTACTS else "", "comment": r.text(a.get("Comment")),
                      "created_by": author(c.emails, a.get("CreatedBy"))}
            obj = Attendance.objects.filter(legacy_id=aid).first()
            if obj is None:
                twin = Attendance.objects.filter(group=group, contract=contract, date=date).first()
                if twin is not None:  # yangi tizimda kiritilgan — yangisi asos, faqat AppSheet kaliti bog'lanadi
                    twin.legacy_id = aid
                    twin.save(update_fields=["legacy_id"])
                    rep.count("Davomat (yangi tizimdagisi bilan bog'landi)", False)
                    continue
                Attendance.objects.create(legacy_id=aid, **values)
                rep.count("Davomat (oktyabr)", True)
            else:
                for k, v in values.items():
                    setattr(obj, k, v)
                obj.save()
                rep.count("Davomat (oktyabr)", False)
        except Exception as e:  # noqa: BLE001
            h.reset()
            rep.error(f"Davomat {aid}: {e}")
    if skipped:
        rep.warn(f"Davomat: shartnomasi ko'chmagani uchun {skipped} qator o'tkazib yuborildi")
    rep.checks["Davomat (oktyabr): Excel / tizimda"] = f"{len(rows)} / {Attendance.objects.filter(branch=c.branch, date__gte=CUT, legacy_id__isnull=False).count()}"


# ------------------------------------------------------------------ to'lovlar

def _confirm(v):
    return {"Tasdiqlandi": Confirm.CONFIRMED, "Tasdiqlashga": Confirm.PENDING}.get(r.text(v), "")


def payments(c, ctr):
    rep = c.rep
    rows = [p for p in c.wb["Payments"] if r.ident(p.get("BranchID")) == c.bid and dt(p.get("Date")) and dt(p.get("Date")) >= CUT]
    rows.sort(key=lambda p: (dt(p.get("Date")), str(p.get("CreatedTime") or "")))
    for p in rows:
        pid, cid = r.ident(p.get("PaymentID")), r.ident(p.get("ContractID"))
        contract = ctr.get(cid)
        if contract is None:
            rep.error(f"To'lov {pid}: shartnomasi ko'chmagan")
            continue
        amount, discount = num(p.get("Summa")), num(p.get("Discount"))
        ctype = TYPES.get(r.text(p.get("Type")), "")
        cashbox = c.account(p.get("Cashbox")) if amount else None
        if amount and (ctype == "" or cashbox is None):
            rep.error(f"To'lov {pid}: pul turi yoki g'azna yo'q")
            continue
        dtype = c.discount_type(r.ident(p.get("DiscountType"))) if discount else None
        values = {
            "branch": c.branch, "contract": contract, "group": contract.group, "date": dt(p.get("Date")), "amount": amount, "cash_type": ctype,
            "cashbox": cashbox, "accountant": c.user(p.get("Accountant")), "discount_type": dtype, "discount": discount,
            "discount_status": _confirm(p.get("DiscountConfirmation")) if discount else "", "discount_confirmed_by": c.user(p.get("DiscountConfirmedBy")) if discount else None,
            "noncash_status": _confirm(p.get("NonCashConfirmation")) if ctype and ctype != CashType.CASH else "",
            "noncash_confirmed_by": c.user(p.get("NonCashConfirmedBy")) if ctype and ctype != CashType.CASH else None,
            "comment": r.text(p.get("Comments")), "created_by": author(c.emails, p.get("CreatedBy")),
        }
        obj = Payment.objects.filter(legacy_id=pid).first()
        if obj is None:
            obj = Payment.objects.filter(legacy_id=None, contract=contract, date=values["date"], amount=amount, discount=discount).first()
            created = obj is None
            if created:
                obj = Payment(legacy_id=pid, number=fin.next_payment_number(c.branch), **values)
            else:
                obj.legacy_id = pid  # yangi tizimda kiritilgan — kalit bog'lanadi, qiymatlari o'zgarmaydi
                obj.save(update_fields=["legacy_id"])
                rep.count("To'lovlar (yangi tizimdagisi bilan bog'landi)", False)
                continue
        else:
            created = False
            for k, v in values.items():
                setattr(obj, k, v)
        obj.save()
        fin.sync_movements(CashMovement.Source.PAYMENT, obj, fin.payment_rows(obj))
        rep.count("To'lovlar (oktyabr)", created)
    got = Payment.objects.filter(branch=c.branch, date__gte=CUT)
    rep.checks["To'lovlar (oktyabr): Excel / tizimda soni"] = f"{len(rows)} / {got.count()}"
    rep.checks["To'lovlar (oktyabr): Excel / tizimda summa"] = pair(sum(num(p.get("Summa")) for p in rows), got.aggregate(s=Sum("amount"))["s"])
    rep.checks["To'lovlar (oktyabr): Excel / tizimda chegirma"] = pair(sum(num(p.get("Discount")) for p in rows), got.aggregate(s=Sum("discount"))["s"])
    pend = got.filter(noncash_status=Confirm.PENDING)
    rep.checks["Naqdsiz to'lov tasdiqlanmagan (g'aznaga hali kirmaydi)"] = f"{pend.count()} ta, {pend.aggregate(s=Sum('amount'))['s'] or 0:,.0f} so'm".replace(",", " ")


# ------------------------------------------------------------------ xarajatlar, o'tkazma, ayirboshlash, kreditor

def expenses(c):
    rep = c.rep
    rows = [x for x in c.wb["Expenses"] if r.ident(x.get("BranchID")) == c.bid and dt(x.get("Date")) and dt(x.get("Date")) >= CUT]
    for x in rows:
        eid = r.ident(x.get("ExpenseID"))
        acc, ctype = c.account(x.get("Cashbox")), TYPES.get(r.text(x.get("TypeID")), "")
        if acc is None or not ctype:
            rep.error(f"Xarajat {eid}: g'azna yoki pul turi yo'q")
            continue
        date = dt(x.get("Date"))
        total = num(x.get("Summa"))
        values = {"branch": c.branch, "date": date, "category": c.category(r.ident(x.get("CategoryID"))), "name": r.text(x.get("Name"))[:150] or "—",
                  "quantity": max(1, r.integer(x.get("Amount"), 1) or 1), "price": num(x.get("Price")), "total": total, "cash_type": ctype, "account": acc,
                  "cashier": c.user(x.get("Cashier")), "period_year": r.integer(x.get("Year"), date.year), "period_month": r.integer(x.get("Month"), date.month),
                  "comment": r.text(x.get("Comment")), "created_by": author(c.emails, x.get("CreatedBy"))}
        obj = Expense.objects.filter(legacy_id=eid).first()
        if obj is None:
            twin = Expense.objects.filter(legacy_id=None, date=date, total=total, account=acc, category=values["category"]).first()
            if twin is not None:
                twin.legacy_id = eid
                twin.save(update_fields=["legacy_id"])
                rep.count("Xarajatlar (yangi tizimdagisi bilan bog'landi)", False)
                continue
            obj, created = Expense(legacy_id=eid, **values), True
        else:
            created = False
            for k, v in values.items():
                setattr(obj, k, v)
        obj.save()
        fin.sync_movements(CashMovement.Source.EXPENSE, obj, [(obj.account, obj.cash_type, -obj.total, True, f"{obj.category}: {obj.name}")])
        rep.count("Xarajatlar (oktyabr)", created)
    got = Expense.objects.filter(branch=c.branch, date__gte=CUT)
    rep.checks["Xarajatlar (oktyabr): Excel / tizimda soni"] = f"{len(rows)} / {got.count()}"
    rep.checks["Xarajatlar (oktyabr): Excel / tizimda summa"] = pair(sum(num(x.get("Summa")) for x in rows), got.aggregate(s=Sum("total"))["s"])


def transfers(c):
    rep = c.rep
    for t in c.wb["Transactions"]:
        date = dt(t.get("Date"))
        if not date or date < CUT:
            continue
        tid = r.ident(t.get("TransactionID"))
        snd, rcv, ctype = c.account(t.get("SenderCashbox")), c.account(t.get("RecieverCashbox")), TYPES.get(r.text(t.get("PaymentType")), CashType.CASH)
        if snd is None or rcv is None:
            rep.error(f"O'tkazma {tid}: g'azna topilmadi")
            continue
        status = Confirm.CONFIRMED if r.text(t.get("ConfirmationStatus")) == "Tasdiqlandi" else Confirm.PENDING
        values = {"date": date, "sender_account": snd, "sender_cashier": c.user(t.get("SenderCashier")), "cash_type": ctype, "amount": num(t.get("Sum")),
                  "receiver_account": rcv, "receiver_cashier": c.user(t.get("RecieverCashier")), "status": status,
                  "confirmed_by": c.user(t.get("ConfirmedBy")) if status == Confirm.CONFIRMED else None, "comment": r.text(t.get("Comment")),
                  "created_by": author(c.emails, t.get("CreatedBy"))}
        obj = Transfer.objects.filter(legacy_id=tid).first()
        if obj is None:
            twin = Transfer.objects.filter(legacy_id=None, date=date, sender_account=snd, receiver_account=rcv, amount=values["amount"], cash_type=ctype).first()
            if twin is not None:
                twin.legacy_id = tid
                twin.save(update_fields=["legacy_id"])
                continue
            obj, created = Transfer(legacy_id=tid, **values), True
        else:
            created = False
            for k, v in values.items():
                setattr(obj, k, v)
        obj.save()
        fin.sync_movements(CashMovement.Source.TRANSFER, obj, fin.transfer_rows(obj))
        rep.count("O'tkazmalar (oktyabr)", created)


def exchanges(c):
    rep = c.rep
    for x in c.wb["Exchange"]:
        date = dt(x.get("Date"))
        if not date or date < CUT:
            continue
        xid = r.ident(x.get("ExchangeID"))
        acc, f, t = c.account(x.get("Cashbox")), TYPES.get(r.text(x.get("CashTypeFrom"))), TYPES.get(r.text(x.get("CashTypeTo")))
        if acc is None or not f or not t:
            rep.error(f"Ayirboshlash {xid}: g'azna yoki pul turi yo'q")
            continue
        values = {"account": acc, "date": date, "from_type": f, "amount": num(x.get("Summa")), "to_type": t, "amount_to": num(x.get("SummaTo")),
                  "created_by": author(c.emails, x.get("CreatedBy"))}
        obj = Exchange.objects.filter(legacy_id=xid).first()
        if obj is None:
            twin = Exchange.objects.filter(legacy_id=None, account=acc, date=date, from_type=f, to_type=t, amount=values["amount"]).first()
            if twin is not None:
                twin.legacy_id = xid
                twin.save(update_fields=["legacy_id"])
                continue
            obj, created = Exchange(legacy_id=xid, **values), True
        else:
            created = False
            for k, v in values.items():
                setattr(obj, k, v)
        obj.save()
        note = f"{obj.get_from_type_display()} → {obj.get_to_type_display()}"
        fin.sync_movements(CashMovement.Source.EXCHANGE, obj, [(acc, obj.from_type, -obj.amount, True, note), (acc, obj.to_type, obj.amount_to, True, note)])
        rep.count("Ayirboshlash (oktyabr)", created)


def creditors(c):
    """Faqat oktyabrda amali bor kreditorlar. Buyurtmachi qarori (2026-10-19): boshlang'ich haqqi 0 — kreditor ekranida faqat oktyabrdagi amallar chiqadi
    (AppSheet'dagi eski qoldiq, masalan MNSH −284,9 mln, ko'chirilmaydi; g'azna qoldig'iga ta'siri 01.10 qoldig'ida allaqachon bor)."""
    rep = c.rep
    flows = c.wb["CashFlow"]
    oct_rows = [x for x in flows if dt(x.get("Date")) and dt(x.get("Date")) >= CUT]
    for cr_id in sorted({r.ident(x.get("CreditorID")) for x in oct_rows}):
        src = c.creditors_src.get(cr_id)
        if src is None:
            rep.error(f"Kreditor {cr_id} Excel'da yo'q")
            continue
        name = r.text(src.get("Name"))
        cr = Creditor.objects.filter(legacy_id=cr_id).first() or Creditor.objects.filter(name=name).first()
        created = cr is None
        if created:
            cr = Creditor(legacy_id=cr_id, name=name)
        cr.legacy_id, cr.initial_balance = cr_id, ZERO  # buyurtmachi qarori 2026-10-19: boshlang'ich — 0, faqat oktyabrdagi amallar (eski qoldiq ko'chmaydi)
        cr.save()
        rep.count("Kreditorlar", created)
        for x in oct_rows:
            if r.ident(x.get("CreditorID")) != cr_id:
                continue
            xid, acc, ctype = r.ident(x.get("CashID")), c.account(x.get("Cashbox")), TYPES.get(r.text(x.get("CashType")))
            if acc is None or not ctype:
                rep.error(f"Kreditor amali {xid}: g'azna yoki pul turi yo'q")
                continue
            values = {"date": dt(x.get("Date")), "creditor": cr, "amount": num(x.get("Summa")), "cash_type": ctype, "account": acc,
                      "cashier": c.user(x.get("Cashier")), "comment": r.text(x.get("Comment")), "created_by": author(c.emails, x.get("CreatedBy"))}
            obj = CreditorTransaction.objects.filter(legacy_id=xid).first()
            if obj is None:
                obj, created = CreditorTransaction(legacy_id=xid, **values), True
            else:
                created = False
                for k, v in values.items():
                    setattr(obj, k, v)
            obj.save()
            fin.sync_movements(CashMovement.Source.CREDITOR, obj, [(obj.account, obj.cash_type, -obj.amount, True, obj.creditor)])
            rep.count("Kreditor amallari (oktyabr)", created)


# ------------------------------------------------------------------ oyliklar

def salaries(c):
    """AppSheet oyliklari: 2026-09 va keyingi oylar belgilashlari + berilganlari. Oldingi oylar — sentyabr belgilashidagi boshlang'ich qoldiq.
    Sentyabr KPI'si (davomat yo'q) — AppSheet'dagi summa bilan «KPI (qo'lda)» ga yoziladi; oktyabr KPI'si yangi tizimda davomatdan hisoblanadi."""
    rep, wb = c.rep, c.wb
    ym = lambda row: (r.integer(row.get("Year")), r.integer(row.get("Month")))  # noqa: E731
    assigns = [a for a in wb["SalaryAppoinment"] if r.ident(a.get("BranchID")) == c.bid]
    gives = [g for g in wb["SalaryGiving"] if r.ident(g.get("BranchID")) == c.bid]

    def imported(g):  # yangi tizimda SalaryPayout bo'ladigan berilganlar
        d = dt(g.get("Date"))
        return (d and d >= CUT) or ym(g) >= FIRST_SALARY

    carry, total_by = collections.defaultdict(Decimal), {}
    for a in assigns:
        t = num(a.get("Fixed")) + num(a.get("Bonus")) + num(a.get("KPI")) + num(a.get("TeacherKPI")) + num(a.get("SupporterKPI")) - num(a.get("Fine"))
        total_by[(r.ident(a.get("UserID")), *ym(a))] = t
        if ym(a) < FIRST_SALARY:
            carry[r.ident(a.get("UserID"))] += t
    for g in gives:
        if ym(g) < FIRST_SALARY and not imported(g):
            carry[r.ident(g.get("UserID"))] -= num(g.get("Summa"))
    users = {r.ident(a.get("UserID")) for a in assigns if ym(a) >= FIRST_SALARY} | {r.ident(g.get("UserID")) for g in gives if imported(g)}
    users |= {u for u, v in carry.items() if v}
    users.discard("")
    working = {r.ident(a.get(k)) for a in wb["Attendance"] if r.ident(a.get("BranchID")) == c.bid and (dt(a.get("Date")) or datetime.date.min) >= CUT
               for k in ("TeacherID", "SupporterID")}  # oktyabrda dars o'tgan/yordam bergan xodim ishlayapti — AppSheet'da «Qo'shilmagan» bo'lsa ham
    busy = working | {r.ident(g.get("UserID")) for g in gives if imported(g)}
    busy |= {r.ident(a.get("UserID")) for a in assigns if ym(a) == FIRST_SALARY and total_by.get((r.ident(a.get("UserID")), *ym(a)))}
    created_a = 0
    for uid in sorted(users):
        user = c.user(uid)
        if user is None:
            continue
        if uid not in busy:
            continue  # buyurtmachi qarori 2026-10-19: ishlamayotgan xodimlar bilan hisob yopilgan — oylik belgilash va qoldig'i ko'chirilmaydi (berilgan pul g'aznada qoladi)
        row = next((a for a in assigns if r.ident(a.get("UserID")) == uid and ym(a) == FIRST_SALARY), None)
        values = {"fixed": num(row.get("Fixed")) if row else ZERO, "bonus": num(row.get("Bonus")) if row else ZERO,
                  "kpi": (num(row.get("KPI")) + num(row.get("TeacherKPI")) + num(row.get("SupporterKPI"))) if row else ZERO,
                  "fine": num(row.get("Fine")) if row else ZERO, "opening_balance": rnd(carry[uid]), "comment": (r.text(row.get("Comment")) if row else "") or "AppSheet'dan"}
        obj = SalaryAssignment.objects.filter(branch=c.branch, user=user, year=FIRST_SALARY[0], month=FIRST_SALARY[1]).first()
        created = obj is None
        if created:
            obj = SalaryAssignment(branch=c.branch, user=user, year=FIRST_SALARY[0], month=FIRST_SALARY[1], legacy_id=r.ident(row.get("SalaryID")) if row else None)
        for k, v in values.items():
            setattr(obj, k, v)
        obj.save()
        created_a += created
        rep.count("Oylik belgilash (2026-09, qoldiq bilan)", created)
        # keyingi oylar (oktyabr belgilash AppSheet'da yo'q bo'lsa — yangi tizimda belgilanadi)
        for a in assigns:
            if r.ident(a.get("UserID")) == uid and ym(a) > FIRST_SALARY:
                y, m = ym(a)
                o2 = SalaryAssignment.objects.filter(branch=c.branch, user=user, year=y, month=m).first()
                if o2 is None:
                    SalaryAssignment.objects.create(branch=c.branch, user=user, year=y, month=m, legacy_id=r.ident(a.get("SalaryID")), fixed=num(a.get("Fixed")),
                                                    bonus=num(a.get("Bonus")), fine=num(a.get("Fine")), kpi=ZERO, comment="AppSheet'dan")
                    rep.count("Oylik belgilash (keyingi oylar)", True)
    kinds = {"Fixed": SalaryPayout.Kind.FIXED, "KPI": SalaryPayout.Kind.KPI, "Bonus": SalaryPayout.Kind.BONUS}
    for g in gives:
        if not imported(g):
            continue
        gid, date = r.ident(g.get("SalaryID")), dt(g.get("Date"))
        user, acc, ctype = c.user(g.get("UserID")), c.account(g.get("CashBox")), TYPES.get(r.text(g.get("CashType")))
        if user is None or acc is None or not ctype or not date:
            rep.error(f"Oylik berish {gid}: xodim, g'azna yoki pul turi/sana yo'q")
            continue
        y, m = ym(g)
        values = {"branch": c.branch, "user": user, "year": y, "month": m, "date": date, "type": kinds.get(r.text(g.get("SalaryType")), SalaryPayout.Kind.FIXED),
                  "amount": num(g.get("Summa")), "cash_type": ctype, "account": acc, "cashier": c.user(g.get("Cashier")), "comment": r.text(g.get("Comment")),
                  "created_by": author(c.emails, g.get("CreatedBy"))}
        obj = SalaryPayout.objects.filter(legacy_id=gid).first()
        if obj is None:
            twin = SalaryPayout.objects.filter(legacy_id=None, user=user, year=y, month=m, date=date, amount=values["amount"]).first()
            if twin is not None:
                twin.legacy_id = gid
                twin.save(update_fields=["legacy_id"])
                continue
            obj, created = SalaryPayout(legacy_id=gid, **values), True
        else:
            created = False
            for k, v in values.items():
                setattr(obj, k, v)
        obj.save()
        # g'azna: faqat 01.10 dan keyingi berilganlar jurnalga (oldingilari g'aznaning boshlang'ich qoldig'ida)
        fin.sync_movements(CashMovement.Source.SALARY, obj, pay.payout_rows(obj) if date >= CUT else [])
        rep.count("Oylik berish", created)
    out = SalaryPayout.objects.filter(branch=c.branch, date__gte=CUT)
    oct_gives = [g for g in gives if dt(g.get("Date")) and dt(g.get("Date")) >= CUT]
    rep.checks["Oylik berish (oktyabr): Excel / tizimda summa"] = pair(sum(num(g.get("Summa")) for g in oct_gives), out.aggregate(s=Sum("amount"))["s"])
    plus, minus = [v for v in carry.values() if v > 0], [v for v in carry.values() if v < 0]
    rep.checks["Xodimlarning 01.10 qoldig'i (haqdor +, qarzdor −)"] = f"{len(plus)} ta +{money(sum(plus))}; {len(minus)} ta {money(sum(minus))}"
    # Solishtirish: AppSheet qoidasi (jarima ayirilgan) bo'yicha xodim balansi — oldingi oylar + sentyabr − hamma berilganlar; oktyabrdan keyin yangi tizimda KPI qo'shiladi
    excel_net = collections.defaultdict(Decimal)
    for (uid, y, m), t in total_by.items():
        if (y, m) <= FIRST_SALARY:
            excel_net[uid] += t
    for g in gives:
        excel_net[r.ident(g.get("UserID"))] -= num(g.get("Summa"))
    system_net, bad = {}, 0
    for a in pay.latest_per_user(SalaryAssignment.objects.filter(branch=c.branch)):
        later = SalaryPayout.objects.filter(branch=c.branch, user=a.user).filter(Q(year__gt=a.year) | Q(year=a.year, month__gt=a.month)).aggregate(s=Sum("amount"))["s"] or ZERO
        system_net[a.user.legacy_id] = a.final - later
    for uid, v in excel_net.items():
        if uid in system_net and abs(rnd(system_net[uid]) - rnd(v)) > 10:
            bad += 1
    rep.checks["Xodim balansi tizim ↔ AppSheet (sentyabrgacha belgilash − barcha berilganlar): farqli xodimlar"] = f"{bad} / {len(system_net)}"


# ------------------------------------------------------------------ solishtirish

def reconcile(c, ctr, excel_balance):
    c.report_unknown()
    """Shartnoma balansi: tizimda (boshlang'ich + oktyabr davomat qarzi − oktyabr to'lov va chegirmalari) AppSheet'ning bugungi balansiga tengmi."""
    from apps.education.services import with_balance

    rep = c.rep
    bad, big = 0, []
    sys_bal = {x.legacy_id: x.balance for x in with_balance(Contract.objects.filter(branch=c.branch).exclude(legacy_id=None))}
    for cid, b in excel_balance.items():
        if cid not in sys_bal:
            continue
        diff = rnd(sys_bal[cid]) - rnd(b)
        if abs(diff) > 10:  # AppSheet kasrlar bilan, tizim har qatorni so'mgacha yaxlitlaydi — bir necha so'm farq normal
            bad += 1
            big.append((abs(diff), cid, diff))
    big.sort(reverse=True)
    top = ", ".join(f"{cid}: {d:+,.0f}" for _, cid, d in big[:5]).replace(",", " ")
    rep.checks["Shartnoma balansi tizim ↔ AppSheet: farqli shartnomalar"] = f"{bad} / {len(excel_balance)}" + (f" · eng kattalari: {top}" if big else "")
    qs = Attendance.objects.filter(branch=c.branch, date__gte=CUT)
    rep.checks["Davomat qatorlari: qarz hisoblanmagan (narx/dars soni yo'q)"] = qs.filter(student_debt__isnull=True, status__in=["1", "0", "X"]).count()
    rep.checks["Davomat qatorlari: KPI stavkasi belgilanmagan"] = qs.filter(calc_note=calc.NOTE_NO_RATE).count()
    rep.checks["Davomat (oktyabr) jami: ustoz KPI / yordamchi KPI / talaba qarzi"] = " / ".join(
        f"{qs.aggregate(s=Sum(f))['s'] or 0:,.0f}".replace(",", " ") for f in ("teacher_kpi", "supporter_kpi", "student_debt"))
    last = Attendance.objects.filter(branch=c.branch).aggregate(m=Max("date"))["m"]
    rep.checks["Oxirgi davomat sanasi (tizimda)"] = str(last)

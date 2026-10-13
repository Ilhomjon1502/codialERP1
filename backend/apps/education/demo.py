"""seed_demo uchun: guruhlar, shartnomalar (talaba, vasiy, 5-statusli lid bilan), KPI stavkalari, o'tgan va joriy oy davomati,
bitta qoldirilgan dars so'rovi. Qayta ishga tushirilsa dublikat yaratmaydi (guruhda shartnoma bo'lsa o'tkazib yuboriladi)."""

import datetime
import random

from django.utils import timezone

from apps.crm.models import AGE_GROUPS, LAPTOP_CHOICES, SOCIAL_STATUSES, Lead, Parent, Student
from apps.payroll.models import KPIRate
from apps.references.services import prev_month

from . import calc
from .models import Attendance, Contract, Group, MakeupRequest
from .services import next_contract_number

# (kalit, xodim, kim sifatida, kurs, turi, o'zgarmas summa, foiz) — prototipdagidek
KPI_RATES = [
    ("k1", "u7", "USTOZ", "c1", "Foiz", 0, 40), ("k2", "u8", "USTOZ", "c2", "O'zgarmas", 260000, 0), ("k3", "u9", "USTOZ", "c3", "Foiz", 0, 40),
    ("k4", "u10", "USTOZ", "c4", "Foiz", 0, 45), ("k5", "u10", "USTOZ", "c5", "O'zgarmas", 150000, 0), ("k6", "u11", "YORDAMCHI", "c1", "O'zgarmas", 60000, 0),
    ("k7", "u11", "YORDAMCHI", "c5", "O'zgarmas", 40000, 0), ("k8", "u12", "YORDAMCHI", "c2", "Foiz", 0, 10),
]
# (kalit, kurs, dars kunlari, vaqt, ustoz, yordamchi, xona, boshlanish — bugundan necha kun, raqam, talabalar soni)
GROUPS = [
    ("g1", "c1", "p1", "t3", "u7", "u11", "r1", -130, 12, 12), ("g2", "c1", "p2", "t4", "u7", "u11", "r2", -60, 13, 9),
    ("g3", "c2", "p1", "t4", "u8", "u12", "r3", -150, 8, 11), ("g4", "c3", "p2", "t2", "u9", None, "r1", -100, 5, 6),
    ("g5", "c4", "p3", "t2", "u10", None, "r2", -75, 3, 7), ("g6", "c5", "p3", "t3", "u10", "u11", "r4", -38, 21, 10),
    ("g7", "c2", "p2", "t5", "u8", "u12", "r3", 8, 9, 3),
]
MALE = ["Ali", "Sardorbek", "Jahongir", "Bobur", "Doniyor", "Islom", "Asadbek", "Muhammadali", "Javohir", "Sanjar", "Temur", "Shohruh", "Azizbek", "Firdavs"]
FEMALE = ["Madina", "Sevara", "Dilnoza", "Mohinur", "Zarina", "Shahzoda", "Gulruh", "Nilufar", "Sabina", "Robiya", "Kamola", "Zilola"]
LAST = ["Karimov", "Rahimov", "Tursunov", "Abdullayev", "Yusupov", "Qodirov", "Ergashev", "Nazarov", "Saidov", "Mamatov", "Olimov", "Umarov"]
FATHER = ["Anvar", "Bahodir", "Rustam", "Shuhrat", "Davron", "Farhod", "Jamshid", "Komil", "Murod", "Nodir", "Olim", "Rasul", "Tohir", "Zafar"]
STOP = ["Moliyaviy qiyinchilik", "Dars sifatidan qoniqmadi", "Kurs yoqmadi - Boshqa kursga o'tyapti"]


def phone(R):
    return f"9{R.randint(10**7, 10**8 - 1):08d}"


def seed(cmd, branch, users, courses, patterns, times, rooms, sources):
    """cmd — seed_demo buyrug'i (upsert va created hisoblagichi)."""
    R = random.Random(20261014)
    today = timezone.localdate()
    prev = prev_month(today.replace(day=1))
    for k, u, rt, c, kind, fixed, pct in KPI_RATES:
        cmd.upsert(KPIRate, k, {"branch": branch, "user": users[u], "role_type": rt, "course": courses[c], "effective_from": prev, "type": kind,
                                "fixed_amount": fixed, "percent": pct})
    staff = [users["u4"], users["u5"]]
    for gk, ck, pk, tk, teacher, supporter, rk, start_days, number, n in GROUPS:
        start = today + datetime.timedelta(days=start_days)
        g = cmd.upsert(Group, gk, {"branch": branch, "course": courses[ck], "day_pattern": patterns[pk], "time": times[tk], "teacher": users[teacher],
                                   "supporter": users.get(supporter), "room": rooms[rk], "start_date": start, "number": number, "created_by": users["u3"]})
        if Contract.all_objects.filter(group=g).exists():
            continue
        contracts = [new_contract(R, cmd, branch, g, gk, i, n, start, today, prev, R.choice(staff), sources) for i in range(n)]
        seed_attendance(R, g, contracts, max(start, prev), today - datetime.timedelta(days=1))
    g1 = Group.objects.filter(legacy_id="demo:g1").first()
    x = Attendance.objects.filter(group=g1, status="X").order_by("-date").first() if g1 else None
    if x and not MakeupRequest.all_objects.filter(legacy_id="demo:mk1").exists():
        MakeupRequest.objects.create(attendance=x, teacher=x.teacher, makeup_date=min(x.date + datetime.timedelta(days=2), today),
                                     comment="Shanba kuni alohida dars o'tib berdim", created_by=x.teacher, updated_by=x.teacher, legacy_id="demo:mk1")


def new_contract(R, cmd, branch, g, gk, i, n, start, today, prev, who, sources):
    male = R.random() < 0.62
    first, last = R.choice(MALE if male else FEMALE), R.choice(LAST) + ("" if male else "a")
    father = R.choice(FATHER) + (" o'g'li" if male else " qizi")
    parent = None
    if R.random() < 0.7:
        parent = Parent.objects.create(branch=branch, first_name=father.split()[0], last_name=last.rstrip("a"), phone=phone(R),
                                       created_by=who, updated_by=who, legacy_id=f"demo:pa-{gk}-{i}")
    st = Student.objects.create(branch=branch, first_name=first, last_name=last, father_name=father, gender="Erkak" if male else "Ayol", parent=parent,
                                phone1=phone(R), phone2=phone(R), birth_date=datetime.date(today.year - R.randint(11, 27), R.randint(1, 12), R.randint(1, 28)),
                                created_by=who, updated_by=who, legacy_id=f"demo:st-{gk}-{i}")
    c_start = max(start, prev) if start <= today else start
    c = Contract(branch=branch, student=st, course=g.course, group=g, number=next_contract_number(branch), start_date=c_start,
                 type="Grant" if R.random() < 0.06 else "Pullik", opening_balance=R.choice([0, 0, 0, 150000, 300000, -100000]) if c_start <= prev else 0,
                 created_by=who, updated_by=who, legacy_id=f"demo:ct-{gk}-{i}")
    if start <= today and n > 5 and i == n - 1:  # har guruhda bittasi to'xtatilgan
        c.end_date = today - datetime.timedelta(days=R.randint(3, 20))
        c.stop_reason = R.choice(STOP)
    c.save()
    if R.random() < 0.6:
        Lead.objects.create(branch=branch, student=st, source=R.choice(sources), course=g.course, day_pattern=g.day_pattern, status="5", group=g,
                            demo_date=c_start, demo_attended=True, age_group=R.choice(AGE_GROUPS[:7]), social_status=R.choice(SOCIAL_STATUSES),
                            laptop=R.choice(LAPTOP_CHOICES), created_by=who, updated_by=who, legacy_id=f"demo:ldc-{gk}-{i}")
    cmd.created += 1
    return c


def seed_attendance(R, g, contracts, start, end):
    """Kechagacha davomat (bugungisini ustoz o'zi oladi): 85% keldi, 7% sababli, 8% besabab."""
    rows, c_calc = [], calc.Calculator()
    d = start
    while d <= end:
        if d.isoweekday() in g.day_pattern.weekdays:
            for c in contracts:
                if c.start_date <= d and (not c.end_date or c.end_date >= d):
                    x = R.random()
                    st = "1" if x < 0.85 else "0" if x < 0.92 else "X"
                    contact = "" if st == "1" else R.choice(["Bog'lanishga", "Gaplashildi", "Tushib bo'lmadi"])
                    comment = "Kasal" if st == "0" else "Ota-onasi bilan gaplashildi" if contact == "Gaplashildi" else ""
                    a = Attendance(branch=g.branch, group=g, course=g.course, contract=c, day_pattern=g.day_pattern, date=d, status=st, teacher=g.teacher,
                                   supporter=g.supporter, contact_status=contact, comment=comment, created_by=g.teacher, updated_by=g.teacher)
                    c_calc.apply(a, c.type)
                    rows.append(a)
        d += datetime.timedelta(days=1)
    Attendance.objects.bulk_create(rows, batch_size=500)

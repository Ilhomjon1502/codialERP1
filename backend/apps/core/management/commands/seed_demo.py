"""Sinov ma'lumotlari (prototipdagi ma'lumotnomalar va xodimlar). Qayta ishga tushirilsa dublikat yaratmaydi.

    python manage.py seed_demo --password "Sinov-parol-2026"

Xodimlar pochtasi «@codial.test» (haqiqiy pochtaga xat ketmaydi). Parol berilmasa xodimlar parolsiz yaratiladi.
"""

import datetime
import os
import random
import zlib

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.crm.models import AGE_GROUPS, LAPTOP_CHOICES, SOCIAL_STATUSES, Lead, LeadComment, Student
from apps.education import demo as edu_demo
from apps.education import demo_m6 as edu_m6_demo
from apps.finance import demo as fin_demo
from apps.finance.models import Account
from apps.payroll import demo as pay_demo
from apps.references import services
from apps.references.models import Branch, Course, CoursePrice, DayPattern, DiscountType, ExpenseCategory, LeadSource, LessonFrequency, LessonTime, Room

USERS = [
    ("u1", "Rustam Mirzayev", "ADMIN", ["Boshqa"]), ("u2", "Dilshod Karimov", "BOSH_MENEJER", ["Moliya", "HR"]),
    ("u3", "Malika Yusupova", "FILIAL_MENEJERI", ["Ta'lim"]), ("u4", "Nodira Azimova", "ADMINISTRATOR", ["Qabul"]),
    ("u5", "Sardor Tursunov", "ADMINISTRATOR_HISOBCHI", ["Qabul", "Moliya"]), ("u6", "Gulnoza Rahimova", "HISOBCHI", ["Moliya"]),
    ("u7", "Jasur Aliyev", "USTOZ", ["Ta'lim"]), ("u8", "Bekzod Nazarov", "USTOZ", ["Ta'lim"]),
    ("u9", "Shahzod Ergashev", "USTOZ", ["Ta'lim"]), ("u10", "Aziz Qodirov", "USTOZ_YORDAMCHI", ["Ta'lim", "IT"]),
    ("u11", "Madina Saidova", "YORDAMCHI", ["Ta'lim"]), ("u12", "Otabek Xolmatov", "YORDAMCHI", ["Ta'lim"]),
    ("u13", "Farrux Olimov", "BOSHQA", ["Ta'minot"]),
]
COURSES = [("c1", "Frontend"), ("c2", "Backend (Python)"), ("c3", "Flutter"), ("c4", "Kiber xavfsizlik"), ("c5", "Kompyuter savodxonligi")]
ROOMS = [("r1", "1-xona", 14), ("r2", "2-xona", 12), ("r3", "3-xona", 16), ("r4", "Kompyuter xonasi", 18)]
PATTERNS = [("p1", [1, 3, 5]), ("p2", [2, 4, 6]), ("p3", [6, 7])]
TIMES = [("t1", "08:00", "10:00"), ("t2", "10:00", "12:00"), ("t3", "14:00", "16:00"), ("t4", "16:00", "18:00"), ("t5", "18:00", "20:00")]
PRICES = [("cp1", "c1", "2026-01", 550000), ("cp2", "c1", "2026-09", 600000), ("cp3", "c2", "2026-01", 650000),
          ("cp4", "c3", "2026-01", 650000), ("cp5", "c4", "2026-03", 700000), ("cp6", "c5", "2026-01", 400000)]
DISCOUNTS = [("d1", "50% Chegirma", 500000, False), ("d2", "Rag'batlantiruvchi", 350000, False),
             ("d3", "Boshlang'ich balansga", 500000, True), ("d4", "Ikki va undan ortiq farzand", 100000, False),
             ("d5", "Avvaldan to'lov", 75000, False)]
ALL_FIN = ["ADMIN", "BOSH_MENEJER", "ADMINISTRATOR_HISOBCHI", "HISOBCHI"]
EXPENSES = [("e1", "Ijara", "Xarajat", ["ADMIN", "BOSH_MENEJER"]), ("e2", "Kommunal", "Xarajat", ALL_FIN),
            ("e3", "Internet va aloqa", "Xarajat", ALL_FIN), ("e4", "Marketing", "Xarajat", ["ADMIN", "BOSH_MENEJER", "HISOBCHI"]),
            ("e5", "Ofis va xo'jalik", "Xarajat", ALL_FIN), ("e6", "Jihozlar (kompyuter, mebel)", "Qayta investitsiya", ["ADMIN", "BOSH_MENEJER"]),
            ("e7", "Dividend", "Dividend", ["ADMIN"]), ("e8", "Kredit foizi", "Tashqi qarz", ["ADMIN", "BOSH_MENEJER"])]
SOURCES = [("s1", "Instagram"), ("s2", "Telegram"), ("s3", "Tanish-bilish"), ("s4", "Banner / flayer"), ("s5", "Sayt"), ("s6", "Qayta murojaat")]


def ym(s):
    y, m = map(int, s.split("-"))
    return datetime.date(y, m, 1)


class Command(BaseCommand):
    help = "Sinov ma'lumotlarini yaratadi (Emirat filiali, ma'lumotnomalar, 13 xodim, lidlar, guruhlar, shartnomalar, davomat)"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=os.environ.get("DEMO_PASSWORD", ""), help="Barcha demo xodimlar uchun parol")

    def upsert(self, model, key, defaults, m2m=None):
        obj = model.all_objects.filter(legacy_id=f"demo:{key}").first() if hasattr(model, "all_objects") else model.objects.filter(legacy_id=f"demo:{key}").first()
        if obj is None and defaults.get("name"):
            # Qo'lda yaratilgan bir xil nomli yozuv bo'lsa — o'shani olamiz (dublikat emas)
            obj = model.objects.filter(name__iexact=defaults["name"]).first()
            if obj:
                obj.legacy_id = f"demo:{key}"
                obj.save(update_fields=["legacy_id"])
        if obj is None:
            obj = model(legacy_id=f"demo:{key}", **defaults)
            obj.save()
            self.created += 1
        for field, values in (m2m or {}).items():
            getattr(obj, field).set(values)
        return obj

    @transaction.atomic
    def handle(self, *args, password, **opts):
        self.created = 0
        roles = {r.code: r for r in Role.objects.all()}
        branch = self.upsert(Branch, "b1", {"name": "Emirat"})
        users = {}
        for key, name, role, teams in USERS:
            u = User.objects.filter(legacy_id=f"demo:{key}").first()
            if u is None:
                email = None if role == "BOSHQA" else f"{name.split()[0].lower()}@codial.test"
                u = User.objects.create_user(email=email, password=password or None, full_name=name, role=roles[role], teams=teams,
                                             phone="9" + str(zlib.crc32(name.encode()) % 10**8).zfill(8), legacy_id=f"demo:{key}")
                if role not in ("ADMIN", "BOSH_MENEJER"):
                    u.branches.set([branch])
                self.created += 1
            users[key] = u
        acc1 = self.upsert(Account, "acc1", {"name": "Emirat g'azna", "cash_type": "ALL", "initial_balance": 40000000, "start_date": datetime.date(2026, 9, 1)},
                           {"responsible": [users["u2"], users["u5"], users["u6"]]})
        acc2 = self.upsert(Account, "acc2", {"name": "Bosh g'azna", "cash_type": "CARD", "initial_balance": 25000000, "start_date": datetime.date(2026, 9, 1)},
                           {"responsible": [users["u1"], users["u2"]]})
        if not branch.default_cashbox_id:
            branch.default_cashbox, branch.noncash_cashbox = acc1, acc2
            branch.save()
        courses = {k: self.upsert(Course, k, {"name": n}, {"branches": [branch]}) for k, n in COURSES}
        for k, n, cap in ROOMS:
            self.upsert(Room, k, {"branch": branch, "name": n, "capacity": cap})
        patterns = {k: self.upsert(DayPattern, k, {"name": "", "weekdays": wd}) for k, wd in PATTERNS}
        times = [self.upsert(LessonTime, k, {"branch": branch, "start_time": a, "end_time": b}) for k, a, b in TIMES]
        for k, c, m, price in PRICES:
            self.upsert(CoursePrice, k, {"branch": branch, "course": courses[c], "effective_from": ym(m), "price": price})
        for k, n, mx, system in DISCOUNTS:
            self.upsert(DiscountType, k, {"name": n, "max_amount": mx, "is_system": system})
        for k, n, kind, rs in EXPENSES:
            self.upsert(ExpenseCategory, k, {"name": n, "kind": kind}, {"allowed_roles": [roles[r] for r in rs]})
        sources = [self.upsert(LeadSource, k, {"name": n}) for k, n in SOURCES]
        # Joriy va o'tgan oy uchun tasdiqlangan dars soni (kalendar bo'yicha)
        today = timezone.localdate().replace(day=1)
        for d in (services.prev_month(today), today):
            for pk, p in patterns.items():
                self.upsert(LessonFrequency, f"f-{pk}-{d:%Y-%m}", {
                    "branch": branch, "day_pattern": p, "year": d.year, "month": d.month, "status": "Tasdiqlangan",
                    "frequency": services.lesson_days_in_month(d.year, d.month, p.weekdays), "approved_at": timezone.now(),
                }, {"courses": list(courses.values())})
        self.seed_leads(branch, list(courses.values()), list(patterns.values()), times, sources, [users[k] for k in ("u3", "u4", "u5")])
        rooms = {k: Room.objects.get(legacy_id=f"demo:{k}") for k, *_ in ROOMS}
        edu_demo.seed(self, branch, users, courses, patterns, {k: t for (k, *_), t in zip(TIMES, times, strict=False)}, rooms, sources)
        fin_demo.seed(self, branch, users)
        pay_demo.seed(self, branch, users)
        edu_m6_demo.seed(self, branch, users)
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {self.created} ta yangi yozuv."))
        if not password:
            self.stdout.write(self.style.WARNING("Parol berilmadi: demo xodimlar parolsiz. --password yoki DEMO_PASSWORD bilan qayta ishga tushiring."))


    def seed_leads(self, branch, courses, patterns, times, sources, staff, n=45):
        """Lidlar voronkasi va statistika uchun sinov lidlari (oxirgi ~60 kun, turli status va manbalar)."""
        R = random.Random(20261013)
        now = timezone.now()
        statuses = ["1"] * 6 + ["2"] * 10 + ["3"] * 6 + ["4"] * 5 + ["5"] * 8 + ["6"] * 4 + ["7"] * 2 + ["8"] * 4
        notes = ["Narxni so'radi, o'ylab ko'radi", "Kechki guruh bo'lsa yoziladi", "Ota-onasi bilan maslahatlashadi",
                 "Qayta qo'ng'iroq qilish kerak", "Noutbuk sotib olgach keladi"]
        for i in range(n):
            if Lead.all_objects.filter(legacy_id=f"demo:ld{i}").exists():
                continue
            gender = R.choice(["Erkak", "Ayol"])
            first = R.choice(DEMO_MALE if gender == "Erkak" else DEMO_FEMALE)
            last = R.choice(DEMO_LAST) + ("" if gender == "Erkak" else "a")
            st = Student.objects.create(branch=branch, first_name=first, last_name=last, gender=gender, phone1=f"9{R.randint(10**7, 10**8 - 1):08d}",
                                        phone2=f"9{R.randint(10**7, 10**8 - 1):08d}", legacy_id=f"demo:st{i}")
            who = R.choice(staff)
            lead = Lead.objects.create(branch=branch, student=st, source=R.choice(sources), course=R.choice(courses), day_pattern=R.choice(patterns),
                                       status=statuses[i % len(statuses)], age_group=R.choice(AGE_GROUPS[:7]), social_status=R.choice(SOCIAL_STATUSES),
                                       laptop=R.choice(LAPTOP_CHOICES), created_by=who, updated_by=who, legacy_id=f"demo:ld{i}")
            lead.preferred_times.set(R.sample(times, R.randint(1, 2)))
            created = now - datetime.timedelta(days=R.randint(0, 60), hours=R.randint(0, 8))
            Lead.objects.filter(pk=lead.pk).update(created_at=created)
            Student.objects.filter(pk=st.pk).update(created_at=created)
            if R.random() < 0.6:
                c = LeadComment.objects.create(lead=lead, comment=R.choice(notes), created_by=who, updated_by=who, legacy_id=f"demo:lc{i}")
                LeadComment.objects.filter(pk=c.pk).update(created_at=created + datetime.timedelta(days=1))
            self.created += 1


DEMO_MALE = ["Abdulloh", "Jasurbek", "Sardor", "Doniyor", "Behruz", "Ibrohim", "Diyorbek", "Ozodbek", "Temur", "Islom", "Asadbek", "Ulug'bek"]
DEMO_FEMALE = ["Zarina", "Kamola", "Nilufar", "Robiya", "Dilnoza", "Mubina", "Muslima", "Gulruh", "Mohinur", "Sevara"]
DEMO_LAST = ["Karimov", "Aliyev", "Sobirov", "Tursunov", "Yusupov", "Nazarov", "Rahimov", "Olimov", "Sultonov", "Qodirov", "Ismoilov", "Hasanov"]

"""M10: AppSheet → yangi tizim (buyurtmachi qarori 2026-10-14, docs/decisions.md).

Faqat Emirat filialidagi import kuni FAOL shartnomalar va ularga kerakli ma'lumotlar ko'chiriladi:
talaba (+ ota-ona), guruh, kurs, dars kunlari, dars vaqti, xona, guruh ustozi va yordamchisi.
Rejadagi shartnomalar ham (boshlanishi sanadan keyin). 2026-10-18 qarori: boshlang'ich qarz, ochiq lidlar, narxlar, dars soni,
KPI stavkalari va g'azna qoldiqlari ham ko'chadi — `extra.py`.

Har bir yozuvda `legacy_id` = AppSheet kaliti. Qayta ishga tushirish dublikat yaratmaydi: avval legacy_id, keyin
tabiiy kalit (nom, pochta, hafta kunlari…) bo'yicha topadi va maydonlarni Excel'dagidek yangilaydi.
Sinov rejimi (dry_run) — hammasi bajariladi va tekshiriladi, oxirida tranzaksiya bekor qilinadi."""

import collections

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import TEAMS, Role, User
from apps.core.models import Status
from apps.core.roles import RoleCode
from apps.crm.models import Parent, Student
from apps.education.models import Contract, Group
from apps.education.services import FAOL, status_q
from apps.references.models import Branch, Course, DayPattern, LessonTime, Room

from . import extra
from . import reader as r

SHEETS = ["Branches", "Courses", "LessonDays", "LessonTimes", "Rooms", "Users", "Groups", "Contracts", "Students", "Parents"]
BRANCH_NAME = "Emirat"

ROLE_MAP = {
    "admin": RoleCode.ADMIN, "bosh menejer": RoleCode.BOSH_MENEJER, "filial menejeri": RoleCode.FILIAL_MENEJERI, "filial menejer": RoleCode.FILIAL_MENEJERI,
    "administrator": RoleCode.ADMINISTRATOR, "administrator+hisobchi": RoleCode.ADMINISTRATOR_HISOBCHI, "hisobchi": RoleCode.HISOBCHI,
    "ustoz": RoleCode.USTOZ, "yordamchi": RoleCode.YORDAMCHI, "yordmachi": RoleCode.YORDAMCHI,
    "ustoz+yordamchi": RoleCode.USTOZ_YORDAMCHI, "ustoz-yordamchi": RoleCode.USTOZ_YORDAMCHI,
    "boshqa": RoleCode.BOSHQA, "aloqa operatori": RoleCode.BOSHQA, "asoschi / investor": RoleCode.BOSHQA,
}
TEACHER_ROLES = {RoleCode.USTOZ, RoleCode.USTOZ_YORDAMCHI}
SUPPORTER_ROLES = {RoleCode.YORDAMCHI, RoleCode.USTOZ_YORDAMCHI}
STOP_REASONS = {v for v, _ in Contract.StopReason.choices}


class Rollback(Exception):
    pass


class Report:
    def __init__(self, on, dry_run):
        self.on, self.dry_run = on, dry_run
        self.counts = collections.defaultdict(collections.Counter)  # model → {created, updated}
        self.warnings, self.errors, self.checks = [], [], {}

    def count(self, model, created):
        self.counts[model]["yaratildi" if created else "yangilandi"] += 1

    def warn(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)

    def lines(self):
        out = [f"AppSheet importi — {'SINOV REJIMI (bazaga yozilmadi)' if self.dry_run else 'BAJARILDI'} · faol shartnomalar sanasi: {self.on:%d.%m.%Y}", ""]
        for model, c in self.counts.items():
            out.append(f"  {model}: " + ", ".join(f"{k} {v}" for k, v in c.items()))
        out += ["", "Tekshiruv:"] + [f"  {k}: {v}" for k, v in self.checks.items()]
        if self.warnings:
            out += ["", f"Ogohlantirishlar ({len(self.warnings)}):"] + [f"  - {w}" for w in self.warnings]
        if self.errors:
            out += ["", f"XATOLAR ({len(self.errors)}) — bu yozuvlar ko'chirilmadi:"] + [f"  - {e}" for e in self.errors]
        return out


def _upsert(model, legacy, find, values, rep, label, m2m=None):
    """legacy_id bo'yicha, bo'lmasa `find` (tabiiy kalit) bo'yicha topadi; topilmasa yaratadi. Maydonlarni yangilaydi."""
    obj = model.objects.filter(legacy_id=legacy).first() or (model.objects.filter(**find).first() if find else None)
    created = obj is None
    if created:
        obj = model(legacy_id=legacy, **values)
    else:
        obj.legacy_id = legacy
        for k, v in values.items():
            setattr(obj, k, v)
    obj.save()
    for field, items in (m2m or {}).items():
        getattr(obj, field).add(*items)
    rep.count(label, created)
    return obj


def _user(row, branch, rep, roles):
    legacy = r.ident(row.get("UserID"))
    name = r.text(row.get("FullName")) or f"AppSheet xodimi {legacy}"
    email = r.text(row.get("Email")).lower() or None
    code = ROLE_MAP.get(r.text(row.get("RoleID")).lower())
    if code is None:
        rep.warn(f"Xodim {name}: noma'lum rol «{r.text(row.get('RoleID'))}» → Boshqa")
        code = RoleCode.BOSHQA
    status = User.Employment.ACTIVE if r.text(row.get("Status")) == "Qo'shilgan" else User.Employment.LEFT
    existing = User.objects.filter(legacy_id=legacy).first() or (User.objects.filter(email__iexact=email).first() if email else None)
    if existing:
        # Tizimda bor xodim (avvalgi importdan yoki o'zi kiritilgan) — faqat bog'lanadi; roli, ismi va holati o'zgartirilmaydi:
        # importdan keyin xodimlar tizimning o'zida boshqariladi
        if existing.legacy_id != legacy:
            rep.warn(f"Xodim {name}: tizimdagi {existing.email} akkauntiga bog'landi (roli o'zgartirilmadi)")
            existing.legacy_id = legacy
            existing.save(update_fields=["legacy_id"])
        existing.branches.add(branch)
        rep.count("Xodimlar", False)
        return existing
    if User.objects.filter(full_name__iexact=name).exists():
        name = f"{name} ({legacy})"
        rep.warn(f"Xodim ismi tizimda bor — «{name}» deb yozildi, keyin tuzating")
    teams = [t for t in (x.strip() for x in str(row.get("Team") or "").split(",")) if t in TEAMS]
    values = {"full_name": name, "email": email if code != RoleCode.BOSHQA else None, "role": roles[code], "employment_status": status,
              "phone": r.phone(row.get("Phone")), "teams": teams}
    user = User.objects.create_user(legacy_id=legacy, **values)  # parolsiz: kirish havolasi o'tish kuni yuboriladi
    user.branches.add(branch)
    rep.count("Xodimlar", True)
    if status != User.Employment.ACTIVE:
        rep.warn(f"Xodim {name} AppSheet'da «Qo'shilmagan» — «Ishdan ketgan» holatida, lekin faol guruhga biriktirilgan. Kerak bo'lsa Sozlamalar → Foydalanuvchilar'da «Faol» qiling")
    return user


def run(path, on=None, dry_run=True):
    on = on or timezone.localdate()
    rep = Report(on, dry_run)
    wb = r.Workbook(path, SHEETS, optional=extra.EXTRA_SHEETS)
    try:
        with transaction.atomic():
            _import(wb, on, rep)
            if dry_run:
                raise Rollback
    except Rollback:
        pass
    return rep


def _import(wb, on, rep):
    roles = {x.code: x for x in Role.objects.all()}
    src_branch = next((b for b in wb["Branches"] if r.text(b.get("Name")) == BRANCH_NAME), None)
    if not src_branch:
        raise ValueError(f"Excel'da «{BRANCH_NAME}» filiali topilmadi")
    bid = r.ident(src_branch["BranchID"])
    branch = _upsert(Branch, bid, {"name": BRANCH_NAME}, {"name": BRANCH_NAME, "status": Status.ACTIVE}, rep, "Filial")

    groups_src, students_src = wb.by_id("Groups", "GroupID"), wb.by_id("Students", "StudentID")
    users_src, parents_src = wb.by_id("Users", "UserID"), wb.by_id("Parents", "ParentID")
    courses_src, days_src = wb.by_id("Courses", "CourseID"), wb.by_id("LessonDays", "DayID")
    times_src, rooms_src = wb.by_id("LessonTimes", "TimeID"), wb.by_id("Rooms", "RoomID")

    # 1. Faol va rejadagi shartnomalar: (end bo'sh yoki end ≥ sana) va boshlanish sanasi bor
    active, all_src = [], {}
    for c in wb["Contracts"]:
        all_src[r.ident(c.get("ContractID"))] = c
        if r.ident(c.get("BranchID")) != bid:
            continue
        try:
            start, end = r.date(c.get("StartDate")), r.date(c.get("EndDate"))
        except ValueError as e:
            rep.error(f"Shartnoma {r.ident(c.get('ContractID'))}: {e}")
            continue
        if start and (end is None or end >= max(on, start)):
            active.append((c, start, end))
    rep.checks["Excel'da faol shartnomalar"] = len(active)

    cache = {}

    def once(kind, key, fn):
        if (kind, key) not in cache:
            cache[(kind, key)] = fn()
        return cache[(kind, key)]

    def course(cid):
        def make():
            src = courses_src.get(cid)
            if not src:
                raise ValueError(f"kurs {cid} topilmadi")
            name = r.text(src.get("Name"))
            status = Status.ACTIVE if r.text(src.get("Status")) == "Faol" else Status.INACTIVE
            if status != Status.ACTIVE:
                rep.warn(f"Kurs «{name}» AppSheet'da Nofaol, lekin faol guruhda ishlatilgan — Nofaol holatda ko'chirildi")
            return _upsert(Course, cid, {"name": name}, {"name": name, "status": status}, rep, "Kurslar", m2m={"branches": [branch]})
        return once("course", cid, make)

    def pattern(did):
        def make():
            src = days_src.get(did)
            if not src:
                raise ValueError(f"dars kunlari {did} topilmadi")
            wds = sorted({7 if int(x) == 0 else int(x) for x in r.ids(src.get("WeekDay"))})  # AppSheet: yakshanba=0 → ISO 7
            return _upsert(DayPattern, did, {"weekdays_key": ",".join(map(str, wds))}, {"weekdays": wds, "name": ""}, rep, "Dars kunlari")
        return once("pattern", did, make)

    def lesson_time(tid):
        def make():
            src = times_src.get(tid)
            if not src:
                raise ValueError(f"dars vaqti {tid} topilmadi")
            s, e = r.time(src.get("StartTime")), r.time(src.get("EndTime"))
            return _upsert(LessonTime, tid, {"branch": branch, "start_time": s, "end_time": e}, {"branch": branch, "start_time": s, "end_time": e}, rep, "Dars vaqtlari")
        return once("time", tid, make)

    def room(rid):
        def make():
            src = rooms_src.get(rid)
            if not src:
                raise ValueError(f"xona {rid} topilmadi")
            name = r.text(src.get("Name"))
            status = Status.ACTIVE if r.text(src.get("Status")) == "Faol" else Status.INACTIVE
            return _upsert(Room, rid, {"branch": branch, "name": name}, {"branch": branch, "name": name, "capacity": r.integer(src.get("RoomCapacity"), 0), "status": status}, rep, "Xonalar")
        return once("room", rid, make)

    def user(uid, need):
        def make():
            src = users_src.get(uid)
            if not src:
                raise ValueError(f"xodim {uid} topilmadi")
            return _user(src, branch, rep, roles)
        u = once("user", uid, make)
        ok = TEACHER_ROLES if need == "teacher" else SUPPORTER_ROLES
        if need and u.role.code not in ok:
            rep.warn(f"{u.full_name}: roli «{u.role.name}», lekin guruhda {'ustoz' if need == 'teacher' else 'yordamchi'} — rolini tekshiring")
        return u

    def group(gid):
        def make():
            g = groups_src.get(gid)
            if not g:
                raise ValueError(f"guruh {gid} topilmadi")
            sup = r.ident(g.get("SupporterID"))
            values = {
                "branch": branch, "course": course(r.ident(g.get("CourseID"))), "day_pattern": pattern(r.ident(g.get("DayID"))),
                "time": lesson_time(r.ident(g.get("TimeID"))), "teacher": user(r.ident(g.get("TeacherID")), "teacher"),
                "supporter": user(sup, "supporter") if sup else None, "room": room(r.ident(g.get("RoomID"))),
                "start_date": r.date(g.get("StartDate")), "end_date": r.date(g.get("EndDate")),
                "number": r.integer(g.get("GroupNumber"), 0), "comment": r.text(g.get("Comment")),
            }
            obj = _upsert(Group, gid, None, values, rep, "Guruhlar")
            _keep_created(Group, obj, g.get("CreatedTime"))
            return obj
        return once("group", gid, make)

    def parent(pid):
        def make():
            p = parents_src.get(pid)
            if not p:
                rep.warn(f"Ota-ona {pid} Excel'da topilmadi — talaba ota-onasiz ko'chirildi")
                return None
            ph = r.phone(p.get("Phone"))
            values = {"branch": branch, "first_name": r.text(p.get("FirstName"))[:50], "last_name": r.text(p.get("SecondName"))[:50], "phone": ph}
            return _upsert(Parent, pid, None, values, rep, "Ota-onalar")
        return once("parent", pid, make)

    def student(sid):
        def make():
            s = students_src.get(sid)
            if not s:
                raise ValueError(f"talaba {sid} topilmadi")
            first, last = r.text(s.get("FirstName")), r.text(s.get("LastName"))
            p1, p2 = r.phone(s.get("Phone1")), r.phone(s.get("Phone2"))
            label = f"talaba {first} {last}".strip()
            if not first or not last:
                raise ValueError(f"{label}: ism yoki familiya bo'sh")
            if len(first) > 20 or len(last) > 20:
                raise ValueError(f"{label}: ism yoki familiya 20 belgidan uzun")
            if not p1:
                raise ValueError(f"{label}: 1-telefon yo'q yoki 9 raqam emas")
            if p2 == p1:
                p2 = ""
            if s.get("Phone2") not in (None, "") and not r.phone(s.get("Phone2")):
                rep.warn(f"{label}: 2-telefon yaroqsiz — tashlab ketildi")
            gender = r.text(s.get("Gender"))
            pid = r.ident(s.get("ParentID"))
            try:
                birth = r.date(s.get("BirthDate"))
            except ValueError:
                birth = None
                rep.warn(f"{label}: tug'ilgan sana tushunarsiz — bo'sh qoldirildi")
            values = {"branch": branch, "first_name": first, "last_name": last, "father_name": r.text(s.get("ParentName")).replace(".", "")[:50],
                      "gender": gender if gender in Student.Gender.values else "", "phone1": p1, "phone2": p2, "birth_date": birth,
                      "parent": parent(pid) if pid else None}
            obj = _upsert(Student, sid, None, values, rep, "Talabalar")
            _keep_created(Student, obj, s.get("CreatedTime"))
            return obj
        return once("student", sid, make)

    def import_contract(c, start, end=None):
        """Bitta shartnoma (+ talaba, guruh, kurs). Faol shartnomalar — end=None; oktyabr uchun kerak bo'lgan tugagan shartnomalar — haqiqiy sana bilan."""
        cid = r.ident(c.get("ContractID"))
        try:
            with transaction.atomic():
                g = group(r.ident(c.get("GroupID"))) if r.ident(c.get("GroupID")) else None
                if g is None:
                    raise ValueError("guruhi ko'rsatilmagan")
                crs = course(r.ident(c.get("CourseID")))
                if crs.pk != g.course_id:
                    rep.warn(f"Shartnoma {cid}: kursi guruh kursidan farq qiladi — guruh kursi olindi")
                    crs = g.course
                reason = r.text(c.get("StopReason"))
                if reason and end is None:
                    rep.warn(f"Shartnoma {cid}: tugash sanasisiz to'xtatish sababi bor («{reason}») — ko'chirilmadi")
                ctype = Contract.Type.GRANT if r.text(c.get("ContractType")) == "Grant" else Contract.Type.PAID
                values = {"branch": branch, "student": student(r.ident(c.get("StudentID"))), "course": crs, "group": g, "type": ctype,
                          "number": r.integer(c.get("ContractNumber"), 0), "start_date": start, "end_date": end, "stop_reason": reason if end and reason in STOP_REASONS else "",
                          "comment": r.text(c.get("Comment_Reason")), "opening_balance": 0}
                obj = _upsert(Contract, cid, None, values, rep, "Shartnomalar" if end is None else "Shartnomalar (tugagan, oktyabr uchun)")
                _keep_created(Contract, obj, c.get("CreatedTime"))
                return obj
        except Exception as e:  # noqa: BLE001 — bitta yozuv xatosi butun importni to'xtatmasin, hisobotga yoziladi
            cache.clear()  # savepoint bekor qilingan bo'lishi mumkin — keshdagi obyektlar qaytadan topiladi
            rep.error(f"Shartnoma {cid}: {e}")
            return None

    for c, start, _end in active:
        import_contract(c, start)

    active_ids = {r.ident(c.get("ContractID")) for c, _, _ in active}
    _close_ended(branch, on, active_ids, all_src, rep)

    import types

    helpers = types.SimpleNamespace(course=course, pattern=pattern, lesson_time=lesson_time, room=room, user=lambda uid: user(uid, None), group=group,
                                    parent=parent, student=student, reset=cache.clear, contract=import_contract, contracts_src=all_src, active_ids=active_ids,
                                    user_need=user)
    extra.run_all(wb, on, rep, branch, bid, helpers)

    in_db = Contract.objects.filter(branch=branch).filter(status_q(FAOL, on))
    rep.checks["Tizimda faol shartnomalar (shu sanada)"] = in_db.count()
    rep.checks["Ko'chirilgan faol shartnomalar"] = in_db.exclude(legacy_id=None).filter(legacy_id__in=[r.ident(c.get("ContractID")) for c, _, _ in active]).count()
    rep.checks["Faol guruhlar (shu sanada)"] = Group.objects.filter(branch=branch).filter(status_q(FAOL, on)).count()
    rep.checks["Talabalar (shu filialda)"] = Student.objects.filter(branch=branch).count()


def _keep_created(model, obj, raw):
    """AppSheet'dagi yaratilgan vaqt saqlansin (statistika uchun)."""
    try:
        dt = r.moment(raw)
    except ValueError:
        return
    if dt:
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        model.all_objects.filter(pk=obj.pk).update(created_at=dt)


def _close_ended(branch, on, active_ids, all_src, rep):
    """Avvalgi importda ko'chgan, lekin endi Excel'da faol bo'lmagan shartnomalar — AppSheet'dagi tugash sanasi va sababi bilan yopiladi
    (import bir necha marta ishga tushirilsa: masalan bugun va o'tish kuni)."""
    stale = Contract.objects.filter(branch=branch).filter(status_q(FAOL, on)).exclude(legacy_id=None).exclude(legacy_id__in=active_ids)
    for c in stale:
        src = all_src.get(c.legacy_id)
        try:
            end = r.date(src.get("EndDate")) if src else None
        except ValueError:
            end = None
        if not end:
            rep.warn(f"Shartnoma №{c.number} ({c.legacy_id}): Excel'da endi faol emas, lekin tugash sanasi yo'q — qo'lda tekshiring")
            continue
        reason = r.text(src.get("StopReason"))
        c.end_date, c.stop_reason = end, reason if reason in STOP_REASONS else ""
        c.save(update_fields=["end_date", "stop_reason", "updated_at"])
        rep.count("Shartnomalar (yopildi)", False)

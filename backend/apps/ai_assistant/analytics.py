"""AI yordamchi uchun faqat o'qiladigan `analytics_*` view'lar (CLAUDE.md 13).

Har bir view — ustunlari o'zbekcha tavsif bilan. Shu tavsiflar LLM'ga sxema sifatida boradi (ma'lumotning o'zi bormaydi).
`pii=True` — talaba/ota-ona shaxsiy ma'lumoti: natija BM ekranida ko'rinadi, lekin «tahlil» qadamida LLM'ga yuborilmaydi.

View'lar har `migrate` dan oldin o'chiriladi va keyin qayta yaratiladi (apps.py) — jadval ustunlari o'zgarsa ham mos bo'lib turadi.
SQL ikki dialektda ishlaydi: PostgreSQL (server) va SQLite (lokal, testlar)."""

from django.db import connection

from apps.crm.models import Lead

ROLE = "codial_ai"  # PostgreSQL: faqat analytics_* view'larni o'qiy oladigan, kirish huquqisiz rol


def _fns(vendor):
    if vendor == "postgresql":
        return {
            "Y": lambda c: f"CAST(EXTRACT(YEAR FROM {c}) AS INTEGER)",
            "M": lambda c: f"CAST(EXTRACT(MONTH FROM {c}) AS INTEGER)",
            "YM": lambda c: f"to_char({c}, 'YYYY-MM')",
            "LD": lambda c: f"CAST(({c} AT TIME ZONE 'Asia/Tashkent') AS DATE)",
            "HM": lambda c: f"to_char({c}, 'HH24:MI')",
            "TODAY": "CAST((now() AT TIME ZONE 'Asia/Tashkent') AS DATE)",
            "NOW_HM": "to_char(now() AT TIME ZONE 'Asia/Tashkent', 'HH24:MI')",
            # guruh × kun: guruh boshlangan va tizimda birinchi davomat olingan kundan (ko'pi bilan 120 kun oldin) bugungacha
            "DAYS_WITH": "",
            "DAYS_JOIN": "CROSS JOIN LATERAL (SELECT CAST(gs AS DATE) AS x FROM generate_series("
                         "CAST(GREATEST(g.start_date, CAST((now() AT TIME ZONE 'Asia/Tashkent') AS DATE) - 120, "
                         "COALESCE((SELECT MIN(fa.date) FROM education_attendance fa WHERE NOT fa.is_deleted), CAST((now() AT TIME ZONE 'Asia/Tashkent') AS DATE))) AS timestamp), "
                         "CAST(LEAST(COALESCE(g.end_date, CAST((now() AT TIME ZONE 'Asia/Tashkent') AS DATE)), CAST((now() AT TIME ZONE 'Asia/Tashkent') AS DATE)) AS timestamp), "
                         "interval '1 day') gs) d",
            "ISODOW": lambda c: f"CAST(EXTRACT(ISODOW FROM {c}) AS INTEGER)",
        }
    return {
        "Y": lambda c: f"CAST(strftime('%Y', {c}) AS INTEGER)",
        "M": lambda c: f"CAST(strftime('%m', {c}) AS INTEGER)",
        "YM": lambda c: f"strftime('%Y-%m', {c})",
        "LD": lambda c: f"date({c}, '+5 hours')",
        "HM": lambda c: f"substr({c}, 1, 5)",
        "TODAY": "date('now', '+5 hours')",
        "NOW_HM": "strftime('%H:%M', 'now', '+5 hours')",
        "DAYS_WITH": "WITH RECURSIVE d(x) AS (SELECT MAX(date('now', '+5 hours', '-120 days'), "
                     "COALESCE((SELECT MIN(fa.date) FROM education_attendance fa WHERE NOT fa.is_deleted), date('now', '+5 hours'))) UNION ALL "
                     "SELECT date(x, '+1 day') FROM d WHERE x < date('now', '+5 hours'))",
        "DAYS_JOIN": "JOIN d ON d.x >= g.start_date AND (g.end_date IS NULL OR d.x <= g.end_date)",
        "ISODOW": lambda c: f"CASE strftime('%w', {c}) WHEN '0' THEN 7 ELSE CAST(strftime('%w', {c}) AS INTEGER) END",
    }


def _sn(a):
    return f"TRIM({a}.first_name || ' ' || {a}.last_name || ' ' || COALESCE({a}.father_name, ''))"


def _gn(course, group):
    return f"({course}.name || ' / #' || CAST({group}.number AS VARCHAR))"


def _dated(f, col):
    return f"{col} AS date, {f['Y'](col)} AS year, {f['M'](col)} AS month, {f['YM'](col)} AS ym"


def _period_status(f, start, end):
    t = f["TODAY"]
    return f"CASE WHEN {end} IS NOT NULL AND {end} < {t} THEN 'Nofaol' WHEN {start} > {t} THEN 'Rejada' ELSE 'Faol' END"


FIRST_LEAD = "(SELECT l2.id FROM crm_lead l2 WHERE l2.student_id = {s} AND NOT l2.is_deleted ORDER BY l2.created_at LIMIT 1)"

D = "sana (YYYY-MM-DD)"
YMD = [("date", D), ("year", "yil (son)"), ("month", "oy (1–12)"), ("ym", "oy 'YYYY-MM' ko'rinishida — oy bo'yicha filtr/guruhlash uchun eng qulay")]


def _views(f):
    """[(nom, tavsif, [(ustun, tavsif, pii)], sql)]"""
    lead_status = " ".join(f"WHEN '{v}' THEN '{v}. {label.replace(chr(39), chr(39) * 2)}'" for v, label in Lead.LeadStatus.choices)
    lead_statuses = "; ".join(f"'{v}' — {label}" for v, label in Lead.LeadStatus.choices)
    return [
        ("analytics_payments", "Talabalardan olingan har bir to'lov (o'chirilganlarsiz). Tushum = SUM(amount); chegirma alohida.", [
            ("payment_id", "to'lov ID", False), *[(c, d, False) for c, d in YMD],
            ("branch", "filial", False), ("course", "kurs", False), ("group_name", "guruh nomi, masalan 'Frontend / #3'", False), ("teacher_name", "guruh ustozi", False),
            ("contract_id", "shartnoma ID", False), ("contract_number", "shartnoma raqami", False), ("contract_type", "'Pullik' yoki 'Grant'", False),
            ("student_name", "talaba F.I.Sh.", True),
            ("amount", "to'lov summasi, so'm", False), ("discount", "chegirma summasi, so'm (0 — chegirma yo'q)", False), ("discount_type", "chegirma turi", False),
            ("discount_status", "chegirma tasdig'i: 'Tasdiqlashga' / 'Tasdiqlandi' / '' (chegirma yo'q)", False),
            ("cash_type", "to'lov turi: 'CASH' naqd, 'BANK' bank, 'CARD' karta", False),
            ("noncash_status", "naqdsiz to'lov tasdig'i: 'Tasdiqlashga' / 'Tasdiqlandi' / '' (naqd)", False),
            ("account", "g'azna", False), ("lead_source", "talaba qaysi manbadan kelgan (lid manbasi)", False), ("created_by", "to'lovni kiritgan xodim", False),
        ], f"""
SELECT p.id AS payment_id, {_dated(f, 'p.date')}, b.name AS branch, co.name AS course, {_gn('gco', 'g')} AS group_name, tu.full_name AS teacher_name,
  c.id AS contract_id, c.number AS contract_number, c.type AS contract_type, {_sn('s')} AS student_name,
  p.amount, COALESCE(p.discount, 0) AS discount, dt.name AS discount_type, p.discount_status, p.cash_type, p.noncash_status,
  acc.name AS account, ls.name AS lead_source, cu.full_name AS created_by
FROM finance_payment p
JOIN education_contract c ON c.id = p.contract_id
JOIN crm_student s ON s.id = c.student_id
JOIN references_branch b ON b.id = p.branch_id
JOIN references_course co ON co.id = c.course_id
LEFT JOIN education_group g ON g.id = p.group_id
LEFT JOIN references_course gco ON gco.id = g.course_id
LEFT JOIN accounts_user tu ON tu.id = g.teacher_id
LEFT JOIN references_discounttype dt ON dt.id = p.discount_type_id
LEFT JOIN finance_account acc ON acc.id = p.cashbox_id
LEFT JOIN accounts_user cu ON cu.id = p.created_by_id
LEFT JOIN crm_lead ld ON ld.id = {FIRST_LEAD.format(s='c.student_id')}
LEFT JOIN references_leadsource ls ON ls.id = ld.source_id
WHERE NOT p.is_deleted"""),

        ("analytics_contracts", "Har bir shartnoma (talaba ↔ kurs/guruh) va uning balansi. Qarzdor: debt > 0. Faol talabalar: status = 'Faol'.", [
            ("contract_id", "shartnoma ID", False), ("contract_number", "shartnoma raqami", False),
            ("branch", "filial", False), ("course", "kurs", False), ("group_name", "guruh nomi", False), ("teacher_name", "guruh ustozi", False),
            ("student_name", "talaba F.I.Sh.", True), ("gender", "'Erkak' / 'Ayol'", False), ("birth_date", "tug'ilgan sana", True),
            ("phone1", "talaba 1-telefoni", True), ("phone2", "talaba 2-telefoni", True), ("parent_name", "ota-ona (vasiy)", True), ("parent_phone", "ota-ona telefoni", True),
            ("contract_type", "'Pullik' yoki 'Grant'", False), ("start_date", "boshlanish sanasi", False), ("end_date", "tugash (to'xtatish) sanasi, NULL — davom etmoqda", False),
            ("start_ym", "boshlanish oyi 'YYYY-MM' (yangi shartnomalar)", False), ("end_ym", "tugash oyi 'YYYY-MM' (to'xtatilgan shartnomalar)", False),
            ("status", "bugungi holat: 'Faol' / 'Rejada' / 'Nofaol'", False), ("stop_reason", "to'xtatish sababi", False),
            ("lead_source", "lid manbasi", False), ("age_group", "yosh guruhi, masalan '16-18'", False),
            ("opening_balance", "boshlang'ich qarz (AppSheet'dan ko'chirilgan)", False), ("charged", "darslar uchun yozilgan jami summa", False),
            ("paid", "jami to'langan", False), ("discount_sum", "jami chegirma", False), ("debt", "joriy qarz = opening_balance + charged − paid − discount_sum (musbat — qarzdor)", False),
        ], f"""
SELECT c.id AS contract_id, c.number AS contract_number, b.name AS branch, co.name AS course, {_gn('gco', 'g')} AS group_name, tu.full_name AS teacher_name,
  {_sn('s')} AS student_name, s.gender, s.birth_date, s.phone1, s.phone2,
  TRIM(COALESCE(pa.first_name, '') || ' ' || COALESCE(pa.last_name, '')) AS parent_name, pa.phone AS parent_phone,
  c.type AS contract_type, c.start_date, c.end_date, {f['YM']('c.start_date')} AS start_ym,
  CASE WHEN c.end_date IS NULL THEN NULL ELSE {f['YM']('c.end_date')} END AS end_ym,
  {_period_status(f, 'c.start_date', 'c.end_date')} AS status, c.stop_reason, ls.name AS lead_source, ld.age_group,
  COALESCE(c.opening_balance, 0) AS opening_balance, COALESCE(ch.s, 0) AS charged, COALESCE(pp.amount, 0) AS paid, COALESCE(pp.discount, 0) AS discount_sum,
  COALESCE(c.opening_balance, 0) + COALESCE(ch.s, 0) - COALESCE(pp.amount, 0) - COALESCE(pp.discount, 0) AS debt
FROM education_contract c
JOIN crm_student s ON s.id = c.student_id
JOIN references_branch b ON b.id = c.branch_id
JOIN references_course co ON co.id = c.course_id
LEFT JOIN crm_parent pa ON pa.id = s.parent_id
LEFT JOIN education_group g ON g.id = c.group_id
LEFT JOIN references_course gco ON gco.id = g.course_id
LEFT JOIN accounts_user tu ON tu.id = g.teacher_id
LEFT JOIN (SELECT contract_id, SUM(student_debt) AS s FROM education_attendance WHERE NOT is_deleted GROUP BY contract_id) ch ON ch.contract_id = c.id
LEFT JOIN (SELECT contract_id, SUM(amount) AS amount, SUM(discount) AS discount FROM finance_payment WHERE NOT is_deleted GROUP BY contract_id) pp ON pp.contract_id = c.id
LEFT JOIN crm_lead ld ON ld.id = {FIRST_LEAD.format(s='c.student_id')}
LEFT JOIN references_leadsource ls ON ls.id = ld.source_id
WHERE NOT c.is_deleted"""),

        ("analytics_attendance", "Davomat: har bir dars × talaba qatori. Davomat foizi = keldi ('1') ulushi, odatda status <> '-' qatorlar orasida.", [
            ("attendance_id", "davomat qatori ID", False), *[(c, d, False) for c, d in YMD],
            ("branch", "filial", False), ("course", "kurs", False), ("group_name", "guruh nomi", False), ("contract_id", "shartnoma ID", False),
            ("contract_type", "'Pullik' / 'Grant'", False), ("student_name", "talaba F.I.Sh.", True),
            ("status", "'1' keldi, '0' sababli, 'X' besabab kelmadi, '-' nofaol", False), ("status_name", "status nomi", False),
            ("teacher_name", "darsni o'tgan ustoz (o'rindosh bo'lsa o'rindosh)", False), ("supporter_name", "yordamchi ustoz", False),
            ("contact_status", "kelmaganlar bilan bog'lanish: 'Bog'lanishga', 'Gaplashildi', 'Tushib bo'lmadi', 'Noto'g'ri raqam'", False),
            ("student_debt", "shu dars uchun talabaga yozilgan summa (NULL — dars soni tasdiqlanmagan)", False),
            ("teacher_kpi", "shu qator uchun ustoz KPI'si, so'm", False), ("supporter_kpi", "shu qator uchun yordamchi KPI'si, so'm", False),
        ], f"""
SELECT a.id AS attendance_id, {_dated(f, 'a.date')}, b.name AS branch, co.name AS course, {_gn('gco', 'g')} AS group_name,
  a.contract_id, c.type AS contract_type, {_sn('s')} AS student_name, a.status, st.name AS status_name,
  tu.full_name AS teacher_name, su.full_name AS supporter_name, a.contact_status, a.student_debt, a.teacher_kpi, a.supporter_kpi
FROM education_attendance a
JOIN education_contract c ON c.id = a.contract_id
JOIN crm_student s ON s.id = c.student_id
JOIN references_branch b ON b.id = a.branch_id
JOIN references_course co ON co.id = a.course_id
JOIN education_group g ON g.id = a.group_id
JOIN references_course gco ON gco.id = g.course_id
LEFT JOIN references_attendancestatus st ON st.code = a.status
LEFT JOIN accounts_user tu ON tu.id = a.teacher_id
LEFT JOIN accounts_user su ON su.id = a.supporter_id
WHERE NOT a.is_deleted"""),

        ("analytics_lessons", "Dars jadvali bo'yicha bo'lishi kerak bo'lgan darslar: guruh × dars kuni — tizimda birinchi davomat olingan kundan "
         "(ko'pi bilan 120 kun oldin) bugungacha. "
         "Davomat OLINMAGAN darslar: taken = 0 AND started = 1. analytics_attendance da faqat olingan davomat bor.", [
            *[(c, d, False) for c, d in YMD], ("weekday", "hafta kuni: 1 Dushanba … 7 Yakshanba", False),
            ("branch", "filial", False), ("course", "kurs", False), ("group_id", "guruh ID", False), ("group_name", "guruh nomi", False),
            ("teacher_name", "guruh ustozi", False), ("supporter_name", "guruh yordamchisi", False),
            ("lesson_time", "dars vaqti, masalan '14:00-16:00'", False), ("start_time", "dars boshlanishi 'HH:MM'", False),
            ("started", "1 — dars boshlangan (o'tgan kun yoki bugun boshlanish vaqti o'tgan), 0 — hali boshlanmagan", False),
            ("students", "shu kuni guruhdagi faol shartnomalar (talabalar) soni", False),
            ("marked", "davomat belgilangan talabalar soni", False), ("came", "keldi ('1')", False), ("excused", "sababli ('0')", False),
            ("absent", "besabab kelmadi ('X')", False), ("taken", "1 — davomat olingan, 0 — olinmagan", False),
        ], f"""{f['DAYS_WITH']}
SELECT y.*, CASE WHEN y.marked > 0 THEN 1 ELSE 0 END AS taken
FROM (
  SELECT d.x AS date, {f['Y']('d.x')} AS year, {f['M']('d.x')} AS month, {f['YM']('d.x')} AS ym, {f['ISODOW']('d.x')} AS weekday,
    b.name AS branch, co.name AS course, g.id AS group_id, {_gn('co', 'g')} AS group_name, tu.full_name AS teacher_name, su.full_name AS supporter_name,
    {f['HM']('lt.start_time')} || '-' || {f['HM']('lt.end_time')} AS lesson_time, {f['HM']('lt.start_time')} AS start_time,
    CASE WHEN d.x < {f['TODAY']} THEN 1 WHEN d.x = {f['TODAY']} AND {f['HM']('lt.start_time')} <= {f['NOW_HM']} THEN 1 ELSE 0 END AS started,
    (SELECT COUNT(*) FROM education_contract c WHERE c.group_id = g.id AND NOT c.is_deleted AND c.start_date <= d.x
       AND (c.end_date IS NULL OR c.end_date >= d.x)) AS students,
    COALESCE(att.marked, 0) AS marked, COALESCE(att.came, 0) AS came, COALESCE(att.excused, 0) AS excused, COALESCE(att.absent, 0) AS absent
  FROM education_group g
  {f['DAYS_JOIN']}
  JOIN references_branch b ON b.id = g.branch_id
  JOIN references_course co ON co.id = g.course_id
  JOIN references_daypattern dp ON dp.id = g.day_pattern_id
  LEFT JOIN references_lessontime lt ON lt.id = g.time_id
  LEFT JOIN accounts_user tu ON tu.id = g.teacher_id
  LEFT JOIN accounts_user su ON su.id = g.supporter_id
  LEFT JOIN (SELECT group_id, date, COUNT(*) AS marked, SUM(CASE WHEN status = '1' THEN 1 ELSE 0 END) AS came,
               SUM(CASE WHEN status = '0' THEN 1 ELSE 0 END) AS excused, SUM(CASE WHEN status = 'X' THEN 1 ELSE 0 END) AS absent
             FROM education_attendance WHERE NOT is_deleted GROUP BY group_id, date) att ON att.group_id = g.id AND att.date = d.x
  WHERE NOT g.is_deleted AND ',' || dp.weekdays_key || ',' LIKE '%,' || CAST({f['ISODOW']('d.x')} AS VARCHAR) || ',%'
) y"""),

        ("analytics_leads", "Lidlar (murojaatlar). Konversiya = has_contract = 1 bo'lgan lidlar ulushi. Lid sanasi — yaratilgan kun.", [
            ("lead_id", "lid ID", False), ("created_date", "lid yaratilgan sana", False), ("year", "yil", False), ("month", "oy (1–12)", False), ("ym", "lid oyi 'YYYY-MM'", False),
            ("branch", "filial", False), ("source", "lid manbasi (Instagram, Telegram, ...)", False), ("course", "qiziqqan kurs", False),
            ("status", f"bosqich kodi: {lead_statuses}", False), ("status_name", "bosqich nomi", False),
            ("student_name", "talaba F.I.Sh.", True), ("phone1", "1-telefon", True), ("phone2", "2-telefon", True), ("gender", "'Erkak' / 'Ayol'", False),
            ("age_group", "yosh guruhi", False), ("social_status", "ijtimoiy holat", False), ("laptop", "noutbuk: 'Bor', 'Yo'q', 'Sotib oladi'", False),
            ("group_name", "sinov darsi guruhi", False), ("demo_date", "sinov dars kuni", False), ("demo_attended", "'Keldi' / 'Kelmadi' / NULL", False),
            ("has_contract", "1 — shartnoma tuzilgan, 0 — yo'q", False), ("has_payment", "1 — kamida bitta to'lov qilgan, 0 — yo'q", False),
            ("created_by", "lidni kiritgan xodim", False),
        ], f"""
SELECT x.lead_id, x.created_date, {f['Y']('x.created_date')} AS year, {f['M']('x.created_date')} AS month, {f['YM']('x.created_date')} AS ym,
  x.branch, x.source, x.course, x.status, x.status_name, x.student_name, x.phone1, x.phone2, x.gender, x.age_group, x.social_status, x.laptop,
  x.group_name, x.demo_date, x.demo_attended, x.has_contract, x.has_payment, x.created_by
FROM (
  SELECT l.id AS lead_id, {f['LD']('l.created_at')} AS created_date, b.name AS branch, ls.name AS source, co.name AS course,
    l.status, CASE l.status {lead_status} END AS status_name, {_sn('s')} AS student_name, s.phone1, s.phone2, s.gender,
    l.age_group, l.social_status, l.laptop, {_gn('gco', 'g')} AS group_name, l.demo_date,
    CASE WHEN l.demo_attended IS NULL THEN NULL WHEN l.demo_attended THEN 'Keldi' ELSE 'Kelmadi' END AS demo_attended,
    CASE WHEN EXISTS (SELECT 1 FROM education_contract c WHERE c.student_id = l.student_id AND NOT c.is_deleted) THEN 1 ELSE 0 END AS has_contract,
    CASE WHEN EXISTS (SELECT 1 FROM finance_payment p JOIN education_contract c ON c.id = p.contract_id
                      WHERE c.student_id = l.student_id AND NOT p.is_deleted) THEN 1 ELSE 0 END AS has_payment,
    cu.full_name AS created_by
  FROM crm_lead l
  JOIN crm_student s ON s.id = l.student_id
  JOIN references_branch b ON b.id = l.branch_id
  LEFT JOIN references_leadsource ls ON ls.id = l.source_id
  LEFT JOIN references_course co ON co.id = l.course_id
  LEFT JOIN education_group g ON g.id = l.group_id
  LEFT JOIN references_course gco ON gco.id = g.course_id
  LEFT JOIN accounts_user cu ON cu.id = l.created_by_id
  WHERE NOT l.is_deleted
) x"""),

        ("analytics_calls", "Qabul telefonidagi qo'ng'iroqlar (raqamsiz — shaxsiy ma'lumot yo'q). Konversiya: manba bo'yicha qo'ng'iroq → lid → shartnoma. "
         "Javobsiz qo'ng'iroqlarga qayta bog'lanish: missed = 1 va callback_done = 1.", [
            ("call_id", "qo'ng'iroq ID", False), *[(c, d, False) for c, d in YMD], ("branch", "filial", False),
            ("direction", "'Kiruvchi', 'Chiquvchi', 'Javobsiz', 'Rad etilgan', 'Bloklangan'", False), ("duration_sec", "suhbat davomiyligi, soniya (0 — gaplashilmagan)", False),
            ("talked", "1 — gaplashilgan (suhbat > 0)", False), ("is_first", "1 — bu raqamdan birinchi qo'ng'iroq", False),
            ("known", "1 — raqam bazadagi talaba yoki vasiyniki", False), ("lead_status", f"raqamga mos lidning bosqich kodi: {lead_statuses}", False),
            ("source", "mos lidning manbasi", False), ("course", "mos lidning kursi", False), ("has_contract", "1 — talabada shartnoma bor", False),
            ("missed", "1 — javobsiz yoki rad etilgan", False), ("callback_done", "1 — qayta bog'lanilgan / qayta qo'ng'iroq qilingan", False),
        ], f"""
SELECT x.call_id, x.date, {f['Y']('x.date')} AS year, {f['M']('x.date')} AS month, {f['YM']('x.date')} AS ym, x.branch, x.direction, x.duration_sec,
  x.talked, x.is_first, x.known, x.lead_status, x.source, x.course, x.has_contract, x.missed, x.callback_done
FROM (
  SELECT c.id AS call_id, {f['LD']('c.started_at')} AS date, b.name AS branch, c.direction, c.duration AS duration_sec,
    CASE WHEN c.duration > 0 THEN 1 ELSE 0 END AS talked, CASE WHEN c.is_first THEN 1 ELSE 0 END AS is_first,
    CASE WHEN c.student_id IS NOT NULL OR c.parent_id IS NOT NULL THEN 1 ELSE 0 END AS known,
    l.status AS lead_status, ls.name AS source, co.name AS course,
    CASE WHEN c.student_id IS NOT NULL AND EXISTS (SELECT 1 FROM education_contract ct WHERE ct.student_id = c.student_id AND NOT ct.is_deleted) THEN 1 ELSE 0 END AS has_contract,
    CASE WHEN c.direction IN ('Javobsiz', 'Rad etilgan') THEN 1 ELSE 0 END AS missed,
    CASE WHEN c.callback_at IS NOT NULL THEN 1 ELSE 0 END AS callback_done
  FROM calls_callrecord c
  JOIN references_branch b ON b.id = c.branch_id
  LEFT JOIN crm_lead l ON l.id = c.lead_id AND NOT l.is_deleted
  LEFT JOIN references_leadsource ls ON ls.id = l.source_id
  LEFT JOIN references_course co ON co.id = l.course_id
  WHERE NOT c.is_deleted
) x"""),

        ("analytics_groups", "Guruhlar va bugungi to'lishi.", [
            ("group_id", "guruh ID", False), ("group_name", "guruh nomi", False), ("branch", "filial", False), ("course", "kurs", False),
            ("teacher_name", "ustoz", False), ("supporter_name", "yordamchi", False), ("room", "xona", False), ("capacity", "xona sig'imi", False),
            ("day_pattern", "dars kunlari, masalan 'Dush,Chor,Jum'", False), ("lesson_time", "dars vaqti, masalan '08:00-10:00'", False),
            ("start_date", "boshlanish sanasi", False), ("end_date", "tugash sanasi", False), ("status", "'Faol' / 'Rejada' / 'Nofaol'", False),
            ("active_contracts", "bugun faol shartnomalar (talabalar) soni", False), ("fill_pct", "to'lish foizi = active_contracts / capacity × 100 (NULL — sig'im yo'q)", False),
        ], f"""
SELECT x.*, CASE WHEN COALESCE(x.capacity, 0) = 0 THEN NULL ELSE ROUND(100.0 * x.active_contracts / x.capacity, 1) END AS fill_pct
FROM (
  SELECT g.id AS group_id, {_gn('co', 'g')} AS group_name, b.name AS branch, co.name AS course, tu.full_name AS teacher_name, su.full_name AS supporter_name,
    r.name AS room, r.capacity, dp.name AS day_pattern, {f['HM']('lt.start_time')} || '-' || {f['HM']('lt.end_time')} AS lesson_time,
    g.start_date, g.end_date, {_period_status(f, 'g.start_date', 'g.end_date')} AS status,
    (SELECT COUNT(*) FROM education_contract c WHERE c.group_id = g.id AND NOT c.is_deleted AND c.start_date <= {f['TODAY']}
       AND (c.end_date IS NULL OR c.end_date >= {f['TODAY']})) AS active_contracts
  FROM education_group g
  JOIN references_branch b ON b.id = g.branch_id
  JOIN references_course co ON co.id = g.course_id
  LEFT JOIN accounts_user tu ON tu.id = g.teacher_id
  LEFT JOIN accounts_user su ON su.id = g.supporter_id
  LEFT JOIN references_room r ON r.id = g.room_id
  LEFT JOIN references_daypattern dp ON dp.id = g.day_pattern_id
  LEFT JOIN references_lessontime lt ON lt.id = g.time_id
  WHERE NOT g.is_deleted
) x"""),

        ("analytics_expenses", "Xarajatlar. Foydadan faqat kind = 'Xarajat' ayiriladi; 'Qayta investitsiya', 'Dividend', 'Tashqi qarz' alohida. Hisob davri — period_ym.", [
            ("expense_id", "xarajat ID", False), *[(c, d, False) for c, d in YMD],
            ("period_year", "hisob davri yili", False), ("period_month", "hisob davri oyi", False), ("period_ym", "hisob davri 'YYYY-MM' (oylik hisobotlar uchun shuni ishlating)", False),
            ("branch", "filial", False), ("category", "kategoriya", False), ("kind", "'Xarajat' / 'Qayta investitsiya' / 'Dividend' / 'Tashqi qarz'", False),
            ("name", "xarajat nomi", False), ("quantity", "soni", False), ("price", "narxi", False), ("total", "jami = quantity × price, so'm", False),
            ("cash_type", "'CASH' / 'BANK' / 'CARD'", False), ("account", "g'azna", False), ("cashier_name", "kassir", False),
        ], f"""
SELECT e.id AS expense_id, {_dated(f, 'e.date')}, e.period_year, e.period_month,
  CAST(e.period_year AS VARCHAR) || '-' || CASE WHEN e.period_month < 10 THEN '0' ELSE '' END || CAST(e.period_month AS VARCHAR) AS period_ym,
  b.name AS branch, cat.name AS category, cat.kind, e.name, e.quantity, e.price, e.total, e.cash_type, acc.name AS account, cu.full_name AS cashier_name
FROM finance_expense e
JOIN references_branch b ON b.id = e.branch_id
JOIN references_expensecategory cat ON cat.id = e.category_id
LEFT JOIN finance_account acc ON acc.id = e.account_id
LEFT JOIN accounts_user cu ON cu.id = e.cashier_id
WHERE NOT e.is_deleted"""),

        ("analytics_salaries", "Oylik belgilash: xodim × oy. total = fixed + bonus + kpi_manual + teacher_kpi + supporter_kpi − fine. Foydadan SUM(total) ayiriladi.", [
            ("salary_id", "yozuv ID", False), ("branch", "filial", False), ("user_name", "xodim", False), ("role", "xodim roli", False),
            ("year", "yil", False), ("month", "oy", False), ("ym", "oy 'YYYY-MM'", False),
            ("fixed", "belgilangan oylik", False), ("bonus", "bonus", False), ("kpi_manual", "qo'lda kiritilgan KPI", False), ("fine", "jarima", False),
            ("teacher_kpi", "davomatdan hisoblangan ustoz KPI'si", False), ("supporter_kpi", "davomatdan hisoblangan yordamchi KPI'si", False),
            ("given", "shu oy uchun berilgan pul", False), ("total", "hisoblangan oylik", False), ("month_balance", "total − given (musbat — xodimga qarzmiz)", False),
        ], f"""
SELECT x.*, x.fixed + x.bonus + x.kpi_manual + x.teacher_kpi + x.supporter_kpi - x.fine AS total,
  x.fixed + x.bonus + x.kpi_manual + x.teacher_kpi + x.supporter_kpi - x.fine - x.given AS month_balance
FROM (
  SELECT sa.id AS salary_id, b.name AS branch, u.full_name AS user_name, r.name AS role, sa.year, sa.month,
    CAST(sa.year AS VARCHAR) || '-' || CASE WHEN sa.month < 10 THEN '0' ELSE '' END || CAST(sa.month AS VARCHAR) AS ym,
    COALESCE(sa.fixed, 0) AS fixed, COALESCE(sa.bonus, 0) AS bonus, COALESCE(sa.kpi, 0) AS kpi_manual, COALESCE(sa.fine, 0) AS fine,
    COALESCE((SELECT SUM(a.teacher_kpi) FROM education_attendance a WHERE NOT a.is_deleted AND a.teacher_id = sa.user_id AND a.branch_id = sa.branch_id
              AND {f['Y']('a.date')} = sa.year AND {f['M']('a.date')} = sa.month), 0) AS teacher_kpi,
    COALESCE((SELECT SUM(a.supporter_kpi) FROM education_attendance a WHERE NOT a.is_deleted AND a.supporter_id = sa.user_id AND a.branch_id = sa.branch_id
              AND {f['Y']('a.date')} = sa.year AND {f['M']('a.date')} = sa.month), 0) AS supporter_kpi,
    COALESCE((SELECT SUM(p.amount) FROM payroll_salarypayout p WHERE NOT p.is_deleted AND p.user_id = sa.user_id AND p.branch_id = sa.branch_id
              AND p.year = sa.year AND p.month = sa.month), 0) AS given
  FROM payroll_salaryassignment sa
  JOIN references_branch b ON b.id = sa.branch_id
  JOIN accounts_user u ON u.id = sa.user_id
  LEFT JOIN accounts_role r ON r.id = u.role_id
  WHERE NOT sa.is_deleted
) x"""),

        ("analytics_salary_payouts", "Xodimlarga berilgan oylik pullari (har bir berish).", [
            ("payout_id", "ID", False), *[(c, d, False) for c, d in YMD],
            ("branch", "filial", False), ("user_name", "xodim", False), ("period_year", "qaysi oy uchun — yil", False), ("period_month", "qaysi oy uchun — oy", False),
            ("type", "turi: O'zgarmas / Bonus / KPI (matn sifatida)", False), ("amount", "summa", False), ("cash_type", "'CASH' / 'BANK' / 'CARD'", False), ("account", "g'azna", False),
        ], f"""
SELECT p.id AS payout_id, {_dated(f, 'p.date')}, b.name AS branch, u.full_name AS user_name, p.year AS period_year, p.month AS period_month,
  p.type, p.amount, p.cash_type, acc.name AS account
FROM payroll_salarypayout p
JOIN references_branch b ON b.id = p.branch_id
JOIN accounts_user u ON u.id = p.user_id
LEFT JOIN finance_account acc ON acc.id = p.account_id
WHERE NOT p.is_deleted"""),

        ("analytics_accounts", "G'aznalar va joriy qoldig'i (tasdiqlangan harakatlar bo'yicha).", [
            ("account", "g'azna nomi", False), ("cash_type", "g'azna turi: 'CASH', 'BANK', 'CARD', 'ALL'", False), ("status", "'Faol' / 'Nofaol'", False),
            ("initial_balance", "boshlang'ich qoldiq", False), ("balance", "joriy qoldiq", False), ("pending", "tasdiqlanmagan (hali qo'shilmagan) summalar", False),
        ], """
SELECT a.name AS account, a.cash_type, a.status, a.initial_balance,
  a.initial_balance + COALESCE((SELECT SUM(m.amount) FROM finance_cashmovement m WHERE m.account_id = a.id AND m.is_confirmed), 0) AS balance,
  COALESCE((SELECT SUM(m.amount) FROM finance_cashmovement m WHERE m.account_id = a.id AND NOT m.is_confirmed), 0) AS pending
FROM finance_account a
WHERE NOT a.is_deleted"""),

        ("analytics_cash_movements", "G'azna harakatlari jurnali: kirim (+) va chiqim (−).", [
            *[(c, d, False) for c, d in YMD], ("account", "g'azna", False), ("cash_type", "'CASH' / 'BANK' / 'CARD'", False), ("amount", "summa: + kirim, − chiqim", False),
            ("source_type", "manba: 'payment' to'lov, 'expense' xarajat, 'transfer' o'tkazma, 'exchange' ayirboshlash, 'creditor' kreditor, 'salary' oylik", False),
            ("is_confirmed", "1 — tasdiqlangan (balansda), 0 — tasdiq kutmoqda", False),
        ], f"""
SELECT {_dated(f, 'm.date')}, acc.name AS account, m.cash_type, m.amount, m.source_type,
  CASE WHEN m.is_confirmed THEN 1 ELSE 0 END AS is_confirmed
FROM finance_cashmovement m
JOIN finance_account acc ON acc.id = m.account_id"""),

        ("analytics_evaluations", "Talabalar ustozni baholashi: 5 mezon, har biri 0–10, jami 0–50.", [
            ("evaluation_id", "ID", False), *[(c, d, False) for c, d in YMD], ("branch", "filial", False), ("teacher_name", "ustoz", False), ("group_name", "guruh", False),
            ("student_name", "baholagan talaba", True),
            ("s1", "mavzuni sodda tushuntiradi", False), ("s2", "dars qiziq, qiziq metodlar", False), ("s3", "adolatli, teng e'tibor", False),
            ("s4", "kerak vaqtda yordam beradi", False), ("s5", "tavsiya berib ruhlantiradi", False), ("total", "jami (s1+…+s5)", False),
        ], f"""
SELECT e.id AS evaluation_id, {_dated(f, 'e.date')}, b.name AS branch, tu.full_name AS teacher_name, {_gn('gco', 'g')} AS group_name, {_sn('s')} AS student_name,
  e.s1, e.s2, e.s3, e.s4, e.s5, e.s1 + e.s2 + e.s3 + e.s4 + e.s5 AS total
FROM education_teacherevaluation e
JOIN references_branch b ON b.id = e.branch_id
JOIN education_contract c ON c.id = e.contract_id
JOIN crm_student s ON s.id = c.student_id
LEFT JOIN accounts_user tu ON tu.id = e.teacher_id
LEFT JOIN education_group g ON g.id = e.group_id
LEFT JOIN references_course gco ON gco.id = g.course_id
WHERE NOT e.is_deleted"""),

        ("analytics_creditors", "Kreditorlar (tashqi qarzlar).", [
            ("creditor", "kreditor", False), ("initial_balance", "boshlang'ich haqqi", False),
            ("current_balance", "joriy haqqi = initial_balance − Σ amallar (amal: '−' qarz olish, '+' qaytarish)", False), ("transactions", "amallar soni", False),
        ], """
SELECT cr.name AS creditor, cr.initial_balance,
  cr.initial_balance - COALESCE((SELECT SUM(t.amount) FROM finance_creditortransaction t WHERE t.creditor_id = cr.id AND NOT t.is_deleted), 0) AS current_balance,
  (SELECT COUNT(*) FROM finance_creditortransaction t WHERE t.creditor_id = cr.id AND NOT t.is_deleted) AS transactions
FROM finance_creditor cr
WHERE NOT cr.is_deleted"""),

        ("analytics_course_prices", "Kurs narxlari tarixi: oy uchun narx — shu oygacha bo'lgan eng oxirgi effective_from.", [
            ("branch", "filial", False), ("course", "kurs", False), ("effective_from", "amal qila boshlagan oy (1-kun)", False), ("price", "oylik narx, so'm", False),
        ], """
SELECT b.name AS branch, co.name AS course, p.effective_from, p.price
FROM references_courseprice p
JOIN references_branch b ON b.id = p.branch_id
JOIN references_course co ON co.id = p.course_id
WHERE NOT p.is_deleted"""),

        ("analytics_staff", "Xodimlar (telefon va pochtasiz).", [
            ("user_name", "xodim", False), ("role", "rol nomi", False), ("role_code", "rol kodi: ADMIN, BOSH_MENEJER, FILIAL_MENEJERI, ADMINISTRATOR, ADMINISTRATOR_HISOBCHI, HISOBCHI, "
                                                    "USTOZ, YORDAMCHI, USTOZ_YORDAMCHI, BOSHQA", False),
            ("employment_status", "'Faol' / 'Ishdan ketgan'", False),
        ], """
SELECT u.full_name AS user_name, r.name AS role, r.code AS role_code, u.employment_status
FROM accounts_user u
LEFT JOIN accounts_role r ON r.id = u.role_id"""),
    ]


def views(vendor=None):
    return _views(_fns(vendor or connection.vendor))


VIEW_NAMES = [v[0] for v in views("sqlite")]
PII_COLUMNS = {c for v in views("sqlite") for c, _, pii in v[2] if pii}
PII_VIEWS = {v[0] for v in views("sqlite") if any(pii for _, _, pii in v[2])}


def schema_text():
    """LLM uchun sxema: faqat nomlar va tavsiflar."""
    out = []
    for name, desc, cols, _ in views():
        out.append(f"VIEW {name} — {desc}\n" + "\n".join(f"  {c}: {d}" for c, d, _ in cols))
    return "\n\n".join(out)


def drop_views(conn=None):
    conn = conn or connection
    with conn.cursor() as cur:
        for name in reversed(VIEW_NAMES):
            cur.execute(f"DROP VIEW IF EXISTS {name}")


def create_views(conn=None):
    conn = conn or connection
    pg = conn.vendor == "postgresql"
    with conn.cursor() as cur:
        for name, _, _, sql in _views(_fns(conn.vendor)):
            cur.execute(f"DROP VIEW IF EXISTS {name}")
            cur.execute(f"CREATE VIEW {name} AS {sql}")
        if pg:
            cur.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN CREATE ROLE {ROLE} NOLOGIN; END IF; END $$")
            cur.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
            cur.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
            cur.execute(f"GRANT SELECT ON {', '.join(VIEW_NAMES)} TO {ROLE}")

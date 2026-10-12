/* Sinov ma'lumotlari. "O'tish sanasi" (AppSheet'dan import) — 2026-09-01 deb olingan. */
(function (A) {
  A.MIGRATION_DATE = '2026-09-01';

  A.buildSeed = function (todayIso) {
    const R = A.rng(20261011);
    const pick = (arr) => arr[Math.floor(R() * arr.length)];
    const chance = (p) => R() < p;
    const ts = (iso, h = 10, m = 0) => {
      const d = A.parse(iso);
      d.setHours(h, m + Math.floor(R() * 50));
      return d.getTime();
    };
    const today = todayIso;
    const curYm = A.ym(today);
    const B = 'b1';

    const S = {
      version: 5,
      seededFor: today,
      settings: { demoToday: null },
      currentUser: null,
      branches: [{ id: B, name: 'Emirat', status: 'Faol', default_cashbox: 'acc1', noncash_cashbox: 'acc2' }],
      roles: A.defaultRoles(),
      users: [
        { id: 'u1', full_name: 'Rustam Mirzayev', role: 'ADMIN', teams: ['Boshqa'] },
        { id: 'u2', full_name: 'Dilshod Karimov', role: 'BOSH_MENEJER', teams: ['Moliya', 'HR'] },
        { id: 'u3', full_name: 'Malika Yusupova', role: 'FILIAL_MENEJERI', teams: ["Ta'lim"] },
        { id: 'u4', full_name: 'Nodira Azimova', role: 'ADMINISTRATOR', teams: ['Qabul'] },
        { id: 'u5', full_name: 'Sardor Tursunov', role: 'ADMINISTRATOR_HISOBCHI', teams: ['Qabul', 'Moliya'] },
        { id: 'u6', full_name: 'Gulnoza Rahimova', role: 'HISOBCHI', teams: ['Moliya'] },
        { id: 'u7', full_name: 'Jasur Aliyev', role: 'USTOZ', teams: ["Ta'lim"] },
        { id: 'u8', full_name: 'Bekzod Nazarov', role: 'USTOZ', teams: ["Ta'lim"] },
        { id: 'u9', full_name: 'Shahzod Ergashev', role: 'USTOZ', teams: ["Ta'lim"] },
        { id: 'u10', full_name: 'Aziz Qodirov', role: 'USTOZ_YORDAMCHI', teams: ["Ta'lim", 'IT'] },
        { id: 'u11', full_name: 'Madina Saidova', role: 'YORDAMCHI', teams: ["Ta'lim"] },
        { id: 'u12', full_name: 'Otabek Xolmatov', role: 'YORDAMCHI', teams: ["Ta'lim"] },
        { id: 'u13', full_name: 'Farrux Olimov', role: 'BOSHQA', teams: ["Ta'minot"] },
      ],
      courses: [
        { id: 'c1', name: 'Frontend', branches: [B], status: 'Faol' },
        { id: 'c2', name: 'Backend (Python)', branches: [B], status: 'Faol' },
        { id: 'c3', name: 'Flutter', branches: [B], status: 'Faol' },
        { id: 'c4', name: 'Kiber xavfsizlik', branches: [B], status: 'Faol' },
        { id: 'c5', name: 'Kompyuter savodxonligi', branches: [B], status: 'Faol' },
      ],
      rooms: [
        { id: 'r1', branch: B, name: '1-xona', capacity: 14, status: 'Faol' },
        { id: 'r2', branch: B, name: '2-xona', capacity: 12, status: 'Faol' },
        { id: 'r3', branch: B, name: '3-xona', capacity: 16, status: 'Faol' },
        { id: 'r4', branch: B, name: 'Kompyuter xonasi', capacity: 18, status: 'Faol' },
      ],
      dayPatterns: [
        { id: 'p1', name: 'Dush, Chor, Jum', weekdays: [1, 3, 5], status: 'Faol' },
        { id: 'p2', name: 'Sesh, Pay, Shan', weekdays: [2, 4, 6], status: 'Faol' },
        { id: 'p3', name: 'Shan, Yak', weekdays: [6, 7], status: 'Faol' },
      ],
      lessonTimes: [
        { id: 't1', branch: B, start: '08:00', end: '10:00', status: 'Faol' },
        { id: 't2', branch: B, start: '10:00', end: '12:00', status: 'Faol' },
        { id: 't3', branch: B, start: '14:00', end: '16:00', status: 'Faol' },
        { id: 't4', branch: B, start: '16:00', end: '18:00', status: 'Faol' },
        { id: 't5', branch: B, start: '18:00', end: '20:00', status: 'Faol' },
      ],
      coursePrices: [
        { id: 'cp1', branch: B, course: 'c1', effective_from: '2026-01', price: 550000 },
        { id: 'cp2', branch: B, course: 'c1', effective_from: '2026-09', price: 600000 },
        { id: 'cp3', branch: B, course: 'c2', effective_from: '2026-01', price: 650000 },
        { id: 'cp4', branch: B, course: 'c3', effective_from: '2026-01', price: 650000 },
        { id: 'cp5', branch: B, course: 'c4', effective_from: '2026-03', price: 700000 },
        { id: 'cp6', branch: B, course: 'c5', effective_from: '2026-01', price: 400000 },
      ],
      lessonFreqs: [],
      kpiRates: [
        { id: 'k1', branch: B, user: 'u7', role_type: 'USTOZ', course: 'c1', effective_from: '2026-09', type: 'Foiz', fixed: 0, percent: 40 },
        { id: 'k2', branch: B, user: 'u8', role_type: 'USTOZ', course: 'c2', effective_from: '2026-09', type: "O'zgarmas", fixed: 260000, percent: 0 },
        { id: 'k3', branch: B, user: 'u9', role_type: 'USTOZ', course: 'c3', effective_from: '2026-09', type: 'Foiz', fixed: 0, percent: 40 },
        { id: 'k4', branch: B, user: 'u10', role_type: 'USTOZ', course: 'c4', effective_from: '2026-09', type: 'Foiz', fixed: 0, percent: 45 },
        { id: 'k5', branch: B, user: 'u10', role_type: 'USTOZ', course: 'c5', effective_from: '2026-09', type: "O'zgarmas", fixed: 150000, percent: 0 },
        { id: 'k6', branch: B, user: 'u11', role_type: 'YORDAMCHI', course: 'c1', effective_from: '2026-09', type: "O'zgarmas", fixed: 60000, percent: 0 },
        { id: 'k7', branch: B, user: 'u11', role_type: 'YORDAMCHI', course: 'c5', effective_from: '2026-09', type: "O'zgarmas", fixed: 40000, percent: 0 },
        { id: 'k8', branch: B, user: 'u12', role_type: 'YORDAMCHI', course: 'c2', effective_from: '2026-09', type: 'Foiz', fixed: 0, percent: 10 },
      ],
      discountTypes: [
        { id: 'd1', name: '50% Chegirma', max: 500000, is_system: false, is_d50: true, courses: [] },
        { id: 'd2', name: "Rag'batlantiruvchi", max: 350000, is_system: false, is_d50: false, courses: [] },
        { id: 'd3', name: "Boshlang'ich balansga", max: 500000, is_system: true, is_d50: false, courses: [] },
        { id: 'd4', name: 'Ikki va undan ortiq farzand', max: 100000, is_system: false, is_d50: false, courses: [] },
        { id: 'd5', name: 'Avvaldan to\'lov', max: 75000, is_system: false, is_d50: false, courses: [] },
      ],
      expenseCats: [
        { id: 'e1', name: 'Ijara', kind: 'Xarajat', allowed_roles: ['ADMIN', 'BOSH_MENEJER'] },
        { id: 'e2', name: 'Kommunal', kind: 'Xarajat', allowed_roles: ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'] },
        { id: 'e3', name: 'Internet va aloqa', kind: 'Xarajat', allowed_roles: ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'] },
        { id: 'e4', name: 'Marketing', kind: 'Xarajat', allowed_roles: ['ADMIN', 'BOSH_MENEJER', 'HISOBCHI'] },
        { id: 'e5', name: "Ofis va xo'jalik", kind: 'Xarajat', allowed_roles: ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'] },
        { id: 'e6', name: 'Jihozlar (kompyuter, mebel)', kind: 'Qayta investitsiya', allowed_roles: ['ADMIN', 'BOSH_MENEJER'] },
        { id: 'e7', name: 'Dividend', kind: 'Dividend', allowed_roles: ['ADMIN'] },
        { id: 'e8', name: 'Kredit foizi', kind: 'Tashqi qarz', allowed_roles: ['ADMIN', 'BOSH_MENEJER'] },
      ],
      leadSources: [
        { id: 's1', name: 'Instagram', status: 'Faol' }, { id: 's2', name: 'Telegram', status: 'Faol' }, { id: 's3', name: 'Tanish-bilish', status: 'Faol' },
        { id: 's4', name: 'Banner / flayer', status: 'Faol' }, { id: 's5', name: 'Sayt', status: 'Faol' }, { id: 's6', name: 'Qayta murojaat', status: 'Faol' },
      ],
      accounts: [
        { id: 'acc1', name: "Emirat g'azna", responsible: ['u2', 'u5', 'u6'], cash_type: 'ALL', initial: 8000000, status: 'Faol', start: '2026-09-01' },
        { id: 'acc2', name: "Bosh g'azna", responsible: ['u1', 'u2'], cash_type: 'CARD', initial: 25000000, status: 'Faol', start: '2026-09-01' },
      ],
      attendanceStatuses: [
        { code: '1', name: 'Keldi', roles: ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI', 'ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI', 'USTOZ', 'USTOZ_YORDAMCHI'] },
        { code: '0', name: 'Sababli', roles: ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI', 'ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI', 'USTOZ', 'USTOZ_YORDAMCHI'] },
        { code: 'X', name: 'Besabab', roles: ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI', 'ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI', 'USTOZ', 'USTOZ_YORDAMCHI'] },
        { code: '-', name: 'Nofaol', roles: ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI'] },
      ],
      parents: [], students: [], leads: [], leadComments: [],
      groups: [], contracts: [], attendance: [], makeups: [],
      payments: [], transfers: [], exchanges: [], expenses: [],
      creditors: [], creditorTx: [], creditorComments: [],
      salaryAssign: [], salaryPayouts: [],
      tasks: [], evaluations: [], gradings: [], parentCalls: [], discount50: [],
      audit: [],
    };
    for (const u of S.users) {
      u.branches = ['ADMIN', 'BOSH_MENEJER'].includes(u.role) ? [] : [B];
      u.phone = '9' + String(Math.floor(R() * 1e8)).padStart(8, '0');
      u.email = u.role === 'BOSHQA' ? '' : u.full_name.toLowerCase().split(' ')[0] + '@codial.uz';
      u.status = 'Faol';
    }

    /* ---- Guruhlar ---- */
    const G = [
      { id: 'g1', course: 'c1', pattern: 'p1', time: 't3', teacher: 'u7', supporter: 'u11', room: 'r1', start: '2026-06-01', number: 12, n: 12 },
      { id: 'g2', course: 'c1', pattern: 'p2', time: 't4', teacher: 'u7', supporter: 'u11', room: 'r2', start: '2026-08-15', number: 13, n: 9 },
      { id: 'g3', course: 'c2', pattern: 'p1', time: 't4', teacher: 'u8', supporter: 'u12', room: 'r3', start: '2026-05-10', number: 8, n: 11 },
      { id: 'g4', course: 'c3', pattern: 'p2', time: 't2', teacher: 'u9', supporter: '', room: 'r1', start: '2026-07-01', number: 5, n: 6 },
      { id: 'g5', course: 'c4', pattern: 'p3', time: 't2', teacher: 'u10', supporter: '', room: 'r2', start: '2026-08-01', number: 3, n: 7 },
      { id: 'g6', course: 'c5', pattern: 'p3', time: 't3', teacher: 'u10', supporter: 'u11', room: 'r4', start: '2026-09-05', number: 21, n: 10 },
      { id: 'g7', course: 'c2', pattern: 'p2', time: 't5', teacher: 'u8', supporter: 'u12', room: 'r3', start: A.addDays(today, 8), number: 9, n: 3 },
    ];
    for (const g of G) {
      S.groups.push({ id: g.id, branch: B, course: g.course, pattern: g.pattern, time: g.time, teacher: g.teacher, supporter: g.supporter, room: g.room, start: g.start, end: '', number: g.number, comment: '', created_by: 'u3', created_at: ts(g.start < '2026-09-01' ? '2026-09-01' : g.start) });
    }

    /* ---- Talabalar ---- */
    const MF = ['Ali', 'Sardorbek', 'Jahongir', 'Bobur', 'Doniyor', 'Islom', "Ulug'bek", 'Asadbek', 'Muhammadali', 'Abdulloh', 'Javohir', 'Sanjar', 'Temur', 'Shohruh', 'Azizbek', 'Behruz', 'Mirjalol', 'Ozodbek', 'Diyorbek', 'Ibrohim', 'Nurislom', 'Firdavs', 'Akmal', 'Samandar'];
    const FF = ['Madina', 'Sevara', 'Dilnoza', 'Mohinur', 'Zarina', 'Shahzoda', 'Gulruh', 'Nilufar', 'Mubina', 'Sabina', 'Robiya', 'Ruxshona', 'Kamola', 'Zilola', 'Muslima'];
    const LN = ['Karimov', 'Rahimov', 'Tursunov', 'Abdullayev', 'Yusupov', 'Qodirov', 'Ergashev', 'Nazarov', 'Aliyev', 'Saidov', 'Mamatov', 'Olimov', 'Sobirov', 'Hasanov', 'Mirzayev', "Jo'rayev", 'Nurmatov', 'Ismoilov', 'Umarov', 'Sultonov'];
    const PN = ['Anvar', 'Bahodir', 'Rustam', 'Shuhrat', 'Davron', 'Farhod', 'Ilhom', 'Jamshid', 'Komil', 'Murod', 'Nodir', 'Olim', "Po'lat", 'Qahramon', 'Rasul', 'Tohir', 'Umid', 'Xurshid', 'Zafar'];
    const OPS = ['90', '91', '93', '94', '97', '99', '88', '33'];
    const phone = () => pick(OPS) + String(Math.floor(R() * 1e7)).padStart(7, '0');
    const used = new Set();
    let pid = 0, sid = 0;
    const newStudent = (createdIso, withBirth = true) => {
      let first, last, father, gender;
      do {
        gender = chance(0.62) ? 'Erkak' : 'Ayol';
        first = gender === 'Erkak' ? pick(MF) : pick(FF);
        last = pick(LN) + (gender === 'Ayol' ? 'a' : '');
        const p = pick(PN);
        father = gender === 'Erkak' ? `${p} o'g'li` : `${p} qizi`;
      } while (used.has(first + last + father));
      used.add(first + last + father);
      let parent = '';
      if (chance(0.7)) {
        const p = { id: 'pa' + ++pid, branch: B, first_name: father.split(' ')[0], last_name: last.replace(/a$/, ''), phone: phone(), created_by: 'u4', created_at: ts(createdIso) };
        S.parents.push(p);
        parent = p.id;
      }
      const age = 10 + Math.floor(R() * 18);
      const s = {
        id: 'st' + ++sid, branch: B, first_name: first, last_name: last, father_name: father, gender,
        phone1: phone(), phone2: chance(0.5) ? phone() : '',
        birth_date: withBirth ? `${2026 - age}-${String(1 + Math.floor(R() * 12)).padStart(2, '0')}-${String(1 + Math.floor(R() * 28)).padStart(2, '0')}` : '',
        parent, created_by: pick(['u4', 'u5']), created_at: ts(createdIso),
      };
      S.students.push(s);
      return s;
    };

    const AGE = ['9-12', '13-15', '16-18', '19-21', '22-24', '25-27', '28-30', '31-33'];
    const SOC = ["Maktab o'quvchisi", 'Oliygoh talabasi', 'Kompaniya xodimi', 'Davlat xizmatchisi', 'Vaqtincha ishsiz'];
    const LAP = ['Bor', "Yo'q", 'Sotib oladi'];
    let lid = 0;
    const newLead = (st, status, extra) => {
      const created = extra.created;
      const l = {
        id: 'l' + ++lid, branch: B, student: st.id, source: pick(['s1', 's1', 's1', 's2', 's2', 's3', 's3', 's4', 's5', 's6']),
        course: extra.course, pattern: extra.pattern || pick(['p1', 'p2', 'p3']), times: [pick(['t2', 't3', 't4', 't5'])],
        status, group: extra.group || '', demo_date: extra.demo || '', demo_attended: extra.attended ?? null,
        age_group: pick(AGE), social: pick(SOC), laptop: pick(LAP), tags: chance(0.3) ? [pick(['VIP', 'Chegirma so\'radi', 'Ota-onasi qo\'ng\'iroq qiladi', 'Kechki vaqt'])] : [],
        created_by: pick(['u4', 'u5']), created_at: ts(created, 11),
      };
      S.leads.push(l);
      return l;
    };

    /* ---- Shartnomalar ---- */
    let cnum = 100;
    const stopReasons = ['Moliyaviy qiyinchilik', 'Dars sifatidan qoniqmadi', "Kurs yoqmadi - Boshqa kursga o'tyapti", 'Kursni tamomladi'];
    for (const g of G) {
      for (let i = 0; i < g.n; i++) {
        let start;
        if (g.id === 'g7') start = g.start;
        else if (g.start >= '2026-09-01') start = A.addDays(g.start, Math.floor(R() * 12));
        else start = chance(0.75) ? g.start : A.addDays(g.start, 7 + Math.floor(R() * 40));
        if (start > today && g.id !== 'g7') start = g.start;
        const createdIso = start < '2026-09-01' ? A.addDays(start, -2) : A.addDays(start, -1);
        const st = newStudent(createdIso);
        const c = {
          id: 'ct' + (cnum + 1), branch: B, student: st.id, course: g.course, group: g.id,
          type: 'Pullik', number: ++cnum, start, end: '', stop_reason: '', comment: '',
          opening: start < '2026-09-01' ? pick([0, 0, 0, 0, 0, 150000, 300000, -100000]) : 0,
          created_by: pick(['u4', 'u5']), created_at: ts(createdIso, 12),
        };
        S.contracts.push(c);
        if (start >= '2026-07-01' || chance(0.4)) {
          newLead(st, "5", { created: A.addDays(createdIso, -6 - Math.floor(R() * 10)), course: g.course, pattern: g.pattern, group: g.id, demo: start, attended: true });
        }
      }
    }
    // Grant shartnomalar
    S.contracts[3].type = 'Grant';
    S.contracts[25].type = 'Grant';
    S.contracts[3].comment = "IT Park granti";
    S.contracts[25].comment = "Ijtimoiy grant (ko'p bolali oila)";
    // To'xtatilgan shartnomalar
    [[7, '2026-09-18'], [14, '2026-09-26'], [30, '2026-10-02'], [41, '2026-09-11']].forEach(([i, end], k) => {
      const c = S.contracts[i];
      if (c && c.start < end) { c.end = end; c.stop_reason = stopReasons[k]; }
    });

    /* ---- Oydagi dars soni ---- */
    const patternCourses = { p1: ['c1', 'c2'], p2: ['c1', 'c2', 'c3'], p3: ['c4', 'c5'] };
    let fid = 0;
    for (let ym = '2026-09'; ym <= curYm; ym = A.addMonths(ym, 1)) {
      for (const p of S.dayPatterns) {
        const isTaklif = ym === curYm && p.id === 'p3';
        S.lessonFreqs.push({
          id: 'f' + ++fid, branch: B, pattern: p.id, courses: [...patternCourses[p.id]],
          year: Number(ym.slice(0, 4)), month: Number(ym.slice(5, 7)),
          frequency: A.lessonDaysInMonth(ym, p.weekdays).length,
          status: isTaklif ? 'Taklif' : 'Tasdiqlangan', approved_by: isTaklif ? '' : 'u3',
          created_by: 'system', created_at: ts(ym + '-01', 6),
        });
      }
    }

    /* ---- Davomat ---- */
    let aid = 0;
    const statusPick = () => {
      const r = R();
      return r < 0.86 ? '1' : r < 0.93 ? 'X' : '0';
    };
    for (const c of S.contracts) {
      const g = S.groups.find((x) => x.id === c.group);
      const pat = S.dayPatterns.find((p) => p.id === g.pattern);
      let d = c.start > A.MIGRATION_DATE ? c.start : A.MIGRATION_DATE;
      const last = A.addDays(today, -1);
      const pauseFrom = c.id === 'ct105' ? '2026-09-14' : null;
      for (; d <= last; d = A.addDays(d, 1)) {
        if (c.end && d > c.end) break;
        if (!pat.weekdays.includes(A.isoWeekday(d))) continue;
        let status = statusPick();
        if (pauseFrom && d >= pauseFrom && d <= A.addDays(pauseFrom, 9)) status = '-';
        const a = {
          id: 'a' + ++aid, branch: B, group: g.id, course: c.course, contract: c.id, date: d, status,
          teacher: g.teacher, supporter: g.supporter, pattern: g.pattern, contact: '', comment: '',
          created_by: g.teacher, created_at: ts(d, 15),
        };
        if (status === 'X' || status === '0') {
          const old = A.diffDays(d, today) > 4;
          a.contact = old ? pick(['Gaplashildi', 'Gaplashildi', "Tushib bo'lmadi"]) : "Bog'lanishga";
          if (a.contact === 'Gaplashildi') a.comment = pick(['Kasal edi', "Ota-onasi bilan gaplashildi, keyingi darsga keladi", "To'yga ketgan", 'Imtihonga tayyorlanyapti']);
          if (status === '0' && !a.comment) a.comment = 'Oldindan ogohlantirdi';
        }
        S.attendance.push(a);
      }
    }
    // O'rindosh ustoz bilan o'tilgan bitta dars
    const subDay = S.attendance.filter((a) => a.group === 'g3' && a.date >= '2026-09-20').map((a) => a.date)[0];
    if (subDay) S.attendance.filter((a) => a.group === 'g3' && a.date === subDay).forEach((a) => (a.teacher = 'u10'));

    /* ---- To'lovlar ---- */
    let payid = 0;
    const months = [];
    for (let ym = '2026-09'; ym <= curYm; ym = A.addMonths(ym, 1)) months.push(ym);
    const priceOf = (course, ym) => A.sortBy(S.coursePrices.filter((p) => p.course === course && p.effective_from <= ym), (p) => p.effective_from, true)[0].price;
    for (const c of S.contracts) {
      if (c.type === 'Grant') continue;
      for (const ym of months) {
        const monthStart = ym + '-01';
        if (c.start > A.addDays(today, -1)) continue;
        if (c.end && c.end < monthStart) continue;
        const isCur = ym === curYm;
        if (isCur && chance(0.32)) continue; // joriy oy to'lamaganlar — qarzdorlar
        let day = A.addDays(c.start > monthStart ? c.start : monthStart, Math.floor(R() * 8));
        if (day >= today) day = A.addDays(today, -1);
        let amount = priceOf(c.course, ym);
        if (ym === months[0] && c.opening > 0 && chance(0.5)) amount += c.opening;
        if (chance(0.12)) amount = Math.round(amount / 2 / 1000) * 1000;
        const r = R();
        const cash_type = r < 0.68 ? 'CASH' : r < 0.9 ? 'CARD' : 'BANK';
        const recent = A.diffDays(day, today) <= 4;
        const p = {
          id: 'pay' + ++payid, branch: B, contract: c.id, date: day, amount, cash_type,
          discount_type: '', discount: 0, disc_status: '', disc_by: '', disc_at: null,
          nc_status: cash_type === 'CASH' ? '' : recent ? 'Tasdiqlashga' : 'Tasdiqlandi',
          nc_by: cash_type !== 'CASH' && !recent ? 'u2' : '', nc_at: null,
          cashbox: cash_type === 'CASH' ? 'acc1' : 'acc2', accountant: cash_type === 'CASH' ? pick(['u5', 'u6']) : 'u2',
          comment: '', created_by: pick(['u5', 'u6']), created_at: ts(day, 9),
        };
        if (chance(0.08)) {
          p.discount_type = 'd4'; p.discount = 100000; p.disc_status = 'Tasdiqlandi'; p.disc_by = 'u1';
        } else if (chance(0.05)) {
          p.discount_type = 'd5'; p.discount = 75000; p.disc_status = 'Tasdiqlandi'; p.disc_by = 'u2';
        }
        S.payments.push(p);
      }
    }
    // Tasdiq kutayotgan chegirma
    const lastPays = S.payments.filter((p) => A.diffDays(p.date, today) <= 6 && !p.discount);
    if (lastPays[0]) Object.assign(lastPays[0], { discount_type: 'd2', discount: 200000, disc_status: 'Tasdiqlashga', comment: "Olimpiadada 2-o'rin uchun rag'bat" });

    /* ---- Xarajatlar ---- */
    let eid = 0;
    const exp = (date, cat, name, qty, price, cash_type, account, by) => {
      if (date >= today) return;
      S.expenses.push({ id: 'ex' + ++eid, branch: B, date, category: cat, name, quantity: qty, price, cash_type, account, cashier: by, period_year: Number(date.slice(0, 4)), period_month: Number(date.slice(5, 7)), comment: '', created_by: by, created_at: ts(date, 13) });
    };
    for (const ym of months) {
      exp(ym + '-02', 'e1', 'Bino ijarasi', 1, 6000000, 'BANK', 'acc2', 'u2');
      exp(ym + '-05', 'e3', 'Internet (100 Mbit)', 1, 600000, 'CASH', 'acc1', 'u6');
      exp(ym + '-08', 'e2', "Elektr va gaz", 1, 870000, 'CASH', 'acc1', 'u6');
      exp(ym + '-03', 'e4', 'Instagram reklama', 1, 1500000, 'CARD', 'acc2', 'u2');
      exp(ym + '-06', 'e5', 'Suv (19 litr)', 8, 18000, 'CASH', 'acc1', 'u5');
      exp(ym + '-09', 'e5', 'Kanselyariya', 1, 240000, 'CASH', 'acc1', 'u6');
    }
    exp('2026-09-12', 'e6', 'Noutbuk Lenovo IdeaPad', 2, 7400000, 'BANK', 'acc2', 'u2');
    exp('2026-09-28', 'e7', "Ta'sischilarga dividend", 1, 5000000, 'CARD', 'acc2', 'u1');
    exp('2026-10-02', 'e8', 'Kredit foizi (sentabr)', 1, 420000, 'BANK', 'acc2', 'u2');
    exp('2026-09-15', 'e4', 'Flayer chop etish', 2000, 350, 'CASH', 'acc1', 'u5');

    /* ---- G'aznalar orasida o'tkazma, ayirboshlash ---- */
    S.transfers.push({ id: 'tr1', date: '2026-09-30', sender: 'acc1', sender_cashier: 'u6', cash_type: 'CASH', amount: 6000000, receiver: 'acc2', receiver_cashier: 'u2', status: 'Tasdiqlandi', confirmed_by: 'u2', confirmed_at: ts('2026-09-30', 18), comment: 'Oy yakuni inkassatsiya', created_by: 'u6', created_at: ts('2026-09-30', 17) });
    S.transfers.push({ id: 'tr2', date: A.addDays(today, -1), sender: 'acc1', sender_cashier: 'u5', cash_type: 'CASH', amount: 5000000, receiver: 'acc2', receiver_cashier: 'u2', status: 'Tasdiqlashga', confirmed_by: '', confirmed_at: null, comment: 'Ijara uchun', created_by: 'u5', created_at: ts(A.addDays(today, -1), 18) });
    S.exchanges.push({ id: 'xc1', account: 'acc2', date: '2026-09-20', from_type: 'CARD', amount: 3000000, to_type: 'CASH', amount_to: 2970000, created_by: 'u2', created_at: ts('2026-09-20', 12) });

    /* ---- Kreditorlar ---- */
    S.creditors.push({ id: 'cr1', name: 'Ipoteka bank (kredit)', initial: 0, created_by: 'u1', created_at: ts('2026-09-01') });
    S.creditors.push({ id: 'cr2', name: 'Investor — Anvar Sobirov', initial: 10000000, created_by: 'u1', created_at: ts('2026-09-01') });
    S.creditorTx.push({ id: 'ctx1', date: '2026-09-02', creditor: 'cr1', amount: -30000000, cash_type: 'BANK', account: 'acc2', cashier: 'u2', comment: 'Kredit olindi (12 oyga)', created_by: 'u2', created_at: ts('2026-09-02') });
    S.creditorTx.push({ id: 'ctx2', date: '2026-10-02', creditor: 'cr1', amount: 2500000, cash_type: 'BANK', account: 'acc2', cashier: 'u2', comment: "1-oy asosiy qarz to'lovi", created_by: 'u2', created_at: ts('2026-10-02') });
    S.creditorComments.push({ id: 'cc1', creditor: 'cr1', comment: "Har oy 2-sanada to'lov qilinadi", created_by: 'u2', created_at: ts('2026-09-02', 15) });

    /* ---- Oyliklar ---- */
    const fixed = { u2: 8000000, u3: 6000000, u4: 3500000, u5: 4500000, u6: 4000000, u10: 1000000, u13: 2500000 };
    let said = 0;
    for (const ym of months) {
      for (const u of S.users) {
        if (u.role === 'ADMIN') continue;
        S.salaryAssign.push({
          id: 'sa' + ++said, branch: B, user: u.id, year: Number(ym.slice(0, 4)), month: Number(ym.slice(5, 7)),
          fixed: fixed[u.id] || 0, bonus: ym === '2026-09' && u.id === 'u7' ? 300000 : 0, kpi: 0,
          fine: ym === '2026-09' && u.id === 'u4' ? 100000 : 0, comment: ym === '2026-09' && u.id === 'u4' ? 'Kechikish uchun jarima' : '',
          created_by: 'u3', created_at: ts(ym + '-01', 9),
        });
      }
    }
    let spid = 0;
    const payout = (user, amount, type, date, viaCard) => {
      if (date >= today) return;
      S.salaryPayouts.push({ id: 'sp' + ++spid, branch: B, user, year: 2026, month: 9, date, type, amount, cash_type: viaCard ? 'CARD' : 'CASH', account: viaCard ? 'acc2' : 'acc1', cashier: viaCard ? 'u2' : 'u6', comment: viaCard ? 'Kartaga' : '', created_by: viaCard ? 'u2' : 'u6', created_at: ts(date, 16) });
    };
    for (const [u, amt] of Object.entries(fixed)) payout(u, u === 'u4' ? amt - 100000 : amt, "O'zgarmas", '2026-10-05', ['u2', 'u3', 'u5'].includes(u));
    payout('u7', 2000000, 'KPI', '2026-10-06');
    payout('u8', 2000000, 'KPI', '2026-10-06');
    payout('u9', 1000000, 'KPI', '2026-10-06');

    /* ---- Lidlar (shartnoma tuzilmaganlar) ---- */
    const leadPlan = [
      ['1', 6], ['2', 5], ['3', 4], ['4', 3], ['5', 1], ['6', 3], ['7', 2], ['8', 3],
    ];
    for (const [status, n] of leadPlan) {
      for (let i = 0; i < n; i++) {
        const created = A.addDays(today, -Math.floor(R() * 70) - 1);
        const course = pick(['c1', 'c1', 'c2', 'c3', 'c4', 'c5']);
        const st = newStudent(created, status !== '5');
        const groupsFor = S.groups.filter((g) => g.course === course);
        const grp = ['3', '4', '5'].includes(status) && groupsFor.length ? pick(groupsFor).id : '';
        newLead(st, status, {
          created, course, group: grp,
          demo: grp ? A.addDays(created, 3 + Math.floor(R() * 5)) : '',
          attended: status === '3' ? null : status === '4' || status === '5' ? true : null,
        });
        if (status === '3') S.leads[S.leads.length - 1].demo_date = A.addDays(today, 1 + i);
      }
    }
    let lcid = 0;
    for (const l of S.leads.filter((x) => ['1', '2', '8', '6'].includes(x.status))) {
      S.leadComments.push({ id: 'lc' + ++lcid, branch: B, lead: l.id, comment: pick(["Narxni so'radi, o'ylab ko'radi", 'Kechki guruh bo\'lsa yoziladi', "Ota-onasi bilan maslahatlashadi", "Qayta qo'ng'iroq qilish kerak", 'Noutbuk sotib olgach keladi']), created_by: l.created_by, created_at: l.created_at + 86400000 });
    }

    /* ---- Qoldirilgan darsni yetkazish so'rovi ---- */
    const xRow = S.attendance.filter((a) => a.group === 'g1' && a.status === 'X').slice(-1)[0];
    if (xRow) S.makeups.push({ id: 'mk1', attendance: xRow.id, teacher: 'u7', makeup_date: A.addDays(xRow.date, 2), comment: "Shanba kuni alohida dars o'tib berdim", status: 'Kutilmoqda', reviewed_by: '', reviewed_at: null, reject_reason: '', created_by: 'u7', created_at: ts(A.addDays(xRow.date, 2), 19) });

    /* ---- Qo'shimcha modullar ---- */
    const g1c = S.contracts.filter((c) => c.group === 'g1');
    S.tasks.push({ id: 'tk1', branch: B, teacher: 'u7', course: 'c1', group: 'g1', contract: g1c[0].id, task: "Portfolio sayt: 3 sahifali landing (HTML/CSS)", deadline: A.addDays(today, 2), status: 'Yuklatildi', completion: null, teacher_comment: '', created_by: 'u7', created_at: ts(A.addDays(today, -3)) });
    S.tasks.push({ id: 'tk2', branch: B, teacher: 'u7', course: 'c1', group: 'g1', contract: g1c[1].id, task: 'JavaScript: massivlar bilan 10 ta masala', deadline: A.addDays(today, -2), status: 'Tamomladi', completion: 85, teacher_comment: 'Yaxshi, 2 ta masalada xato', created_by: 'u7', created_at: ts(A.addDays(today, -8)) });
    S.tasks.push({ id: 'tk3', branch: B, teacher: 'u8', course: 'c2', group: 'g3', contract: S.contracts.find((c) => c.group === 'g3').id, task: 'Django: blog ilovasi (CRUD)', deadline: A.addDays(today, 5), status: 'Rejada', completion: null, teacher_comment: '', created_by: 'u8', created_at: ts(A.addDays(today, -1)) });
    S.evaluations.push({ id: 'ev1', branch: B, date: '2026-09-29', contract: g1c[2].id, group: 'g1', teacher: 'u7', scores: [9, 10, 9, 8, 9], comment: 'Darslar juda qiziq', created_by: 'u4', created_at: ts('2026-09-29') });
    S.evaluations.push({ id: 'ev2', branch: B, date: '2026-09-29', contract: S.contracts.find((c) => c.group === 'g3').id, group: 'g3', teacher: 'u8', scores: [7, 6, 8, 9, 7], comment: "Ba'zan tez tushuntiradi", created_by: 'u4', created_at: ts('2026-09-29') });
    S.gradings.push({
      id: 'gr1', branch: B, teacher: 'u7', course: 'c1', group: 'g1', date: '2026-09-30', comment: 'Sentabr yakuni',
      rows: g1c.filter((c) => !c.end).map((c) => ({ contract: c.id, att: 14 + Math.floor(R() * 7), task: 25 + Math.floor(R() * 16), final: 300 + Math.floor(R() * 200) })),
      created_by: 'u7', created_at: ts('2026-09-30', 18),
    });
    S.parentCalls.push({ id: 'pc1', branch: B, course: 'c1', group: 'g1', contract: g1c[4].id, date: A.addDays(today, -2), comment: "Darsga 2 marta kelmadi, ota-onasi bilan gaplashildi", created_by: 'u4', created_at: ts(A.addDays(today, -2)) });
    // Har bir guruhdan 1–3 ta qo'ng'iroq: "Ota-onalar bilan aloqa" daraxtida kurs → guruh bo'yicha ko'rinsin
    const PC_TEXT = ["Qarzini eslatdik, hafta oxirigacha to'laydi", "O'zlashtirishi yaxshi, maqtadik", "Uy vazifasini bajarmayapti, nazorat qilishni so'radik", 'Kech qolib kelyapti, sababini aytdi', "Telefon ko'tarmadi, SMS yuborildi", 'Kurs tugagach davom ettirmoqchi'];
    let pcid = 1;
    for (const g of S.groups) {
      const cs = S.contracts.filter((c) => c.group === g.id && !c.end);
      const n = Math.min(cs.length, 1 + Math.floor(R() * 3));
      for (let i = 0; i < n; i++) {
        const d = A.addDays(today, -Math.floor(R() * 30) - 1);
        S.parentCalls.push({ id: 'pc' + ++pcid, branch: B, course: g.course, group: g.id, contract: cs[i].id, date: d, comment: pick(PC_TEXT), created_by: pick(['u3', 'u4', 'u5']), created_at: ts(d) });
      }
    }
    S.discount50.push({ id: 'dc1', branch: B, date: '2026-09-05', group: 'g3', contract: S.contracts.filter((c) => c.group === 'g3')[2].id, month: 9, year: 2026, discount_type: 'd1', created_by: 'u3', created_at: ts('2026-09-05') });

    S.audit.push({ id: 'au0', at: ts('2026-09-01', 7), user: 'u1', action: 'import', model: 'Tizim', obj: '', detail: "AppSheet'dan import: Emirat filiali, boshlang'ich qoldiqlar (o'tish sanasi 01.09.2026)" });
    return S;
  };
})(window.App);

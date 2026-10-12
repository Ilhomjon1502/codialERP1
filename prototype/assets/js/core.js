/* Ma'lumotlar ombori, ruxsatlar va biznes servislari (Django'dagi services/ qatlamining JS nusxasi) */
(function (A) {
  const STORE_KEY = 'codial_prototype_v3';
  const TODAY_KEY = 'codial_demo_today';

  /* ================= Rollar va ruxsatlar ================= */
  A.ROLES = {
    ADMIN: 'Admin',
    BOSH_MENEJER: 'Bosh menejer',
    FILIAL_MENEJERI: 'Filial menejeri',
    ADMINISTRATOR: 'Administrator',
    ADMINISTRATOR_HISOBCHI: 'Administrator+Hisobchi',
    HISOBCHI: 'Hisobchi',
    USTOZ: 'Ustoz',
    YORDAMCHI: 'Yordamchi ustoz',
    USTOZ_YORDAMCHI: 'Ustoz+Yordamchi',
    BOSHQA: 'Boshqa',
  };
  const SHORT = { AD: 'ADMIN', BM: 'BOSH_MENEJER', FM: 'FILIAL_MENEJERI', A: 'ADMINISTRATOR', AH: 'ADMINISTRATOR_HISOBCHI', H: 'HISOBCHI', U: 'USTOZ', Y: 'YORDAMCHI', UY: 'USTOZ_YORDAMCHI' };

  A.SECTIONS = [
    ['dashboard', 'Bosh sahifa'], ['leads', 'Lidlar'], ['contracts', 'Shartnomalar'], ['payments', "To'lovlar"],
    ['debtors', 'Qarzdorlar'], ['attendance', 'Davomatlar'], ['grading', "Baholash bo'limi"], ['profit', 'Foyda'],
    ['expenses', 'Xarajatlar'], ['export', 'Shartnoma yuklash'], ['groupAnalysis', 'Guruhlar tahlili'], ['groups', 'Guruhlar'],
    ['discount50', '50% chegirmalar'], ['approvals', 'Tasdiqlashlar'], ['salaries', 'Oyliklar'], ['transfers', 'Ichki pul oqimi'],
    ['creditors', 'Tashqi pul oqimi'], ['exchange', 'Pul ayirboshlash'], ['accounts', "G'aznalar"], ['evaluations', 'Baholash'],
    ['tasks', 'Talaba vazifalari'], ['parentCalls', 'Ota-onalar bilan aloqa'], ['settings', 'Sozlamalar'], ['ai', 'AI yordamchi'], ['audit', 'Audit tarixi'],
  ];

  const MATRIX = {
    dashboard: { AD: 'v', BM: 'v', FM: 'v', A: 'v', AH: 'v', H: 'v', U: 'v', Y: 'v', UY: 'v' },
    leads: { AD: 'vaed', BM: 'vaed', FM: 'vaed', A: 'vaed', AH: 'vaed', H: 'v', U: 'v', Y: 'v', UY: 'v' },
    contracts: { AD: 'vaed', BM: 'vaed', FM: 'vaed', A: 'vaed', AH: 'vaed', H: 'v', U: 'v', UY: 'v' },
    payments: { AD: 'vaedp', BM: 'vaedp', FM: 'vp', AH: 'vaed', H: 'vaed' },
    debtors: { AD: 'v', BM: 'v', FM: 'v', AH: 'v', H: 'v' },
    attendance: { AD: 'vaedp', BM: 'vaedp', FM: 'vaedp', A: 'vaedp', AH: 'vaedp', U: 'vae', UY: 'vae', Y: 'v' },
    grading: { AD: 'vaed', BM: 'vaed', FM: 'vaed', A: 'v', AH: 'v', H: 'v', U: 'vae', UY: 'vae' },
    profit: { AD: 'v', BM: 'v' },
    expenses: { AD: 'vaed', BM: 'vaed', FM: 'v', AH: 'vaed', H: 'vaed' },
    export: { AD: 'v', BM: 'v', FM: 'v', A: 'v', AH: 'v', H: 'v' },
    groupAnalysis: { AD: 'v', BM: 'v', FM: 'v', A: 'v', AH: 'v', H: 'v', U: 'v' },
    groups: { AD: 'vaed', BM: 'vaed', FM: 'vaed', A: 'vae', AH: 'vae', H: 'v', U: 'v', Y: 'v', UY: 'v' },
    discount50: { AD: 'vaed', BM: 'vaed', FM: 'vae', A: 'vae', AH: 'vae' },
    approvals: { AD: 'v', BM: 'v', FM: 'v', A: 'v', AH: 'v', H: 'v', U: 'v', UY: 'v' },
    salaries: { AD: 'vaed', BM: 'vaed', FM: 'vaed', AH: 'va', H: 'va', A: 'v', U: 'v', Y: 'v', UY: 'v' },
    transfers: { AD: 'vaed', BM: 'vaed', FM: 'v', AH: 'vaed', H: 'vaed' },
    creditors: { AD: 'vaed', BM: 'vaed' },
    exchange: { AD: 'vae', BM: 'vae' },
    accounts: { AD: 'vaed', BM: 'vaed', FM: 'v', AH: 'v', H: 'v' },
    evaluations: { AD: 'vaed', BM: 'vaed', FM: 'vaed', A: 'vae', AH: 'vae' },
    tasks: { AD: 'vaed', BM: 'vaed', FM: 'v', A: 'v', AH: 'v', U: 'vaed', UY: 'vaed', Y: 'v' },
    parentCalls: { AD: 'vaed', BM: 'vaed', FM: 'vae', A: 'vae', AH: 'vae', H: 'v', U: 'vae', UY: 'vae', Y: 'v' },
    settings: { AD: 'vaed', BM: 'vaed', FM: 'vae', A: 'v', AH: 'v', H: 'v' },
    ai: { BM: 'v' },
    audit: { AD: 'v', BM: 'v' },
  };

  A.defaultRoles = () =>
    Object.entries(A.ROLES).map(([code, name]) => {
      const perms = {};
      for (const [sec] of A.SECTIONS) {
        const row = MATRIX[sec] || {};
        const short = Object.keys(SHORT).find((k) => SHORT[k] === code);
        perms[sec] = (short && row[short]) || '';
      }
      return { code, name, perms };
    });

  /* ================= Ombor ================= */
  A.S = null;
  A.version = 0;

  A.today = () => {
    try {
      return localStorage.getItem(TODAY_KEY) || A.realToday();
    } catch (e) {
      return A.realToday();
    }
  };
  A.setDemoToday = (iso) => {
    try {
      if (iso) localStorage.setItem(TODAY_KEY, iso);
      else localStorage.removeItem(TODAY_KEY);
    } catch (e) { /* storage yo'q */ }
  };

  A.load = () => {
    let s = null;
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) s = JSON.parse(raw);
    } catch (e) { s = null; }
    if (!s || s.version !== 5) s = A.buildSeed(A.today());
    A.S = s;
    A.recalcAll();
    A.save();
  };
  A.save = () => {
    A.version++;
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(A.S));
    } catch (e) { /* xotira to'lgan yoki taqiqlangan */ }
  };
  A.reset = () => {
    const user = A.S && A.S.currentUser;
    A.S = A.buildSeed(A.today());
    A.S.currentUser = user;
    A.recalcAll();
    A.save();
  };

  const memo = new Map();
  A.memo = (key, fn) => {
    const m = memo.get(key);
    if (m && m.v === A.version) return m.val;
    const val = fn();
    memo.set(key, { v: A.version, val });
    return val;
  };

  /* ================= Joriy foydalanuvchi va ruxsat ================= */
  A.me = () => A.S.users.find((u) => u.id === A.S.currentUser) || null;
  A.role = () => (A.me() || {}).role;
  A.roleRec = (code) => A.S.roles.find((r) => r.code === code);
  A.can = (section, op = 'v') => {
    const r = A.roleRec(A.role());
    return !!(r && (r.perms[section] || '').includes(op));
  };
  A.isTop = () => ['ADMIN', 'BOSH_MENEJER'].includes(A.role());
  A.isTeacherRole = () => ['USTOZ', 'YORDAMCHI', 'USTOZ_YORDAMCHI'].includes(A.role());
  A.isManager = () => ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI'].includes(A.role());

  A.editDays = (role, section) => {
    if (role === 'ADMIN' || role === 'BOSH_MENEJER') return Infinity;
    if (role === 'FILIAL_MENEJERI') return 15;
    if (role === 'ADMINISTRATOR' || role === 'ADMINISTRATOR_HISOBCHI') {
      return ['payments', 'expenses', 'transfers', 'salaries'].includes(section) ? 0 : 7;
    }
    if (role === 'HISOBCHI') return 0;
    if (['USTOZ', 'YORDAMCHI', 'USTOZ_YORDAMCHI'].includes(role)) return 0;
    return -1;
  };
  A.editRule = (role, section) => {
    const d = A.editDays(role, section);
    return d === Infinity ? 'cheklovsiz' : d === 0 ? 'faqat bugun' : d < 0 ? "yo'q" : `oxirgi ${d} kun`;
  };
  /** Yozuvni tahrirlash mumkinmi: {ok, why} */
  A.canEdit = (section, rec, dateField = 'date', op = 'e') => {
    if (!A.can(section, op)) return { ok: false, why: "Sizning rolingizda bu amalga ruxsat yo'q" };
    if (rec.locked && !A.isTop()) return { ok: false, why: "Tasdiqlangan yozuvni faqat Admin va Bosh menejer o'zgartiradi" };
    const days = A.editDays(A.role(), section);
    if (days === Infinity) return { ok: true };
    let d = rec[dateField] || rec.created_at || A.today();
    if (typeof d === 'number') d = A.iso(new Date(d));
    const diff = A.diffDays(d, A.today());
    if (diff > days) return { ok: false, why: `Tahrirlash muddati o'tgan (${A.editRule(A.role(), section)})` };
    return { ok: true };
  };

  /* ================= Ma'lumot doirasi ================= */
  A.branchIds = () => (A.isTop() ? A.S.branches.map((b) => b.id) : (A.me() || {}).branches || []);
  A.inScope = (rec) => A.branchIds().includes(rec.branch) || rec.created_by === A.S.currentUser;

  A.rows = (coll) => (A.S[coll] || []).filter((x) => !x.deleted);
  A.get = (coll, id) => (A.S[coll] || []).find((x) => x.id === id);

  A.myGroupIds = () =>
    A.memo('myGroups:' + A.S.currentUser, () => {
      const me = A.S.currentUser;
      const r = A.role();
      return A.rows('groups').filter((g) => {
        if (r === 'USTOZ') return g.teacher === me;
        if (r === 'YORDAMCHI') return g.supporter === me;
        if (r === 'USTOZ_YORDAMCHI') return g.teacher === me || g.supporter === me;
        return A.branchIds().includes(g.branch);
      }).map((g) => g.id);
    });

  A.vis = (coll) => {
    const rows = A.rows(coll);
    const me = A.S.currentUser;
    const r = A.role();
    if (['groups'].includes(coll)) {
      const ids = A.myGroupIds();
      return rows.filter((g) => ids.includes(g.id));
    }
    if (['contracts', 'tasks', 'gradings', 'parentCalls'].includes(coll) && A.isTeacherRole()) {
      const ids = A.myGroupIds();
      return rows.filter((x) => ids.includes(x.group) || x.created_by === me);
    }
    if (coll === 'attendance' && A.isTeacherRole()) {
      const ids = A.myGroupIds();
      return rows.filter((a) => ids.includes(a.group) || a.teacher === me || a.supporter === me);
    }
    if (['salaryAssign', 'salaryPayouts', 'kpiRates'].includes(coll)) {
      if (A.isTop()) return rows;
      if (r === 'FILIAL_MENEJERI' || (coll === 'salaryPayouts' && A.can('salaries', 'a'))) return rows.filter((x) => A.branchIds().includes(x.branch));
      return rows.filter((x) => x.user === me);
    }
    if (['transfers', 'exchanges', 'creditors', 'creditorTx', 'accounts'].includes(coll)) return rows;
    if (rows.length && rows[0].branch === undefined) return rows;
    return rows.filter(A.inScope);
  };

  /* ================= Audit va o'zgartirishlar ================= */
  A.log = (action, model, obj, detail) => {
    A.S.audit.push({ id: 'au' + A.uid(), at: Date.now(), user: A.S.currentUser, action, model, obj, detail: detail || '' });
  };
  A.insert = (coll, rec, model, label) => {
    rec.id = rec.id || coll.slice(0, 3) + A.uid();
    rec.created_by = rec.created_by || A.S.currentUser;
    rec.created_at = rec.created_at || Date.now();
    A.S[coll].push(rec);
    A.log('create', model, label || rec.id);
    A.save();
    return rec;
  };
  A.patch = (coll, id, changes, model, label) => {
    const rec = A.get(coll, id);
    const diff = [];
    for (const [k, v] of Object.entries(changes)) {
      if (JSON.stringify(rec[k]) !== JSON.stringify(v)) diff.push(`${k}: ${fmtVal(rec[k])} → ${fmtVal(v)}`);
    }
    Object.assign(rec, changes, { updated_by: A.S.currentUser, updated_at: Date.now() });
    if (diff.length) A.log('update', model, label || id, diff.join('; '));
    A.save();
    return rec;
  };
  A.softDelete = (coll, id, model, label) => {
    const rec = A.get(coll, id);
    rec.deleted = true;
    rec.deleted_by = A.S.currentUser;
    rec.deleted_at = Date.now();
    A.log('delete', model, label || id, "Soft delete (yozuv bazada qoladi)");
    A.save();
  };
  function fmtVal(v) {
    if (v === null || v === undefined || v === '') return '∅';
    if (Array.isArray(v)) return '[' + v.join(',') + ']';
    return String(v);
  }

  /* ================= Nomlar ================= */
  A.userName = (id) => (A.get('users', id) || {}).full_name || '—';
  A.courseName = (id) => (A.get('courses', id) || {}).name || '—';
  A.patternName = (id) => (A.get('dayPatterns', id) || {}).name || '—';
  A.timeName = (id) => {
    const t = A.get('lessonTimes', id);
    return t ? `${t.start} - ${t.end}` : '—';
  };
  A.roomName = (id) => (A.get('rooms', id) || {}).name || '—';
  A.accName = (id) => (A.get('accounts', id) || {}).name || '—';
  A.branchName = (id) => (A.get('branches', id) || {}).name || '—';
  A.sourceName = (id) => (A.get('leadSources', id) || {}).name || '—';
  A.groupName = (g) => {
    g = typeof g === 'string' ? A.get('groups', g) : g;
    return g ? `${A.courseName(g.course)} / #${g.number}` : '—';
  };
  A.studentName = (s) => {
    s = typeof s === 'string' ? A.get('students', s) : s;
    return s ? `${s.first_name} ${s.last_name} ${s.father_name}`.trim() : '—';
  };
  A.contractName = (c) => {
    c = typeof c === 'string' ? A.get('contracts', c) : c;
    return c ? `${A.studentName(c.student)} №${c.number}` : '—';
  };
  A.CASH = { CASH: 'Naqd', CARD: 'Karta', BANK: 'Bank', ALL: 'Hammasi' };
  A.LEAD_STATUSES = {
    1: "Qayta bog'lanishga", 2: 'Yangi guruhga kutyapti', 3: 'Sinov darsga yozildi', 4: 'Sinov darsga qatnashdi',
    5: "O'qishni boshladi", 6: "Ma'qul kelmadi", 7: "Ma'qul kelmadi (Sifatsiz)", 8: "Keyinroq o'qiydi",
  };
  A.ATT = { 1: 'Keldi', 0: 'Sababli', X: 'Besabab', '-': 'Nofaol' };
  A.STOP_REASONS = ['Kursni tamomladi', 'Moliyaviy qiyinchilik', 'Dars sifatidan qoniqmadi', 'Markaz sharoiti yoqmadi', "Chetlashtirildi - o'zlashtirish past", 'Chetlashtirildi - xulqi yomon', "Kurs yoqmadi - Boshqa kursga o'tyapti"];
  A.CONTACT = ["Bog'lanishga", 'Gaplashildi', "Tushib bo'lmadi", "Noto'g'ri raqam"];

  /* ================= Hisob-kitob servislari ================= */
  A.priceFor = (branch, course, ym) => {
    const list = A.rows('coursePrices').filter((p) => p.branch === branch && p.course === course && p.effective_from <= ym);
    const p = A.sortBy(list, (x) => x.effective_from, true)[0];
    return p ? p.price : null;
  };
  A.freqRec = (branch, pattern, course, ym) => {
    const y = Number(ym.slice(0, 4)), m = Number(ym.slice(5, 7));
    return A.rows('lessonFreqs').find((f) => f.branch === branch && f.pattern === pattern && f.year === y && f.month === m && f.courses.includes(course));
  };
  /** 5.1 — faqat tasdiqlangan yozuv olinadi */
  A.freqFor = (branch, pattern, course, ym) => {
    const f = A.freqRec(branch, pattern, course, ym);
    return f && f.status === 'Tasdiqlangan' ? f.frequency : null;
  };
  A.rateFor = (branch, user, roleType, course, ym) => {
    const list = A.rows('kpiRates').filter((k) => k.branch === branch && k.user === user && k.role_type === roleType && k.course === course && k.effective_from <= ym);
    return A.sortBy(list, (x) => x.effective_from, true)[0] || null;
  };
  /** 5.2 va 5.3 — bitta davomat qatori uchun qarz va KPI */
  A.calcAtt = (a) => {
    const c = A.get('contracts', a.contract);
    const ym = A.ym(a.date);
    const price = A.priceFor(a.branch, a.course, ym);
    const freq = A.freqFor(a.branch, a.pattern, a.course, ym);
    const grant = c && c.type === 'Grant';
    a.no_freq = !freq;
    a.debt = a.status === '-' || grant || !price || !freq ? 0 : Math.round(price / freq);
    const kpi = (user, rt) => {
      if (!user || grant || a.status === 'X' || a.status === '-' || !freq || !price) return 0;
      const r = A.rateFor(a.branch, user, rt, a.course, ym);
      if (!r) return 0;
      return r.type === 'Foiz' ? Math.round(((r.percent / 100) * price) / freq) : Math.round(r.fixed / freq);
    };
    a.tkpi = kpi(a.teacher, 'USTOZ');
    a.skpi = kpi(a.supporter, 'YORDAMCHI');
  };
  A.recalcAll = () => A.S.attendance.forEach(A.calcAtt);
  /** 5.5 — qayta hisoblash */
  A.recalc = (pred) => {
    let n = 0;
    for (const a of A.S.attendance) if (!a.deleted && pred(a)) { A.calcAtt(a); n++; }
    return n;
  };

  A.contractStatus = (c, on) => {
    const t = on || A.today();
    if (c.end && c.end < t) return 'Nofaol';
    if (c.start > t) return 'Rejada';
    return 'Faol';
  };
  A.groupStatus = (g) => {
    const t = A.today();
    if (g.start > t) return 'Rejada';
    if (!g.end || g.end >= t) return 'Faol';
    return 'Nofaol';
  };

  A.debts = () =>
    A.memo('debts', () => {
      const m = new Map();
      for (const c of A.rows('contracts')) m.set(c.id, { opening: c.opening || 0, charged: 0, paid: 0, discount: 0 });
      for (const a of A.rows('attendance')) { const x = m.get(a.contract); if (x) x.charged += a.debt || 0; }
      for (const p of A.rows('payments')) { const x = m.get(p.contract); if (x) { x.paid += p.amount || 0; x.discount += p.discount || 0; } }
      for (const x of m.values()) x.balance = x.opening + x.charged - x.paid - x.discount;
      return m;
    });
  A.debtOf = (cid) => (A.debts().get(cid) || { balance: 0 }).balance;

  A.activeContractsOf = (gid, on) => A.rows('contracts').filter((c) => c.group === gid && A.contractStatus(c, on) === 'Faol');
  A.groupFill = (g) => {
    const n = A.activeContractsOf(g.id).length;
    const cap = (A.get('rooms', g.room) || {}).capacity || 0;
    const pct = cap ? n / cap : 0;
    let label = "Bo'sh", cls = 'red';
    if (n === 0) { label = "Bo'sh"; cls = 'red'; }
    else if (pct <= 0.5) { label = 'Yomon'; cls = 'red'; }
    else if (pct <= 0.75) { label = "O'rtacha"; cls = 'orange'; }
    else if (pct <= 0.85) { label = 'Yaxshi'; cls = 'blue'; }
    else { label = "Zo'r"; cls = 'green'; }
    return { n, cap, pct, free: cap - n, label, cls };
  };
  A.hasLesson = (g, date) => {
    const p = A.get('dayPatterns', g.pattern);
    return !!p && p.weekdays.includes(A.isoWeekday(date)) && g.start <= date && (!g.end || g.end >= date);
  };
  A.attendanceTaken = (gid, date) => A.rows('attendance').some((a) => a.group === gid && a.date === date);

  /* ---- G'azna: yagona pul harakatlari jurnali (CashMovement ledger) ---- */
  A.ledger = () =>
    A.memo('ledger', () => {
      const L = [];
      for (const p of A.rows('payments')) {
        if (!p.amount) continue;
        L.push({ account: p.cashbox, type: p.cash_type, amount: p.amount, date: p.date, src: "To'lov", ref: A.contractName(p.contract), confirmed: p.cash_type === 'CASH' || p.nc_status === 'Tasdiqlandi', id: p.id });
      }
      for (const e of A.rows('expenses')) L.push({ account: e.account, type: e.cash_type, amount: -(e.quantity * e.price), date: e.date, src: 'Xarajat', ref: e.name, confirmed: true, id: e.id });
      for (const s of A.rows('salaryPayouts')) L.push({ account: s.account, type: s.cash_type, amount: -s.amount, date: s.date, src: 'Oylik berish', ref: A.userName(s.user), confirmed: true, id: s.id });
      for (const t of A.rows('transfers')) {
        const ok = t.status === 'Tasdiqlandi';
        L.push({ account: t.sender, type: t.cash_type, amount: -t.amount, date: t.date, src: "O'tkazma (chiquvchi)", ref: '→ ' + A.accName(t.receiver), confirmed: ok, id: t.id });
        L.push({ account: t.receiver, type: t.cash_type, amount: t.amount, date: t.date, src: "O'tkazma (kiruvchi)", ref: '← ' + A.accName(t.sender), confirmed: ok, id: t.id });
      }
      for (const x of A.rows('exchanges')) {
        L.push({ account: x.account, type: x.from_type, amount: -x.amount, date: x.date, src: 'Ayirboshlash', ref: `${A.CASH[x.from_type]} → ${A.CASH[x.to_type]}`, confirmed: true, id: x.id });
        L.push({ account: x.account, type: x.to_type, amount: x.amount_to, date: x.date, src: 'Ayirboshlash', ref: `${A.CASH[x.from_type]} → ${A.CASH[x.to_type]}`, confirmed: true, id: x.id });
      }
      for (const t of A.rows('creditorTx')) L.push({ account: t.account, type: t.cash_type, amount: -t.amount, date: t.date, src: 'Kreditor', ref: (A.get('creditors', t.creditor) || {}).name, confirmed: true, id: t.id });
      return A.sortBy(L, (x) => x.date, true);
    });
  A.baseType = (acc) => (acc.cash_type === 'ALL' ? 'CASH' : acc.cash_type);
  /** g'azna balansi = initial + Σ tasdiqlangan harakatlar */
  A.balance = (accId, type) => {
    const acc = A.get('accounts', accId);
    if (!acc) return 0;
    let b = !type || type === A.baseType(acc) ? acc.initial : 0;
    for (const m of A.ledger()) if (m.account === accId && m.confirmed && (!type || m.type === type)) b += m.amount;
    return b;
  };
  A.pendingOf = (accId) => A.sum(A.ledger().filter((m) => m.account === accId && !m.confirmed), 'amount');
  A.myAccounts = () => A.rows('accounts').filter((a) => a.status === 'Faol' && (A.role() === 'ADMIN' || a.responsible.includes(A.S.currentUser)));

  /* ---- Oylik ---- */
  A.kpiAgg = () =>
    A.memo('kpiAgg', () => {
      const m = new Map();
      const add = (k, v) => m.set(k, (m.get(k) || 0) + v);
      for (const a of A.rows('attendance')) {
        const ym = A.ym(a.date);
        if (a.teacher) add(`T|${a.branch}|${a.teacher}|${ym}`, a.tkpi || 0);
        if (a.supporter) add(`S|${a.branch}|${a.supporter}|${ym}`, a.skpi || 0);
      }
      return m;
    });
  const ymOf = (y, m) => `${y}-${String(m).padStart(2, '0')}`;
  A.salaryBase = (sa) => {
    const ym = ymOf(sa.year, sa.month);
    const agg = A.kpiAgg();
    const tkpi = agg.get(`T|${sa.branch}|${sa.user}|${ym}`) || 0;
    const skpi = agg.get(`S|${sa.branch}|${sa.user}|${ym}`) || 0;
    const total = (sa.fixed || 0) + (sa.bonus || 0) + (sa.kpi || 0) + tkpi + skpi - (sa.fine || 0);
    const given = A.sum(A.rows('salaryPayouts').filter((p) => p.branch === sa.branch && p.user === sa.user && p.year === sa.year && p.month === sa.month), 'amount');
    return { tkpi, skpi, total, given };
  };
  /** carried — yillar oralig'ida ham (AppSheet'dagi xato tuzatilgan) */
  A.salaryCalc = (sa) => {
    const base = A.salaryBase(sa);
    const key = sa.year * 100 + sa.month;
    const prev = A.rows('salaryAssign').filter((x) => x.user === sa.user && x.branch === sa.branch && x.year * 100 + x.month < key);
    const carried = A.sum(prev, (x) => { const b = A.salaryBase(x); return b.total - b.given; });
    return { ...base, carried, final: base.total + carried - base.given };
  };

  /* ---- Lid ---- */
  A.hasContract = (studentId) => A.rows('contracts').some((c) => c.student === studentId);

  /* ---- Tasdiqlashlar ---- */
  const ageDays = (rec) => A.diffDays(A.iso(new Date(rec.created_at)), A.today());
  A.canApproveDiscount = (p) => A.role() === 'ADMIN' || (A.role() === 'BOSH_MENEJER' && ageDays(p) <= 30);
  A.canApproveNoncash = (p) => {
    const r = A.role();
    if (r === 'ADMIN') return true;
    if (r === 'BOSH_MENEJER') return ageDays(p) <= 360;
    if (r === 'FILIAL_MENEJERI' && A.can('payments', 'p')) return ageDays(p) <= 7;
    return false;
  };
  A.canApproveTransfer = (t) => A.role() === 'ADMIN' || (A.get('accounts', t.receiver) || { responsible: [] }).responsible.includes(A.S.currentUser);
  A.canApproveMakeup = () => A.can('attendance', 'p');
  A.canApproveFreq = () => ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI'].includes(A.role());

  A.pending = () =>
    A.memo('pending:' + A.S.currentUser, () => {
      const pays = A.vis('payments');
      return {
        discounts: pays.filter((p) => p.disc_status === 'Tasdiqlashga'),
        noncash: pays.filter((p) => p.nc_status === 'Tasdiqlashga'),
        transfers: A.rows('transfers').filter((t) => t.status === 'Tasdiqlashga'),
        makeups: A.rows('makeups').filter((m) => m.status === 'Kutilmoqda' && (!A.isTeacherRole() || m.teacher === A.S.currentUser)),
        freqs: A.rows('lessonFreqs').filter((f) => f.status === 'Taklif' && A.branchIds().includes(f.branch)),
      };
    });
  A.pendingCount = () => {
    const p = A.pending();
    let n = 0;
    n += p.discounts.filter(A.canApproveDiscount).length;
    n += p.noncash.filter(A.canApproveNoncash).length;
    n += p.transfers.filter(A.canApproveTransfer).length;
    if (A.canApproveMakeup()) n += p.makeups.length;
    if (A.canApproveFreq()) n += p.freqs.length;
    return n;
  };
})(window.App);

/* Sozlamalar, Audit tarixi, AI yordamchi */
(function (A) {
  const esc = A.esc;

  /* ===================================================== Umumiy CRUD */
  const CRUD = {};
  const crudList = (key) => {
    const c = CRUD[key];
    const rows = c.rows ? c.rows() : A.rows(c.coll);
    const canA = A.can('settings', 'a'), canE = A.can('settings', 'e');
    return `<div class="row between"><h2>${esc(c.title)}</h2>${canA && !c.noAdd ? A.btn("Qo'shish", 'crud-add', { id: key, icon: 'plus' }) : ''}</div>
      ${c.note ? `<p class="muted small">${c.note}</p>` : ''}
      ${A.table([...c.cols, { h: '', f: (r) => (canE ? `<button class="btn sm ghost" data-act="crud-edit" data-id="${key}|${r.id}">✎</button>` : '') }], rows)}`;
  };
  const crudForm = (key, rec) => {
    const c = CRUD[key];
    A.form({
      title: (rec ? '' : 'Yangi: ') + c.title,
      values: rec ? { ...rec } : { ...(c.defaults || {}) },
      fields: c.fields,
      onSubmit(x) {
        const clean = {};
        for (const f of c.fields) if (!['note', 'computed'].includes(f.type)) clean[f.name] = f.type === 'money' || f.type === 'number' ? Number(x[f.name]) || 0 : x[f.name];
        const err = c.check && c.check(clean, rec);
        if (err) return err;
        if (c.save) c.save(clean, rec);
        else if (rec) A.patch(c.coll, rec.id, clean, c.title, clean.name || rec.id);
        else A.insert(c.coll, { ...(c.extra ? c.extra() : {}), ...clean }, c.title, clean.name);
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['crud-add'] = (el) => crudForm(el.dataset.id, null);
  A.act['crud-edit'] = (el) => {
    const [key, id] = el.dataset.id.split('|');
    const c = CRUD[key];
    crudForm(key, (c.rows ? c.rows() : A.rows(c.coll)).find((r) => r.id === id));
  };
  const B = () => A.branchIds()[0] || 'b1';
  const unique = (coll, field, msg) => (val, x) => (A.rows(coll).some((r) => String(r[field]).toLowerCase() === String(val).toLowerCase() && r.id !== x.id) ? msg : '');

  CRUD.courses = {
    coll: 'courses', title: 'Kurslar',
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Amaldagi narx', f: (r) => A.num(A.priceFor(B(), r.id, A.ym(A.today()))), cls: 'num' }, { h: 'Status', f: (r) => A.badge(r.status, r.status === 'Faol' ? 'green' : 'gray') }],
    fields: [{ name: 'name', label: 'Nomi', required: true, validate: unique('courses', 'name', "Avval kiritilgan nom") }, { name: 'status', label: 'Status', type: 'seg', options: ['Faol', 'Nofaol'], default: 'Faol' }],
    extra: () => ({ branches: [B()] }),
  };
  CRUD.discounts = {
    coll: 'discountTypes', title: 'Chegirma turlari',
    note: "Limit majburiy tekshiriladi: to'lovdagi chegirma «Eng ko'p miqdori»dan oshmaydi. Tizim turi oddiy tanlovda ko'rinmaydi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Eng ko'p miqdori", f: (r) => A.num(r.max), cls: 'num' }, { h: 'Belgilar', f: (r) => (r.is_system ? A.badge('tizim', 'gray') : '') + (r.is_d50 ? A.badge('50% chegirma', 'orange') : '') }],
    fields: [
      { name: 'name', label: 'Nomi', required: true, validate: unique('discountTypes', 'name', "Avval qo'shilgan nom!") },
      { name: 'max', label: "Eng ko'p miqdori", type: 'money', required: true },
      { name: 'is_system', label: 'Tizim turi (oddiy tanlovda ko\'rinmaydi)', type: 'checkbox' },
      { name: 'is_d50', label: '«50% chegirmalar» bo\'limi uchun tur', type: 'checkbox' },
    ],
  };
  CRUD.expcats = {
    coll: 'expenseCats', title: 'Xarajat kategoriyalari',
    note: "Turi foyda hisobini belgilaydi: faqat «Xarajat» turi foydadan ayiriladi. «Kim qila oladi» — shu kategoriyada xarajat kirita oladigan rollar.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Turi', f: (r) => A.badge(r.kind, r.kind === 'Xarajat' ? 'gray' : 'blue') }, { h: 'Kim qila oladi', f: (r) => r.allowed_roles.map((x) => A.ROLES[x]).join(', ') }],
    fields: [
      { name: 'name', label: 'Nomi', required: true },
      { name: 'kind', label: 'Turi', type: 'seg', options: ['Xarajat', 'Qayta investitsiya', 'Dividend', 'Tashqi qarz'], default: 'Xarajat' },
      { name: 'allowed_roles', label: 'Kim qila oladi?', type: 'chips', options: () => ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'].map((r) => [r, A.ROLES[r]]), default: [] },
    ],
  };
  CRUD.sources = { coll: 'leadSources', title: 'Lid manbalari', cols: [{ h: 'Nomi', f: (r) => esc(r.name) }, { h: 'Lidlar', f: (r) => A.rows('leads').filter((l) => l.source === r.id).length, cls: 'num' }], fields: [{ name: 'name', label: 'Nomi', required: true }] };
  CRUD.rooms = {
    coll: 'rooms', title: 'Xonalar',
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Sig'imi", f: (r) => r.capacity, cls: 'num' }, { h: 'Guruhlar', f: (r) => A.rows('groups').filter((g) => g.room === r.id && A.groupStatus(g) !== 'Nofaol').map((g) => esc(A.groupName(g))).join(', ') }, { h: 'Status', f: (r) => A.badge(r.status, r.status === 'Faol' ? 'green' : 'gray') }],
    fields: [{ name: 'name', label: 'Xona nomi', required: true }, { name: 'capacity', label: "Xona sig'imi", type: 'number', required: true, min: 1 }, { name: 'status', label: 'Status', type: 'seg', options: ['Faol', 'Nofaol'], default: 'Faol' }],
    extra: () => ({ branch: B() }),
  };
  CRUD.patterns = {
    coll: 'dayPatterns', title: 'Dars kunlari',
    note: "Hafta kunlari ISO raqamlarda saqlanadi (Dushanba = 1 … Yakshanba = 7). AppSheet'dagi WEEKDAY()−1 formati importda shunga o'giriladi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Kunlar (ISO)', f: (r) => r.weekdays.join(', ') }],
    fields: [{ name: 'weekdays', label: 'Hafta kunlari', type: 'chips', required: true, options: [1, 2, 3, 4, 5, 6, 7].map((d) => [String(d), A.WD_FULL[d]]) }],
    save(x, rec) {
      const wd = x.weekdays.map(Number).sort();
      const name = wd.map((d) => A.WD[d]).join(', ');
      if (rec) A.patch('dayPatterns', rec.id, { weekdays: wd, name }, 'Dars kunlari', name);
      else A.insert('dayPatterns', { weekdays: wd, name }, 'Dars kunlari', name);
    },
    check: (x, rec) => (A.rows('dayPatterns').some((p) => p.weekdays.join() === x.weekdays.map(Number).sort().join() && (!rec || p.id !== rec.id)) ? 'Avval kiritilgan, mavjudlarni tekshiring' : ''),
    rows: () => A.rows('dayPatterns').map((p) => ({ ...p, weekdays: p.weekdays.map(String) })),
  };
  CRUD.times = {
    coll: 'lessonTimes', title: 'Dars vaqtlari',
    cols: [{ h: 'Vaqt', f: (r) => `<b>${r.start} - ${r.end}</b>` }, { h: 'Guruhlar', f: (r) => A.rows('groups').filter((g) => g.time === r.id && A.groupStatus(g) !== 'Nofaol').length, cls: 'num' }],
    fields: [
      { name: 'start', label: 'Boshlanish vaqti', type: 'time', required: true, onChange: (x) => { if (x.start) { const [h, m] = x.start.split(':').map(Number); x.end = `${String((h + 2) % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`; } } },
      { name: 'end', label: 'Tugash vaqti', type: 'time', required: true, show: (x) => x.start, help: 'Standart: boshlanish + 2 soat' },
    ],
    check: (x, rec) => (A.rows('lessonTimes').some((t) => t.start === x.start && t.end === x.end && (!rec || t.id !== rec.id)) ? "Avval qo'shilgan vaqt!" : ''),
    extra: () => ({ branch: B() }),
  };
  CRUD.branches = {
    coll: 'branches', title: 'Filiallar',
    note: 'Faol filial bitta bo\'lsa, u hamma joyda avtomatik tanlanadi va filial maydoni ko\'rinmaydi.',
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Naqd g'azna (standart)", f: (r) => esc(A.accName(r.default_cashbox)) }, { h: "Naqdsiz g'azna", f: (r) => esc(A.accName(r.noncash_cashbox)) }, { h: 'Status', f: (r) => A.badge(r.status, r.status === 'Faol' ? 'green' : 'gray') }],
    fields: [
      { name: 'name', label: 'Nomi', required: true, validate: unique('branches', 'name', "Avval qo'shilgan") },
      { name: 'default_cashbox', label: "Standart g'azna", type: 'select', options: () => A.optList('accounts') },
      { name: 'noncash_cashbox', label: "Naqdsiz to'lovlar g'aznasi", type: 'select', options: () => A.optList('accounts'), help: "AppSheet'da «cb4963b4» deb qattiq yozilgan edi" },
      { name: 'status', label: 'Status', type: 'seg', options: ['Faol', 'Nofaol'], default: 'Faol' },
    ],
  };

  /* ---- Foydalanuvchilar ---- */
  const assignable = () => {
    const r = A.role();
    if (r === 'ADMIN') return Object.keys(A.ROLES);
    if (r === 'BOSH_MENEJER') return Object.keys(A.ROLES).filter((x) => x !== 'ADMIN');
    return ['ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI', 'USTOZ', 'YORDAMCHI', 'USTOZ_YORDAMCHI', 'BOSHQA'];
  };
  CRUD.users = {
    coll: 'users', title: 'Foydalanuvchilar',
    note: "Rol ro'yxati sizning rolingiz tayinlay oladigan rollar bilan cheklangan (RolePower). Ishdan ketgan xodim tizimga kira olmaydi, lekin tarixi saqlanadi.",
    cols: [
      { h: 'Ism', f: (u) => `<b>${esc(u.full_name)}</b><br><small class="muted">${esc(u.email || '—')}</small>` },
      { h: 'Lavozim', f: (u) => esc(A.ROLES[u.role]) },
      { h: 'Filial', f: (u) => (u.branches.length ? u.branches.map(A.branchName).join(', ') : '<span class="muted">hammasi</span>') },
      { h: "Bo'lim", f: (u) => (u.teams || []).join(', ') },
      { h: 'Telefon', f: (u) => esc(u.phone) },
      { h: 'Holat', f: (u) => A.badge(u.status === 'Faol' ? 'Faol' : 'Ishdan ketgan', u.status === 'Faol' ? 'green' : 'gray') },
    ],
    fields: [
      { name: 'full_name', label: "To'liq ism", required: true, validate: unique('users', 'full_name', 'Avval kiritilgan ism! Boshqa nom bering') },
      { name: 'role', label: 'Lavozim', type: 'select', required: true, show: (x) => x.full_name, options: () => assignable().map((r) => [r, A.ROLES[r]]) },
      { name: 'branches', label: 'Filial', type: 'chips', show: (x) => x.role && !['ADMIN', 'BOSH_MENEJER'].includes(x.role), options: () => A.optList('branches'), default: ['b1'] },
      { name: 'phone', label: 'Telefon', show: (x) => x.role, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
      { name: 'teams', label: "Bo'lim", type: 'chips', show: (x) => x.role, options: ['Qabul', 'Marketing', 'Moliya', 'HR', "Ta'lim", 'Boshqa', "Qurilish va ta'mirlash", 'IT', "Ta'minot"], default: [] },
      { name: 'email', label: 'Pochta (login)', type: 'email', show: (x) => x.role && x.role !== 'BOSHQA', required: (x) => x.role && x.role !== 'BOSHQA', validate: unique('users', 'email', 'Avval kiritilgan pochta!') },
      { name: 'status', label: 'Holat', type: 'seg', options: [['Faol', 'Faol'], ['Ketgan', 'Ishdan ketgan']], default: 'Faol', show: (x) => x.role },
      { name: 'inv', type: 'note', tone: 'info', show: (x) => x.email, text: 'Haqiqiy tizimda xodimga birinchi kirish uchun parol o\'rnatish havolasi yuboriladi.' },
    ],
  };

  /* ---- Davomat statuslari ---- */
  CRUD.attstatus = {
    title: 'Davomat statuslari', noAdd: true,
    note: 'Har bir statusni qaysi rollar qo\'ya olishi. Davomat olish ekranida faqat ruxsat berilgan tugmalar chiqadi.',
    rows: () => A.S.attendanceStatuses.map((s) => ({ ...s, id: s.code })),
    cols: [{ h: 'Kod', f: (s) => A.attBadge(s.code) }, { h: 'Nomi', f: (s) => `<b>${esc(s.name)}</b>` }, { h: 'Ruxsat berilgan lavozimlar', f: (s) => s.roles.map((r) => A.ROLES[r]).join(', ') }],
    fields: [{ name: 'roles', label: 'Ruxsat berilgan lavozimlar', type: 'chips', options: () => Object.entries(A.ROLES).filter(([k]) => k !== 'BOSHQA') }],
    save(x, rec) {
      const s = A.S.attendanceStatuses.find((y) => y.code === rec.code);
      s.roles = x.roles;
      A.log('update', 'Davomat statusi', s.name, x.roles.join(', '));
      A.save();
    },
  };

  /* ===================================================== Oydagi dars soni */
  A.freqTable = (rows) =>
    A.table(
      [
        { h: 'Oy', f: (f) => `${A.MONTHS[f.month - 1]} ${f.year}` },
        { h: 'Dars kunlari', f: (f) => `<b>${esc(A.patternName(f.pattern))}</b>` },
        { h: 'Kurslar', f: (f) => f.courses.map(A.courseName).map(esc).join(', ') },
        { h: 'Darslar soni', f: (f) => { const cal = A.lessonDaysInMonth(`${f.year}-${String(f.month).padStart(2, '0')}`, A.get('dayPatterns', f.pattern).weekdays).length; return `<b>${f.frequency}</b>${cal !== f.frequency ? ` <small class="muted">(kalendar: ${cal})</small>` : ''}`; }, cls: 'num' },
        { h: 'Status', f: (f) => A.badge(f.status, f.status === 'Tasdiqlangan' ? 'green' : 'orange') + (f.approved_by && f.approved_by !== 'system' ? `<br><small class="muted">${esc(A.userName(f.approved_by))}</small>` : '') },
        { h: '', f: (f) => `<div class="row gap nowrap">${A.can('settings', 'e') ? `<button class="btn sm ghost" data-act="freq-edit" data-id="${f.id}">✎</button>` : ''}${f.status === 'Taklif' && A.canApproveFreq() ? `<button class="btn sm primary" data-act="freq-ok" data-id="${f.id}">Tasdiqlash</button>` : ''}</div>` },
      ],
      rows,
      { empty: "Taklif yo'q" },
    );
  A.act['freq-ok'] = (el) => {
    const f = A.get('lessonFreqs', el.dataset.id);
    A.patch('lessonFreqs', f.id, { status: 'Tasdiqlangan', approved_by: A.S.currentUser }, 'Oydagi dars soni', `${A.patternName(f.pattern)} ${f.month}/${f.year}`);
    const ym = `${f.year}-${String(f.month).padStart(2, '0')}`;
    const n = A.recalc((a) => a.pattern === f.pattern && A.ym(a.date) === ym);
    A.save();
    A.toast(`Tasdiqlandi. ${n} ta davomat qatori qayta hisoblandi (qarz va KPI)`);
    A.refresh();
  };
  A.act['freq-edit'] = (el) => {
    const f = A.get('lessonFreqs', el.dataset.id);
    A.form({
      title: `${A.patternName(f.pattern)} · ${A.MONTHS[f.month - 1]} ${f.year}`,
      values: { ...f },
      fields: [
        { name: 'courses', label: 'Kurslar', type: 'chips', options: () => A.optList('courses'), required: true },
        { name: 'frequency', label: 'Oydagi dars soni', type: 'number', min: 4, max: 26, required: true, validate: (n) => (n < 4 || n > 26 ? "Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos" : ''), help: 'Bayram kunlari bo\'lsa kamaytiring' },
      ],
      onSubmit(x) {
        A.patch('lessonFreqs', f.id, { courses: x.courses, frequency: Number(x.frequency) }, 'Oydagi dars soni', A.patternName(f.pattern));
        const ym = `${f.year}-${String(f.month).padStart(2, '0')}`;
        const n = A.recalc((a) => a.pattern === f.pattern && A.ym(a.date) === ym);
        A.save();
        A.toast(`Saqlandi, ${n} ta qator qayta hisoblandi`);
        A.refresh();
      },
    });
  };
  A.act['freq-gen'] = (el) => {
    const ym = el.dataset.id;
    const [y, m] = ym.split('-').map(Number);
    const prev = A.addMonths(ym, -1);
    let n = 0;
    for (const p of A.rows('dayPatterns')) {
      if (A.rows('lessonFreqs').some((f) => f.pattern === p.id && f.year === y && f.month === m)) continue;
      const pf = A.rows('lessonFreqs').find((f) => f.pattern === p.id && `${f.year}-${String(f.month).padStart(2, '0')}` === prev);
      A.S.lessonFreqs.push({ id: 'f' + A.uid(), branch: B(), pattern: p.id, courses: pf ? [...pf.courses] : [], year: y, month: m, frequency: A.lessonDaysInMonth(ym, p.weekdays).length, status: 'Taklif', approved_by: '', created_by: 'system', created_at: Date.now() });
      n++;
    }
    A.log('create', 'Oydagi dars soni', `${A.ymLabel(ym)}: ${n} ta taklif (kalendar bo'yicha)`);
    A.save();
    A.toast(n ? `${n} ta taklif yaratildi (haqiqiy tizimda cron har oy 1-kuni qiladi)` : 'Bu oy uchun takliflar allaqachon bor');
    A.refresh();
  };

  /* ===================================================== Sozlamalar sahifasi */
  const TABS = [
    ['courses', 'Kurslar'], ['prices', 'Kurs narxlari'], ['freq', 'Oydagi dars soni'], ['rates', 'KPI stavkalari'],
    ['discounts', 'Chegirma turlari'], ['expcats', 'Xarajat kategoriyalari'], ['sources', 'Lid manbalari'], ['rooms', 'Xonalar'],
    ['patterns', 'Dars kunlari'], ['times', 'Dars vaqtlari'], ['branches', 'Filiallar'], ['accounts', "G'aznalar"],
    ['users', 'Foydalanuvchilar'], ['roles', 'Rollar va ruxsatlar'], ['attstatus', 'Davomat statuslari'],
  ];
  A.page('settings', {
    title: 'Sozlamalar',
    section: 'settings',
    render(p, q) {
      const tab = q.tab || 'courses';
      let body = '';
      if (CRUD[tab]) body = crudList(tab);
      else if (tab === 'prices') body = pricesView();
      else if (tab === 'freq') body = freqView();
      else if (tab === 'rates') body = `<h2>KPI stavkalari</h2><p>KPI stavkalari «Oyliklar» bo'limida boshqariladi.</p><a class="btn primary" href="#/salaries?tab=rates">KPI stavkalariga o'tish →</a>`;
      else if (tab === 'accounts') body = `<h2>G'aznalar</h2><p>G'aznalar va ularning mas'ullari «G'aznalar» bo'limida.</p><a class="btn primary" href="#/accounts">G'aznalarga o'tish →</a>`;
      else if (tab === 'roles') body = rolesView();
      return `${A.head('Sozlamalar', 'Barcha ma\'lumotnomalar. Bosh menejer hammasini, Filial menejeri o\'z filiali doirasida boshqaradi')}
        <div class="settings"><nav class="side-tabs">${TABS.map(([k, l]) => `<a href="#/settings?tab=${k}" class="${k === tab ? 'on' : ''}">${esc(l)}</a>`).join('')}</nav><div class="settings-body card">${body}</div></div>`;
    },
  });

  function pricesView() {
    const b = B();
    const cur = A.ym(A.today());
    return `<div class="row between"><h2>Kurs narxlari</h2>${A.can('settings', 'a') ? A.btn("Narxni o'zgartirish", 'price-new', { icon: 'plus' }) : ''}</div>
      <p class="muted small">Yangi mantiq: narx «amal qilish oyi» bilan saqlanadi. Narx faqat o'zgarganda yangi yozuv qo'shiladi — har oy qayta kiritish shart emas. Oy uchun shu oyda amalda bo'lgan oxirgi narx olinadi.</p>
      ${A.rows('courses')
        .map((c) => {
          const hist = A.sortBy(A.rows('coursePrices').filter((p) => p.course === c.id && p.branch === b), (p) => p.effective_from, true);
          const active = A.priceFor(b, c.id, cur);
          return `<div class="price-row"><div><b>${esc(c.name)}</b><div class="muted small">${hist.map((h) => `${A.ymLabel(h.effective_from)} dan: ${A.num(h.price)}`).join(' · ')}</div></div><div class="big-num sm">${A.money(active)}</div></div>`;
        })
        .join('')}`;
  }
  A.act['price-new'] = () =>
    A.form({
      title: "Kurs narxini o'zgartirish",
      values: { effective_from: A.ym(A.today()) },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, options: () => A.optList('courses', 'name', (c) => c.status === 'Faol') },
        { name: 'cur', type: 'note', tone: 'info', show: (x) => x.course, text: (x) => `Hozirgi narx: <b>${A.money(A.priceFor(B(), x.course, A.ym(A.today())))}</b>` },
        { name: 'effective_from', label: 'Qaysi oydan amal qiladi', type: 'month', required: true, show: (x) => x.course },
        { name: 'price', label: 'Yangi narx (oyiga)', type: 'money', required: true, show: (x) => x.course },
        { name: 'w', type: 'note', tone: 'warn', show: (x) => x.effective_from && x.effective_from <= A.ym(A.today()), text: "Joriy yoki o'tgan oy tanlandi — shu oydan boshlab davomat qatorlaridagi talaba qarzi va Foiz-KPI qayta hisoblanadi." },
      ],
      onSubmit(x) {
        const ex = A.rows('coursePrices').find((p) => p.course === x.course && p.branch === B() && p.effective_from === x.effective_from);
        if (ex) A.patch('coursePrices', ex.id, { price: x.price }, 'Kurs narxi', A.courseName(x.course));
        else A.insert('coursePrices', { branch: B(), course: x.course, effective_from: x.effective_from, price: x.price }, 'Kurs narxi', `${A.courseName(x.course)}: ${A.num(x.price)} (${x.effective_from})`);
        const n = A.recalc((a) => a.course === x.course && A.ym(a.date) >= x.effective_from);
        A.save();
        A.toast(`Saqlandi. ${n} ta davomat qatori qayta hisoblandi`);
        A.refresh();
      },
    });

  function freqView() {
    const ym = A.q('freq:month', A.ym(A.today()));
    const opts = [...A.monthOptions()];
    const next = A.addMonths(A.ym(A.today()), 1);
    opts.unshift([next, A.ymLabel(next) + ' (keyingi)']);
    const [y, m] = ym.split('-').map(Number);
    const rows = A.rows('lessonFreqs').filter((f) => f.year === y && f.month === m);
    return `<div class="row between wrap"><h2>Oydagi dars soni</h2><div class="row gap"><select class="f-input" data-filter="freq:month">${opts.map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select>
      ${A.can('settings', 'a') ? A.btn("Kalendar bo'yicha taklif yaratish", 'freq-gen', { id: ym, cls: 'ghost' }) : ''}</div></div>
      <p class="muted small">Har oy 1-kuni tizim har bir dars kunlari jadvali uchun kalendardan darslar sonini hisoblab «Taklif» yaratadi (o'tgan oydagi kurslar nusxalanadi). Menejer bayramlarni hisobga olib tuzatadi va tasdiqlaydi. <b>Tasdiqlanmagan oy uchun qarz va KPI hisoblanmaydi.</b></p>
      ${A.freqTable(rows)}`;
  }

  function rolesView() {
    const editable = A.role() === 'ADMIN' || A.role() === 'BOSH_MENEJER';
    const roles = A.S.roles.filter((r) => r.code !== 'BOSHQA');
    const OPS = [['v', "ko'rish"], ['a', "qo'shish"], ['e', 'tahrirlash'], ['d', "o'chirish"], ['p', 'tasdiqlash']];
    return `<h2>Rollar va ruxsatlar</h2>
      <p class="muted small">Har katakda: <b>v</b> ko'rish · <b>a</b> qo'shish · <b>e</b> tahrirlash · <b>d</b> o'chirish · <b>p</b> tasdiqlash. ${editable ? 'Harfni bosib yoqing/o\'chiring — menyu darhol o\'zgaradi.' : 'Faqat Admin va Bosh menejer o\'zgartiradi.'} Boshlang'ich qiymatlar AppSheet sozlamalaridan olingan.</p>
      <div class="tbl-wrap"><table class="tbl perm"><thead><tr><th>Bo'lim</th>${roles.map((r) => `<th>${esc(r.name)}</th>`).join('')}</tr></thead><tbody>
      ${A.SECTIONS.map(([sec, name]) => `<tr><td>${esc(name)}</td>${roles
        .map((r) => `<td class="pc">${OPS.map(([o, t]) => `<button class="pbit ${(r.perms[sec] || '').includes(o) ? 'on' : ''}" title="${t}" ${editable ? `data-act="perm" data-id="${r.code}|${sec}|${o}"` : 'disabled'}>${o}</button>`).join('')}</td>`)
        .join('')}</tr>`).join('')}
      </tbody></table></div>
      <h3>Tahrirlash va o'chirish muddatlari</h3>
      ${A.table(
        [{ h: 'Rol', f: (r) => esc(r.name) }, { h: 'Shartnoma, lid, davomat', f: (r) => A.editRule(r.code, 'contracts') }, { h: "To'lov, xarajat", f: (r) => A.editRule(r.code, 'payments') }],
        roles,
      )}
      <p class="muted small">Tasdiqlangan to'lov, chegirma va o'tkazmani faqat Admin va Bosh menejer o'zgartiradi. Muddat: bugun − yozuv sanasi ≤ N kun.</p>`;
  }
  A.act.perm = (el) => {
    const [code, sec, op] = el.dataset.id.split('|');
    const r = A.S.roles.find((x) => x.code === code);
    const cur = r.perms[sec] || '';
    r.perms[sec] = cur.includes(op) ? cur.replace(op, '') : cur + op;
    A.log('update', 'Rol ruxsati', `${r.name} · ${sec}`, `${cur || '∅'} → ${r.perms[sec] || '∅'}`);
    A.save();
    A.refresh();
  };

  /* ===================================================== Audit tarixi */
  const ACT = { create: ['Yaratildi', 'green'], update: ["O'zgartirildi", 'blue'], delete: ["O'chirildi", 'red'], login: ['Kirish', 'gray'], import: ['Import', 'gray'], export: ['Eksport', 'gray'], ai: ['AI so\'rov', 'orange'] };
  A.page('audit', {
    title: 'Audit tarixi',
    section: 'audit',
    render() {
      return `${A.head('Audit tarixi', "Har bir yaratish, o'zgartirish va o'chirish: kim, qachon, nima, eski → yangi qiymat")}
        ${A.filterBar('audit', [A.fSearch('audit'), A.fSelect('audit', 'user', A.S.users.map((u) => [u.id, u.full_name]), 'Barcha xodimlar'), A.fSelect('audit', 'action', Object.entries(ACT).map(([k, v]) => [k, v[0]]), 'Barcha amallar')])}
        <div data-results>${this.results()}</div>`;
    },
    results() {
      const s = A.q('audit:search', ''), u = A.q('audit:user', ''), a = A.q('audit:action', '');
      const rows = A.sortBy(A.S.audit, (x) => x.at, true).filter((x) => (!u || x.user === u) && (!a || x.action === a) && A.match(`${x.model} ${x.obj} ${x.detail}`, s)).slice(0, 300);
      return A.table(
        [
          { h: 'Vaqt', f: (x) => A.fdt(x.at) },
          { h: 'Xodim', f: (x) => esc(A.userName(x.user)) },
          { h: 'Amal', f: (x) => A.badge(...(ACT[x.action] || [x.action, 'gray'])) },
          { h: "Bo'lim", f: (x) => esc(x.model) },
          { h: 'Yozuv', f: (x) => esc(x.obj) },
          { h: "O'zgarish", f: (x) => `<small>${esc(x.detail)}</small>` },
        ],
        rows,
        { empty: "Yozuv yo'q. Biror narsa qo'shing yoki o'zgartiring — shu yerda paydo bo'ladi" },
      );
    },
  });

  /* ===================================================== AI yordamchi */
  A.ui.chat = A.ui.chat || [];
  const SUGG = ["Shu oyda qaysi kurs eng ko'p to'lov keltirdi?", "Manbalar bo'yicha lid konversiyasi qanday?", "Qaysi guruhda qarzdorlik eng ko'p?", "Ustozlar bo'yicha davomat foizi", 'Shu oy xarajatlari kategoriya bo\'yicha', "Ustozlar KPI'si shu oyda"];
  A.page('ai', {
    title: 'AI yordamchi',
    section: 'ai',
    render() {
      const used = A.ui.chat.filter((m) => m.role === 'user').length;
      return `${A.head('AI yordamchi', `Faqat Bosh menejer uchun · bugun ${used}/50 so'rov`)}
        <div class="alert info">${A.icon('sparkle')}<div><b>Prototip.</b> Bu yerda javoblar oldindan yozilgan namunaviy qoidalar bilan hisoblanadi. Haqiqiy tizimda: savol + view'lar sxemasi LLM'ga yuboriladi → LLM SQL yozadi → server faqat <code>SELECT</code>, faqat <code>analytics_*</code> view'lar, LIMIT va 5 soniya timeout'ni tekshiradi → natija jadval yoki diagramma bo'lib chiqadi. Talabalar ismlari va telefonlar LLM'ga yuborilmaydi.</div></div>
        <div class="chat" id="chat">${A.ui.chat.map(msgHTML).join('') || `<div class="muted pad">Savol bering yoki quyidagi namunalardan birini tanlang.</div>`}</div>
        <div class="chips sugg">${SUGG.map((s) => `<button class="chip" data-act="ai-ask" data-id="${esc(s)}">${esc(s)}</button>`).join('')}</div>
        <form class="chat-input" id="chat-form"><input class="f-input grow" id="chat-q" placeholder="Masalan: Oxirgi oyda Instagram'dan kelgan lidlar konversiyasi qancha?"><button class="btn primary">Yuborish</button></form>`;
    },
    mount() {
      document.getElementById('chat-form').onsubmit = (e) => {
        e.preventDefault();
        const q = document.getElementById('chat-q').value.trim();
        if (q) ask(q);
      };
      const c = document.getElementById('chat');
      c.scrollTop = c.scrollHeight;
    },
  });
  function msgHTML(m) {
    if (m.role === 'user') return `<div class="msg user">${esc(m.text)}</div>`;
    return `<div class="msg bot">${m.html}</div>`;
  }
  A.act['ai-ask'] = (el) => ask(el.dataset.id);
  function ask(q) {
    A.ui.chat.push({ role: 'user', text: q });
    A.ui.chat.push({ role: 'bot', html: answer(q) });
    A.log('ai', 'AI yordamchi', q);
    A.save();
    A.refresh();
  }
  function answer(q) {
    const s = q.toLowerCase();
    const ym = A.ym(A.today());
    const sql = (t) => `<details><summary class="small muted">Yaratilgan SQL (tekshirildi: faqat SELECT, analytics_* view, LIMIT 100)</summary><pre class="sql">${esc(t)}</pre></details>`;
    if (/kurs/.test(s) && /(to'lov|foyda|tushum|keltir)/.test(s)) {
      const rows = A.rows('courses').map((c) => ({ c, sum: A.sum(A.rows('payments').filter((p) => A.ym(p.date) === ym && (A.get('contracts', p.contract) || {}).course === c.id), 'amount') }));
      const top = A.sortBy(rows, (r) => r.sum, true);
      return `<p><b>${esc(top[0].c.name)}</b> ${A.ymLabel(ym)}da eng ko'p to'lov keltirdi: ${A.money(top[0].sum)}.</p>
        ${A.table([{ h: 'Kurs', f: (r) => esc(r.c.name) }, { h: "To'lovlar", f: (r) => A.num(r.sum), cls: 'num' }], top)}
        ${A.chart({ type: 'bar', data: { labels: top.map((r) => r.c.name), datasets: [{ label: "To'lovlar", data: top.map((r) => r.sum), backgroundColor: A.PALETTE[0] }] }, options: { plugins: { legend: { display: false } } } }, 200)}
        ${sql(`SELECT course_name, SUM(amount) AS total\nFROM analytics_payments\nWHERE month = '${ym}'\nGROUP BY course_name\nORDER BY total DESC\nLIMIT 100;`)}`;
    }
    if (/(manba|konversiya|instagram|telegram)/.test(s)) {
      const rows = A.rows('leadSources').map((src) => { const l = A.rows('leads').filter((x) => x.source === src.id); const c = l.filter((x) => A.hasContract(x.student)).length; return { n: src.name, l: l.length, c, r: l.length ? c / l.length : 0 }; });
      const best = A.sortBy(rows, (r) => r.r, true)[0];
      return `<p>Eng yuqori konversiya — <b>${esc(best.n)}</b>: ${A.pct(best.r)} (${best.c}/${best.l}).</p>${A.table([{ h: 'Manba', f: (r) => esc(r.n) }, { h: 'Lidlar', f: (r) => r.l, cls: 'num' }, { h: 'Shartnoma', f: (r) => r.c, cls: 'num' }, { h: 'Konversiya', f: (r) => A.pct(r.r), cls: 'num' }], A.sortBy(rows, (r) => r.l, true))}
        ${sql("SELECT source, COUNT(*) AS leads,\n  COUNT(*) FILTER (WHERE has_contract) AS converted,\n  ROUND(100.0 * COUNT(*) FILTER (WHERE has_contract) / COUNT(*), 1) AS rate\nFROM analytics_leads\nGROUP BY source\nORDER BY leads DESC\nLIMIT 100;")}`;
    }
    if (/qarz/.test(s)) {
      const rows = [...A.groupBy(A.rows('contracts').filter((c) => A.debtOf(c.id) > 0), (c) => c.group)].map(([g, l]) => ({ g, n: l.length, sum: A.sum(l, (c) => A.debtOf(c.id)) }));
      const top = A.sortBy(rows, (r) => r.sum, true);
      return `<p>Eng katta qarzdorlik — <b>${esc(A.groupName(top[0].g))}</b>: ${A.money(top[0].sum)} (${top[0].n} talaba).</p>${A.table([{ h: 'Guruh', f: (r) => esc(A.groupName(r.g)) }, { h: 'Qarzdorlar', f: (r) => r.n, cls: 'num' }, { h: 'Qarz', f: (r) => A.num(r.sum), cls: 'num' }], top)}
        ${sql('SELECT group_name, COUNT(*) AS debtors, SUM(debt) AS total_debt\nFROM analytics_contracts\nWHERE debt > 0\nGROUP BY group_name\nORDER BY total_debt DESC\nLIMIT 100;')}`;
    }
    if (/davomat/.test(s)) {
      const att = A.rows('attendance').filter((a) => A.ym(a.date) === ym && a.status !== '-');
      const rows = [...A.groupBy(att, (a) => a.teacher)].map(([t, l]) => ({ t, r: l.filter((a) => a.status === '1').length / l.length, n: l.length }));
      return `<p>${A.ymLabel(ym)} bo'yicha ustozlar davomat foizi:</p>${A.table([{ h: 'Ustoz', f: (r) => esc(A.userName(r.t)) }, { h: 'Qatorlar', f: (r) => r.n, cls: 'num' }, { h: 'Davomat', f: (r) => A.pct(r.r), cls: 'num' }], A.sortBy(rows, (r) => r.r, true))}
        ${sql(`SELECT teacher_name,\n  ROUND(100.0 * AVG(CASE WHEN status = '1' THEN 1 ELSE 0 END), 1) AS attendance_pct\nFROM analytics_attendance\nWHERE month = '${ym}' AND status <> '-'\nGROUP BY teacher_name\nORDER BY attendance_pct DESC\nLIMIT 100;`)}`;
    }
    if (/xarajat/.test(s)) {
      const [y, m] = ym.split('-').map(Number);
      const rows = [...A.groupBy(A.rows('expenses').filter((e) => e.period_year === y && e.period_month === m), (e) => e.category)].map(([c, l]) => ({ c, sum: A.sum(l, (e) => e.quantity * e.price) }));
      const top = A.sortBy(rows, (r) => r.sum, true);
      return `<p>${A.ymLabel(ym)} xarajatlari: jami ${A.money(A.sum(top, 'sum'))}.</p>${A.chart({ type: 'doughnut', data: { labels: top.map((r) => A.get('expenseCats', r.c).name), datasets: [{ data: top.map((r) => r.sum), backgroundColor: A.PALETTE }] } }, 220)}
        ${sql(`SELECT category, kind, SUM(total) AS total\nFROM analytics_expenses\nWHERE period = '${ym}'\nGROUP BY category, kind\nORDER BY total DESC\nLIMIT 100;`)}`;
    }
    if (/(kpi|oylik)/.test(s)) {
      const agg = A.kpiAgg();
      const rows = A.S.users.filter((u) => ['USTOZ', 'USTOZ_YORDAMCHI', 'YORDAMCHI'].includes(u.role)).map((u) => ({ u, t: agg.get(`T|b1|${u.id}|${ym}`) || 0, sp: agg.get(`S|b1|${u.id}|${ym}`) || 0 }));
      return `<p>${A.ymLabel(ym)} uchun hisoblangan KPI (bugungi holat):</p>${A.table([{ h: 'Xodim', f: (r) => esc(r.u.full_name) }, { h: 'Ustoz KPI', f: (r) => A.num(r.t), cls: 'num' }, { h: 'Yordamchi KPI', f: (r) => A.num(r.sp), cls: 'num' }, { h: 'Jami', f: (r) => `<b>${A.num(r.t + r.sp)}</b>`, cls: 'num' }], A.sortBy(rows, (r) => r.t + r.sp, true))}
        ${sql(`SELECT user_name, SUM(teacher_kpi) AS teacher_kpi, SUM(supporter_kpi) AS supporter_kpi\nFROM analytics_kpi\nWHERE month = '${ym}'\nGROUP BY user_name\nLIMIT 100;`)}`;
    }
    return `<p>Kechirasiz, prototipda faqat namunaviy savollar ishlaydi: kurslar bo'yicha to'lovlar, manba konversiyasi, qarzdorlik, davomat, xarajatlar va KPI. Haqiqiy tizimda istalgan savol LLM orqali SQL'ga aylantiriladi.</p>`;
  }
})(window.App);

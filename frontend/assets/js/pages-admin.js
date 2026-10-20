/* Sozlamalar, Audit tarixi, Bosh sahifa (M1), AI yordamchi. Barcha yozuvlar server API orqali saqlanadi. */
(function (A) {
  const esc = A.esc;

  /* ===================================================== Umumiy CRUD */
  const CRUD = {};
  const canDo = (c, op) => A.can(c.section || 'settings', op) && (!c.topOnly || A.isTop());
  const crudList = (key) => {
    const c = CRUD[key];
    const rows = c.rows ? c.rows() : A.rows(c.coll);
    const canA = canDo(c, 'a'), canE = canDo(c, 'e'), canD = canDo(c, 'd') && c.deletable;
    const extra = c.rowActions || (() => '');
    return `<div class="row between"><h2>${esc(c.title)}</h2>${canA && !c.noAdd ? A.btn("Qo'shish", 'crud-add', { id: key, icon: 'plus' }) : ''}</div>
      ${c.note ? `<p class="muted small">${c.note}</p>` : ''}
      ${A.table([...c.cols, { h: '', f: (r) => `<span class="nowrap-cell">${extra(r)}${canE ? `<button class="btn sm ghost" data-act="crud-edit" data-id="${key}|${r.id}" title="Tahrirlash">✎</button>` : ''}${canD ? ` <button class="btn sm ghost" data-act="crud-del" data-id="${key}|${r.id}" title="O'chirish">🗑</button>` : ''}</span>` }], rows, { empty: c.empty })}`;
  };
  const crudForm = (key, rec) => {
    const c = CRUD[key];
    A.form({
      title: (rec ? '' : 'Yangi: ') + c.title,
      values: rec ? { ...rec } : { ...(c.defaults || {}) },
      fields: c.fields,
      async onSubmit(x) {
        const clean = {};
        for (const f of c.fields) if (!['note', 'computed'].includes(f.type) && !f.local) clean[f.name] = f.type === 'money' || f.type === 'number' ? (x[f.name] === '' ? null : Number(x[f.name])) : x[f.name];
        if (c.save) await c.save(clean, rec);
        else if (rec) await A.update(c.coll, rec.id, clean);
        else await A.create(c.coll, { ...(c.extra ? c.extra() : {}), ...clean });
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
  // O'chirish: server ishlatilgan ma'lumotnoma yozuvini o'chirmaydi (409) — faqat nofaol qilinadi (CLAUDE.md 6.4)
  A.act['crud-del'] = async (el) => {
    const [key, id] = el.dataset.id.split('|');
    const c = CRUD[key];
    const rec = A.get(c.coll, id);
    const name = c.label ? c.label(rec) : rec.name;
    if (!(await A.confirm(`«${esc(name)}» o'chirilsinmi?`, "O'chirish", true))) return;
    try {
      await A.remove(c.coll, id);
      A.toast("O'chirildi");
      A.refresh();
    } catch (e) {
      A.toast(e.message, 'warn');
    }
  };
  const isActive = (r) => (r.status || 'Faol') === 'Faol';
  const statusBadge = (r) => A.badge(r.status || 'Faol', isActive(r) ? 'green' : 'gray');
  const STATUS_FIELD = { name: 'status', label: 'Status', type: 'seg', options: ['Faol', 'Nofaol'], default: 'Faol' };
  const B = () => A.branchIds()[0];

  CRUD.courses = {
    coll: 'courses', title: 'Kurslar',
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Amaldagi narx', f: (r) => A.num(A.priceFor(B(), r.id, A.ym(A.today()))), cls: 'num' }, { h: 'Status', f: statusBadge }],
    fields: [{ name: 'name', label: 'Nomi', required: true }, STATUS_FIELD],
    extra: () => ({ branches: [B()] }),
  };
  CRUD.discounts = {
    coll: 'discountTypes', title: 'Chegirma turlari',
    note: "Limit majburiy tekshiriladi: to'lovdagi chegirma «Eng ko'p miqdori»dan oshmaydi. Tizim turi oddiy tanlovda ko'rinmaydi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Eng ko'p miqdori", f: (r) => A.num(r.max), cls: 'num' }, { h: 'Belgilar', f: (r) => (r.is_system ? A.badge('tizim', 'gray') : '') }],
    fields: [
      { name: 'name', label: 'Nomi', required: true },
      { name: 'max', label: "Eng ko'p miqdori", type: 'money', required: true },
      { name: 'is_system', label: 'Tizim turi (oddiy tanlovda ko\'rinmaydi)', type: 'checkbox' },
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
  CRUD.sources = {
    coll: 'leadSources', title: 'Lid manbalari',
    note: "Nofaol manba yangi lid formasida chiqmaydi. Eski lidlar va statistikada saqlanib qoladi.",
    cols: [{ h: 'Nomi', f: (r) => esc(r.name) }, { h: 'Status', f: statusBadge }],
    fields: [{ name: 'name', label: 'Nomi', required: true }, STATUS_FIELD],
  };
  CRUD.rooms = {
    coll: 'rooms', title: 'Xonalar',
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Sig'imi", f: (r) => r.capacity, cls: 'num' }, { h: 'Status', f: statusBadge }],
    fields: [{ name: 'name', label: 'Xona nomi', required: true }, { name: 'capacity', label: "Xona sig'imi", type: 'number', required: true, min: 1 }, STATUS_FIELD],
    extra: () => ({ branch: B() }),
  };
  CRUD.patterns = {
    coll: 'dayPatterns', title: 'Dars kunlari', deletable: true,
    note: "Hafta kunlari ISO raqamlarda saqlanadi (Dushanba = 1 … Yakshanba = 7). AppSheet'dagi WEEKDAY()−1 formati importda shunga o'giriladi. Nofaol dars kunlari yangi guruh va lid formalarida chiqmaydi, oydagi dars soni taklifiga kirmaydi. Guruh, lid yoki dars sonida ishlatilganini o'chirib bo'lmaydi — faqat nofaol qilinadi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Kunlar (ISO)', f: (r) => r.weekdays.join(', ') }, { h: 'Status', f: statusBadge }],
    fields: [{ name: 'weekdays', label: 'Hafta kunlari', type: 'chips', required: true, options: [1, 2, 3, 4, 5, 6, 7].map((d) => [String(d), A.WD_FULL[d]]) }, STATUS_FIELD],
    save: async (x, rec) => {
      const data = { weekdays: x.weekdays.map(Number), status: x.status };
      if (rec) await A.update('dayPatterns', rec.id, data);
      else await A.create('dayPatterns', data);
    },
    rows: () => A.rows('dayPatterns').map((p) => ({ ...p, weekdays: p.weekdays.map(String) })),
  };
  CRUD.branches = {
    coll: 'branches', title: 'Filiallar', topOnly: true,
    note: "Faol filial bitta bo'lsa, u hamma joyda avtomatik tanlanadi va filial maydoni ko'rinmaydi. Filiallarni faqat Admin va Bosh menejer o'zgartiradi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Naqd g'azna (standart)", f: (r) => esc(A.accName(r.default_cashbox)) }, { h: "Naqdsiz g'azna", f: (r) => esc(A.accName(r.noncash_cashbox)) }, { h: 'Status', f: statusBadge }],
    fields: [
      { name: 'name', label: 'Nomi', required: true },
      { name: 'default_cashbox', label: "Standart g'azna", type: 'select', options: () => A.optList('accounts') },
      { name: 'noncash_cashbox', label: "Naqdsiz to'lovlar g'aznasi", type: 'select', options: () => A.optList('accounts'), help: "AppSheet'da «cb4963b4» deb qattiq yozilgan edi" },
      { name: 'payment_due_day', label: "Oylik to'lov muddati (oyning kuni)", type: 'number', default: 10, help: "Shu kungacha o'quvchi shu oy uchun to'lashi kerak; undan keyin Qarzdorlar → «Shu oy to'lovi»da «muddati o'tgan» bo'ladi" },
      STATUS_FIELD,
    ],
    save: async (x, rec) => {
      const data = { ...x, default_cashbox: x.default_cashbox || null, noncash_cashbox: x.noncash_cashbox || null, payment_due_day: Number(x.payment_due_day) || 10 };
      if (rec) await A.update('branches', rec.id, data);
      else await A.create('branches', data);
    },
  };
  const ACC_ROLES = ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'];
  CRUD.accounts = {
    coll: 'accounts', title: "G'aznalar", section: 'accounts',
    note: "Joriy qoldiq va pul harakatlari jurnali «G'aznalar» bo'limida ko'rinadi. Mas'ullarni faqat Admin va Bosh menejer o'zgartiradi.",
    cols: [
      { h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: 'Turi', f: (r) => A.badge(A.CASH[r.cash_type], 'gray') },
      { h: "Mas'ullar", f: (r) => r.responsible.map(A.userName).map(esc).join(', ') },
      { h: "Boshlang'ich qoldiq", f: (r) => A.num(r.initial), cls: 'num' }, { h: 'Status', f: statusBadge },
    ],
    fields: [
      { name: 'name', label: 'Nomi', required: true },
      { name: 'cash_type', label: 'Turi', type: 'seg', options: Object.entries(A.CASH), default: 'CASH' },
      { name: 'responsible', label: "Mas'ullar", type: 'chips', show: () => A.isTop(), options: () => A.S.users.filter((u) => ACC_ROLES.includes(u.role) && u.status === 'Faol').map((u) => [u.id, u.full_name]), default: [] },
      { name: 'initial', label: "Boshlang'ich qoldiq", type: 'money', default: 0 },
      { name: 'start', label: "Boshlang'ich qoldiq sanasi", type: 'date' },
      STATUS_FIELD,
    ],
    save: async (x, rec) => {
      const data = { ...x, start: x.start || null };
      if (!A.isTop()) delete data.responsible;
      if (rec) await A.update('accounts', rec.id, data);
      else await A.create('accounts', data);
    },
  };

  /* ---- Foydalanuvchilar ---- */
  const assignable = () => ((A.roleRec(A.role()) || {}).can_assign || []);
  const userRowActions = (u) =>
    u.email && u.status === 'Faol' && A.can('settings', 'e') && assignable().includes(u.role)
      ? `<button class="btn sm ghost" data-act="user-invite" data-id="${u.id}" title="Parol o'rnatish havolasini qayta yuborish">✉</button> `
      : '';
  CRUD.users = {
    coll: 'users', title: 'Foydalanuvchilar', rowActions: userRowActions,
    note: "Rol ro'yxati sizning rolingiz tayinlay oladigan rollar bilan cheklangan (RolePower). Ishdan ketgan xodim tizimga kira olmaydi, lekin tarixi saqlanadi. ✉ — parol o'rnatish havolasini qayta yuborish.",
    cols: [
      { h: 'Ism', f: (u) => `<b>${esc(u.full_name)}</b><br><small class="muted">${esc(u.email || '—')}</small>` },
      { h: 'Lavozim', f: (u) => esc(A.ROLES[u.role]) },
      { h: 'Filial', f: (u) => (u.branches.length ? u.branches.map(A.branchName).join(', ') : '<span class="muted">hammasi</span>') },
      { h: "Bo'lim", f: (u) => (u.teams || []).join(', ') },
      { h: 'Telefon', f: (u) => esc(u.phone) },
      { h: 'Holat', f: (u) => A.badge(u.status, u.status === 'Faol' ? 'green' : 'gray') + (u.email && u.status === 'Faol' && !u.has_password ? `<br><small class="muted">parol o'rnatilmagan</small>` : '') },
    ],
    fields: [
      { name: 'full_name', label: "To'liq ism", required: true },
      { name: 'role', label: 'Lavozim', type: 'select', required: true, show: (x) => x.full_name, options: (x) => [...new Set([...assignable(), ...(x.role ? [x.role] : [])])].map((r) => [r, A.ROLES[r]]) },
      { name: 'branches', label: 'Filial', type: 'chips', show: (x) => x.role && !['ADMIN', 'BOSH_MENEJER'].includes(x.role), options: () => A.optList('branches', 'name', (b) => A.branchIds().includes(b.id)), default: () => [B()] },
      { name: 'phone', label: 'Telefon', show: (x) => x.role, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
      { name: 'teams', label: "Bo'lim", type: 'chips', show: (x) => x.role, options: ['Qabul', 'Marketing', 'Moliya', 'HR', "Ta'lim", 'Boshqa', "Qurilish va ta'mirlash", 'IT', "Ta'minot"], default: [] },
      { name: 'email', label: 'Pochta (login)', type: 'email', show: (x) => x.role && x.role !== 'BOSHQA', required: (x) => x.role && x.role !== 'BOSHQA' },
      { name: 'status', label: 'Holat', type: 'seg', options: ['Faol', 'Ishdan ketgan'], default: 'Faol', show: (x) => x.role },
      { name: 'inv', type: 'note', tone: 'info', show: (x) => x.email && !x.id, text: "Saqlangach xodim pochtasiga parol o'rnatish havolasi yuboriladi. Xodim parolini o'zi qo'yadi." },
    ],
    save: async (x, rec) => {
      const data = { ...x, branches: ['ADMIN', 'BOSH_MENEJER'].includes(x.role) ? [] : x.branches };
      delete data.inv;
      if (rec) await A.update('users', rec.id, data);
      else {
        await A.create('users', data);
        if (data.email) A.toast(`${data.email} manziliga parol o'rnatish havolasi yuborildi`);
      }
    },
  };
  A.act['user-invite'] = async (el) => {
    const u = A.get('users', el.dataset.id);
    if (!(await A.confirm(`${esc(u.full_name)} (${esc(u.email)}) pochtasiga parol o'rnatish havolasi qayta yuborilsinmi?`, 'Yuborish'))) return;
    const r = await A.http.post(`/users/${u.id}/send-invite/`);
    A.toast(r.detail);
  };

  /* ---- Davomat statuslari ---- */
  CRUD.attstatus = {
    coll: 'attendanceStatuses', title: 'Davomat statuslari', noAdd: true,
    note: 'Har bir statusni qaysi rollar qo\'ya olishi. Davomat olish ekranida faqat ruxsat berilgan tugmalar chiqadi.',
    cols: [{ h: 'Kod', f: (s) => A.attBadge(s.code) }, { h: 'Nomi', f: (s) => `<b>${esc(s.name)}</b>` }, { h: 'Ruxsat berilgan lavozimlar', f: (s) => s.roles.map((r) => A.ROLES[r]).join(', ') }],
    fields: [{ name: 'roles', label: 'Ruxsat berilgan lavozimlar', type: 'chips', options: () => Object.entries(A.ROLES).filter(([k]) => k !== 'BOSHQA') }],
    save: (x, rec) => A.update('attendanceStatuses', rec.code, { roles: x.roles }),
  };

  /* ===================================================== Oydagi dars soni */
  A.freqTable = (rows) =>
    A.table(
      [
        { h: 'Oy', f: (f) => `${A.MONTHS[f.month - 1]} ${f.year}` },
        { h: 'Dars kunlari', f: (f) => `<b>${esc(A.patternName(f.pattern))}</b>` },
        { h: 'Kurslar', f: (f) => f.courses.map(A.courseName).map(esc).join(', ') || '<span class="t-red">kurs belgilanmagan</span>' },
        { h: 'Darslar soni', f: (f) => { const p = A.get('dayPatterns', f.pattern); const cal = p ? A.lessonDaysInMonth(`${f.year}-${String(f.month).padStart(2, '0')}`, p.weekdays).length : f.frequency; return `<b>${f.frequency}</b>${cal !== f.frequency ? ` <small class="muted">(kalendar: ${cal})</small>` : ''}`; }, cls: 'num' },
        { h: 'Status', f: (f) => A.badge(f.status, f.status === 'Tasdiqlangan' ? 'green' : 'orange') + (f.approved_by ? `<br><small class="muted">${esc(A.userName(f.approved_by))}</small>` : '') },
        { h: '', f: (f) => `<div class="row gap nowrap">${A.can('settings', 'e') ? `<button class="btn sm ghost" data-act="freq-edit" data-id="${f.id}">✎</button>` : ''}${f.status === 'Taklif' && A.canApproveFreq() ? `<button class="btn sm primary" data-act="freq-ok" data-id="${f.id}">Tasdiqlash</button>` : ''}</div>` },
      ],
      rows,
      { empty: "Taklif yo'q" },
    );
  A.act['freq-ok'] = async (el) => {
    const f = A.get('lessonFreqs', el.dataset.id);
    A.putLocal('lessonFreqs', await A.http.post(`/lesson-frequencies/${f.id}/approve/`));
    A.toast('Tasdiqlandi');
    A.refresh();
  };
  A.act['freq-edit'] = (el) => {
    const f = A.get('lessonFreqs', el.dataset.id);
    A.form({
      title: `${A.patternName(f.pattern)} · ${A.MONTHS[f.month - 1]} ${f.year}`,
      values: { ...f },
      fields: [
        { name: 'courses', label: 'Kurslar', type: 'chips', options: () => A.optList('courses', 'name', (c) => c.status === 'Faol' || f.courses.includes(c.id)), required: true },
        { name: 'frequency', label: 'Oydagi dars soni', type: 'number', min: 4, max: 26, required: true, validate: (n) => (n < 4 || n > 26 ? "Oyda eng ozi 4 marta, ko'p 26 marta bo'lishi mumkin, xolos" : ''), help: 'Bayram kunlari bo\'lsa kamaytiring' },
      ],
      async onSubmit(x) {
        await A.update('lessonFreqs', f.id, { courses: x.courses, frequency: Number(x.frequency) });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['freq-gen'] = async (el) => {
    const ym = el.dataset.id;
    const r = await A.http.post('/lesson-frequencies/propose/', { month: ym, branch: B() });
    for (const f of await A.http.get(`/lesson-frequencies/?month=${ym}`)) A.putLocal('lessonFreqs', f);
    A.toast(r.created ? `${r.created} ta taklif yaratildi (serverda har oy 1-kuni avtomatik yaratiladi)` : 'Bu oy uchun takliflar allaqachon bor');
    A.refresh();
  };

  /* ===================================================== Sozlamalar sahifasi */
  const TABS = [
    ['courses', 'Kurslar'], ['prices', 'Kurs narxlari'], ['freq', 'Oydagi dars soni'], ['rates', 'KPI stavkalari'],
    ['discounts', 'Chegirma turlari'], ['expcats', 'Xarajat kategoriyalari'], ['sources', 'Lid manbalari'], ['rooms', 'Xonalar'],
    ['patterns', 'Dars kunlari'], ['branches', 'Filiallar'], ['accounts', "G'aznalar"],
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
      else if (tab === 'rates') body = `<h2>KPI stavkalari</h2><p>Ustoz va yordamchilarning KPI stavkalari «Oyliklar» bo'limida kiritiladi: har bir xodim, kurs va oy uchun (o'zgarmas summa yoki foiz). O'tgan oy stavkalarini nusxalash ham o'sha yerda.</p>
        ${A.can('salaries') ? `<a class="btn primary" href="#/salaries?tab=rates">KPI stavkalarini ochish →</a>` : ''}`;
      else if (tab === 'roles') body = rolesView();
      return `${A.head('Sozlamalar', 'Barcha ma\'lumotnomalar. Bosh menejer hammasini, Filial menejeri o\'z filiali doirasida boshqaradi')}
        <div class="settings"><nav class="side-tabs">${TABS.map(([k, l]) => `<a href="#/settings?tab=${k}" class="${k === tab ? 'on' : ''}">${esc(l)}</a>`).join('')}</nav><div class="settings-body card">${body}</div></div>`;
    },
  });

  function pricesView() {
    const b = B();
    const cur = A.ym(A.today());
    return `<div class="row between"><h2>Kurs narxlari</h2>${A.can('settings', 'a') ? A.btn("Narxni o'zgartirish", 'price-new', { icon: 'plus' }) : ''}</div>
      <p class="muted small">Narx «amal qilish oyi» bilan saqlanadi. Narx faqat o'zgarganda yangi yozuv qo'shiladi — har oy qayta kiritish shart emas. Oy uchun shu oyda amalda bo'lgan oxirgi narx olinadi.</p>
      ${A.rows('courses')
        .map((c) => {
          const hist = A.sortBy(A.rows('coursePrices').filter((p) => p.course === c.id && p.branch === b), (p) => p.effective_from, true);
          const active = A.priceFor(b, c.id, cur);
          return `<div class="price-row"><div><b>${esc(c.name)}</b><div class="muted small">${hist.map((h) => `${A.ymLabel(h.effective_from)} dan: ${A.num(h.price)}`).join(' · ') || 'narx kiritilmagan'}</div></div><div class="big-num sm">${active === null ? '—' : A.money(active)}</div></div>`;
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
        { name: 'w', type: 'note', tone: 'warn', show: (x) => x.effective_from && x.effective_from <= A.ym(A.today()), text: "Joriy yoki o'tgan oy tanlandi — shu oydan boshlab davomat qatorlaridagi talaba qarzi va Foiz-KPI qayta hisoblanadi (M3 dan boshlab)." },
      ],
      async onSubmit(x) {
        A.putLocal('coursePrices', await A.http.post('/course-prices/', { branch: B(), course: x.course, effective_from: x.effective_from, price: x.price }));
        A.toast('Saqlandi');
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
      <p class="muted small">Har oy 1-kuni tizim har bir faol dars kunlari jadvali uchun kalendardan darslar sonini hisoblab «Taklif» yaratadi (o'tgan oydagi kurslar nusxalanadi). Menejer bayramlarni hisobga olib tuzatadi va tasdiqlaydi. <b>Tasdiqlanmagan oy uchun qarz va KPI hisoblanmaydi.</b></p>
      ${A.freqTable(rows)}`;
  }

  function rolesView() {
    const editable = A.isTop();
    const roles = A.S.roles.filter((r) => r.code !== 'BOSHQA');
    const OPS = [['v', "ko'rish"], ['a', "qo'shish"], ['e', 'tahrirlash'], ['d', "o'chirish"], ['p', 'tasdiqlash']];
    return `<h2>Rollar va ruxsatlar</h2>
      <p class="muted small">Har katakda: <b>v</b> ko'rish · <b>a</b> qo'shish · <b>e</b> tahrirlash · <b>d</b> o'chirish · <b>p</b> tasdiqlash. ${editable ? 'Harfni bosib yoqing/o\'chiring — o\'zgarish darhol saqlanadi va audit\'ga yoziladi. Admin rolining ruxsatlari o\'zgarmaydi.' : 'Faqat Admin va Bosh menejer o\'zgartiradi.'} Boshlang'ich qiymatlar AppSheet sozlamalaridan olingan.</p>
      <div class="tbl-wrap perm-wrap"><table class="tbl perm"><thead><tr><th>Bo'lim</th>${roles.map((r) => `<th>${esc(r.name)}</th>`).join('')}</tr></thead><tbody>
      ${A.SECTIONS.map(([sec, name]) => `<tr><td>${esc(name)}</td>${roles
        .map((r) => `<td class="pc">${OPS.map(([o, t]) => `<button class="pbit ${(r.perms[sec] || '').includes(o) ? 'on' : ''}" title="${esc(r.name)} · ${esc(name)} · ${t}" ${editable && r.code !== 'ADMIN' ? `data-act="perm" data-id="${r.code}|${sec}|${o}"` : 'disabled'}>${o}</button>`).join('')}</td>`)
        .join('')}</tr>`).join('')}
      </tbody></table></div>
      <h3>Tahrirlash va o'chirish muddatlari</h3>
      ${A.table(
        [{ h: 'Rol', f: (r) => esc(r.name) }, { h: 'Shartnoma, lid, davomat', f: (r) => A.editRule(r.code, 'contracts') }, { h: "To'lov, xarajat", f: (r) => A.editRule(r.code, 'payments') }],
        roles,
      )}
      <p class="muted small">Tasdiqlangan to'lov, chegirma va o'tkazmani faqat Admin va Bosh menejer o'zgartiradi. Muddat: bugun − yozuv sanasi ≤ N kun.</p>`;
  }
  A.act.perm = async (el) => {
    const [code, section, op] = el.dataset.id.split('|');
    el.disabled = true;
    A.putLocal('roles', await A.http.post(`/roles/${code}/toggle/`, { section, op }));
    // Qayta chizilganda jadval aylantirilgan joyida qolsin
    const w = document.querySelector('.perm-wrap'), pos = w && [w.scrollTop, w.scrollLeft], y = window.scrollY;
    await A.refresh();
    const w2 = document.querySelector('.perm-wrap');
    if (w2 && pos) [w2.scrollTop, w2.scrollLeft] = pos;
    window.scrollTo(0, y);
  };

  /* ===================================================== Audit tarixi (serverdan, 50 tadan) */
  const ACT = { create: ['Yaratildi', 'green'], update: ["O'zgartirildi", 'blue'], delete: ["O'chirildi", 'red'], login: ['Kirish', 'gray'], logout: ['Chiqish', 'gray'], password: ['Parol', 'gray'], import: ['Import', 'gray'], export: ['Eksport', 'gray'], ai: ['AI so\'rov', 'orange'] };
  let auditData = { results: [], count: 0, page: 1, pages: 1 };
  A.page('audit', {
    title: 'Audit tarixi',
    section: 'audit',
    async load() {
      const qs = new URLSearchParams({ page: A.q('audit:page', 1) });
      for (const k of ['search', 'user', 'action']) if (A.q('audit:' + k, '')) qs.set(k, A.q('audit:' + k));
      auditData = await A.http.get('/audit-log/?' + qs);
    },
    render() {
      const d = auditData;
      return `${A.head('Audit tarixi', "Har bir yaratish, o'zgartirish va o'chirish: kim, qachon, nima, eski → yangi qiymat")}
        ${A.filterBar('audit', [A.fSearch('audit'), A.fSelect('audit', 'user', A.S.users.map((u) => [u.id, u.full_name]), 'Barcha xodimlar'), A.fSelect('audit', 'action', Object.entries(ACT).map(([k, v]) => [k, v[0]]), 'Barcha amallar')])}
        ${A.table(
          [
            { h: 'Vaqt', f: (x) => A.fdt(x.at) },
            { h: 'Xodim', f: (x) => esc(A.userName(x.user)) },
            { h: 'Amal', f: (x) => A.badge(...(ACT[x.action] || [x.action, 'gray'])) },
            { h: "Bo'lim", f: (x) => esc(x.model) },
            { h: 'Yozuv', f: (x) => esc(x.obj) },
            { h: "O'zgarish", f: (x) => `<small>${esc(x.detail)}</small>` },
          ],
          d.results,
          { empty: "Yozuv yo'q" },
        )}
        ${d.pages > 1 ? `<div class="row gap pager"><button class="btn sm ghost" data-act="audit-page" data-id="${d.page - 1}" ${d.page <= 1 ? 'disabled' : ''}>← Oldingi</button><span class="muted small">${d.page} / ${d.pages} · jami ${d.count}</span><button class="btn sm ghost" data-act="audit-page" data-id="${d.page + 1}" ${d.page >= d.pages ? 'disabled' : ''}>Keyingi →</button></div>` : ''}`;
    },
  });
  A.act['audit-page'] = (el) => {
    A.ui.q['audit:page'] = Number(el.dataset.id);
    A.refresh();
  };
  // Filtr o'zgarsa 1-sahifadan boshlanadi
  document.addEventListener('input', (e) => {
    if (e.target.closest('[data-filter^="audit:"]')) A.ui.q['audit:page'] = 1;
  }, true);

  /* ===================================================== Dars jadvali (bosh sahifa) */
  // Guruhlardan avtomatik: kun → xona (yoki ustoz) × vaqt. Bir qatorda vaqti ustma-ust tushgan guruhlar qizil bilan.
  const SLOT = 30; // daqiqa
  const STRIP = 17; // px — ustma-ust guruhlarda orqadagisining chiqib turadigan qirrasi
  const SLOT_MIN = 40; // px — bundan tor bo'lsa jadval gorizontal aylanadi
  const SCHED_COLORS = ['#2f80ed', '#27ae60', '#9b51e0', '#F26A1B', '#56ccf2', '#bb6bd9', '#6fcf97', '#f2c94c']; // qizilsiz — qizil faqat ustma-ust uchun
  const mins = (t) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
  const hhmm = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
  function schedHTML(data) {
    if (!data || !data.groups.length) return '';
    const groups = data.groups.map((g) => ({ ...g, s: mins(g.start), e: mins(g.end) }));
    const days = [1, 2, 3, 4, 5, 6, 7].filter((d) => d < 7 || groups.some((g) => g.weekdays.includes(7)));
    const todayWd = A.isoWeekday(A.today());
    let day = Number(A.ui.schedDay) || (days.includes(todayWd) ? todayWd : days[0]);
    if (!days.includes(day)) day = days[0];
    const by = A.ui.schedBy === 'teacher' ? 'teacher' : 'room';
    const t0 = Math.floor(Math.min(...groups.map((g) => g.s)) / SLOT) * SLOT;
    const t1 = Math.ceil(Math.max(...groups.map((g) => g.e)) / SLOT) * SLOT;
    const slots = [];
    for (let t = t0; t < t1; t += SLOT) slots.push(t);
    const todays = groups.filter((g) => g.weekdays.includes(day));
    const courses = [...new Set(groups.map((g) => g.course))];
    const color = (g) => SCHED_COLORS[courses.indexOf(g.course) % SCHED_COLORS.length];
    let rows;
    if (by === 'room') rows = data.rooms.map((r) => ({ key: r.id, label: r.name, sub: r.capacity ? `${r.capacity} o'rin` : '' }));
    else {
      const seen = new Map();
      groups.forEach((g) => seen.set(g.teacher, g.teacher_name));
      rows = [...seen].sort((a, b) => a[1].localeCompare(b[1])).map(([id, name]) => ({ key: id, label: name, sub: '' }));
    }
    const rowKey = (g) => (by === 'room' ? g.room : g.teacher);
    const busy = todays.reduce((s, g) => s + (g.e - g.s), 0);
    const roomsUsed = new Set(todays.map((g) => g.room)).size;
    const pct = data.rooms.length ? Math.round((100 * busy) / (data.rooms.length * (t1 - t0))) : 0;
    const span = t1 - t0;
    const pos = (m) => `${(100 * m) / span}%`;
    const canEdit = A.can('groups', 'e');
    const canAdd = A.can('groups', 'a');
    const rowHTML = (row) => {
      const items = todays.filter((g) => rowKey(g) === row.key).sort((a, b) => a.s - b.s);
      // Vaqti ustma-ust guruhlar pog'onaga joylanadi: orqadagisining yuqori qirrasi (ushlagich) chiqib turadi — bosib tanlanadi
      const laneEnd = [];
      items.forEach((g) => {
        let i = laneEnd.findIndex((e) => e <= g.s);
        if (i < 0) i = laneEnd.length;
        laneEnd[i] = g.e;
        g.lane = i;
      });
      const lanes = Math.max(1, laneEnd.length);
      const blocks = items.map((g) => {
        const clash = items.some((o) => o !== g && o.s < g.e && g.s < o.e);
        const c = color(g);
        const second = by === 'room' ? g.teacher_name : data.rooms.find((r) => r.id === g.room)?.name || '';
        const plan = g.status === 'Rejada';
        const title = `${g.name} · ${g.start}–${g.end} · ${g.teacher_name}${g.supporter_name ? ` (yordamchi: ${g.supporter_name})` : ''} · ${g.students}/${g.capacity || '—'} talaba${plan ? `, ${g.leads} ta lid · Rejada: ${A.fdate(g.start_date)} dan` : ''}${clash ? ' · DIQQAT: vaqti boshqa guruh bilan ustma-ust' : ''}`;
        const cls = `sched-b${g.status === 'Rejada' ? ' plan' : ''}${clash ? ' clash' : ''}${lanes > 1 ? ' stack' : ''}`;
        const inner = `${plan ? '<em class="plan-tag">rejada</em>' : ''}<b>${esc(g.name)}</b><small>${esc(second)} · 👥 ${g.students}/${g.capacity || '—'}${plan ? ` · ${g.leads} lid` : ''}</small>`;
        const st = `left:calc(${pos(g.s - t0)} + 3px);width:calc(${pos(g.e - g.s)} - 6px);--c:${c}${lanes > 1 ? `;top:${6 + g.lane * STRIP}px;z-index:${g.lane + 1}` : ''}`;
        return canEdit
          ? `<div class="${cls}" role="button" tabindex="0" data-act="group-manage" data-id="${g.id}" title="${esc(title)} · bosing — guruhni boshqarish" style="${st}">${inner}</div>`
          : `<a class="${cls}" href="#/groups/${g.id}" title="${esc(title)}" style="${st}">${inner}</a>`;
      }).join('');
      return `<div class="sched-row"><div class="sched-l"><b>${esc(row.label)}</b>${row.sub ? `<small>${esc(row.sub)}</small>` : ''}</div>
        <div class="sched-track${canAdd ? ' addable' : ''}" ${lanes > 1 ? `style="min-height:${64 + (lanes - 1) * STRIP}px"` : ''} ${canAdd ? `data-act="sched-add" data-key="${row.key}" data-day="${day}" data-by="${by}" data-t0="${t0}" data-span="${span}" title="Bo'sh joyni bosing — shu vaqtga yangi guruh ochish"` : ''}>${slots.map(() => '<i></i>').join('')}${blocks}</div></div>`;
    };
    const tabs = days.map((d) => `<button class="sched-day${d === day ? ' on' : ''}" data-act="sched-day" data-id="${d}">${A.WD_FULL[d]}${d === todayWd ? ' •' : ''}
      <span>${groups.filter((g) => g.weekdays.includes(d)).length}</span></button>`).join('');
    const shown = rows.filter((row) => by === 'room' || todays.some((g) => rowKey(g) === row.key));
    // Telefonda: kun bo'yicha ro'yxat (vaqt · guruh · xona · ustoz)
    const agendaHTML = () => {
      const items = [...todays].sort((a, b) => a.s - b.s || a.name.localeCompare(b.name));
      if (!items.length) return `<ul class="sched-agenda"><li class="muted">${A.WD_FULL[day]} kuni dars yo'q</li></ul>`;
      return `<ul class="sched-agenda">${items.map((g) => {
        const clash = items.some((o) => o !== g && (o.room === g.room || o.teacher === g.teacher) && o.s < g.e && g.s < o.e);
        const room = data.rooms.find((r) => r.id === g.room)?.name || '';
        const attrs = canEdit ? `data-act="group-manage" data-id="${g.id}" role="button"` : `href="#/groups/${g.id}"`;
        return `<li><div class="t">${g.start}<small>${g.end}</small></div>
          <a class="g${clash ? ' clash' : ''}${g.status === 'Rejada' ? ' plan' : ''}" ${attrs} style="--c:${color(g)}"><b>${esc(g.name)}</b>
          <small>${esc(room)} · ${esc(g.teacher_name)} · 👥 ${g.students}/${g.capacity || '—'}${g.status === 'Rejada' ? ` · ${g.leads} lid · rejada` : ''}${clash ? ' · ⚠️ ustma-ust' : ''}</small></a></li>`;
      }).join('')}</ul>`;
    };
    return `<section class="card sched"><div class="row between wrap"><h2>Dars jadvali</h2>
        <div class="seg">${[['room', 'Xonalar'], ['teacher', 'Ustozlar']].map(([k, l]) => `<button class="${by === k ? 'on' : ''}" data-act="sched-by" data-id="${k}">${l}</button>`).join('')}</div></div>
      <div class="sched-days">${tabs}</div>
      <p class="muted small">${todays.length} dars · ${roomsUsed}/${data.rooms.length} xona band · ${pct}% band<span class="sched-help"> · ${hhmm(t0)}–${hhmm(t1)}. Jadval guruhlardan avtomatik tuziladi; ${canEdit ? "guruhni bosing — uni shu yerda to'liq boshqarasiz (jadval, o'quvchilar, yopish)." : 'guruhni bosing — batafsil.'} Och yashil — rejadagi guruh (talabalar va lidlar soni bilan), qizil — vaqti ustma-ust.</span></p>
      <div class="sched-wrap"><div class="sched-grid" style="min-width:${slots.length * SLOT_MIN + 150}px">
        <div class="sched-row head"><div class="sched-l">${by === 'room' ? 'Xona' : 'Ustoz'} / vaqt</div><div class="sched-track">${slots.map((t) => `<span>${hhmm(t)}</span>`).join('')}</div></div>
        ${shown.map(rowHTML).join('') || `<div class="muted pad">${A.WD_FULL[day]} kuni dars yo'q</div>`}
      </div></div>${agendaHTML()}</section>`;
  }
  A.act['sched-day'] = (el) => { A.ui.schedDay = el.dataset.id; A.refresh(); };
  A.act['sched-by'] = (el) => { A.ui.schedBy = el.dataset.id; A.refresh(); };
  // Bo'sh joyni bosish → yangi guruh formasi (kun, vaqt, xona/ustoz oldindan to'ldiriladi)
  A.act['sched-add'] = (el, ev) => {
    const r = el.getBoundingClientRect();
    const t0 = Number(el.dataset.t0);
    const at = t0 + (Number(el.dataset.span) * (ev.clientX - r.left)) / r.width;
    const day = Number(el.dataset.day);
    const preset = {};
    const pat = A.rows('dayPatterns').find((p) => (p.status || 'Faol') === 'Faol' && (p.weekdays || []).includes(day));
    if (pat) preset.pattern = pat.id;
    const s0 = Math.floor(at / 30) * 30; // bosilgan joydan boshlab, yarim soatga yaxlitlab, 2 soatlik dars
    Object.assign(preset, { new_start: hhmm(s0), new_end: hhmm(Math.min(s0 + 120, 23 * 60 + 30)) });
    if (el.dataset.by === 'room') preset.room = el.dataset.key;
    else preset.teacher = el.dataset.key;
    A.groupForm(null, preset);
  };

  /* ---- Guruhni boshqarish oynasi (jadvaldagi guruh ustiga bosilganda): jadval, tahrir, yopish/qayta ochish, o'quvchilar ---- */
  async function manageGroup(id) {
    const g = A.get('groups', id);
    if (!g) return A.go('groups/' + id);
    const res = await A.http.get(`/contracts/?group=${id}&page_size=200`);
    res.results.forEach(A.keepContract);
    const list = res.results;
    const active = A.sortBy(list.filter((c) => c.status !== 'Nofaol'), (c) => (c.student_data || {}).full_name || c.name);
    const ended = list.filter((c) => c.status === 'Nofaol');
    const f = A.groupFill(g);
    const canE = A.can('groups', 'e');
    const canC = A.can('contracts', 'a');
    const today = A.today();
    const m = A.modal({
      title: `${A.groupName(g)} — boshqarish`,
      wide: true,
      body: `<div class="row gap wrap" style="margin-bottom:10px">${A.badge(g.status, g.status === 'Faol' ? 'green' : g.status === 'Rejada' ? 'blue' : 'red')}
          <span>${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}</span></div>
        <p class="muted small">Ustoz: <b>${esc(A.userName(g.teacher))}</b>${g.supporter ? ` · yordamchi: <b>${esc(A.userName(g.supporter))}</b>` : ''} · o'quvchilar: <b>${f.n}/${f.cap || '—'}</b>${g.end ? ` · tugash: ${A.fdate(g.end)}` : ''}</p>
        <div class="row gap wrap" style="margin:10px 0">
          ${canE ? '<button class="btn ghost" data-m="sched">🗓 Kun, vaqt, xona, ustoz</button><button class="btn ghost" data-m="edit">✏️ To\'liq tahrirlash</button>' : ''}
          ${A.can('attendance', 'a') && g.status === 'Faol' && A.hasLesson(g, today) ? `<a class="btn ghost" href="#/attendance?tab=take&group=${g.id}" data-close>📋 Davomat olish</a>` : ''}
          <a class="btn ghost" href="#/groups/${g.id}" data-close>📊 Jurnal va sahifa</a>
          ${canE ? (g.status === 'Nofaol' ? '<button class="btn ghost" data-m="reopen">♻️ Qayta faollashtirish</button>' : '<button class="btn danger" data-m="close">⛔ Guruhni yopish (nofaol)</button>') : ''}
        </div>
        <div class="row between" style="margin:14px 0 6px"><h3 style="margin:0">O'quvchilar (${active.length})</h3>${canC && g.status !== 'Nofaol' ? '<button class="btn primary sm" data-m="add">＋ O\'quvchi qo\'shish</button>' : ''}</div>
        ${active.length ? A.table([
          { h: "O'quvchi", f: (c) => `<a href="#/contracts/${c.id}" data-close class="${Number(c.balance) > 0 ? 't-red' : ''}">${esc((c.student_data || {}).full_name || c.name)}</a>` },
          { h: 'Telefon', f: (c) => ((c.student_data || {}).phone1 ? `<a href="tel:+998${c.student_data.phone1}">${c.student_data.phone1}</a>` : '') },
          { h: 'Holat', f: (c) => A.contractStatusBadge(c.status) },
          { h: 'Balans', f: (c) => A.num(c.balance), cls: 'num' },
          { h: '', f: (c) => (A.can('contracts', 'e') ? `<button class="btn sm ghost" data-m="out" data-id="${c.id}" title="Guruhdan chiqarish (shartnomani to'xtatish)">Chiqarish</button>` : '') },
        ], active) : A.empty("Faol o'quvchi yo'q")}
        ${ended.length ? `<p class="muted small" style="margin-top:10px">Nofaol shartnomalar: ${ended.length} ta (guruh sahifasida ko'rinadi)</p>` : ''}`,
    });
    const again = () => { A.refresh(); setTimeout(() => manageGroup(id), 50); };
    m.el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-m]');
      if (!b) return;
      const what = b.dataset.m;
      m.close();
      if (what === 'sched') A.act['sched-edit']({ dataset: { id } });
      else if (what === 'edit') A.groupForm(A.get('groups', id));
      else if (what === 'add') A.contractForm(null, { course: g.course, group: g.id, _after: again }, false);
      else if (what === 'out') A.contractForm(A.get('contracts', b.dataset.id), { _after: again }, true);
      else if (what === 'close') closeGroup(id, again);
      else if (what === 'reopen') reopenGroup(id, again);
    });
  }
  function closeGroup(id, done) {
    const g = A.get('groups', id);
    A.form({
      title: `${A.groupName(g)} — guruhni yopish`,
      intro: "<p class=\"muted\">Tanlangan sanagacha guruh faol, ertasidan <b>nofaol</b> bo'ladi: jadvalda, davomat olishda va yangi shartnomalarda chiqmaydi. Shartnomalar o'z holicha qoladi — o'quvchilarni alohida «Chiqarish» yoki boshqa guruhga o'tkazish mumkin.</p>",
      values: { end: today0() },
      submit: 'Yopish',
      fields: [{ name: 'end', label: 'Oxirgi faol kun', type: 'date', required: true, validate: (d) => (d && g.start && d <= g.start ? "Boshlanish sanadan keyin bo'lsin" : '') }],
      async onSubmit(x) {
        const saved = await A.http.patch(`/groups/${id}/`, { end: x.end });
        A.putLocal('groups', saved);
        A.toast(`${A.groupName(g)}: ${x.end < today0() ? 'guruh yopildi' : A.fdate(x.end) + ' dan keyin yopiladi'}`);
        done();
      },
    });
  }
  const today0 = () => A.today();
  async function reopenGroup(id, done) {
    const g = A.get('groups', id);
    if (!(await A.confirm(`${A.groupName(g)} qayta faollashtirilsinmi? Tugash sanasi olib tashlanadi.`, 'Faollashtirish'))) return done();
    const saved = await A.http.patch(`/groups/${id}/`, { end: null });
    A.putLocal('groups', saved);
    A.toast('Guruh qayta faollashtirildi');
    done();
  }
  A.act['group-manage'] = (el) => manageGroup(el.dataset.id);

  // Jadvaldan tez tahrir: dars kunlari, vaqti, xona, ustoz (to'liq forma — guruh sahifasida). Ustma-ust tushish oldindan ogohlantiriladi.
  const overlap = (a, b) => a.weekdays.some((d) => b.weekdays.includes(d)) && a.s < b.e && b.s < a.e;
  A.act['sched-edit'] = (el) => {
    const g = A.get('groups', el.dataset.id);
    if (!g) return A.go('groups/' + el.dataset.id);
    const B = g.branch;
    const staff = (roles, x) => A.S.users.filter((u) => roles.includes(u.role) && (u.status === 'Faol' || u.id === x) && (u.branches || []).includes(B));
    const others = ((dash.sched && dash.sched.groups) || []).filter((o) => o.id !== g.id).map((o) => ({ ...o, s: mins(o.start), e: mins(o.end) }));
    const probe = (x) => {
      const p = A.get('dayPatterns', x.pattern);
      const t = x.new_start && x.new_end && x.new_end > x.new_start ? { start: x.new_start, end: x.new_end } : null;
      return p && t ? { weekdays: p.weekdays || [], s: mins(t.start), e: mins(t.end) } : null;
    };
    const clashes = (x) => {
      const me = probe(x);
      if (!me) return [];
      return others.filter((o) => overlap(me, o) && (o.room === x.room || o.teacher === x.teacher))
        .map((o) => `${o.name} (${o.start}–${o.end}, ${o.room === x.room ? 'xona band' : 'ustoz band'})`);
    };
    A.form({
      title: `${A.groupName(g)} — jadval`,
      values: { pattern: g.pattern, ...A.timeValues(g.time), room: g.room, teacher: g.teacher, supporter: g.supporter || '' },
      fields: [
        { name: 'pattern', label: 'Dars kunlari', type: 'seg', required: true, options: (x) => A.optList('dayPatterns', 'name', (p) => (p.status || 'Faol') === 'Faol' || p.id === x.pattern) },
        ...A.timeFields(),
        {
          name: 'room', label: 'Xona', type: 'select', required: true,
          options: (x) => A.rows('rooms').filter((r) => r.branch === B && (r.status === 'Faol' || r.id === x.room)).map((r) => {
            const me = probe(x);
            const busy = me && others.some((o) => o.room === r.id && overlap(me, o));
            return [r.id, `${r.name} (${r.capacity} o'rin)${busy ? ' — shu vaqtda band!' : ''}`];
          }),
        },
        { name: 'teacher', label: 'Ustoz', type: 'select', required: true, options: (x) => staff(['USTOZ', 'USTOZ_YORDAMCHI'], x.teacher).map((u) => [u.id, u.full_name]) },
        { name: 'supporter', label: 'Yordamchi ustoz (ixtiyoriy)', type: 'select', placeholder: "Yo'q", options: (x) => staff(['YORDAMCHI', 'USTOZ_YORDAMCHI'], x.supporter).filter((u) => u.id !== x.teacher).map((u) => [u.id, u.full_name]) },
        { name: 'warn', label: 'Tekshiruv', type: 'computed', compute: (x) => { const c = clashes(x); return c.length ? `⚠️ Ustma-ust: ${c.join('; ')}` : "✓ Xona va ustoz bu vaqtda bo'sh"; } },
      ],
      async onSubmit(x) {
        const time = await A.ensureTime(x.new_start, x.new_end, B);
        const saved = await A.http.patch(`/groups/${g.id}/`, { pattern: x.pattern, time, room: x.room, teacher: x.teacher, supporter: x.supporter || null });
        A.putLocal('groups', saved);
        A.toast(`Saqlandi: ${saved.name}`);
        A.refresh();
      },
    });
  };

  /* ===================================================== Bosh sahifa (M1) */
  let dash = {};
  A.page('dashboard', {
    title: 'Bosh sahifa',
    section: 'dashboard',
    async load() {
      const get = (ok, path) => (ok ? A.http.get(path) : Promise.resolve(null));
      const [, debt, contracts, summary, pays, , , sched] = await Promise.all([
        A.reloadGroups(),
        get(A.can('debtors'), '/debtors/'),
        get(A.can('contracts'), '/contracts/?page_size=1'),
        get(A.isTeacherRole(), '/attendance/summary/'),
        get(A.can('payments'), '/payments/summary/'),
        A.can('accounts') ? A.reloadMoney() : null,
        A.reloadPending(),
        A.http.get('/schedule/'),
        A.reloadTaskSummary ? A.reloadTaskSummary() : null,
      ]);
      dash = { debt, counts: contracts ? contracts.counts : null, summary, pays, sched };
    },
    render() {
      const me = A.me();
      const today = A.today();
      const activeGroups = A.rows('groups').filter((g) => g.status === 'Faol');
      const mine = A.isTeacherRole() ? activeGroups.filter((g) => g.teacher === me.id || g.supporter === me.id) : activeGroups;
      const sm = dash.summary;
      const ym = A.ym(A.today());
      const [y, m] = ym.split('-').map(Number);
      const unapproved = A.rows('dayPatterns').filter(isActive).filter((p) => !A.rows('lessonFreqs').some((f) => f.pattern === p.id && f.year === y && f.month === m && f.status === 'Tasdiqlangan'));
      return `${A.head(`Assalomu alaykum, ${esc(me.full_name.split(' ')[0])}!`, `${A.WD_FULL[A.isoWeekday(A.today())]}, ${A.fdate(A.today())} · ${esc(A.ROLES[me.role])}`)}
        ${unapproved.length && A.can('settings') ? `<div class="alert warn">${A.icon('alert')}<div><b>${A.ymLabel(ym)} uchun oydagi dars soni tasdiqlanmagan:</b> ${unapproved.map((p) => esc(p.name)).join(', ')}. <a href="#/settings?tab=freq">Tekshirish va tasdiqlash →</a></div></div>` : ''}
        ${(() => { const ts = A.S.taskSummary; return ts && ts.in_open ? `<div class="alert ${ts.in_overdue ? 'danger' : 'info'}">${A.icon('task')}<div><b>Sizda ${ts.in_open} ta ochiq topshiriq${ts.in_overdue ? `, ${ts.in_overdue} tasining muddati o'tgan` : ''}.</b> <a href="#/tasks">Topshiriqlarni ochish →</a></div></div>` : ''; })()}
        <div class="stats">
          ${dash.pays ? A.stat("Bugungi to'lovlar", A.money(Number(dash.pays.cash) + Number(dash.pays.noncash)), `Naqd: ${A.num(dash.pays.cash)} · Naqdsiz: ${A.num(dash.pays.noncash)}`, '', '#/payments') : ''}
          ${dash.pays ? A.stat('Shu oy tushum', A.money(dash.pays.month), A.ymLabel(A.ym(today)), '', '#/payments') : ''}
          ${A.can('approvals') ? A.stat('Tasdiq kutmoqda', A.pendingCount(), A.pendingCount() ? 'sizning tasdiqingiz kerak' : 'hammasi tasdiqlangan', A.pendingCount() ? 'warn' : '', '#/approvals') : ''}
          ${dash.counts ? A.stat('Faol talabalar', dash.counts.Faol, `${activeGroups.length} ta faol guruh`, '', '#/contracts') : A.stat('Faol guruhlar', mine.length, '', '', '#/groups')}
          ${dash.debt ? A.stat('Jami qarzdorlik', A.money(dash.debt.total), `${dash.debt.count} ta qarzdor`, 'danger', '#/debtors') : ''}
          ${sm ? A.stat('Shu oy KPI (hisoblangan)', A.money(sm.kpi), `${sm.rows} ta dars qatori${sm.no_freq ? ` · ${sm.no_freq} tasi hisoblanmagan` : ''}`) : ''}
          ${sm ? A.stat('Besabab kelmaganlar', sm.absent, "shu oyda · «Darsni yetkazdim» so'rovi", sm.absent ? 'warn' : '', '#/attendance?tab=absent') : ''}
        </div>
        ${schedHTML(dash.sched)}
`;
    },
  });

  /* ===================================================== AI yordamchi (M9) */
  // Savol + view'lar sxemasi → LLM → SQL → server tekshiradi va bajaradi. Natija faqat shu ekranda; LLM'ga ma'lumot bormaydi.
  A.ui.chat = A.ui.chat || [];
  let ai = null;
  const RAW_COLS = /(^|_)(id|year|month|ym|number|phone1|phone2|phone)$/;
  A.page('ai', {
    title: 'AI yordamchi',
    section: 'ai',
    async load() {
      if (!ai || A.ui.aiStale) {
        ai = await A.http.get('/ai/');
        A.ui.aiStale = false;
      }
    },
    render() {
      const busy = A.ui.chat.some((m) => m.pending);
      const hist = ai.history || [];
      return `${A.head('AI yordamchi', `Faqat Bosh menejer uchun · bugun ${ai.used}/${ai.limit} so'rov`)}
        ${ai.configured ? '' : `<div class="alert warn">${A.icon('alert')}<div><b>AI hali sozlanmagan.</b> Serverda <code>bash /srv/codial-test/deploy/set-ai.sh</code> ni ishga tushirib, Gemini API kalitini kiriting.</div></div>`}
        <div class="alert info">${A.icon('sparkle')}<div>Gemini'ga faqat <b>savolingiz</b> va jadvallar <b>tuzilmasi</b> boradi. Natija (ismlar, telefonlar, summalar) faqat shu ekranda ko'rinadi. «Tahlil» tugmasida shaxsiy ma'lumotsiz yig'ma raqamlar yuboriladi. <span class="muted">Savolga talaba ismini yozsangiz, savol matni Gemini'ga boradi.</span></div></div>
        <div class="settings tree-layout ai-layout">
          <section class="card ai-hist"><h2>Oxirgi savollar</h2>${hist.length ? hist.map((h) => `<a class="ai-h" data-act="ai-rerun" data-id="${h.id}" title="Qayta bajarish (limitga kirmaydi)">
            <span>${esc(h.question)}</span><small class="muted">${A.fdate(h.created_at.slice(0, 10))} · ${h.status === 'ok' ? `${h.row_count} qator` : "natija yo'q"}</small></a>`).join('') : '<div class="muted small">Hali savol berilmagan</div>'}</section>
          <div class="settings-body">
            <div class="chat" id="chat">${A.ui.chat.map(msgHTML).join('') || '<div class="muted pad">Savol bering yoki quyidagi namunalardan birini tanlang.</div>'}</div>
            <div class="chips sugg">${(ai.examples || []).map((s) => `<button class="chip" data-act="ai-ask" data-id="${esc(s)}" ${busy || !ai.configured ? 'disabled' : ''}>${esc(s)}</button>`).join('')}</div>
            <form class="chat-input" id="chat-form"><input class="f-input grow" id="chat-q" maxlength="1000" placeholder="Masalan: O'tgan oyda Instagram'dan kelgan lidlar konversiyasi qancha?" ${busy ? 'disabled' : ''}><button class="btn primary" ${busy || !ai.configured ? 'disabled' : ''}>Yuborish</button></form>
          </div>
        </div>`;
    },
    mount() {
      document.getElementById('chat-form').onsubmit = (e) => {
        e.preventDefault();
        const q = document.getElementById('chat-q').value.trim();
        if (q && ai.configured) ask(q);
      };
      const c = document.getElementById('chat');
      c.scrollTop = c.scrollHeight;
    },
  });
  function cell(col, v) {
    if (v === null || v === undefined) return '<span class="muted">—</span>';
    if (typeof v === 'number' && !RAW_COLS.test(col)) return A.num(v);
    return esc(String(v));
  }
  function chartOf(r) {
    const ch = r.chart || {};
    if (!ch.type || ch.type === 'none' || !r.rows.length || r.rows.length > 60) return '';
    const xi = r.columns.indexOf(ch.x);
    const ys = (ch.y || []).map((y) => r.columns.indexOf(y)).filter((i) => i >= 0);
    if (xi < 0 || !ys.length) return '';
    const labels = r.rows.map((row) => String(row[xi] ?? '—'));
    const round = ch.type === 'pie' || ch.type === 'doughnut';
    const datasets = (round ? ys.slice(0, 1) : ys).map((i, k) => ({
      label: r.columns[i],
      data: r.rows.map((row) => Number(row[i]) || 0),
      backgroundColor: round ? A.PALETTE : A.PALETTE[k % A.PALETTE.length],
      borderColor: A.PALETTE[k % A.PALETTE.length],
      tension: 0.25,
    }));
    return A.chart({ type: ch.type, data: { labels, datasets }, options: { plugins: { legend: { display: datasets.length > 1 || round } } } }, round ? 240 : 260);
  }
  function resultHTML(r) {
    const sql = r.sql
      ? `<details><summary class="small muted">SQL (server tekshirdi: faqat o'qish, faqat analytics_* view'lar${r.ms ? ` · ${r.ms.db} ms` : ''})</summary><pre class="sql">${esc(r.sql)}</pre></details>`
      : '';
    if (r.status === 'no_sql') return `<p>${esc(r.note || "Bu savolga ma'lumotlardan javob topilmadi. Savolni boshqacha yozib ko'ring.")}</p>`;
    if (r.status !== 'ok') return `<div class="alert warn">${A.icon('alert')}<div>${esc(r.error || 'Xatolik')}</div></div>${sql}`;
    const cols = r.columns.map((c, i) => ({ h: c, f: (row) => cell(c, row[i]), cls: r.rows.some((row) => typeof row[i] === 'number') && !RAW_COLS.test(c) ? 'num' : '' }));
    const one = r.rows.length === 1 && r.columns.length === 1;
    if (!r.rows.length) {
      // Bo'sh natija: server sababini aytadi (ma'lumot hali yo'q, shartga mos yozuv yo'q, kurs narxi kiritilmagan…)
      const why = (r.explain || []).map((x) => `<li>${esc(x)}</li>`).join('');
      return `${r.title ? `<p><b>${esc(r.title)}</b></p>` : ''}${r.note ? `<p class="muted small">${esc(r.note)}</p>` : ''}
        <div class="alert info">${A.icon('alert')}<div><b>Savolga mos ma'lumot topilmadi.</b>${why ? `<ul class="ai-why">${why}</ul>` : ' Savolni boshqacha yozib ko\'ring yoki davrni o\'zgartiring.'}</div></div>${sql}`;
    }
    const tools = r.analysis || r.analyzing ? '' : `<button class="btn sm" data-act="ai-analyze" data-id="${r.id}" ${ai.configured ? '' : 'disabled'}>${A.icon('sparkle')} Tahlil</button>`;
    return `${r.title ? `<p><b>${esc(r.title)}</b></p>` : ''}${r.note ? `<p class="muted small">${esc(r.note)}</p>` : ''}
      ${one ? `<p class="ai-big">${cell(r.columns[0], r.rows[0][0])}</p>` : `${chartOf(r)}${A.table(cols, r.rows, { empty: "Natija bo'sh" })}`}
      <p class="muted small">${r.rows.length} qator${r.truncated ? ` · birinchi ${r.rows.length} tasi ko'rsatildi` : ''}</p>
      ${r.analysis ? `<div class="alert info">${A.icon('sparkle')}<div><b>Tahlil${r.aggregated ? " (faqat yig'ma raqamlar asosida)" : ''}:</b> ${esc(r.analysis)}</div></div>` : ''}
      <div class="row gap">${tools}${r.analyzing ? '<span class="muted small">Tahlil qilinmoqda…</span>' : ''}
        <button class="btn sm ghost" data-act="ai-csv" data-id="${r.id}">CSV yuklash</button></div>${sql}`;
  }
  function msgHTML(m) {
    if (m.role === 'user') return `<div class="msg user">${esc(m.text)}</div>`;
    if (m.pending) return '<div class="msg bot"><span class="muted">⏳ Savol tahlil qilinmoqda va SQL tekshirilmoqda…</span></div>';
    return `<div class="msg bot">${resultHTML(m.r)}</div>`;
  }
  const findMsg = (id) => A.ui.chat.find((m) => m.r && String(m.r.id) === String(id));
  async function send(text, call) {
    const m = { role: 'bot', pending: true };
    A.ui.chat.push({ role: 'user', text }, m);
    A.refresh();
    try {
      m.r = await call();
    } catch (e) {
      m.r = { status: 'error', error: e.message };
    }
    m.pending = false;
    A.ui.aiStale = true;
    A.refresh();
  }
  const ask = (q) => send(q, () => A.http.post('/ai/ask/', { question: q }));
  A.act['ai-ask'] = (el) => ask(el.dataset.id);
  A.act['ai-rerun'] = (el) => {
    const h = (ai.history || []).find((x) => String(x.id) === el.dataset.id);
    return send(h ? h.question : '…', () => A.http.post(`/ai/${el.dataset.id}/run/`));
  };
  A.act['ai-analyze'] = async (el) => {
    const m = findMsg(el.dataset.id);
    if (!m) return;
    m.r.analyzing = true;
    A.refresh();
    try {
      const a = await A.http.post(`/ai/${el.dataset.id}/analyze/`);
      Object.assign(m.r, { analysis: a.analysis, aggregated: a.aggregated_only });
    } catch (e) {
      A.toast(e.message, 'warn');
    }
    m.r.analyzing = false;
    A.ui.aiStale = true;
    A.refresh();
  };
  A.act['ai-csv'] = (el) => {
    const m = findMsg(el.dataset.id);
    if (!m) return;
    const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const csv = [m.r.columns.map(q).join(';'), ...m.r.rows.map((row) => row.map(q).join(';'))].join('\r\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }));
    a.download = `ai-${el.dataset.id}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
})(window.App);

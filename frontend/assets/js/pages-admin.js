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
  CRUD.times = {
    coll: 'lessonTimes', title: 'Dars vaqtlari', deletable: true,
    note: "Nofaol dars vaqti yangi guruh va lid formalarida chiqmaydi. Guruh yoki lidda ishlatilganini o'chirib bo'lmaydi — faqat nofaol qilinadi.",
    label: (r) => `${r.start} - ${r.end}`,
    cols: [{ h: 'Vaqt', f: (r) => `<b>${r.start} - ${r.end}</b>` }, { h: 'Status', f: statusBadge }],
    fields: [
      { name: 'start', label: 'Boshlanish vaqti', type: 'time', required: true, onChange: (x) => { if (x.start) { const [h, m] = x.start.split(':').map(Number); x.end = `${String((h + 2) % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`; } } },
      { name: 'end', label: 'Tugash vaqti', type: 'time', required: true, show: (x) => x.start, help: 'Standart: boshlanish + 2 soat' },
      { ...STATUS_FIELD, show: (x) => x.start },
    ],
    extra: () => ({ branch: B() }),
  };
  CRUD.branches = {
    coll: 'branches', title: 'Filiallar', topOnly: true,
    note: "Faol filial bitta bo'lsa, u hamma joyda avtomatik tanlanadi va filial maydoni ko'rinmaydi. Filiallarni faqat Admin va Bosh menejer o'zgartiradi.",
    cols: [{ h: 'Nomi', f: (r) => `<b>${esc(r.name)}</b>` }, { h: "Naqd g'azna (standart)", f: (r) => esc(A.accName(r.default_cashbox)) }, { h: "Naqdsiz g'azna", f: (r) => esc(A.accName(r.noncash_cashbox)) }, { h: 'Status', f: statusBadge }],
    fields: [
      { name: 'name', label: 'Nomi', required: true },
      { name: 'default_cashbox', label: "Standart g'azna", type: 'select', options: () => A.optList('accounts') },
      { name: 'noncash_cashbox', label: "Naqdsiz to'lovlar g'aznasi", type: 'select', options: () => A.optList('accounts'), help: "AppSheet'da «cb4963b4» deb qattiq yozilgan edi" },
      STATUS_FIELD,
    ],
    save: async (x, rec) => {
      const data = { ...x, default_cashbox: x.default_cashbox || null, noncash_cashbox: x.noncash_cashbox || null };
      if (rec) await A.update('branches', rec.id, data);
      else await A.create('branches', data);
    },
  };
  const ACC_ROLES = ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'];
  CRUD.accounts = {
    coll: 'accounts', title: "G'aznalar", section: 'accounts',
    note: "G'azna balansi va pul harakatlari jurnali M4 bosqichida ulanadi. Mas'ullarni faqat Admin va Bosh menejer o'zgartiradi.",
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
      else if (tab === 'rates') body = `<h2>KPI stavkalari</h2><p>KPI stavkalari «Oyliklar» bo'limida boshqariladi. Bu bo'lim M5 bosqichida serverga ulanadi.</p>`;
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

  /* ===================================================== Bosh sahifa (M1) */
  const PLAN = [
    ['M1', "Asos: kirish, rollar va ruxsatlar, Sozlamalar, Audit tarixi", true],
    ['M2', 'Lidlar, talabalar, ota-onalar', true],
    ['M3', "Guruhlar, shartnomalar, davomat, qarz va KPI hisobi", true],
    ['M4', "To'lovlar, g'aznalar, o'tkazmalar, xarajatlar, kreditorlar", true],
    ['M5', 'Oyliklar va KPI stavkalari', true],
    ['M6', "Ustozni baholash, ota-onalar bilan aloqa, Excel", true],
    ['M7', 'Bosh sahifa statistikasi, foyda, guruhlar tahlili', true],
    ['M8', "Telegram bot: xabarlar va kunlik hisobot", true],
    ['M10', "AppSheet'dan ma'lumotlarni ko'chirish"],
    ['M11', 'Haqiqiy ishga tushirish'],
  ];
  let dash = {};
  A.page('dashboard', {
    title: 'Bosh sahifa',
    section: 'dashboard',
    async load() {
      const get = (ok, path) => (ok ? A.http.get(path) : Promise.resolve(null));
      const [, debt, contracts, summary, pays] = await Promise.all([
        A.reloadGroups(),
        get(A.can('debtors'), '/debtors/'),
        get(A.can('contracts'), '/contracts/?page_size=1'),
        get(A.isTeacherRole(), '/attendance/summary/'),
        get(A.can('payments'), '/payments/summary/'),
        A.can('accounts') ? A.reloadMoney() : null,
        A.reloadPending(),
      ]);
      dash = { debt, counts: contracts ? contracts.counts : null, summary, pays };
    },
    render() {
      const me = A.me();
      const today = A.today();
      const activeGroups = A.rows('groups').filter((g) => g.status === 'Faol');
      const mine = A.isTeacherRole() ? activeGroups.filter((g) => g.teacher === me.id || g.supporter === me.id) : activeGroups;
      const notTaken = mine.filter((g) => A.hasLesson(g, today) && !A.attendanceTaken(g.id, today));
      const sm = dash.summary;
      const ym = A.ym(A.today());
      const [y, m] = ym.split('-').map(Number);
      const unapproved = A.rows('dayPatterns').filter(isActive).filter((p) => !A.rows('lessonFreqs').some((f) => f.pattern === p.id && f.year === y && f.month === m && f.status === 'Tasdiqlangan'));
      return `${A.head(`Assalomu alaykum, ${esc(me.full_name.split(' ')[0])}!`, `${A.WD_FULL[A.isoWeekday(A.today())]}, ${A.fdate(A.today())} · ${esc(A.ROLES[me.role])}`)}
        ${unapproved.length && A.can('settings') ? `<div class="alert warn">${A.icon('alert')}<div><b>${A.ymLabel(ym)} uchun oydagi dars soni tasdiqlanmagan:</b> ${unapproved.map((p) => esc(p.name)).join(', ')}. <a href="#/settings?tab=freq">Tekshirish va tasdiqlash →</a></div></div>` : ''}
        ${notTaken.length && A.can('attendance') ? `<div class="alert info">${A.icon('check')}<div><b>Bugun davomati olinmagan guruhlar (${notTaken.length}):</b> ${notTaken
          .map((g) => `<a href="#/attendance?tab=take&group=${g.id}">${esc(A.groupName(g))}</a> <span class="muted">(${A.timeName(g.time)}, ${esc(A.userName(g.teacher))})</span>`).join(' · ')}</div></div>` : ''}
        <div class="stats">
          ${dash.pays ? A.stat("Bugungi to'lovlar", A.money(Number(dash.pays.cash) + Number(dash.pays.noncash)), `Naqd: ${A.num(dash.pays.cash)} · Naqdsiz: ${A.num(dash.pays.noncash)}`, '', '#/payments') : ''}
          ${dash.pays ? A.stat('Shu oy tushum', A.money(dash.pays.month), A.ymLabel(A.ym(today)), '', '#/payments') : ''}
          ${A.can('approvals') ? A.stat('Tasdiq kutmoqda', A.pendingCount(), A.pendingCount() ? 'sizning tasdiqingiz kerak' : 'hammasi tasdiqlangan', A.pendingCount() ? 'warn' : '', '#/approvals') : ''}
          ${dash.counts ? A.stat('Faol talabalar', dash.counts.Faol, `${activeGroups.length} ta faol guruh`, '', '#/contracts') : A.stat('Faol guruhlar', mine.length, '', '', '#/groups')}
          ${dash.debt ? A.stat('Jami qarzdorlik', A.money(dash.debt.total), `${dash.debt.count} ta qarzdor`, 'danger', '#/debtors') : ''}
          ${sm ? A.stat('Shu oy KPI (hisoblangan)', A.money(sm.kpi), `${sm.rows} ta dars qatori${sm.no_freq ? ` · ${sm.no_freq} tasi hisoblanmagan` : ''}`) : ''}
          ${sm ? A.stat('Besabab kelmaganlar', sm.absent, "shu oyda · «Darsni yetkazdim» so'rovi", sm.absent ? 'warn' : '', '#/attendance?tab=absent') : ''}
        </div>
        <div class="stats">
          ${A.stat('Faol kurslar', A.rows('courses').filter(isActive).length, '', '', A.can('settings') ? '#/settings?tab=courses' : '')}
          ${A.stat('Xodimlar', A.S.users.filter((u) => u.status === 'Faol').length, 'faol', '', A.can('settings') ? '#/settings?tab=users' : '')}
          ${A.stat('Xonalar', A.rows('rooms').filter(isActive).length)}
          ${A.stat("G'aznalar", A.rows('accounts').filter(isActive).length)}
        </div>
        ${A.can('accounts') ? `<section class="card"><h2>G'azna qoldiqlari</h2>${A.rows('accounts').filter((a) => a.status === 'Faol' && a.balance !== null)
          .map((a) => `<a class="acc-row" href="#/accounts/${a.id}"><span>${A.icon('safe')} ${esc(a.name)} <small class="muted">${A.CASH[a.cash_type]}</small></span><b>${A.money(a.balance)}</b>${Number(a.pending) ? `<small class="muted">tasdiqlanmagan: ${A.num(a.pending)}</small>` : ''}</a>`)
          .join('') || A.empty("G'azna yo'q")}</section>` : ''}
        ${activeGroups.length ? `<section class="card"><div class="row between"><h2>Faol guruhlar to'lishi</h2>${A.isManager() ? '<a href="#/stats">Statistika →</a>' : ''}</div>${A.sortBy(activeGroups, (g) => A.groupFill(g).pct, true)
          .map((g) => { const f = A.groupFill(g); return `<div class="fill-row"><a href="#/groups/${g.id}" class="t-${f.cls}">${esc(A.groupName(g))}</a><div class="bar"><i class="bg-${f.cls}" style="width:${Math.min(100, f.pct * 100)}%"></i></div><span class="muted">${f.n}/${f.cap}</span></div>`; })
          .join('')}</section>` : ''}
        <section class="card"><h2>Tizimni ishga tushirish bosqichlari</h2>
          <p class="muted small">Bo'limlar bosqichma-bosqich serverga ulanadi. Menyudagi xira bo'limlar keyingi bosqichlarda ishlaydi.</p>
          ${A.table([{ h: 'Bosqich', f: (r) => `<b>${r[0]}</b>` }, { h: 'Nima', f: (r) => esc(r[1]) }, { h: 'Holat', f: (r) => (r[2] ? A.badge('ishlayapti', 'green') : A.badge('tez orada', 'gray')) }], PLAN)}
        </section>`;
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

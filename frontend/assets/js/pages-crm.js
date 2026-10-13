/* Bosh sahifa, Lidlar, Talabalar, Shartnomalar, Qarzdorlar */
(function (A) {
  const esc = A.esc;

  /* ===================================================== Bosh sahifa */
  A.page('dashboard', {
    title: 'Bosh sahifa',
    section: 'dashboard',
    render() {
      const me = A.me();
      const today = A.today();
      const ym = A.ym(today);
      if (A.isTeacherRole()) return teacherDash(me, today, ym);

      const pays = A.vis('payments');
      const todayPays = pays.filter((p) => p.date === today);
      const cash = A.sum(todayPays.filter((p) => p.cash_type === 'CASH'), 'amount');
      const noncash = A.sum(todayPays.filter((p) => p.cash_type !== 'CASH'), 'amount');
      const contracts = A.vis('contracts');
      const debtors = contracts.filter((c) => A.debtOf(c.id) > 0);
      const totalDebt = A.sum(debtors, (c) => A.debtOf(c.id));
      const active = contracts.filter((c) => A.contractStatus(c) === 'Faol');
      const groups = A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol');
      const taklif = A.rows('lessonFreqs').filter((f) => f.status === 'Taklif' && `${f.year}-${String(f.month).padStart(2, '0')}` === ym);
      const lessonsToday = A.vis('groups').filter((g) => A.hasLesson(g, today));
      const notTaken = lessonsToday.filter((g) => !A.attendanceTaken(g.id, today));
      const pc = A.pendingCount();
      const monthPays = A.sum(pays.filter((p) => A.ym(p.date) === ym), 'amount');
      const newLeads = A.vis('leads').filter((l) => A.ym(A.iso(new Date(l.created_at))) === ym).length;

      let warn = '';
      if (taklif.length) {
        warn += `<div class="alert warn">${A.icon('alert')}<div><b>${A.ymLabel(ym)} uchun oydagi dars soni tasdiqlanmagan:</b> ${taklif.map((f) => A.patternName(f.pattern)).join(', ')}.
          Bu guruhlar uchun talaba qarzi va KPI hisoblanmayapti. ${A.canApproveFreq() ? `<a href="#/settings?tab=freq">Tekshirish va tasdiqlash →</a>` : ''}</div></div>`;
      }
      if (notTaken.length && A.can('attendance')) {
        warn += `<div class="alert info">${A.icon('check')}<div><b>Bugun davomati olinmagan guruhlar (${notTaken.length}):</b> ${notTaken
          .map((g) => `<a href="#/attendance?tab=take&group=${g.id}">${esc(A.groupName(g))}</a> <span class="muted">(${A.timeName(g.time)}, ${esc(A.userName(g.teacher))})</span>`)
          .join(' · ')}</div></div>`;
      }

      const accounts = A.can('accounts') ? A.rows('accounts').filter((a) => a.status === 'Faol') : [];
      const fillGroups = A.sortBy(groups, (g) => A.groupFill(g).pct, true);

      // Oxirgi 6 oy to'lovlari va xarajatlari
      const months = [];
      for (let i = 5; i >= 0; i--) months.push(A.addMonths(ym, -i));
      const payByM = months.map((m) => A.sum(pays.filter((p) => A.ym(p.date) === m), 'amount'));
      const expByM = months.map((m) => A.sum(A.vis('expenses').filter((e) => A.ym(e.date) === m), (e) => e.quantity * e.price));
      const leadsByM = months.map((m) => A.vis('leads').filter((l) => A.ym(A.iso(new Date(l.created_at))) === m).length);

      return `
        ${A.head(`Assalomu alaykum, ${esc(me.full_name.split(' ')[0])}!`, `${A.WD_FULL[A.isoWeekday(today)]}, ${A.fdate(today)} · ${esc(A.ROLES[me.role])}`)}
        ${warn}
        <div class="stats">
          ${A.can('payments') ? A.stat("Bugungi to'lovlar", A.money(cash + noncash), `Naqd: ${A.num(cash)} · Naqdsiz: ${A.num(noncash)}`, '', '#/payments') : ''}
          ${A.can('payments') ? A.stat('Shu oy tushum', A.money(monthPays), A.ymLabel(ym), '', '#/payments') : ''}
          ${A.can('debtors') ? A.stat('Jami qarzdorlik', A.money(totalDebt), `${debtors.length} ta qarzdor`, 'danger', '#/debtors') : ''}
          ${A.stat('Faol talabalar', active.length, `${groups.length} ta faol guruh`, '', '#/contracts')}
          ${A.stat('Yangi lidlar', newLeads, 'shu oyda', '', '#/leads')}
          ${A.can('approvals') ? A.stat('Tasdiq kutmoqda', pc, pc ? 'sizning tasdiqingiz kerak' : 'hammasi tasdiqlangan', pc ? 'warn' : '', '#/approvals') : ''}
        </div>
        <div class="grid-2">
          ${accounts.length ? `<section class="card"><h2>G'azna qoldiqlari</h2>${accounts
            .map((a) => {
              const p = A.pendingOf(a.id);
              return `<a class="acc-row" href="#/accounts/${a.id}"><span>${A.icon('safe')} ${esc(a.name)} <small class="muted">${A.CASH[a.cash_type]}</small></span><b>${A.money(A.balance(a.id))}</b>${p ? `<small class="muted">tasdiqlanmagan: ${A.num(p)}</small>` : ''}</a>`;
            })
            .join('')}</section>` : ''}
          <section class="card"><h2>Faol guruhlar to'lishi</h2>${fillGroups
            .map((g) => {
              const f = A.groupFill(g);
              return `<div class="fill-row"><a href="#/groups/${g.id}" class="t-${f.cls}">${esc(A.groupName(g))}</a><div class="bar"><i class="bg-${f.cls}" style="width:${Math.min(100, f.pct * 100)}%"></i></div><span class="muted">${f.n}/${f.cap}</span></div>`;
            })
            .join('') || A.empty("Faol guruh yo'q")}</section>
        </div>
        ${A.can('payments') ? `<section class="card"><h2>Oyma-oy: tushum va xarajat</h2>
          <p class="muted small">Tizim 01.09.2026 da ishga tushgan (AppSheet'dan import), shuning uchun avvalgi oylar bo'sh.</p>
          ${A.chart({ type: 'bar', data: { labels: months.map(A.ymLabel), datasets: [{ label: "To'lovlar", data: payByM, backgroundColor: A.PALETTE[0] }, { label: 'Xarajatlar', data: expByM, backgroundColor: A.PALETTE[1] }] } })}</section>` : ''}
        <section class="card"><h2>Yangi lidlar</h2>${A.chart({ type: 'line', data: { labels: months.map(A.ymLabel), datasets: [{ label: 'Lidlar', data: leadsByM, borderColor: A.PALETTE[0], backgroundColor: 'rgba(242,106,27,.15)', fill: true, tension: 0.3 }] } }, 200)}</section>
      `;
    },
  });

  function teacherDash(me, today, ym) {
    const groups = A.vis('groups');
    const todays = groups.filter((g) => A.hasLesson(g, today));
    const att = A.rows('attendance').filter((a) => A.ym(a.date) === ym);
    const myT = att.filter((a) => a.teacher === me.id);
    const myS = att.filter((a) => a.supporter === me.id);
    const kpi = A.sum(myT, 'tkpi') + A.sum(myS, 'skpi');
    const absentees = A.vis('attendance').filter((a) => a.status === 'X' && A.ym(a.date) === ym && (a.teacher === me.id || a.supporter === me.id));
    const mk = A.rows('makeups').filter((m) => m.teacher === me.id);
    const pendingFreq = att.filter((a) => (a.teacher === me.id || a.supporter === me.id) && a.no_freq).length;
    return `
      ${A.head(`Assalomu alaykum, ${esc(me.full_name.split(' ')[0])}!`, `${A.WD_FULL[A.isoWeekday(today)]}, ${A.fdate(today)} · ${esc(A.ROLES[me.role])}`)}
      ${pendingFreq ? `<div class="alert warn">${A.icon('alert')}<div>Shu oyning ${pendingFreq} ta dars qatori uchun oydagi dars soni hali tasdiqlanmagan — KPI tasdiqlangandan keyin hisoblanadi.</div></div>` : ''}
      <section class="card"><h2>Bugungi darslarim</h2>
        ${todays.length ? todays
          .map((g) => {
            const taken = A.attendanceTaken(g.id, today);
            const isTeacher = g.teacher === me.id;
            return `<div class="lesson-row"><div><b>${esc(A.groupName(g))}</b><div class="muted small">${A.timeName(g.time)} · ${esc(A.roomName(g.room))} · ${A.activeContractsOf(g.id).length} talaba${isTeacher ? '' : ' · siz yordamchisiz'}</div></div>
              ${taken ? A.badge('Davomat olingan', 'green') : isTeacher ? `<a class="btn primary" href="#/attendance?tab=take&group=${g.id}">${A.icon('check')}Davomat olish</a>` : A.badge('Davomatni ustoz oladi', 'gray')}</div>`;
          })
          .join('') : A.empty('Bugun darsingiz yo\'q')}
      </section>
      <div class="stats">
        ${A.stat('Shu oy KPI (hisoblangan)', A.money(kpi), `${myT.length + myS.length} ta dars qatori`, '', '#/salaries?tab=kpi')}
        ${A.stat('Guruhlarim', groups.length, groups.map((g) => A.groupName(g)).join(', '), '', '#/groups')}
        ${A.stat('Besabab kelmaganlar', absentees.length, 'shu oyda', absentees.length ? 'warn' : '', '#/attendance?tab=absent')}
        ${A.stat("Yetkazilgan dars so'rovlari", mk.filter((m) => m.status === 'Kutilmoqda').length, 'kutilmoqda', '', '#/attendance?tab=makeup')}
      </div>`;
  }

  /* ===================================================== Lidlar (server API: /leads/, /leads/board/, /leads/stats/) */
  const LS = A.LEAD_STATUSES;
  const leadStatusTone = { 1: 'gray', 2: 'blue', 3: 'orange', 4: 'orange', 5: 'green', 6: 'red', 7: 'red', 8: 'gray' };
  const keepStudent = (l) => l && l.student_data && A.putLocal('students', l.student_data);
  const leadFilters = () => {
    const qs = new URLSearchParams();
    for (const k of ['search', 'course', 'source']) if (A.q('leads:' + k, '')) qs.set(k, A.q('leads:' + k));
    return qs;
  };
  let leadData = {};

  A.page('leads', {
    title: 'Lidlar',
    section: 'leads',
    async load(p, q) {
      const tab = q.tab || 'funnel';
      const qs = leadFilters();
      if (tab === 'funnel') {
        leadData = await A.http.get('/leads/board/?' + qs);
        Object.values(leadData.columns).flat().forEach(keepStudent);
      } else if (tab === 'list') {
        qs.set('page', A.q('leads:page', 1));
        leadData = await A.http.get('/leads/?' + qs);
        leadData.results.forEach(keepStudent);
      } else if (tab === 'stats') leadData = await A.http.get('/leads/stats/?' + qs);
    },
    render(p, q) {
      const tab = q.tab || 'funnel';
      const actions = A.can('leads', 'a') ? A.btn('Yangi lid', 'lead-new', { icon: 'plus' }) : '';
      let body = '';
      if (tab === 'funnel') body = funnel(leadData);
      else if (tab === 'list') body = leadTable(leadData.results) + pager(leadData);
      else if (tab === 'stats') body = leadStats(leadData);
      else body = `<div class="empty">Talabasi to'lov qilgan lidlar «To'lovlar» bo'limi bilan birga (M4 bosqichida) ulanadi.</div>`;
      return `${A.head('Lidlar', 'Murojaatlar voronkasi: birinchi qo\'ng\'iroqdan shartnomagacha', actions)}
        ${A.tabs([['funnel', 'Voronka', tab === 'funnel' ? leadData.total : undefined], ['list', "Ro'yxat"], ['stats', 'Statistika'], ['paid', "To'lov qilganlar"]], tab, 'leads')}
        ${tab === 'paid' ? '' : A.filterBar('leads', [A.fSearch('leads', 'Ism yoki telefon…'), A.fSelect('leads', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('leads', 'source', A.optList('leadSources'), 'Barcha manbalar')])}
        <div>${body}</div>`;
    },
  });
  document.addEventListener('input', (e) => {
    if (e.target.closest('[data-filter^="leads:"]')) A.ui.q['leads:page'] = 1;
  }, true);
  A.act['leads-page'] = (el) => {
    A.ui.q['leads:page'] = Number(el.dataset.id);
    A.refresh();
  };
  const pager = (d) =>
    d.pages > 1
      ? `<div class="row gap pager"><button class="btn sm ghost" data-act="leads-page" data-id="${d.page - 1}" ${d.page <= 1 ? 'disabled' : ''}>← Oldingi</button><span class="muted small">${d.page} / ${d.pages} · jami ${d.count}</span><button class="btn sm ghost" data-act="leads-page" data-id="${d.page + 1}" ${d.page >= d.pages ? 'disabled' : ''}>Keyingi →</button></div>`
      : '';

  function contractStatusOf(l) {
    const has = l.has_contract;
    const tone = has ? 'green' : l.status === '5' ? 'red' : 'orange';
    return `<span class="t-${tone}">${has ? 'Tuzilgan' : 'Tuzilmagan'}</span>`;
  }

  function funnel(b) {
    const cols = Object.keys(LS).map((k) => {
      const list = b.columns[k] || [];
      const n = b.counts[k] || 0;
      return `<div class="kcol"><div class="kcol-h"><span class="badge ${leadStatusTone[k]}">${k}</span> ${esc(LS[k])} <b>${n}</b></div>
        ${list
          .map((l) => {
            const st = l.student_data;
            return `<button class="kcard" data-act="lead-open" data-id="${l.id}">
              <b>${esc(st.first_name)} ${esc(st.last_name)}</b>
              <span class="muted small">${esc(A.courseName(l.course))} · ${esc(A.sourceName(l.source))}</span>
              ${l.demo_date && ['3', '4'].includes(l.status) ? `<span class="small">Sinov: ${A.fdate(l.demo_date)}</span>` : ''}
              ${l.status === '5' || l.has_contract ? `<span class="small">Shartnoma: ${contractStatusOf(l)}</span>` : ''}
            </button>`;
          })
          .join('') || '<div class="muted small pad">—</div>'}
        ${n > list.length ? `<div class="muted small pad">… yana ${n - list.length} ta («Ro'yxat» tabida)</div>` : ''}
      </div>`;
    });
    const conv = `<div class="conv">${['3', '4', '5']
      .map((k) => `<div><span class="muted small">${k}-bosqichga yetgan (${esc(LS[k]).toLowerCase()})</span><b>${A.pct(b.reached[k])}</b></div>`)
      .join('')}<div><span class="muted small">Lid → shartnoma</span><b>${A.pct(b.contract_rate)}</b></div></div>`;
    return conv + `<div class="kanban">${cols.join('')}</div>`;
  }

  function leadTable(leads) {
    return A.table(
      [
        { h: 'Murojaatchi', f: (l) => `<a href="#" data-act="lead-open" data-id="${l.id}">${esc(l.student_data.full_name)}</a>` },
        { h: 'Telefon', f: (l) => esc(l.student_data.phone1) },
        { h: 'Kurs', f: (l) => esc(A.courseName(l.course)) },
        { h: 'Manba', f: (l) => esc(A.sourceName(l.source)) },
        { h: 'Status', f: (l) => A.badge(`${l.status}. ${LS[l.status]}`, leadStatusTone[l.status]) },
        { h: 'Shartnoma', f: contractStatusOf },
        { h: "Qo'shilgan", f: (l) => A.fdate(A.iso(new Date(l.created_at))) },
      ],
      leads,
      { empty: "Lid topilmadi" },
    );
  }

  function leadStats(s) {
    const months = [...new Set(s.by_month.map((r) => r.month))].sort();
    const ages = Object.keys(s.by_age).sort((a, b) => parseInt(a) - parseInt(b));
    const srcRows = s.by_source.map((r) => ({ name: A.sourceName(r.source), n: r.n, conv: r.contracts, rate: r.n ? r.contracts / r.n : 0 }));
    return `<div class="grid-2">
      <section class="card"><h2>Manba bo'yicha konversiya</h2>${A.table(
        [
          { h: 'Manba', f: (r) => esc(r.name) },
          { h: 'Lidlar', f: (r) => r.n, cls: 'num' },
          { h: 'Shartnoma', f: (r) => r.conv, cls: 'num' },
          { h: 'Konversiya', f: (r) => `<b>${A.pct(r.rate)}</b>`, cls: 'num' },
        ],
        srcRows,
      )}<p class="muted small">Shartnomalar soni M3 bosqichidan keyin hisoblanadi.</p></section>
      <section class="card"><h2>Status bo'yicha</h2>${A.chart({ type: 'doughnut', data: { labels: Object.values(LS), datasets: [{ data: Object.keys(LS).map((k) => s.by_status[k] || 0), backgroundColor: A.PALETTE }] } }, 260)}</section>
      <section class="card"><h2>Oylar bo'yicha yangi lidlar (manba kesimida)</h2>${A.chart({
        type: 'bar',
        data: { labels: months.map(A.ymLabel), datasets: A.rows('leadSources').map((src, i) => ({ label: src.name, data: months.map((m) => A.sum(s.by_month.filter((r) => r.month === m && r.source === src.id), 'n')), backgroundColor: A.PALETTE[i % A.PALETTE.length] })) },
        options: { scales: { x: { stacked: true }, y: { stacked: true } } },
      })}</section>
      <section class="card"><h2>Yosh guruhi va ijtimoiy holat</h2>${A.chart({ type: 'bar', data: { labels: ages, datasets: [{ label: 'Lidlar', data: ages.map((a) => s.by_age[a]), backgroundColor: A.PALETTE[0] }] }, options: { plugins: { legend: { display: false } } } }, 200)}
      ${A.table([{ h: 'Ijtimoiy holat', f: (r) => esc(r[0]) }, { h: 'Soni', f: (r) => r[1], cls: 'num' }], Object.entries(s.by_social))}</section>
    </div>`;
  }

  /* ---- Lid formasi (AppSheet Show_If zanjiri bo'yicha). Tekshiruvlar serverda ham bor ---- */
  A.leadForm = (lead, freeStudents = []) => {
    const isNew = !lead;
    const B = lead ? lead.branch : A.branchIds()[0];
    const v = lead ? { ...lead } : { status: '2', times: [], tags: [], mode: 'new' };
    const phone = (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin. Masalan, 998883322" : '');
    const fields = [
      { name: 'mode', label: 'Murojaatchi', type: 'seg', options: [['new', 'Yangi talaba'], ['old', "Bazadagi talaba"]], show: () => isNew },
      {
        name: 'student', label: 'Talabani tanlang', type: 'select', show: (x) => !isNew || x.mode === 'old', required: true, readonly: () => !isNew,
        options: () => (isNew ? freeStudents : [lead.student_data]).map((s) => [s.id, `${s.full_name} · ${s.phone1}`]),
        help: "Shartnomasi bor yoki lidi ochilgan talabalar ro'yxatda chiqmaydi",
      },
      { name: 'first_name', label: 'Ism', show: (x) => isNew && x.mode === 'new', required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
      { name: 'last_name', label: 'Familiya', show: (x) => isNew && x.mode === 'new' && x.first_name, required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
      { name: 'phone1', label: '1-telefon (+998)', placeholder: '901234567', show: (x) => isNew && x.mode === 'new' && x.last_name, required: true, half: true, validate: phone },
      { name: 'phone2', label: '2-telefon (+998)', placeholder: '911234567', show: (x) => isNew && x.mode === 'new' && x.last_name, required: true, half: true, validate: (t, x) => phone(t) || (t === x.phone1 ? "Ikki bir xil nomer kiritib bo'lmaydi!" : '') },
      { name: 'comment', label: 'Izoh', type: 'textarea', placeholder: "Masalan: narxni so'radi, kechki guruh bo'lsa yoziladi", show: (x) => isNew && (x.student || (x.phone1 && x.phone2)) },
      { name: 'gender', label: 'Jins', type: 'seg', options: ['Erkak', 'Ayol'], show: (x) => isNew && x.mode === 'new' && x.phone1 && x.phone2 },
      { name: 'age_group', label: 'Yosh guruhi', type: 'select', options: ['9-12', '13-15', '16-18', '19-21', '22-24', '25-27', '28-30', '31-33', '34-36', '37-39', '40-42'], show: (x) => x.student || (x.phone1 && x.phone2), half: true },
      { name: 'social', label: 'Ijtimoiy holati', type: 'select', options: ["Maktab o'quvchisi", 'Oliygoh talabasi', 'Kompaniya xodimi', 'Davlat xizmatchisi', 'Vaqtincha ishsiz'], show: (x) => x.age_group, half: true },
      { name: 'laptop', label: 'Noutbuki bormi?', type: 'seg', options: ['Bor', "Yo'q", 'Sotib oladi'], show: (x) => x.social },
      { name: 'tags', label: 'Teglar', type: 'chips', options: ['VIP', "Chegirma so'radi", "Ota-onasi qo'ng'iroq qiladi", 'Kechki vaqt', 'Hafta oxiri'], show: (x) => x.laptop },
      { name: 'source', label: 'Manba', type: 'select', options: (x) => A.optList('leadSources', 'name', (s) => (s.status || 'Faol') === 'Faol' || s.id === x.source), required: true, half: true },
      { name: 'course', label: 'Kurs', type: 'select', options: (x) => A.optList('courses', 'name', (c) => (c.status === 'Faol' && c.branches.includes(B)) || c.id === x.course), required: true, half: true },
      { name: 'pattern', label: 'Hafta kunlari', type: 'seg', options: (x) => A.optList('dayPatterns', 'name', (p) => (p.status || 'Faol') === 'Faol' || p.id === x.pattern) },
      { name: 'times', label: "Ma'qul dars vaqti", type: 'chips', options: (x) => A.optList('lessonTimes', (t) => `${t.start}-${t.end}`, (t) => t.branch === B && ((t.status || 'Faol') === 'Faol' || (x.times || []).includes(t.id))) },
      { name: 'status', label: 'Status', type: 'select', options: Object.entries(LS).map(([k, l]) => [k, `${k}. ${l}`]), required: true },
      { name: 'g', type: 'note', tone: 'info', show: (x) => ['3', '4', '5'].includes(x.status), text: "Guruh va sinov dars kuni guruhlar bo'limi bilan birga (M3 bosqichida) tanlanadi." },
    ];
    A.form({
      title: isNew ? 'Yangi lid' : 'Lidni tahrirlash',
      fields,
      values: v,
      async onSubmit(x) {
        const rec = { source: x.source, course: x.course, pattern: x.pattern || null, times: x.times, status: x.status, age_group: x.age_group, social: x.social, laptop: x.laptop, tags: x.tags };
        let saved;
        if (isNew) {
          const who = x.mode === 'old' ? { mode: 'old', student: x.student } : { mode: 'new', first_name: x.first_name, last_name: x.last_name, phone1: x.phone1, phone2: x.phone2, gender: x.gender };
          saved = await A.http.post('/leads/', { ...rec, ...who, comment: x.comment || '' });
        } else saved = await A.http.patch(`/leads/${lead.id}/`, rec);
        keepStudent(saved);
        A.toast(isNew ? "Lid qo'shildi" : 'Saqlandi');
        A.refresh();
        if (saved.status === '5') setTimeout(() => A.openLead(saved.id), 50);
      },
    });
  };
  A.act['lead-new'] = async () => {
    const free = await A.http.get('/students/?free=1&page_size=200');
    A.leadForm(null, free.results);
  };

  A.openLead = async (id) => {
    const l = await A.http.get(`/leads/${id}/`);
    keepStudent(l);
    const st = l.student_data;
    const edit = A.canEdit('leads', l, 'created_at');
    const canContract = l.status === '5' && !l.has_contract && A.can('contracts', 'a');
    const needsBirth = l.status === '5' && !st.birth_date;
    const m = A.modal({
      title: st.full_name,
      wide: true,
      body: `
        <div class="detail-top">
          ${A.badge(`${l.status}. ${LS[l.status]}`, leadStatusTone[l.status])}
          <span>Shartnoma: ${contractStatusOf(l)}</span>
          ${(l.tags || []).map((t) => A.badge(t, 'gray')).join('')}
        </div>
        ${needsBirth ? `<div class="alert warn">${A.icon('alert')}<div>O'qishni boshladi, lekin talabaning to'liq ma'lumotlari (sharif, tug'ilgan sana, vasiy) kiritilmagan. Avval talaba ma'lumotlarini to'ldiring.</div></div>` : ''}
        <dl class="dl">
          <dt>Telefon</dt><dd><a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ` · <a href="tel:+998${st.phone2}">+998 ${st.phone2}</a>` : ''}</dd>
          <dt>Kurs</dt><dd>${esc(A.courseName(l.course))}</dd>
          <dt>Manba</dt><dd>${esc(A.sourceName(l.source))}</dd>
          <dt>Hafta kunlari / vaqt</dt><dd>${esc(A.patternName(l.pattern))} · ${(l.times || []).map(A.timeName).join(', ') || '—'}</dd>
          <dt>Yosh / holat / noutbuk</dt><dd>${esc(l.age_group || '—')} · ${esc(l.social || '—')} · ${esc(l.laptop || '—')}</dd>
          <dt>Qo'shdi</dt><dd>${esc(A.userName(l.created_by))}, ${A.fdt(l.created_at)}</dd>
        </dl>
        ${A.can('leads', 'e') ? `<h4>Statusni o'zgartirish</h4><div class="seg wrap">${Object.entries(LS)
          .map(([k, t]) => `<button class="${l.status === k ? 'on' : ''}" data-status="${k}" ${edit.ok ? '' : 'disabled'}>${k}. ${esc(t)}</button>`)
          .join('')}</div>${edit.ok ? '' : `<p class="muted small">${esc(edit.why)}</p>`}` : ''}
        <h4>Izohlar (${l.comments.length})</h4>
        ${A.can('leads', 'a') ? `<div class="row gap"><input class="f-input grow" id="lc-text" placeholder="Izoh yozing…"><button class="btn" id="lc-add">Qo'shish</button></div>` : ''}
        <ul class="comments">${l.comments.map((c) => `<li><p>${esc(c.comment)}</p><small class="muted">${esc(A.userName(c.created_by))} · ${A.fdt(c.created_at)}</small></li>`).join('') || '<li class="muted">Izoh yo\'q</li>'}</ul>`,
      footer: `
        ${A.can('leads', 'e') && edit.ok ? `<button class="btn ghost" data-edit>Tahrirlash</button>` : ''}
        ${l.status === '5' && A.can('leads', 'e') ? `<button class="btn" data-student>Talaba ma'lumotlarini to'ldirish</button>` : ''}
        ${canContract ? `<button class="btn primary" disabled title="Shartnomalar bo'limi M3 bosqichida ulanadi">Shartnoma tuzish</button>` : ''}`,
    });
    const reopen = () => { m.close(); A.refresh(); A.openLead(id); };
    const fail = (e) => A.toast(e.message, 'warn');
    m.el.querySelectorAll('[data-status]').forEach((b) =>
      (b.onclick = () => A.http.patch(`/leads/${id}/`, { status: b.dataset.status }).then(reopen, fail)));
    const add = m.el.querySelector('#lc-add');
    if (add)
      add.onclick = () => {
        const t = m.el.querySelector('#lc-text').value.trim();
        if (t) A.http.post(`/leads/${id}/comments/`, { comment: t }).then(reopen, fail);
      };
    const e = m.el.querySelector('[data-edit]');
    if (e) e.onclick = () => { m.close(); A.leadForm(l); };
    const sb = m.el.querySelector('[data-student]');
    if (sb) sb.onclick = () => { m.close(); A.studentForm(st, () => A.openLead(id)); };
  };
  A.act['lead-open'] = (el) => A.openLead(el.dataset.id);

  /* ---- Talaba ma'lumotlarini to'ldirish ---- */
  A.studentForm = async (st, after) => {
    const parents = (await A.http.get('/parents/')).filter((p) => p.branch === st.branch);
    A.form({
      title: "Talaba ma'lumotlari",
      values: { ...st, parent: st.parent || '' },
      fields: [
        { name: 'first_name', label: 'Ism', required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'last_name', label: 'Familiya', required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'phone1', label: '1-telefon (+998)', required: true, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
        { name: 'father_name', label: 'Sharif', required: true, half: true, validate: (t) => (t.includes('.') ? "Nuqta qo'yib bo'lmaydi!" : t.trim().length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'phone2', label: '2-telefon (+998)', half: true, validate: (t, x) => (t === x.phone1 ? "Ikki bir xil nomer kiritib bo'lmaydi!" : !/^\d{9}$/.test(t) ? "9 ta sondan iborat bo'lsin" : '') },
        { name: 'gender', label: 'Jins', type: 'seg', options: ['Erkak', 'Ayol'], half: true },
        { name: 'birth_date', label: "Tug'ilgan sanasi", type: 'date', required: true, half: true },
        { name: 'parent', label: 'Vasiy (ota-ona)', type: 'select', half: true, options: () => parents.map((p) => [p.id, `${p.first_name} ${p.last_name} · ${p.phone}`]), placeholder: "Tanlang yoki bo'sh qoldiring" },
        { name: 'new_parent', label: "Yangi vasiy qo'shish", type: 'checkbox', show: (x) => !x.parent },
        { name: 'p_first', label: 'Vasiy ismi', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, validate: (t) => (t.trim().length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'p_phone', label: 'Vasiy telefoni', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
      ],
      async onSubmit(x) {
        const body = { first_name: x.first_name, last_name: x.last_name, father_name: x.father_name, phone1: x.phone1, phone2: x.phone2 || '', gender: x.gender || '', birth_date: x.birth_date, parent: x.parent || null, new_parent: !!x.new_parent, p_first: x.p_first || '', p_phone: x.p_phone || '' };
        A.putLocal('students', await A.http.patch(`/students/${st.id}/`, body));
        A.toast('Saqlandi');
        A.refresh();
        after && after();
      },
    });
  };

  /* ===================================================== Shartnomalar */
  A.page('contracts', {
    title: 'Shartnomalar',
    section: 'contracts',
    render(p, q) {
      const tab = q.tab || 'Faol';
      const all = A.vis('contracts');
      const cnt = (s) => all.filter((c) => A.contractStatus(c) === s).length;
      const actions = (A.can('contracts', 'a') ? A.btn('Yangi shartnoma', 'contract-new', { icon: 'plus' }) : '') + A.btn('Excel', 'contracts-csv', { cls: 'ghost', icon: 'download' });
      return `${A.head('Shartnomalar', 'Guruhlash: kurs → guruh. Qarzdor talaba nomi qizil', actions)}
        ${A.tabs([['Faol', 'Faol', cnt('Faol')], ['Rejada', 'Rejada', cnt('Rejada')], ['Nofaol', 'Nofaol', cnt('Nofaol')], ['students', 'Talabalar']], tab, 'contracts')}
        ${A.filterBar('contracts', [A.fSearch('contracts', 'Ism, telefon yoki raqam…'), A.fSelect('contracts', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('contracts', 'type', [['Pullik', 'Pullik'], ['Grant', 'Grant']], 'Barcha turlar')])}
        <div data-results>${this.results(p, q)}</div>`;
    },
    results(p, q) {
      const tab = q.tab || 'Faol';
      const s = A.q('contracts:search', ''), course = A.q('contracts:course', ''), type = A.q('contracts:type', '');
      if (tab === 'students') {
        const studs = A.vis('students').filter((st) => A.match(A.studentName(st) + st.phone1, s));
        return A.table(
          [
            { h: 'Talaba', f: (st) => `<a href="#" data-act="student-edit" data-id="${st.id}">${esc(A.studentName(st))}</a>` },
            { h: 'Telefon', f: (st) => esc(st.phone1) },
            { h: "Tug'ilgan", f: (st) => A.fdate(st.birth_date) },
            { h: 'Vasiy', f: (st) => { const pr = A.get('parents', st.parent); return pr ? `${esc(pr.first_name)} · ${esc(pr.phone)}` : '—'; } },
            { h: 'Shartnomalar', f: (st) => A.rows('contracts').filter((c) => c.student === st.id).map((c) => `<a href="#/contracts/${c.id}">№${c.number}</a>`).join(', ') || '—' },
          ],
          A.sortBy(studs, (st) => st.first_name),
        );
      }
      const rows = A.vis('contracts').filter((c) => {
        const st = A.get('students', c.student) || {};
        return A.contractStatus(c) === tab && (!course || c.course === course) && (!type || c.type === type) && A.match(`${A.studentName(st)} ${st.phone1} ${c.number}`, s);
      });
      if (!rows.length) return A.empty("Shartnoma topilmadi");
      const byGroup = A.groupBy(A.sortBy(rows, (c) => A.groupName(c.group)), (c) => c.group);
      return [...byGroup]
        .map(([gid, list]) => {
          const debt = A.sum(list, (c) => Math.max(0, A.debtOf(c.id)));
          return `<section class="group-block"><h3>${esc(A.groupName(gid))} <span class="muted">· ${list.length} ta${debt ? ` · qarz ${A.money(debt)}` : ''}</span></h3>
          ${A.table(
            [
              { h: 'Shartnoma', f: (c) => `<a href="#/contracts/${c.id}" class="${A.debtOf(c.id) > 0 ? 't-red' : ''}">${esc(A.contractName(c))}</a>` },
              { h: 'Turi', f: (c) => (c.type === 'Grant' ? A.badge('Grant', 'blue') : 'Pullik') },
              { h: 'Boshlanish', f: (c) => A.fdate(c.start) },
              { h: 'Tugash', f: (c) => (c.end ? `${A.fdate(c.end)} <span class="muted small">${esc(c.stop_reason)}</span>` : '—') },
              { h: 'Status', f: (c) => A.contractStatusBadge(A.contractStatus(c)) },
              { h: 'Balans', f: (c) => A.moneyCell(A.debtOf(c.id), true), cls: 'num' },
            ],
            A.sortBy(list, (c) => A.contractName(c)),
          )}</section>`;
        })
        .join('');
    },
  });
  A.act['student-edit'] = (el) => A.studentForm(A.get('students', el.dataset.id));
  A.act['contracts-csv'] = () => {
    const rows = A.vis('contracts');
    A.downloadCSV('shartnomalar.csv', [
      ['№', 'Talaba', 'Telefon', 'Kurs', 'Guruh', 'Turi', 'Boshlanish', 'Tugash', 'Status', 'Balans'],
      ...rows.map((c) => [c.number, A.studentName(c.student), (A.get('students', c.student) || {}).phone1, A.courseName(c.course), A.groupName(c.group), c.type, c.start, c.end, A.contractStatus(c), A.debtOf(c.id)]),
    ]);
  };

  A.contractForm = (c, preset = {}) => {
    const isNew = !c;
    const B = A.branchIds()[0];
    const v = c ? { ...c } : { branch: B, type: 'Pullik', start: A.today(), ...preset };
    A.form({
      title: isNew ? 'Yangi shartnoma' : `Shartnoma №${c.number}`,
      values: v,
      fields: [
        { name: 'student', label: 'Talaba', type: 'select', required: true, readonly: () => !isNew, options: () => A.rows('students').filter((s) => s.branch === B).map((s) => [s.id, `${A.studentName(s)} · ${s.phone1}`]), help: isNew ? "Yaratilgandan keyin talabani o'zgartirib bo'lmaydi" : "Talaba o'zgarmaydi" },
        { name: 'course', label: 'Kurs', type: 'select', required: true, resets: ['group'], readonly: () => !isNew && A.role() !== 'ADMIN', options: () => A.optList('courses', 'name', (x) => x.status === 'Faol'), help: isNew ? '' : "Kursni faqat Admin o'zgartiradi" },
        { name: 'group', label: 'Guruh', type: 'select', required: true, show: (x) => x.course, options: (x) => A.rows('groups').filter((g) => g.course === x.course && g.branch === B && A.groupStatus(g) !== 'Nofaol').map((g) => { const f = A.groupFill(g); return [g.id, `${A.groupName(g)} · ${A.patternName(g.pattern)} ${A.timeName(g.time)} · ${f.n}/${f.cap}`]; }) },
        { name: 'type', label: 'Shartnoma turi', type: 'seg', options: ['Pullik', 'Grant'], show: (x) => x.course, readonly: () => !A.isTop(), help: () => (A.isTop() ? '' : "Turini faqat Admin va Bosh menejer o'zgartiradi") },
        { name: 'number', label: 'Shartnoma raqami', type: 'computed', show: (x) => x.type, compute: () => (c ? c.number : Math.max(0, ...A.rows('contracts').filter((y) => y.branch === B).map((y) => y.number)) + 1) + ' (avtomatik)' },
        { name: 'start', label: 'Boshlanish sana', type: 'date', required: true, show: (x) => x.type, half: true },
        { name: 'end', label: 'Tugash sana', type: 'date', show: (x) => x.type && x.start, half: true, validate: (d, x) => (d < x.start ? "Boshlanish sanadan kichik bo'lolmaydi" : '') },
        { name: 'stop_reason', label: "To'xtatish sababi", type: 'select', options: A.STOP_REASONS, show: (x) => x.end, required: (x) => !!x.end },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.type },
      ],
      onSubmit(x) {
        if (isNew && A.rows('contracts').some((y) => y.student === x.student && y.group === x.group && A.contractStatus(y) !== 'Nofaol')) return 'Bu talabaning shu guruhda faol shartnomasi bor';
        const rec = { student: x.student, course: x.course, group: x.group, type: x.type, start: x.start, end: x.end, stop_reason: x.stop_reason, comment: x.comment };
        let id;
        if (isNew) {
          const num = Math.max(0, ...A.rows('contracts').filter((y) => y.branch === B).map((y) => y.number)) + 1;
          id = A.insert('contracts', { ...rec, branch: B, number: num, opening: 0 }, 'Shartnoma', `${A.studentName(x.student)} №${num}`).id;
        } else {
          A.patch('contracts', c.id, rec, 'Shartnoma', A.contractName(c));
          id = c.id;
          if (c.type !== x.type) A.toast(`Turi o'zgardi — ${A.recalc((a) => a.contract === id)} ta davomat qatori qayta hisoblandi`);
        }
        A.recalc((a) => a.contract === id);
        A.save();
        A.toast('Saqlandi');
        if (isNew) A.go('contracts/' + id);
        else A.refresh();
      },
    });
  };
  A.act['contract-new'] = () => A.contractForm(null);

  /* ---- Shartnoma sahifasi ---- */
  A.page('contracts/:id', {
    title: 'Shartnoma',
    section: 'contracts',
    render({ id }, q) {
      const c = A.get('contracts', id);
      if (!c || !A.vis('contracts').includes(c)) return A.head('Shartnoma topilmadi') + A.empty("Shartnoma yo'q yoki sizga ko'rinmaydi");
      const st = A.get('students', c.student);
      const d = A.debts().get(c.id);
      const status = A.contractStatus(c);
      const pays = A.sortBy(A.rows('payments').filter((p) => p.contract === id), (p) => p.date, true);
      const att = A.sortBy(A.rows('attendance').filter((a) => a.contract === id), (a) => a.date, true);
      const lead = A.rows('leads').find((l) => l.student === c.student);
      const edit = A.canEdit('contracts', c, 'start');
      const tab = q.tab || 'pay';
      const parent = A.get('parents', st.parent);
      return `
        <a class="back" href="#/contracts">← Shartnomalar</a>
        ${A.head(A.contractName(c), `${A.contractStatusBadge(status)} ${c.type === 'Grant' ? A.badge('Grant', 'blue') : ''} · ${esc(A.groupName(c.group))}`,
          `${A.can('payments', 'a') ? A.btn("To'lov qilish", 'pay-new', { id: c.id, icon: 'cash' }) : ''}
           ${A.can('contracts', 'e') ? A.btn('Tahrirlash', 'contract-edit', { id: c.id, cls: 'ghost', disabled: !edit.ok, title: edit.why }) : ''}`)}
        <div class="stats">
          ${A.stat('Balans (qarz)', `<span class="${d.balance > 0 ? 't-red' : 't-green'}">${A.money(d.balance)}</span>`, d.balance > 0 ? 'talaba qarzdor' : d.balance < 0 ? 'oldindan to\'langan' : 'qarz yo\'q', d.balance > 0 ? 'danger' : '')}
          ${A.stat('Hisoblangan (darslar)', A.money(d.charged), `${att.filter((a) => a.debt).length} ta dars uchun`)}
          ${A.stat("To'langan", A.money(d.paid), `${pays.length} ta to'lov`)}
          ${A.stat('Chegirmalar', A.money(d.discount))}
        </div>
        <div class="grid-2">
          <section class="card"><h2>Ma'lumotlar</h2><dl class="dl">
            <dt>Talaba</dt><dd>${esc(A.studentName(st))} ${A.can('leads', 'e') ? `<a href="#" data-act="student-edit" data-id="${st.id}" class="small">tahrirlash</a>` : ''}</dd>
            <dt>Telefon</dt><dd><a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ` · <a href="tel:+998${st.phone2}">${st.phone2}</a>` : ''}</dd>
            <dt>Vasiy</dt><dd>${parent ? `${esc(parent.first_name)} ${esc(parent.last_name)} · <a href="tel:+998${parent.phone}">${parent.phone}</a>` : '—'}</dd>
            <dt>Kurs / guruh</dt><dd>${esc(A.courseName(c.course))} · <a href="#/groups/${c.group}">${esc(A.groupName(c.group))}</a></dd>
            <dt>Muddat</dt><dd>${A.fdate(c.start)} — ${c.end ? A.fdate(c.end) : '…'}</dd>
            ${c.stop_reason ? `<dt>To'xtatish sababi</dt><dd>${esc(c.stop_reason)}</dd>` : ''}
            <dt>Yosh guruhi</dt><dd>${lead ? esc(lead.age_group) : '—'}</dd>
            <dt>Izoh</dt><dd>${esc(c.comment || '—')}</dd>
            <dt>Qo'shdi</dt><dd>${esc(A.userName(c.created_by))}, ${A.fdt(c.created_at)}</dd>
          </dl>${edit.ok ? '' : `<p class="muted small">${esc(edit.why)}</p>`}</section>
          <section class="card"><h2>Qarz qanday hisoblandi</h2>
            <table class="calc"><tr><td>Boshlang'ich qoldiq (AppSheet'dan, 01.09.2026)</td><td class="num">${A.num(d.opening)}</td></tr>
            <tr><td>+ Darslar uchun hisoblangan (Σ talaba qarzi)</td><td class="num">${A.num(d.charged)}</td></tr>
            <tr><td>− To'lovlar</td><td class="num">${A.num(d.paid)}</td></tr>
            <tr><td>− Chegirmalar</td><td class="num">${A.num(d.discount)}</td></tr>
            <tr class="tot"><td>= Balans</td><td class="num">${A.num(d.balance)}</td></tr></table>
            <p class="muted small">Bir dars narxi = kurs narxi ÷ oydagi dars soni. Talaba kelmasa ham dars uchun qarz yoziladi ("Nofaol" va Grant bundan mustasno).</p>
          </section>
        </div>
        ${A.tabs([['pay', "To'lovlar", pays.length], ['att', 'Davomat', att.length]], tab, 'contracts/' + id)}
        ${tab === 'pay'
          ? A.table(
              [
                { h: 'Sana', f: (p) => A.fdate(p.date) },
                { h: 'Summa', f: (p) => A.num(p.amount), cls: 'num', sum: (r) => A.num(A.sum(r, 'amount')) },
                { h: 'Turi', f: (p) => A.CASH[p.cash_type] + (p.nc_status ? ' ' + A.badge(p.nc_status, p.nc_status === 'Tasdiqlandi' ? 'green' : 'orange') : '') },
                { h: 'Chegirma', f: (p) => (p.discount ? `${A.num(p.discount)} ${A.badge(p.disc_status, p.disc_status === 'Tasdiqlandi' ? 'green' : 'orange')}` : '—'), cls: 'num' },
                { h: 'Chek', f: (p) => `<a href="#" data-act="receipt" data-id="${p.id}">Chek</a>` },
              ],
              pays,
              { empty: "To'lov yo'q" },
            )
          : A.table(
              [
                { h: 'Sana', f: (a) => `${A.fdate(a.date)} <span class="muted small">${A.WD[A.isoWeekday(a.date)]}</span>` },
                { h: 'Status', f: (a) => A.attBadge(a.status) + ' ' + A.ATT[a.status] },
                { h: 'Ustoz', f: (a) => esc(A.userName(a.teacher)) + (a.teacher !== (A.get('groups', a.group) || {}).teacher ? ' ' + A.badge("o'rindosh", 'blue') : '') },
                { h: 'Dars narxi (qarz)', f: (a) => (a.no_freq ? A.badge('dars soni tasdiqlanmagan', 'orange') : A.num(a.debt)), cls: 'num', sum: (r) => A.num(A.sum(r, 'debt')) },
                { h: 'Izoh', f: (a) => esc(a.comment || '') },
              ],
              att,
              { empty: "Davomat yo'q" },
            )}`;
    },
  });
  A.act['contract-edit'] = (el) => A.contractForm(A.get('contracts', el.dataset.id));

  /* ===================================================== Qarzdorlar */
  A.page('debtors', {
    title: 'Qarzdorlar',
    section: 'debtors',
    render(p, q) {
      return `${A.head('Qarzdorlar', 'Qarzi 0 dan katta shartnomalar. Guruhlash: kurs → guruh, saralash: qarz bo\'yicha', A.btn('Excel', 'debtors-csv', { cls: 'ghost', icon: 'download' }))}
        ${A.filterBar('debtors', [A.fSearch('debtors'), A.fSelect('debtors', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('debtors', 'status', [['Faol', 'Faol'], ['Nofaol', 'Nofaol']], 'Barcha statuslar')])}
        <div data-results>${this.results()}</div>`;
    },
    results() {
      const s = A.q('debtors:search', ''), course = A.q('debtors:course', ''), stf = A.q('debtors:status', '');
      const rows = A.vis('contracts').filter((c) => A.debtOf(c.id) > 0 && (!course || c.course === course) && (!stf || A.contractStatus(c) === stf) && A.match(A.contractName(c), s));
      const total = A.sum(rows, (c) => A.debtOf(c.id));
      if (!rows.length) return A.empty("Qarzdor yo'q");
      const byG = A.groupBy(A.sortBy(rows, (c) => A.groupName(c.group)), (c) => c.group);
      return `<div class="stats">${A.stat('Jami qarz', A.money(total), `${rows.length} ta shartnoma`, 'danger')}</div>` +
        [...byG]
          .map(([gid, list]) => `<section class="group-block"><h3>${esc(A.groupName(gid))} <span class="muted">· ${list.length} ta · ${A.money(A.sum(list, (c) => A.debtOf(c.id)))}</span></h3>${A.table(
            [
              { h: 'Shartnoma', f: (c) => `<a class="t-red" href="#/contracts/${c.id}">${esc(A.contractName(c))}</a>` },
              { h: 'Telefon', f: (c) => { const st = A.get('students', c.student); return `<a href="tel:+998${st.phone1}">${st.phone1}</a>`; } },
              { h: 'Status', f: (c) => A.contractStatusBadge(A.contractStatus(c)) },
              { h: "Oxirgi to'lov", f: (c) => { const p = A.sortBy(A.rows('payments').filter((x) => x.contract === c.id), (x) => x.date, true)[0]; return p ? A.fdate(p.date) : '—'; } },
              { h: 'Qarz', f: (c) => `<b class="t-red">${A.num(A.debtOf(c.id))}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (c) => A.debtOf(c.id))) },
              { h: '', f: (c) => (A.can('payments', 'a') ? `<button class="btn sm" data-act="pay-new" data-id="${c.id}">To'lov</button>` : '') },
            ],
            A.sortBy(list, (c) => A.debtOf(c.id), true),
          )}</section>`)
          .join('');
    },
  });
  A.act['debtors-csv'] = () => {
    const rows = A.vis('contracts').filter((c) => A.debtOf(c.id) > 0);
    A.downloadCSV('qarzdorlar.csv', [['Shartnoma', 'Telefon', 'Guruh', 'Qarz'], ...rows.map((c) => [A.contractName(c), (A.get('students', c.student) || {}).phone1, A.groupName(c.group), A.debtOf(c.id)])]);
  };
})(window.App);

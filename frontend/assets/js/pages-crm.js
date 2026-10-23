/* Bosh sahifa, Lidlar, Talabalar, Shartnomalar, Qarzdorlar */
(function (A) {
  const esc = A.esc;

  /* ===================================================== Bosh sahifa */
  let dash = {};
  A.page('dashboard', {
    title: 'Bosh sahifa',
    section: 'dashboard',
    async load() {
      dash = {};
      const [, extra] = await Promise.all([
        A.reloadGroups(),
        A.isTeacherRole()
          ? A.http.get('/attendance/summary/').then((summary) => ({ summary }))
          : Promise.all([A.can('debtors') ? A.http.get('/debtors/') : null, A.can('contracts') ? A.http.get('/contracts/?page_size=1') : null]).then(([debt, cs]) => ({ debt, counts: cs ? cs.counts : {} })),
      ]);
      dash = extra;
    },
    render() {
      const me = A.me();
      const today = A.today();
      const ym = A.ym(today);
      if (A.isTeacherRole()) return teacherDash(me, today, ym);

      const pays = A.vis('payments');
      const todayPays = pays.filter((p) => p.date === today);
      const cash = A.sum(todayPays.filter((p) => p.cash_type === 'CASH'), 'amount');
      const noncash = A.sum(todayPays.filter((p) => p.cash_type !== 'CASH'), 'amount');
      const totalDebt = dash.debt ? dash.debt.total : 0;
      const debtorsCount = dash.debt ? dash.debt.count : 0;
      const activeCount = (dash.counts || {}).Faol || 0;
      const groups = A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol');
      const taklif = A.rows('lessonFreqs').filter((f) => f.status === 'Taklif' && `${f.year}-${String(f.month).padStart(2, '0')}` === ym);
      const lessonsToday = A.vis('groups').filter((g) => A.hasLesson(g, today));
      const pc = A.pendingCount();
      const monthPays = A.sum(pays.filter((p) => A.ym(p.date) === ym), 'amount');
      const newLeads = A.vis('leads').filter((l) => A.ym(A.iso(new Date(l.created_at))) === ym).length;

      let warn = '';
      if (taklif.length) {
        warn += `<div class="alert warn">${A.icon('alert')}<div><b>${A.ymLabel(ym)} uchun oydagi dars soni tasdiqlanmagan:</b> ${taklif.map((f) => A.patternName(f.pattern)).join(', ')}.
          Bu guruhlar uchun talaba qarzi va KPI hisoblanmayapti. ${A.canApproveFreq() ? `<a href="#/settings?tab=freq">Tekshirish va tasdiqlash →</a>` : ''}</div></div>`;
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
          ${A.can('debtors') ? A.stat('Jami qarzdorlik', A.money(totalDebt), `${debtorsCount} ta qarzdor`, 'danger', '#/debtors') : ''}
          ${A.stat('Faol talabalar', activeCount, `${groups.length} ta faol guruh`, '', '#/contracts')}
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
    const sm = dash.summary || { kpi: 0, rows: 0, absent: 0, no_freq: 0, makeups_pending: 0 };
    const pendingFreq = sm.no_freq;
    return `
      ${A.head(`Assalomu alaykum, ${esc(me.full_name.split(' ')[0])}!`, `${A.WD_FULL[A.isoWeekday(today)]}, ${A.fdate(today)} · ${esc(A.ROLES[me.role])}`)}
      ${pendingFreq ? `<div class="alert warn">${A.icon('alert')}<div>Shu oyning ${pendingFreq} ta dars qatori uchun oydagi dars soni hali tasdiqlanmagan — KPI tasdiqlangandan keyin hisoblanadi.</div></div>` : ''}
      <section class="card"><h2>Bugungi darslarim</h2>
        ${todays.length ? todays
          .map((g) => {
            const taken = A.attendanceTaken(g.id, today);
            const isTeacher = g.teacher === me.id;
            return `<div class="lesson-row"><div><b>${esc(A.groupName(g))}</b><div class="muted small">${A.timeName(g.time)} · ${esc(A.roomName(g.room))} · ${A.groupFill(g).n} talaba${isTeacher ? '' : ' · siz yordamchisiz'}</div></div>
              ${taken ? A.badge('Davomat olingan', 'green') : isTeacher ? `<a class="btn primary" href="#/attendance?tab=take&group=${g.id}">${A.icon('check')}Davomat olish</a>` : A.badge('Davomatni ustoz oladi', 'gray')}</div>`;
          })
          .join('') : A.empty('Bugun darsingiz yo\'q')}
      </section>
      <div class="stats">
        ${A.stat('Shu oy KPI (hisoblangan)', A.money(sm.kpi), `${sm.rows} ta dars qatori`)}
        ${A.stat('Guruhlarim', groups.length, groups.map((g) => A.groupName(g)).join(', '), '', '#/groups')}
        ${A.stat('Besabab kelmaganlar', sm.absent, 'shu oyda', sm.absent ? 'warn' : '', '#/attendance?tab=absent')}
        ${A.stat("Yetkazilgan dars so'rovlari", sm.makeups_pending, 'kutilmoqda', '', '#/attendance?tab=makeup')}
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
      if (q.open) { // botdagi havola: lid kartochkasini ochish
        const openId = q.open;
        history.replaceState(null, '', location.hash.replace(/[?&]open=[^&]*/, '').replace(/\?&/, '?').replace(/\?$/, ''));
        setTimeout(() => A.openLead(openId), 400);
      }
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
      else if (tab === 'paid') {
        qs.set('paid', 1);
        qs.set('page', A.q('leads:page', 1));
        leadData = await A.http.get('/leads/?' + qs);
        leadData.results.forEach(keepStudent);
      }
    },
    render(p, q) {
      const tab = q.tab || 'funnel';
      const actions = A.can('leads', 'a') ? A.btn('Yangi lid', 'lead-new', { icon: 'plus' }) : '';
      let body = '';
      if (tab === 'funnel') body = funnel(leadData);
      else if (tab === 'list') body = leadTable(leadData.results) + pager(leadData);
      else if (tab === 'stats') body = leadStats(leadData);
      else body = paidTable(leadData.results) + pager(leadData);
      return `${A.head('Lidlar', 'Murojaatlar voronkasi: birinchi qo\'ng\'iroqdan shartnomagacha', actions)}
        ${A.tabs([['funnel', 'Voronka', tab === 'funnel' ? leadData.total : undefined], ['list', "Ro'yxat"], ['stats', 'Statistika'], ['paid', "To'lov qilganlar"]], tab, 'leads')}
        ${A.filterBar('leads', [A.fSearch('leads', 'Ism yoki telefon…'), A.fSelect('leads', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('leads', 'source', A.optList('leadSources'), 'Barcha manbalar')])}
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
      return `<div class="kcol"><div class="kcol-h" title="${esc(LS[k])}"><span class="badge ${leadStatusTone[k]}">${k}</span><span class="kcol-t">${esc(LS[k])}</span><b>${n}</b></div>
        ${list
          .map((l) => {
            const st = l.student_data;
            return `<button class="kcard" data-act="lead-open" data-id="${l.id}">
              <b>${esc(st.first_name)} ${esc(st.last_name)}</b>
              <span class="muted small">${esc(A.courseName(l.course))} · ${esc(A.sourceName(l.source))}</span>
              ${l.demo_date && ['3', '4'].includes(l.status) ? `<span class="small">Sinov: ${demoTime(l) ? `${demoTime(l)} · ` : ''}${A.fdate(l.demo_date)}</span>` : ''}
              ${CB.includes(l.status) && l.callback_at ? `<span class="small ${cbOverdue(l) ? 't-red' : ''}">⏰ ${cbShort(l)}</span>` : ''}
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
        { h: "Qayta bog'lanish", f: (l) => (CB.includes(l.status) && l.callback_at ? `<span class="${cbOverdue(l) ? 't-red' : ''}">⏰ ${cbShort(l)}</span>` : '—') },
        { h: 'Shartnoma', f: contractStatusOf },
        { h: "Qo'shilgan", f: (l) => A.fdate(A.iso(new Date(l.created_at))) },
      ],
      leads,
      { empty: "Lid topilmadi" },
    );
  }

  function paidTable(leads) {
    return A.table(
      [
        { h: 'Murojaatchi', f: (l) => `<a href="#" data-act="lead-open" data-id="${l.id}">${esc(l.student_data.full_name)}</a>` },
        { h: 'Kurs', f: (l) => esc(A.courseName(l.course)) },
        { h: 'Manba', f: (l) => esc(A.sourceName(l.source)) },
        { h: 'Status', f: (l) => A.badge(`${l.status}. ${LS[l.status]}`, leadStatusTone[l.status]) },
        { h: "Birinchi to'lov", f: (l) => A.fdate(l.first_paid) },
        { h: "To'lovlar jami", f: (l) => `<b>${A.num(l.paid_total)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (l) => Number(l.paid_total))) },
      ],
      leads,
      { empty: "Talabasi to'lov qilgan lid yo'q" },
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
      )}<p class="muted small">Shartnoma — talabasi shartnoma tuzgan lidlar.</p></section>
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
  // Sinov dars vaqti: tanlangan guruhning dars vaqti, bo'lmasa lidning ma'qul vaqti
  const demoTime = (l) => {
    const g = l.group && A.get('groups', l.group);
    const id = g ? g.time : (l.times || [])[0];
    return id ? A.timeName(id) : '';
  };
  /* Qayta bog'lanish vaqti (1- va 8-statuslar): shu vaqtda bot Administrator+Hisobchilarga eslatadi */
  const CB = ['1', '8'];
  const pad2 = (n) => String(n).padStart(2, '0');
  const dtLocal = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  const cbValue = (l) => (l && l.callback_at ? l.callback_at.slice(0, 16) : '');
  const cbTomorrow = () => { const d = new Date(Date.now() + 864e5); d.setHours(10, 0, 0, 0); return dtLocal(d); };
  const cbOverdue = (l) => CB.includes(l.status) && l.callback_at && new Date(l.callback_at) < new Date();
  const cbShort = (l) => `${l.callback_at.slice(8, 10)}.${l.callback_at.slice(5, 7)} ${l.callback_at.slice(11, 16)}`;
  /** Sana-vaqt so'raydi va holat (ixtiyoriy) bilan birga saqlaydi */
  A.callbackForm = (l, status, done) =>
    A.form({
      title: "Qayta bog'lanish vaqti",
      values: { callback_at: cbValue(l) && new Date(l.callback_at) > new Date() ? cbValue(l) : cbTomorrow() },
      fields: [
        { name: 'note', type: 'note', text: () => `Shu vaqtda bot Administrator+Hisobchilarga «qayta bog'lanish vaqti keldi» deb xabar beradi${status ? ` (${status}. ${LS[status]})` : ''}.` },
        { name: 'callback_at', label: 'Sana va vaqt', type: 'datetime-local', required: true, validate: (t) => (new Date(t) < new Date(Date.now() - 6e5) ? "Bu vaqt o'tib ketgan" : '') },
      ],
      async onSubmit(x) {
        const body = { callback_at: x.callback_at };
        if (status) body.status = status;
        await A.http.patch(`/leads/${l.id}/`, body);
        A.toast(status ? 'Status va qayta bog\'lanish vaqti saqlandi' : 'Vaqt saqlandi');
        done && done();
      },
    });

  /* ---- Suhbatdan keyingi izoh: izoh + (ixtiyoriy) holat + keyingi qayta bog'lanish vaqti ---- */
  A.callNoteForm = (l, done) => {
    const futureCb = l.callback_at && new Date(l.callback_at) > new Date();
    A.form({
      title: 'Suhbatdan keyingi izoh',
      values: { status: l.status, callback_at: futureCb ? cbValue(l) : CB.includes(l.status) ? cbTomorrow() : '' },
      fields: [
        { name: 'note', type: 'note', text: () => `${l.student_data.full_name} bilan suhbat${l.callback_talked_at ? ` (${A.fdt(l.callback_talked_at)})` : ''}. Izoh majburiy; lid qayta bog'lanishda qolsa — keyingi vaqtni belgilang.` },
        { name: 'comment', label: 'Suhbat haqida izoh', type: 'textarea', required: true, placeholder: "Masalan: narxni so'radi, ertaga javob beradi" },
        { name: 'status', label: 'Holat', type: 'select', options: Object.entries(LS).map(([k, t]) => [k, `${k}. ${t}`]), required: true },
        { name: 'callback_at', label: "Keyingi qayta bog'lanish sana va vaqti", type: 'datetime-local', show: (x) => CB.includes(x.status),
          required: (x) => CB.includes(x.status) && (x.status !== l.status || !futureCb), help: futureCb ? "Bo'sh qoldirsangiz, avval belgilangan vaqt saqlanadi" : '',
          validate: (t) => (t && new Date(t) < new Date(Date.now() - 6e5) ? "Bu vaqt o'tib ketgan" : '') },
      ],
      async onSubmit(x) {
        const body = { comment: x.comment, status: x.status };
        if (CB.includes(x.status) && x.callback_at && x.callback_at !== cbValue(l)) body.callback_at = x.callback_at;
        await A.http.post(`/leads/${l.id}/call-note/`, body);
        A.toast('Izoh saqlandi');
        done && done();
      },
    });
  };
  const ago = (ts) => {
    const m = Math.round((Date.now() - new Date(ts)) / 6e4);
    return m < 1 ? 'hozirgina' : m < 60 ? `${m} daqiqa oldin` : m < 1440 ? `${Math.floor(m / 60)} soat oldin` : `${Math.floor(m / 1440)} kun oldin`;
  };
  const CALL_ICON = { Kiruvchi: '↙', Chiquvchi: '↗', Javobsiz: '✕', 'Rad etilgan': '⊘', Bloklangan: '⊘' };
  const callDur = (s) => (s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : '—');
  /** Lid yoki talaba kartochkasida: shu raqamlardagi qo'ng'iroqlar tarixi va oxirgi aloqa (server: /leads/{id}/calls/, /students/{id}/calls/) */
  const SMS_TONE = { Navbatda: 'orange', Yuborilmoqda: 'blue', Yuborildi: 'green', Xato: 'red' };
  A.fillCalls = async (el, url, search) => {
    if (!el || !(A.can('calls', 'v') || A.can('sms', 'v'))) return;
    let d;
    try { d = await A.http.get(url); } catch (e) { return; }
    if (!d.allowed) return;
    let calls = '';
    if (d.calls_allowed !== false) {
      const rows = d.results.slice(0, 6);
      calls = `<div><h4>Qo'ng'iroqlar (${d.count})${d.last ? ` <span class="muted small">· oxirgi aloqa: ${esc(ago(d.last.started_at))}</span>` : ''}</h4>
        ${rows.length ? `<ul class="comments">${rows.map((c) => `<li><p>${CALL_ICON[c.direction] || ''} <b>${esc(c.direction)}</b> · ${esc(c.phone)} · ${callDur(c.duration)}${c.missed && !c.callback_at ? ' <span class="t-red">javob berilmagan</span>' : ''}${c.comment ? ` — ${esc(c.comment)}` : ''}</p><small class="muted">${A.fdt(c.started_at)}</small></li>`).join('')}</ul>
          ${d.count > rows.length ? `<a href="#" data-calls-all>Barcha ${d.count} ta qo'ng'iroq →</a>` : ''}` : `<p class="muted small">Qo'ng'iroq yo'q</p>`}</div>`;
    }
    let sms = '';
    if (d.sms) {
      const rows = d.sms.results.slice(0, 6);
      const head = (m) => (m.direction === 'Kiruvchi'
        ? `↙ <b>Kelgan</b> · ${esc(m.recipient || '')} ${esc(m.phone)}`
        : `↗ ${A.badge(m.status, SMS_TONE[m.status] || 'gray')}${m.delivery === 'Yetkazildi' ? ' ' + A.badge('✓✓', 'green') : m.delivery === 'Yetkazilmadi' ? ' ' + A.badge('Yetkazilmadi', 'red') : ''} · ${esc(m.recipient || '')} ${esc(m.phone)}`);
      sms = `<div><h4>SMS (${d.sms.count}${d.sms.incoming ? `, kelgan ${d.sms.incoming}` : ''})${rows.length ? ` <span class="muted small">· oxirgisi: ${esc(ago(rows[0].sent_at || rows[0].created_at))}</span>` : ''}</h4>
        ${rows.length ? `<ul class="comments">${rows.map((m) => `<li${m.direction === 'Kiruvchi' ? ' class="sms-in"' : ''}><p>${head(m)}</p>
          <p class="small">${esc(m.text)}</p>${m.error ? `<p class="small t-red">${esc(m.error)}</p>` : ''}<small class="muted">${A.fdt(m.sent_at || m.created_at)}${m.by ? ` · ${esc(m.by)}` : ''}</small></li>`).join('')}</ul>
          ${d.sms.count > rows.length && A.can('calls') ? `<a href="#" data-sms-all>Barcha ${d.sms.count} ta SMS →</a>` : ''}` : `<p class="muted small">SMS yo'q</p>`}</div>`;
    }
    el.innerHTML = calls && sms ? `<div class="grid-2">${calls}${sms}</div>` : calls || sms;
    const all = el.querySelector('[data-calls-all]');
    if (all) all.onclick = (e) => { e.preventDefault(); A.ui.q['calls:search'] = search; A.ui.q['calls:page'] = 1; A.go('calls?tab=list'); };
    const allSms = el.querySelector('[data-sms-all]');
    if (allSms) allSms.onclick = (e) => { e.preventDefault(); A.ui.q['smsj:search'] = search; A.ui.q['smsj:page'] = 1; A.go('calls?tab=sms'); };
  };

  A.leadForm = (lead, freeStudents = [], preset = {}) => {
    const isNew = !lead;
    const B = lead ? lead.branch : A.branchIds()[0];
    const v = lead ? { ...lead } : { status: '2', times: [], tags: [], mode: 'new', ...preset };
    Object.assign(v, A.timeValues((v.times || [])[0]));
    if (v.demo_date == null) delete v.demo_date; // standart — bugun (guruh tanlanganda ko'rinadi)
    v.callback_at = cbValue(lead); // datetime-local uchun mahalliy ko'rinish
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
      ...A.timeFields({ optional: true }),
      { name: 'status', label: 'Status', type: 'select', options: Object.entries(LS).map(([k, l]) => [k, `${k}. ${l}`]), required: true },
      { name: 'callback_at', label: "Qayta bog'lanish sana va vaqti", type: 'datetime-local', show: (x) => CB.includes(x.status), required: (x) => CB.includes(x.status) && (isNew || x.status !== lead.status),
        help: 'Shu vaqtda bot Administrator+Hisobchilarga eslatadi' },
      {
        name: 'group', label: 'Guruh', type: 'select', show: (x) => ['3', '4', '5'].includes(x.status) || (x.group && !['1', '2'].includes(x.status)),
        options: (x) => A.rows('groups').filter((g) => (g.branch === B && g.course === x.course && g.status !== 'Nofaol') || g.id === x.group).map((g) => [g.id, `${A.groupName(g)} · ${A.patternName(g.pattern)} ${A.timeName(g.time)} (${g.status})`]),
        help: "3, 4, 5-statuslarda ko'rinadi. Faqat shu kursning faol yoki rejadagi guruhlari",
      },
      { name: 'demo_date', label: 'Sinov dars kuni', type: 'date', show: (x) => x.group && ['3', '4', '5'].includes(x.status), default: A.today() },
      { name: 'demo_attended', label: 'Sinov darsga qatnashdimi?', type: 'seg', options: [['yes', 'Ha, qatnashdi'], ['no', 'Kelmadi']], show: (x) => x.demo_date && x.group && ['3', '4', '5'].includes(x.status) },
    ];
    if (lead) v.demo_attended = lead.demo_attended === true ? 'yes' : lead.demo_attended === false ? 'no' : '';
    A.form({
      title: isNew ? 'Yangi lid' : 'Lidni tahrirlash',
      fields,
      values: v,
      async onSubmit(x) {
        const withGroup = ['3', '4', '5'].includes(x.status) && x.group;
        let times = [];
        if (x.new_start && x.new_end) {
          const first = (v.times || [])[0] && A.get('lessonTimes', v.times[0]);
          times = first && first.start === x.new_start && first.end === x.new_end ? [...v.times] : [await A.ensureTime(x.new_start, x.new_end, B)];
        }
        const rec = {
          source: x.source, course: x.course, pattern: x.pattern || null, times, status: x.status, age_group: x.age_group, social: x.social, laptop: x.laptop, tags: x.tags,
          group: withGroup ? x.group : x.group && !['1', '2'].includes(x.status) ? x.group : null,
          demo_date: withGroup ? x.demo_date || null : null,
          demo_attended: withGroup && x.demo_date ? (x.demo_attended === 'yes' ? true : x.demo_attended === 'no' ? false : null) : null,
        };
        if (CB.includes(x.status) && (isNew || x.status !== lead.status || x.callback_at !== cbValue(lead))) rec.callback_at = x.callback_at; // o'zgarmagan eski vaqt qayta yuborilmaydi
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
        ${l.callback_talked_at && A.can('leads', 'a') ? `<div class="alert warn">${A.icon('phone')}<div><b>${A.fdt(l.callback_talked_at)}</b> da gaplashilgan — izoh hali yozilmagan. <button class="btn sm" data-callnote>📝 Izoh yozish</button></div></div>` : ''}
        ${needsBirth ? `<div class="alert warn">${A.icon('alert')}<div>O'qishni boshladi, lekin talabaning to'liq ma'lumotlari (tug'ilgan sana, vasiy) kiritilmagan. Avval talaba ma'lumotlarini to'ldiring.</div></div>` : ''}
        <dl class="dl">
          <dt>Telefon</dt><dd><a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ` · <a href="tel:+998${st.phone2}">+998 ${st.phone2}</a>` : ''}</dd>
          <dt>Kurs</dt><dd>${esc(A.courseName(l.course))}</dd>
          <dt>Manba</dt><dd>${esc(A.sourceName(l.source))}</dd>
          <dt>Hafta kunlari / vaqt</dt><dd>${esc(A.patternName(l.pattern))} · ${(l.times || []).map(A.timeName).join(', ') || '—'}</dd>
          ${l.group ? `<dt>Guruh</dt><dd><a href="#/groups/${l.group}">${esc(A.groupName(l.group))}</a></dd>` : ''}
          ${l.demo_date ? `<dt>Sinov darsi</dt><dd>${A.fdate(l.demo_date)} ${l.demo_attended === true ? A.badge('Keldi', 'green') : l.demo_attended === false ? A.badge('Kelmadi', 'red') : ''}</dd>` : ''}
          ${CB.includes(l.status) ? `<dt>Qayta bog'lanish</dt><dd><b class="${cbOverdue(l) ? 't-red' : ''}">${l.callback_at ? `⏰ ${A.fdt(l.callback_at)}${cbOverdue(l) ? ' (muddati o\'tdi)' : ''}` : 'vaqti belgilanmagan'}</b> ${edit.ok && A.can('leads', 'e') ? `<button class="btn sm ghost" data-cb>${l.callback_at ? '✎ O\'zgartirish' : '＋ Belgilash'}</button>` : ''}</dd>` : ''}
          <dt>Yosh / holat / noutbuk</dt><dd>${esc(l.age_group || '—')} · ${esc(l.social || '—')} · ${esc(l.laptop || '—')}</dd>
          <dt>Qo'shdi</dt><dd>${esc(A.userName(l.created_by))}, ${A.fdt(l.created_at)}</dd>
        </dl>
        ${A.can('leads', 'e') ? `<h4>Statusni o'zgartirish</h4><div class="seg wrap">${Object.entries(LS)
          .map(([k, t]) => `<button class="${l.status === k ? 'on' : ''}" data-status="${k}" ${edit.ok ? '' : 'disabled'}>${k}. ${esc(t)}</button>`)
          .join('')}</div>${edit.ok ? '' : `<p class="muted small">${esc(edit.why)}</p>`}` : ''}
        <div id="lead-calls"></div>
        <h4>Izohlar (${l.comments.length})</h4>
        ${A.can('leads', 'a') ? `<div class="row gap"><input class="f-input grow" id="lc-text" placeholder="Izoh yozing…"><button class="btn" id="lc-add">Qo'shish</button></div>` : ''}
        <ul class="comments">${l.comments.map((c) => `<li><p>${esc(c.comment)}</p><small class="muted">${esc(A.userName(c.created_by))} · ${A.fdt(c.created_at)}</small></li>`).join('') || '<li class="muted">Izoh yo\'q</li>'}</ul>`,
      footer: `
        ${A.can('leads', 'e') && edit.ok ? `<button class="btn ghost" data-edit>Tahrirlash</button>` : ''}
        ${l.status === '5' && A.can('leads', 'e') ? `<button class="btn" data-student>Talaba ma'lumotlarini to'ldirish</button>` : ''}
        ${canContract ? `<button class="btn primary" data-contract ${needsBirth ? `disabled title="Avval talaba ma'lumotlarini to'ldiring"` : ''}>Shartnoma tuzish</button>` : ''}`,
    });
    const reopen = () => { m.close(); A.refresh(); A.openLead(id); };
    const fail = (e) => A.toast(e.message, 'warn');
    m.el.querySelectorAll('[data-status]').forEach((b) =>
      (b.onclick = () => {
        if (CB.includes(b.dataset.status) && b.dataset.status !== l.status) { m.close(); A.callbackForm(l, b.dataset.status, () => { A.refresh(); A.openLead(id); }); return; }
        A.http.patch(`/leads/${id}/`, { status: b.dataset.status }).then(reopen, fail);
      }));
    const cnBtn = m.el.querySelector('[data-callnote]');
    if (cnBtn) cnBtn.onclick = () => { m.close(); A.callNoteForm(l, () => { A.refresh(); A.openLead(id); }); };
    A.fillCalls(m.el.querySelector('#lead-calls'), `/leads/${id}/calls/`, st.phone1);
    const cbBtn = m.el.querySelector('[data-cb]');
    if (cbBtn) cbBtn.onclick = () => { m.close(); A.callbackForm(l, '', () => { A.refresh(); A.openLead(id); }); };
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
    const cb = m.el.querySelector('[data-contract]');
    if (cb)
      cb.onclick = async () => {
        if (!l.group) return A.toast('Avval lidga guruh tanlang (Tahrirlash → Guruh)', 'warn');
        try {
          const c = await A.http.post(`/leads/${id}/contract/`);
          await A.reloadGroups();
          m.close();
          A.toast(`Shartnoma №${c.number} tuzildi: ${A.groupName(l.group)}`);
          A.go('contracts/' + c.id);
        } catch (e) { fail(e); }
      };
  };
  A.act['lead-open'] = (el) => A.openLead(el.dataset.id);

  /* ---- Talaba ma'lumotlarini to'ldirish ---- */
  const PARENT_RELATIONS = ['Ota', 'Ona', 'Aka', 'Uka', 'Opa', 'Singil', 'Amaki', "Tog'a", 'Xola', 'Amma', 'Buvi', 'Bobo', 'Boshqa'];
  A.studentForm = async (st, after) => {
    const parents = (await A.http.get('/parents/')).filter((p) => p.branch === st.branch);
    A.form({
      title: "Talaba ma'lumotlari",
      values: { ...st, parent: st.parent || '' },
      fields: [
        { name: 'first_name', label: 'Ism', required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'last_name', label: 'Familiya', required: true, half: true, validate: (t) => (t.trim().length < 3 || t.trim().length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'phone1', label: '1-telefon (+998)', required: true, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
        { name: 'father_name', label: 'Sharif (ixtiyoriy)', half: true, validate: (t) => (!t.trim() ? '' : t.includes('.') ? "Nuqta qo'yib bo'lmaydi!" : t.trim().length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'phone2', label: '2-telefon (+998)', half: true, validate: (t, x) => (t === x.phone1 ? "Ikki bir xil nomer kiritib bo'lmaydi!" : !/^\d{9}$/.test(t) ? "9 ta sondan iborat bo'lsin" : '') },
        { name: 'gender', label: 'Jins', type: 'seg', options: ['Erkak', 'Ayol'], half: true },
        { name: 'birth_date', label: "Tug'ilgan sanasi", type: 'date', required: true, half: true },
        { name: 'parent', label: 'Vasiy (ota-ona)', type: 'select', half: true, options: () => parents.map((p) => [p.id, `${p.relation ? p.relation + ': ' : ''}${p.first_name} ${p.last_name} · ${p.phone}`]), placeholder: "Tanlang yoki bo'sh qoldiring" },
        { name: 'new_parent', label: "Yangi vasiy qo'shish", type: 'checkbox', show: (x) => !x.parent },
        { name: 'p_relation', label: 'Vasiy kim bo\'ladi', type: 'select', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, options: () => PARENT_RELATIONS.map((r) => [r, r]), placeholder: 'Tanlang' },
        { name: 'p_first', label: 'Vasiy ismi (ixtiyoriy)', show: (x) => x.new_parent, required: (x) => x.new_parent && x.p_relation === 'Boshqa', half: true, validate: (t, x) => (!t.trim() ? (x.p_relation === 'Boshqa' ? 'Ismini yozing' : '') : t.trim().length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'p_phone', label: 'Vasiy telefoni', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
      ],
      async onSubmit(x) {
        const body = { first_name: x.first_name, last_name: x.last_name, father_name: x.father_name, phone1: x.phone1, phone2: x.phone2 || '', gender: x.gender || '', birth_date: x.birth_date, parent: x.parent || null, new_parent: !!x.new_parent, p_first: x.p_first || '', p_relation: x.p_relation || '', p_phone: x.p_phone || '' };
        A.putLocal('students', await A.http.patch(`/students/${st.id}/`, body));
        A.toast('Saqlandi');
        A.refresh();
        after && after();
      },
    });
  };

  /* ===================================================== Shartnomalar (server API: /contracts/, /debtors/, /students/) */
  /** Server javobidagi shartnoma va talabani keshga qo'yish (nomlar boshqa sahifalarda ham ko'rinsin) */
  A.keepContract = (c) => {
    if (c.student_data) A.putLocal('students', { ...(A.get('students', c.student) || {}), ...c.student_data, branch: c.branch });
    return A.putLocal('contracts', c);
  };
  /** Sahifalash tugmalari: data-act="page" data-id="kalit~sahifa" */
  A.pager = (key, d) =>
    d && d.pages > 1
      ? `<div class="row gap pager"><button class="btn sm ghost" data-act="page" data-id="${key}~${d.page - 1}" ${d.page <= 1 ? 'disabled' : ''}>← Oldingi</button><span class="muted small">${d.page} / ${d.pages} · jami ${d.count}</span><button class="btn sm ghost" data-act="page" data-id="${key}~${d.page + 1}" ${d.page >= d.pages ? 'disabled' : ''}>Keyingi →</button></div>`
      : '';
  A.act.page = (el) => {
    const [key, n] = el.dataset.id.split('~');
    A.ui.q[key + ':page'] = Number(n);
    A.refresh();
  };
  // Filtr o'zgarsa — birinchi sahifaga
  document.addEventListener('input', (e) => {
    const el = e.target.closest('[data-filter]');
    if (el && !el.dataset.filter.endsWith(':page')) A.ui.q[el.dataset.filter.split(':')[0] + ':page'] = 1;
  }, true);
  const filterQS = (key, names, extra = {}) => {
    const qs = new URLSearchParams(extra);
    for (const k of names) if (A.q(`${key}:${k}`, '')) qs.set(k, A.q(`${key}:${k}`));
    return qs;
  };
  const paymentsReady = () => A.CONNECTED.has('payments') && A.can('payments', 'a');

  let cData = { results: [], counts: {} };
  let cCounts = {};
  A.page('contracts', {
    title: 'Shartnomalar',
    section: 'contracts',
    async load(p, q) {
      const tab = q.tab || 'Faol';
      if (tab === 'students') {
        cData = await A.http.get('/students/?' + filterQS('contracts', ['search'], { page: A.q('contracts:page', 1) }));
        cData.results.forEach((st) => A.putLocal('students', st));
      } else {
        cData = await A.http.get('/contracts/?' + filterQS('contracts', ['search', 'course', 'type'], { status: tab, page: A.q('contracts:page', 1) }));
        cData.results.forEach(A.keepContract);
        cCounts = cData.counts;
      }
    },
    render(p, q) {
      const tab = q.tab || 'Faol';
      const actions = (A.can('contracts', 'a') ? A.btn('Yangi shartnoma', 'contract-new', { icon: 'plus' }) : '') + A.btn('Excel', 'contracts-csv', { cls: 'ghost', icon: 'download' });
      return `${A.head('Shartnomalar', 'Guruhlash: kurs → guruh. Qarzdor talaba nomi qizil', actions)}
        ${A.tabs([['Faol', 'Faol', cCounts.Faol], ['Rejada', 'Rejada', cCounts.Rejada], ['Nofaol', 'Nofaol', cCounts.Nofaol], ['students', 'Talabalar']], tab, 'contracts')}
        ${A.filterBar('contracts', [A.fSearch('contracts', tab === 'students' ? 'Ism yoki telefon…' : 'Ism, telefon yoki raqam…'), ...(tab === 'students' ? [] : [A.fSelect('contracts', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('contracts', 'type', [['Pullik', 'Pullik'], ['Grant', 'Grant']], 'Barcha turlar')])])}
        <div>${tab === 'students' ? studentsTable(cData.results) : contractGroups(cData.results)}${A.pager('contracts', cData)}</div>`;
    },
  });

  function studentsTable(rows) {
    return A.table(
      [
        { h: 'Talaba', f: (st) => (A.can('leads', 'e') ? `<a href="#" data-act="student-edit" data-id="${st.id}">${esc(st.full_name)}</a>` : esc(st.full_name)) },
        { h: 'Telefon', f: (st) => esc(st.phone1) + (st.phone2 ? `<br><small class="muted">${esc(st.phone2)}</small>` : '') },
        { h: "Tug'ilgan", f: (st) => A.fdate(st.birth_date) },
        { h: 'Shartnomalar', f: (st) => (st.contracts || []).map((c) => `<a href="#/contracts/${c.id}">№${c.number}</a>`).join(', ') || '—' },
      ],
      rows,
      { empty: 'Talaba topilmadi' },
    );
  }

  function contractGroups(rows) {
    if (!rows.length) return A.empty('Shartnoma topilmadi');
    const byGroup = A.groupBy(rows, (c) => c.group);
    return [...byGroup]
      .map(([gid, list]) => {
        const debt = A.sum(list, (c) => Math.max(0, c.balance));
        return `<section class="group-block"><h3>${esc(A.groupName(gid))} <span class="muted">· ${list.length} ta${debt ? ` · qarz ${A.money(debt)}` : ''}</span></h3>
          ${A.table(
            [
              { h: 'Shartnoma', f: (c) => `<a href="#/contracts/${c.id}" class="${c.balance > 0 ? 't-red' : ''}">${esc(c.name)}</a>` },
              { h: 'Turi', f: (c) => (c.type === 'Grant' ? A.badge('Grant', 'blue') : 'Pullik') },
              { h: 'Boshlanish', f: (c) => A.fdate(c.start) },
              { h: 'Tugash', f: (c) => (c.end ? `${A.fdate(c.end)} <span class="muted small">${esc(c.stop_reason)}</span>` : '—') },
              { h: 'Status', f: (c) => A.contractStatusBadge(c.status) },
              { h: 'Balans', f: (c) => A.moneyCell(c.balance, true), cls: 'num' },
            ],
            list,
          )}</section>`;
      })
      .join('');
  }
  A.act['student-edit'] = (el) => A.studentForm(A.get('students', el.dataset.id), () => A.refresh());

  /** Joriy filtr bo'yicha barcha sahifalarni yig'ib olish (Excel/CSV uchun) */
  const fetchAll = async (path, qs) => {
    qs.set('page_size', 200);
    let page = 1, out = [];
    for (;;) {
      qs.set('page', page);
      const d = await A.http.get(path + qs);
      out = out.concat(d.results);
      if (page >= (d.pages || 1)) return out;
      page++;
    }
  };
  A.act['contracts-csv'] = () => {
    const tab = (A.current.query || {}).tab || 'Faol';
    A.downloadXlsx(filterQS('contracts', ['search', 'course', 'type'], tab === 'students' ? {} : { status: tab }));
  };

  /* ---- Shartnoma formasi. Tekshiruvlar serverda ham bor (services.validate_contract) ---- */
  /** stopOnly — muddati o'tgan shartnoma: faqat to'xtatish (tugash sanasi oxirgi 30 kun ichida, sabab, izoh) */
  A.contractForm = async (c, preset = {}, stopOnly = false) => {
    const isNew = !c;
    const lock = () => !isNew && stopOnly;
    const B = c ? c.branch : A.branchIds()[0];
    const students = isNew ? (await A.http.get('/students/?page_size=200')).results.filter((s) => s.branch === B) : [c.student_data];
    const v = c ? { ...c } : { type: 'Pullik', start: A.today(), ...preset };
    A.form({
      title: isNew ? 'Yangi shartnoma' : `Shartnoma №${c.number}`,
      values: v,
      fields: [
        { name: 'student', label: 'Talaba', type: 'select', required: true, readonly: () => !isNew, options: () => students.map((s) => [s.id, `${s.full_name} · ${s.phone1}`]), help: isNew ? "Yaratilgandan keyin talabani o'zgartirib bo'lmaydi" : "Talaba o'zgarmaydi" },
        { name: 'course', label: 'Kurs', type: 'select', required: true, resets: ['group'], readonly: () => lock() || (!isNew && A.role() !== 'ADMIN'), options: (x) => A.optList('courses', 'name', (k) => (k.status === 'Faol' && k.branches.includes(B)) || k.id === x.course), help: isNew ? '' : "Kursni faqat Admin o'zgartiradi" },
        { name: 'group', label: 'Guruh', type: 'select', required: true, show: (x) => x.course, readonly: lock, options: (x) => A.rows('groups').filter((g) => (g.course === x.course && g.branch === B && g.status !== 'Nofaol') || g.id === x.group).map((g) => { const f = A.groupFill(g); return [g.id, `${A.groupName(g)} · ${A.patternName(g.pattern)} ${A.timeName(g.time)} · ${f.n}/${f.cap}`]; }) },
        { name: 'type', label: 'Shartnoma turi', type: 'seg', options: ['Pullik', 'Grant'], show: (x) => x.course, readonly: () => lock() || !A.isTop(), help: () => (A.isTop() ? '' : "Turini faqat Admin va Bosh menejer o'zgartiradi") },
        { name: 'number', label: 'Shartnoma raqami', type: 'computed', show: (x) => x.type, compute: () => (c ? `№${c.number}` : 'avtomatik (filialdagi oxirgi raqam + 1)') },
        { name: 'start', label: 'Boshlanish sana', type: 'date', required: true, show: (x) => x.type, half: true, readonly: lock },
        { name: 'end', label: 'Tugash sana', type: 'date', show: (x) => x.type && x.start, half: true, required: lock,
          help: () => (lock() ? "To'xtatish: tugash sanasi oxirgi 30 kun ichida" : ''),
          validate: (d, x) => (d && d < x.start ? "Boshlanish sanadan kichik bo'lolmaydi" : d && lock() && A.diffDays(d, A.today()) > 30 ? "Tugash sanasini oxirgi 30 kun ichida qo'yish mumkin" : '') },
        { name: 'stop_reason', label: "To'xtatish sababi", type: 'select', options: A.STOP_REASONS, show: (x) => x.end, required: (x) => !!x.end },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.type },
      ],
      async onSubmit(x) {
        const rec = lock()
          ? { end: x.end || null, stop_reason: x.end ? x.stop_reason : '', comment: x.comment || '' }
          : { course: x.course, group: x.group, type: x.type, start: x.start, end: x.end || null, stop_reason: x.end ? x.stop_reason : '', comment: x.comment || '' };
        const saved = isNew ? await A.http.post('/contracts/', { ...rec, student: x.student }) : await A.http.patch(`/contracts/${c.id}/`, rec);
        A.keepContract(saved);
        await A.reloadGroups();
        A.toast(isNew ? `Shartnoma №${saved.number} tuzildi` : 'Saqlandi');
        if (preset._after) preset._after(saved); // guruhni boshqarish oynasidan — oynaga qaytadi
        else if (isNew) A.go('contracts/' + saved.id);
        else A.refresh();
      },
    });
  };
  A.act['contract-new'] = () => A.contractForm(null);

  /* ---- Shartnoma sahifasi ---- */
  let cDetail = null;
  A.page('contracts/:id', {
    title: 'Shartnoma',
    section: 'contracts',
    async load({ id }) {
      cDetail = await A.http.get(`/contracts/${id}/`);
      A.keepContract(cDetail);
    },
    mount() {
      const el = document.getElementById('stu-calls');
      if (el) A.fillCalls(el, `/students/${cDetail.student}/calls/`, cDetail.student_data.phone1);
    },
    render({ id }, q) {
      const c = cDetail;
      const st = c.student_data;
      const status = c.status;
      const pays = c.payments || [];
      const att = c.attendance || [];
      const edit = A.canEdit('contracts', c, 'start');
      const stopOnly = !edit.ok && A.can('contracts', 'e');
      const tab = q.tab || 'att';
      const parent = c.parent;
      const g = A.get('groups', c.group);
      return `
        <a class="back" href="#/contracts">← Shartnomalar</a>
        ${A.head(c.name, `${A.contractStatusBadge(status)} ${c.type === 'Grant' ? A.badge('Grant', 'blue') : ''} · ${esc(A.groupName(c.group))}`,
          `${paymentsReady() ? A.btn("To'lov qilish", 'pay-new', { id: c.id, icon: 'cash' }) : ''}
           ${A.can('contracts', 'e') ? (stopOnly ? A.btn("To'xtatish", 'contract-stop', { id: c.id, cls: 'ghost', title: `${edit.why}. Faqat to'xtatish mumkin` }) : A.btn('Tahrirlash', 'contract-edit', { id: c.id, cls: 'ghost' })) : ''}`)}
        <div class="stats">
          ${A.stat('Balans (qarz)', `<span class="${c.balance > 0 ? 't-red' : 't-green'}">${A.money(c.balance)}</span>`, c.balance > 0 ? 'talaba qarzdor' : c.balance < 0 ? "oldindan to'langan" : "qarz yo'q", c.balance > 0 ? 'danger' : '')}
          ${A.stat('Hisoblangan (darslar)', A.money(c.charged), `${att.filter((a) => a.debt).length} ta dars uchun`)}
          ${A.stat("To'langan", A.money(c.paid), `${pays.length} ta to'lov`)}
          ${A.stat('Chegirmalar', A.money(c.discount))}
        </div>
        <div class="grid-2">
          <section class="card"><h2>Ma'lumotlar</h2><dl class="dl">
            <dt>Talaba</dt><dd>${esc(st.full_name)} ${A.can('leads', 'e') ? `<a href="#" data-act="student-edit" data-id="${st.id}" class="small">tahrirlash</a>` : ''}</dd>
            <dt>Telefon</dt><dd><a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ` · <a href="tel:+998${st.phone2}">${st.phone2}</a>` : ''}</dd>
            <dt>Vasiy</dt><dd>${parent ? `${parent.relation ? esc(parent.relation) + ': ' : ''}${esc(parent.first_name)} ${esc(parent.last_name)} · <a href="tel:+998${parent.phone}">${parent.phone}</a>` : '—'}</dd>
            <dt>Kurs / guruh</dt><dd>${esc(A.courseName(c.course))} · <a href="#/groups/${c.group}">${esc(A.groupName(c.group))}</a></dd>
            <dt>Muddat</dt><dd>${A.fdate(c.start)} — ${c.end ? A.fdate(c.end) : '…'}</dd>
            ${c.stop_reason ? `<dt>To'xtatish sababi</dt><dd>${esc(c.stop_reason)}</dd>` : ''}
            <dt>Yosh guruhi</dt><dd>${esc(c.age_group || '—')}</dd>
            <dt>Izoh</dt><dd>${esc(c.comment || '—')}</dd>
            <dt>Qo'shdi</dt><dd>${esc(A.userName(c.created_by))}, ${A.fdt(c.created_at)}</dd>
          </dl>${edit.ok ? '' : `<p class="muted small">${esc(edit.why)}${stopOnly ? ". Shartnomani to'xtatish mumkin (tugash sanasi oxirgi 30 kun ichida)" : ''}</p>`}</section>
          <section class="card"><h2>Qarz qanday hisoblandi</h2>
            <table class="calc"><tr><td>Boshlang'ich qoldiq (AppSheet'dan)</td><td class="num">${A.num(c.opening)}</td></tr>
            <tr><td>+ Darslar uchun hisoblangan (Σ talaba qarzi)</td><td class="num">${A.num(c.charged)}</td></tr>
            <tr><td>− To'lovlar</td><td class="num">${A.num(c.paid)}</td></tr>
            <tr><td>− Chegirmalar</td><td class="num">${A.num(c.discount)}</td></tr>
            <tr class="tot"><td>= Balans</td><td class="num">${A.num(c.balance)}</td></tr></table>
            <p class="muted small">Bir dars narxi = kurs narxi ÷ oydagi dars soni. Talaba kelmasa ham dars uchun qarz yoziladi ("Nofaol" va Grant bundan mustasno).</p>
          </section>
        </div>
        ${A.can('calls', 'v') || A.can('sms', 'v') ? '<section class="card" id="stu-calls"></section>' : ''}
        ${A.tabs([['att', 'Davomat', att.length], ...(A.can('payments') ? [['pay', "To'lovlar", pays.length]] : [])], tab, 'contracts/' + id)}
        ${tab === 'pay'
          ? A.table(
              [
                { h: 'Sana', f: (p) => A.fdate(p.date) },
                { h: '№', f: (p) => p.number },
                { h: 'Summa', f: (p) => A.num(p.amount), cls: 'num', sum: (r) => A.num(A.sum(r, (p) => Number(p.amount))) },
                { h: 'Turi', f: (p) => (p.amount ? A.CASH[p.cash_type] : '—') + (p.nc_status ? ' ' + A.badge(p.nc_status, p.nc_status === 'Tasdiqlandi' ? 'green' : 'orange') : '') },
                { h: 'Chegirma', f: (p) => (Number(p.discount) ? `${A.num(p.discount)} ${A.badge(p.disc_status, p.disc_status === 'Tasdiqlandi' ? 'green' : 'orange')}` : '—'), cls: 'num' },
                { h: '', f: (p) => (A.payActions ? A.payActions(p) : `<a href="#" data-act="receipt" data-id="${p.id}">Chek</a>`) },
              ],
              pays,
              { empty: "To'lov yo'q" },
            )
          : A.table(
              [
                { h: 'Sana', f: (a) => `${A.fdate(a.date)} <span class="muted small">${A.WD[A.isoWeekday(a.date)]}</span>` },
                { h: 'Status', f: (a) => A.attSelect({ contract: cDetail.id, group: a.group, date: a.date, status: a.status, comment: a.comment }) },
                { h: 'Ustoz', f: (a) => esc(A.userName(a.teacher)) + (g && a.teacher !== g.teacher ? ' ' + A.badge("o'rindosh", 'blue') : '') },
                { h: 'Dars narxi (qarz)', f: (a) => (a.no_freq ? A.badge(a.calc_note || 'hisoblanmagan', 'orange') : A.num(a.debt)), cls: 'num', sum: (r) => A.num(A.sum(r, (a) => a.debt || 0)) },
                { h: 'Izoh', f: (a) => esc(a.comment || '') },
              ],
              att,
              { empty: "Davomat yo'q" },
            )}`;
    },
  });
  A.act['contract-edit'] = () => A.contractForm(cDetail);
  A.act['contract-stop'] = () => A.contractForm(cDetail, {}, true);

  /* ===================================================== Qarzdorlar */
  let dData = { results: [], total: 0, count: 0 };
  let mData = { results: [], total: 0, count: 0, overdue_count: 0, overdue_total: 0 };
  A.page('debtors', {
    title: 'Qarzdorlar',
    section: 'debtors',
    async load(p, q) {
      if ((q.tab || 'month') === 'month') {
        mData = await A.http.get('/debtors/month/?' + filterQS('debtors', ['search', 'course', 'state', 'month', 'dismissed']));
        mData.results.forEach(A.keepContract);
      } else {
        dData = await A.http.get('/debtors/?' + filterQS('debtors', ['search', 'course', 'status']));
        dData.results.forEach(A.keepContract);
      }
    },
    render(p, q) {
      const tab = q.tab || 'month';
      const tabs = A.tabs([['month', "To'lovga tavsiya"], ['debt', 'Qarz (davomat bo\'yicha)']], tab, 'debtors');
      const month = `<input class="f-input" type="month" data-filter="debtors:month" title="Oy" value="${esc(A.q('debtors:month', '') || mData.month || '')}">`;
      if (tab === 'month') {
        return `${A.head("To'lovga tavsiya", "Eslatma uchun: shu oy kurs narxi bo'yicha to'lov qilmaganlar. Bu qarz emas (qarz — «Qarz (davomat bo'yicha)» tabida). To'lov qilganini «✓ To'lov qilgan» bilan ro'yxatdan olib tashlang", `${A.can('sms', 'a') ? A.btn('SMS yuborish', 'due-sms-all', { icon: 'sms' }) : ''}${A.btn('Excel', 'debtors-csv', { cls: 'ghost', icon: 'download' })}`)}
        ${tabs}
        ${A.filterBar('debtors', [A.fSearch('debtors'), A.fSelect('debtors', 'course', A.optList('courses'), 'Barcha kurslar'),
          A.fSelect('debtors', 'state', [['wait', 'Kutilmoqda'], ['overdue', "Muddati o'tgan"]], 'Barcha holatlar'),
          ...(A.can('payments', 'a') ? [A.fSelect('debtors', 'dismissed', [['1', "Olib tashlanganlar"]], 'Tavsiyadagilar')] : []), month])}
        <div>${monthDues(mData)}</div>`;
      }
      return `${A.head('Qarzdorlar', "Davomat bo'yicha qarzi 0 dan katta shartnomalar. Chapdagi daraxt: filial → kurs → guruh", A.btn('Excel', 'debtors-csv', { cls: 'ghost', icon: 'download' }))}
        ${tabs}
        ${A.filterBar('debtors', [A.fSearch('debtors'), A.fSelect('debtors', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('debtors', 'status', [['Faol', 'Faol'], ['Nofaol', 'Nofaol']], 'Barcha statuslar')])}
        <div>${debtorGroups(dData)}</div>`;
    },
  });
  /* Daraxt (Barchasi → filial → kurs → guruh, har tugunda summa) va tanlangan tugun bo'yicha jadval — ikkala tab uchun */
  function treeView(key, rows, amount, emptyMsg, cols, statsHTML) {
    const opts = { value: (l) => A.num(A.sum(l, amount)) };
    const sel = A.treeFilter(key, rows, opts);
    const stats = statsHTML(sel);
    if (!rows.length) return A.empty(emptyMsg);
    return `<div class="settings tree-layout">${A.treeNav(key, rows, opts)}<div class="settings-body">${stats}${sel.length ? A.table(cols, A.sortBy(sel, amount, true)) : A.empty(emptyMsg)}</div></div>`;
  }
  const contractCol = { h: 'Shartnoma', f: (c) => `<a class="t-red" href="#/contracts/${c.id}">${esc(c.name)}</a>` };
  const phoneCol = { h: 'Telefon', f: (c) => [c.student_data.phone1, c.student_data.phone2].filter(Boolean).map((t) => `<a href="tel:+998${t}">${t}</a>`).join('<br>') };
  const payCol = { h: '', f: (c) => (paymentsReady() ? `<button class="btn sm" data-act="pay-new" data-id="${c.id}">To'lov</button>` : '') };
  const groupCol = { h: 'Guruh', f: (c) => esc(A.groupName(c.group)) };
  const dismissCol = (restore) => ({ h: '', f: (c) => (A.can('payments', 'a') ? `<button class="btn sm ${restore ? 'ghost' : 'success'}" data-act="${restore ? 'due-restore' : 'due-dismiss'}" data-id="${c.id}">${restore ? 'Qaytarish' : "✓ To'lov qilgan"}</button>` : '') });
  const dueMonth = () => (mData.month || '');
  const dueCall = async (el, what, msg) => {
    await A.http.post(`/debtors/${el.dataset.id}/${what}/`, { month: dueMonth() });
    A.toast(msg);
    A.refresh();
  };
  /* SMS (2026-10-22): qabul telefoni orqali to'lov eslatmasi — forma va jurnal pages-calls.js da (A.smsDueForm) */
  let dueSel = [];
  const smsCol = { h: 'SMS', f: (c) => {
    const s = c.sms;
    const badge = !s ? '' : s.failed && !s.sent && !s.queued ? A.badge(`✕ xato (${s.failed})`, 'red')
      : s.queued ? A.badge(`⏳ navbatda (${s.queued})`, 'orange') : A.badge(`✓ ${s.sent}`, 'green');
    const tip = s ? `title="${esc(`SMS: yuborildi ${s.sent}, navbatda ${s.queued}, xato ${s.failed} · ${s.at}`)}"` : '';
    const btn = A.can('sms', 'a') ? `<button class="btn sm ghost" data-act="due-sms" data-id="${c.id}" title="SMS yuborish">✉</button>` : '';
    return `<span ${tip} style="white-space:nowrap">${badge} ${btn}</span>`;
  } };
  A.act['due-sms'] = (el) => A.smsDueForm(mData.results.filter((c) => String(c.id) === el.dataset.id), dueMonth());
  A.act['due-sms-all'] = () => {
    if (!dueSel.length) return A.toast("Ro'yxatda talaba yo'q", 'warn');
    A.smsDueForm(dueSel, dueMonth());
  };
  A.act['due-dismiss'] = (el) => dueCall(el, 'dismiss', "Tavsiya ro'yxatidan olib tashlandi");
  A.act['due-restore'] = (el) => dueCall(el, 'restore', "Tavsiyaga qaytarildi");
  function monthDues(d) {
    const gone = /dismissed=1/.test(location.hash) || A.q('debtors:dismissed', '') === '1';
    const prev = (c) => (c.prev_balance > 0 ? `<span class="t-red">${A.num(c.prev_balance)} qarz</span>` : c.prev_balance < 0 ? `<span class="t-green">${A.num(-c.prev_balance)} oldindan</span>` : '—');
    const cols = [
      contractCol, phoneCol, groupCol,
      { h: 'Oy narxi', f: (c) => `${A.num(c.month_price)}${c.lessons < c.lessons_total ? ` <span class="muted" title="Oyning ${c.lessons}/${c.lessons_total} darsi">(${c.lessons}/${c.lessons_total})</span>` : ''}${c.no_price ? ' ' + A.badge("narx yo'q", 'orange') : ''}`, cls: 'num' },
      { h: 'Oldingi balans', f: prev, cls: 'num' },
      { h: "Shu oy to'langan", f: (c) => A.num(c.paid_month), cls: 'num' },
      { h: "Tavsiya summasi", f: (c) => `<b class="t-red">${A.num(c.to_pay)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, 'to_pay')) },
      { h: 'Holat', f: (c) => (c.overdue ? A.badge(`Muddati o'tgan · ${c.days_over} kun`, 'red') : A.badge(`${c.deadline.slice(8)}.${c.deadline.slice(5, 7)} gacha`, 'orange')) },
      ...(A.can('sms') && !gone ? [smsCol] : []),
      payCol,
      dismissCol(gone),
    ];
    return treeView('dm', d.results, (c) => c.to_pay, gone ? "Olib tashlangan o'quvchi yo'q" : "Tavsiya qilinadigan o'quvchi yo'q", cols, (sel) => {
      dueSel = gone ? [] : sel;
      const over = sel.filter((c) => c.overdue);
      return `<div class="stats">${A.stat("To'lovga tavsiya", A.money(A.sum(sel, 'to_pay')), `${sel.length} ta o'quvchi`, 'danger')}
        ${A.stat("Muddati o'tgan", A.money(A.sum(over, 'to_pay')), `${over.length} ta o'quvchi`, over.length ? 'danger' : '')}</div>`;
    });
  }
  function debtorGroups(d) {
    const cols = [
      contractCol, phoneCol, groupCol,
      { h: 'Status', f: (c) => A.contractStatusBadge(c.status) },
      { h: 'Qarz', f: (c) => `<b class="t-red">${A.num(c.balance)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, 'balance')) },
      payCol,
    ];
    return treeView('dd', d.results, (c) => c.balance, "Qarzdor yo'q", cols, (sel) => `<div class="stats">${A.stat('Jami qarz', A.money(A.sum(sel, 'balance')), `${sel.length} ta shartnoma`, 'danger')}</div>`);
  }
  A.act['debtors-csv'] = () => {
    if ((A.route && A.route.q && A.route.q.tab) === 'debt' || /tab=debt/.test(location.hash)) {
      A.downloadCSV('qarzdorlar.csv', [['Shartnoma', 'Telefon', 'Guruh', 'Status', 'Qarz'], ...dData.results.map((c) => [c.name, c.student_data.phone1, A.groupName(c.group), c.status, c.balance])]);
    } else {
      A.downloadCSV('shu-oy-tolovi.csv', [['Oquvchi', 'Telefon', 'Telefon 2', 'Guruh', 'Oy narxi', 'Oldingi balans', 'Shu oy tolangan', 'Tolashi kerak', 'Muddat'],
        ...mData.results.map((c) => [c.name, c.student_data.phone1, c.student_data.phone2 || '', A.groupName(c.group), c.month_price, c.prev_balance, c.paid_month, c.to_pay, c.deadline])]);
    }
  };
})(window.App);

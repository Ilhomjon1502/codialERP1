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

  /* ===================================================== Lidlar */
  const LS = A.LEAD_STATUSES;
  const leadStatusTone = { 1: 'gray', 2: 'blue', 3: 'orange', 4: 'orange', 5: 'green', 6: 'red', 7: 'red', 8: 'gray' };

  A.page('leads', {
    title: 'Lidlar',
    section: 'leads',
    render(p, q) {
      const tab = q.tab || 'funnel';
      const leads = A.vis('leads');
      const actions = A.can('leads', 'a') ? A.btn('Yangi lid', 'lead-new', { icon: 'plus' }) : '';
      return `${A.head('Lidlar', 'Murojaatlar voronkasi: birinchi qo\'ng\'iroqdan shartnomagacha', actions)}
        ${A.tabs([['funnel', 'Voronka', leads.length], ['list', "Ro'yxat"], ['stats', 'Statistika'], ['paid', "To'lov qilganlar"]], tab, 'leads')}
        ${tab === 'stats' ? '' : A.filterBar('leads', [A.fSearch('leads', 'Ism yoki telefon…'), A.fSelect('leads', 'course', A.optList('courses'), 'Barcha kurslar'), A.fSelect('leads', 'source', A.optList('leadSources'), 'Barcha manbalar')])}
        <div data-results>${this.results(p, q)}</div>`;
    },
    results(p, q) {
      const tab = q.tab || 'funnel';
      let leads = A.vis('leads');
      const s = A.q('leads:search', ''), c = A.q('leads:course', ''), src = A.q('leads:source', '');
      leads = leads.filter((l) => {
        const st = A.get('students', l.student) || {};
        return A.match(A.studentName(st) + ' ' + st.phone1, s) && (!c || l.course === c) && (!src || l.source === src);
      });
      if (tab === 'funnel') return funnel(leads);
      if (tab === 'list') return leadTable(A.sortBy(leads, (l) => l.created_at, true));
      if (tab === 'paid') {
        const paid = leads.filter((l) => A.rows('payments').some((pay) => (A.get('contracts', pay.contract) || {}).student === l.student));
        return `<p class="muted">Talabasi kamida bitta to'lov qilgan lidlar (AppSheet: Lead_payments slice).</p>` + leadTable(paid);
      }
      return leadStats(A.vis('leads'));
    },
  });

  function contractStatusOf(l) {
    const has = A.hasContract(l.student);
    const tone = has ? 'green' : l.status === '5' ? 'red' : 'orange';
    return `<span class="t-${tone}">${has ? 'Tuzilgan' : 'Tuzilmagan'}</span>`;
  }

  function funnel(leads) {
    const cols = Object.keys(LS).map((k) => {
      const list = A.sortBy(leads.filter((l) => l.status === k), (l) => l.created_at, true);
      return `<div class="kcol"><div class="kcol-h"><span class="badge ${leadStatusTone[k]}">${k}</span> ${esc(LS[k])} <b>${list.length}</b></div>
        ${list
          .slice(0, 40)
          .map((l) => {
            const st = A.get('students', l.student) || {};
            return `<button class="kcard" data-act="lead-open" data-id="${l.id}">
              <b>${esc(st.first_name)} ${esc(st.last_name)}</b>
              <span class="muted small">${esc(A.courseName(l.course))} · ${esc(A.sourceName(l.source))}</span>
              ${l.demo_date && ['3', '4'].includes(l.status) ? `<span class="small">Sinov: ${A.fdate(l.demo_date)}</span>` : ''}
              ${l.status === '5' || A.hasContract(l.student) ? `<span class="small">Shartnoma: ${contractStatusOf(l)}</span>` : ''}
            </button>`;
          })
          .join('') || '<div class="muted small pad">—</div>'}
      </div>`;
    });
    const total = leads.length || 1;
    const reached = (k) => leads.filter((l) => Number(l.status) >= Number(k) && Number(l.status) <= 5).length;
    const conv = `<div class="conv">${['3', '4', '5']
      .map((k) => `<div><span class="muted small">${k}-bosqichga yetgan (${esc(LS[k]).toLowerCase()})</span><b>${A.pct(reached(k) / total)}</b></div>`)
      .join('')}<div><span class="muted small">Lid → shartnoma</span><b>${A.pct(leads.filter((l) => A.hasContract(l.student)).length / total)}</b></div></div>`;
    return conv + `<div class="kanban">${cols.join('')}</div>`;
  }

  function leadTable(leads) {
    return A.table(
      [
        { h: 'Murojaatchi', f: (l) => `<a href="#" data-act="lead-open" data-id="${l.id}">${esc(A.studentName(l.student))}</a>` },
        { h: 'Telefon', f: (l) => esc((A.get('students', l.student) || {}).phone1) },
        { h: 'Kurs', f: (l) => esc(A.courseName(l.course)) },
        { h: 'Manba', f: (l) => esc(A.sourceName(l.source)) },
        { h: 'Status', f: (l) => A.badge(`${l.status}. ${LS[l.status]}`, leadStatusTone[l.status]) },
        { h: 'Shartnoma', f: contractStatusOf },
        { h: "Qo'shilgan", f: (l) => A.fdate(A.iso(new Date(l.created_at))) },
      ],
      leads,
    );
  }

  function leadStats(leads) {
    const bySrc = A.groupBy(leads, (l) => l.source);
    const srcRows = A.rows('leadSources').map((s) => {
      const list = bySrc.get(s.id) || [];
      const conv = list.filter((l) => A.hasContract(l.student)).length;
      return { name: s.name, n: list.length, conv, rate: list.length ? conv / list.length : 0 };
    });
    const months = [...new Set(leads.map((l) => A.ym(A.iso(new Date(l.created_at)))))].sort();
    const byStatus = Object.keys(LS).map((k) => leads.filter((l) => l.status === k).length);
    const ages = [...new Set(leads.map((l) => l.age_group))].sort((a, b) => parseInt(a) - parseInt(b));
    return `<div class="grid-2">
      <section class="card"><h2>Manba bo'yicha konversiya</h2>${A.table(
        [
          { h: 'Manba', f: (r) => esc(r.name) },
          { h: 'Lidlar', f: (r) => r.n, cls: 'num' },
          { h: 'Shartnoma', f: (r) => r.conv, cls: 'num' },
          { h: 'Konversiya', f: (r) => `<b>${A.pct(r.rate)}</b>`, cls: 'num' },
        ],
        A.sortBy(srcRows, (r) => r.n, true),
      )}</section>
      <section class="card"><h2>Status bo'yicha</h2>${A.chart({ type: 'doughnut', data: { labels: Object.values(LS), datasets: [{ data: byStatus, backgroundColor: A.PALETTE }] } }, 260)}</section>
      <section class="card"><h2>Oylar bo'yicha yangi lidlar (manba kesimida)</h2>${A.chart({
        type: 'bar',
        data: { labels: months.map(A.ymLabel), datasets: A.rows('leadSources').map((s, i) => ({ label: s.name, data: months.map((m) => leads.filter((l) => l.source === s.id && A.ym(A.iso(new Date(l.created_at))) === m).length), backgroundColor: A.PALETTE[i] })) },
        options: { scales: { x: { stacked: true }, y: { stacked: true } } },
      })}</section>
      <section class="card"><h2>Yosh guruhi va ijtimoiy holat</h2>${A.chart({ type: 'bar', data: { labels: ages, datasets: [{ label: 'Lidlar', data: ages.map((a) => leads.filter((l) => l.age_group === a).length), backgroundColor: A.PALETTE[0] }] }, options: { plugins: { legend: { display: false } } } }, 200)}
      ${A.table([{ h: 'Ijtimoiy holat', f: (r) => esc(r[0]) }, { h: 'Soni', f: (r) => r[1], cls: 'num' }], [...A.groupBy(leads, (l) => l.social)].map(([k, v]) => [k, v.length]))}</section>
    </div>`;
  }

  /* ---- Lid formasi (AppSheet Show_If zanjiri bo'yicha) ---- */
  A.leadForm = (lead) => {
    const isNew = !lead;
    const B = A.branchIds()[0];
    const v = lead ? { ...lead } : { branch: B, status: '2', times: [], tags: [], mode: 'new' };
    const freeStudents = () =>
      A.rows('students')
        .filter((s) => s.branch === B && !A.hasContract(s.id) && !A.rows('leads').some((l) => l.student === s.id && (!lead || l.id !== lead.id)))
        .map((s) => [s.id, `${A.studentName(s)} · ${s.phone1}`]);
    const fields = [
      { name: 'mode', label: 'Murojaatchi', type: 'seg', options: [['new', 'Yangi talaba'], ['old', "Bazadagi talaba"]], show: () => isNew },
      { name: 'student', label: 'Talabani tanlang', type: 'select', options: freeStudents, show: (x) => !isNew || x.mode === 'old', required: true, readonly: () => !isNew, help: "Shartnomasi bor yoki lidi ochilgan talabalar ro'yxatda chiqmaydi" },
      { name: 'first_name', label: 'Ism', show: (x) => isNew && x.mode === 'new', required: true, half: true, validate: (t) => (t.length < 3 || t.length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
      { name: 'last_name', label: 'Familiya', show: (x) => isNew && x.mode === 'new' && x.first_name, required: true, half: true, validate: (t) => (t.length < 3 || t.length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
      { name: 'phone1', label: '1-telefon (+998)', placeholder: '901234567', show: (x) => isNew && x.mode === 'new' && x.last_name, required: true, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin. Masalan, 998883322" : '') },
      {
        name: 'phone2', label: '2-telefon (+998)', placeholder: '911234567', show: (x) => isNew && x.mode === 'new' && x.last_name, required: true, half: true,
        validate: (t, x) => {
          if (!/^\d{9}$/.test(t)) return "9 sondan iborat bo'lsin. Masalan, 998883322";
          if (t === x.phone1) return "Ikki bir xil nomer kiritib bo'lmaydi!";
          // Dublikat: shu filialda ism + familiya bir xil va telefonlardan biri mos kelsa
          const same = (a, b) => (a || '').trim().toLowerCase() === (b || '').trim().toLowerCase();
          const dup = A.rows('students').some((s) => s.branch === B && same(s.first_name, x.first_name) && same(s.last_name, x.last_name) && [s.phone1, s.phone2].some((p) => p && (p === x.phone1 || p === t)));
          return dup ? "Ushbu o'quvchi avval kiritilgan. Lidlar yoki shartnomalar oynasidan qidiring" : '';
        },
      },
      { name: 'comment', label: 'Izoh', type: 'textarea', placeholder: "Masalan: narxni so'radi, kechki guruh bo'lsa yoziladi", show: (x) => isNew && (x.student || (x.phone1 && x.phone2)) },
      { name: 'gender', label: 'Jins', type: 'seg', options: ['Erkak', 'Ayol'], show: (x) => isNew && x.mode === 'new' && x.phone1 && x.phone2 },
      { name: 'age_group', label: 'Yosh guruhi', type: 'select', options: ['9-12', '13-15', '16-18', '19-21', '22-24', '25-27', '28-30', '31-33', '34-36', '37-39', '40-42'], show: (x) => x.student || (x.phone1 && x.phone2), half: true },
      { name: 'social', label: 'Ijtimoiy holati', type: 'select', options: ["Maktab o'quvchisi", 'Oliygoh talabasi', 'Kompaniya xodimi', 'Davlat xizmatchisi', 'Vaqtincha ishsiz'], show: (x) => x.age_group, half: true },
      { name: 'laptop', label: 'Noutbuki bormi?', type: 'seg', options: ['Bor', "Yo'q", 'Sotib oladi'], show: (x) => x.social },
      { name: 'tags', label: 'Teglar', type: 'chips', options: ['VIP', "Chegirma so'radi", "Ota-onasi qo'ng'iroq qiladi", 'Kechki vaqt', 'Hafta oxiri'], show: (x) => x.laptop },
      { name: 'source', label: 'Manba', type: 'select', options: () => A.optList('leadSources'), required: true, half: true },
      { name: 'course', label: 'Kurs', type: 'select', options: () => A.optList('courses', 'name', (c) => c.status === 'Faol' && c.branches.includes(B)), required: true, half: true, resets: ['group'] },
      { name: 'pattern', label: 'Hafta kunlari', type: 'seg', options: () => A.optList('dayPatterns') },
      { name: 'times', label: "Ma'qul dars vaqti", type: 'chips', options: () => A.optList('lessonTimes', (t) => `${t.start}-${t.end}`, (t) => t.branch === B) },
      { name: 'status', label: 'Status', type: 'select', options: Object.entries(LS).map(([k, l]) => [k, `${k}. ${l}`]), required: true },
      {
        name: 'group', label: 'Guruh', type: 'select', show: (x) => ['3', '4', '5'].includes(x.status) || (x.group && !['1', '2'].includes(x.status)),
        options: (x) => A.rows('groups').filter((g) => g.branch === B && g.course === x.course && A.groupStatus(g) !== 'Nofaol').map((g) => [g.id, `${A.groupName(g)} · ${A.patternName(g.pattern)} ${A.timeName(g.time)} (${A.groupStatus(g)})`]),
        help: '3, 4, 5-statuslarda ko\'rinadi. Faqat shu kursning faol yoki rejadagi guruhlari',
      },
      { name: 'demo_date', label: 'Sinov dars kuni', type: 'date', show: (x) => x.group && ['3', '4', '5'].includes(x.status), default: A.today() },
      { name: 'demo_attended', label: 'Sinov darsga qatnashdimi?', type: 'seg', options: [['yes', 'Ha, qatnashdi'], ['no', 'Kelmadi']], show: (x) => x.demo_date && x.group && ['3', '4', '5'].includes(x.status) },
    ];
    if (lead) v.demo_attended = lead.demo_attended === true ? 'yes' : lead.demo_attended === false ? 'no' : '';
    A.form({
      title: isNew ? 'Yangi lid' : 'Lidni tahrirlash',
      fields,
      values: v,
      onSubmit(x) {
        let studentId = x.student;
        if (isNew && x.mode === 'new') {
          const s = A.insert('students', { branch: B, first_name: x.first_name.trim(), last_name: x.last_name.trim(), father_name: '', gender: x.gender, phone1: x.phone1, phone2: x.phone2, birth_date: '', parent: '' }, 'Talaba', `${x.first_name} ${x.last_name}`);
          studentId = s.id;
        }
        const rec = {
          branch: B, student: studentId, source: x.source, course: x.course, pattern: x.pattern, times: x.times, status: x.status,
          group: x.group, demo_date: x.demo_date, demo_attended: x.demo_attended === 'yes' ? true : x.demo_attended === 'no' ? false : null,
          age_group: x.age_group, social: x.social, laptop: x.laptop, tags: x.tags,
        };
        let id;
        if (isNew) id = A.insert('leads', rec, 'Lid', A.studentName(studentId)).id;
        if (isNew && x.comment && x.comment.trim()) A.insert('leadComments', { branch: B, lead: id, comment: x.comment.trim() }, 'Lid izohi', A.studentName(studentId));
        else { A.patch('leads', lead.id, rec, 'Lid', A.studentName(studentId)); id = lead.id; }
        A.toast(isNew ? "Lid qo'shildi" : 'Saqlandi');
        A.refresh();
        if (rec.status === '5') setTimeout(() => A.openLead(id), 50);
      },
    });
  };
  A.act['lead-new'] = () => A.leadForm(null);

  A.openLead = (id) => {
    const l = A.get('leads', id);
    const st = A.get('students', l.student);
    const comments = A.sortBy(A.rows('leadComments').filter((c) => c.lead === id), (c) => c.created_at, true);
    const contract = A.rows('contracts').find((c) => c.student === l.student);
    const edit = A.canEdit('leads', l, 'created_at');
    const canContract = l.status === '5' && !contract && A.can('contracts', 'a');
    const needsBirth = l.status === '5' && !st.birth_date;
    const m = A.modal({
      title: A.studentName(st),
      wide: true,
      body: `
        <div class="detail-top">
          ${A.badge(`${l.status}. ${LS[l.status]}`, leadStatusTone[l.status])}
          <span>Shartnoma: ${contractStatusOf(l)}</span>
          ${l.tags && l.tags.length ? l.tags.map((t) => A.badge(t, 'gray')).join('') : ''}
        </div>
        ${needsBirth ? `<div class="alert warn">${A.icon('alert')}<div>O'qishni boshladi, lekin talabaning to'liq ma'lumotlari (tug'ilgan sana, vasiy) kiritilmagan. Avval talaba ma'lumotlarini to'ldiring.</div></div>` : ''}
        <dl class="dl">
          <dt>Telefon</dt><dd><a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ` · <a href="tel:+998${st.phone2}">+998 ${st.phone2}</a>` : ''}</dd>
          <dt>Kurs</dt><dd>${esc(A.courseName(l.course))}</dd>
          <dt>Manba</dt><dd>${esc(A.sourceName(l.source))}</dd>
          <dt>Hafta kunlari / vaqt</dt><dd>${esc(A.patternName(l.pattern))} · ${(l.times || []).map(A.timeName).join(', ') || '—'}</dd>
          <dt>Guruh</dt><dd>${l.group ? esc(A.groupName(l.group)) : '—'}</dd>
          <dt>Sinov darsi</dt><dd>${A.fdate(l.demo_date)} ${l.demo_attended === true ? A.badge('Keldi', 'green') : l.demo_attended === false ? A.badge('Kelmadi', 'red') : ''}</dd>
          <dt>Yosh / holat / noutbuk</dt><dd>${esc(l.age_group || '—')} · ${esc(l.social || '—')} · ${esc(l.laptop || '—')}</dd>
          <dt>Qo'shdi</dt><dd>${esc(A.userName(l.created_by))}, ${A.fdt(l.created_at)}</dd>
        </dl>
        ${A.can('leads', 'e') ? `<h4>Statusni o'zgartirish</h4><div class="seg wrap">${Object.entries(LS)
          .map(([k, t]) => `<button class="${l.status === k ? 'on' : ''}" data-status="${k}" ${edit.ok ? '' : 'disabled'}>${k}. ${esc(t)}</button>`)
          .join('')}</div>${edit.ok ? '' : `<p class="muted small">${esc(edit.why)}</p>`}` : ''}
        <h4>Izohlar (${comments.length})</h4>
        ${A.can('leads', 'a') ? `<div class="row gap"><input class="f-input grow" id="lc-text" placeholder="Izoh yozing…"><button class="btn" id="lc-add">Qo'shish</button></div>` : ''}
        <ul class="comments">${comments.map((c) => `<li><p>${esc(c.comment)}</p><small class="muted">${esc(A.userName(c.created_by))} · ${A.fdt(c.created_at)}</small></li>`).join('') || '<li class="muted">Izoh yo\'q</li>'}</ul>`,
      footer: `
        ${A.can('leads', 'e') && edit.ok ? `<button class="btn ghost" data-edit>Tahrirlash</button>` : ''}
        ${needsBirth && A.can('leads', 'e') ? `<button class="btn" data-student>Talaba ma'lumotlarini to'ldirish</button>` : ''}
        ${contract ? `<a class="btn" href="#/contracts/${contract.id}" data-close>Shartnomani ochish</a>` : ''}
        ${canContract ? `<button class="btn primary" data-contract ${needsBirth ? 'disabled title="Avval talaba ma\'lumotlarini to\'ldiring"' : ''}>Shartnoma tuzish</button>` : ''}`,
    });
    m.el.querySelectorAll('[data-status]').forEach((b) =>
      (b.onclick = () => {
        A.patch('leads', id, { status: b.dataset.status }, 'Lid', A.studentName(st));
        m.close();
        A.refresh();
        A.openLead(id);
        if (b.dataset.status === '3' || b.dataset.status === '4' || b.dataset.status === '5') {
          if (!A.get('leads', id).group) A.toast("Guruhni tanlash uchun «Tahrirlash»ni bosing", 'warn');
        }
      }));
    const add = m.el.querySelector('#lc-add');
    if (add)
      add.onclick = () => {
        const t = m.el.querySelector('#lc-text').value.trim();
        if (!t) return;
        A.insert('leadComments', { branch: l.branch, lead: id, comment: t }, 'Lid izohi', A.studentName(st));
        m.close();
        A.openLead(id);
      };
    const e = m.el.querySelector('[data-edit]');
    if (e) e.onclick = () => { m.close(); A.leadForm(l); };
    const sb = m.el.querySelector('[data-student]');
    if (sb) sb.onclick = () => { m.close(); A.studentForm(st, () => A.openLead(id)); };
    const cb = m.el.querySelector('[data-contract]');
    if (cb)
      cb.onclick = () => {
        if (!l.group) {
          A.toast('Avval lidga guruh tanlang', 'warn');
          return;
        }
        const g = A.get('groups', l.group);
        const num = Math.max(0, ...A.rows('contracts').filter((c) => c.branch === l.branch).map((c) => c.number)) + 1;
        const c = A.insert('contracts', { branch: l.branch, student: l.student, course: l.course, group: l.group, type: 'Pullik', number: num, start: l.demo_date || A.today(), end: '', stop_reason: '', comment: '', opening: 0 }, 'Shartnoma', `${A.studentName(st)} №${num}`);
        A.recalc((a) => a.contract === c.id);
        A.save();
        m.close();
        A.toast(`Shartnoma №${num} tuzildi: ${A.groupName(g)}`);
        A.go('contracts/' + c.id);
      };
  };
  A.act['lead-open'] = (el) => A.openLead(el.dataset.id);

  /* ---- Talaba formasi ---- */
  A.studentForm = (st, after) => {
    const B = st ? st.branch : A.branchIds()[0];
    A.form({
      title: st ? "Talaba ma'lumotlari" : 'Yangi talaba',
      values: st ? { ...st } : { branch: B },
      fields: [
        { name: 'first_name', label: 'Ism', required: true, half: true, validate: (t) => (t.length < 3 || t.length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'last_name', label: 'Familiya', required: true, half: true, validate: (t) => (t.length < 3 || t.length > 20 ? "Eng ozi 3 harf, ko'pi 20" : '') },
        { name: 'phone1', label: '1-telefon (+998)', required: true, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
        { name: 'father_name', label: 'Sharif', required: true, half: true, validate: (t) => (t.includes('.') ? "Nuqta qo'yib bo'lmaydi!" : t.length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'phone2', label: '2-telefon (+998)', half: true, validate: (t, x) => (t === x.phone1 ? "Ikki bir xil nomer kiritib bo'lmaydi!" : !/^\d{9}$/.test(t) ? "9 ta sondan iborat bo'lsin" : '') },
        { name: 'gender', label: 'Jins', type: 'seg', options: ['Erkak', 'Ayol'], half: true },
        { name: 'birth_date', label: "Tug'ilgan sanasi", type: 'date', required: true, half: true },
        { name: 'parent', label: 'Vasiy (ota-ona)', type: 'select', half: true, options: () => A.rows('parents').filter((p) => p.branch === B).map((p) => [p.id, `${p.first_name} ${p.last_name} · ${p.phone}`]), placeholder: "Tanlang yoki bo'sh qoldiring" },
        { name: 'new_parent', label: "Yangi vasiy qo'shish", type: 'checkbox', show: (x) => !x.parent },
        { name: 'p_first', label: 'Vasiy ismi', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, validate: (t) => (t.length < 3 ? 'Eng ozi 3 harf' : '') },
        { name: 'p_phone', label: 'Vasiy telefoni', show: (x) => x.new_parent, required: (x) => x.new_parent, half: true, validate: (t) => (!/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
      ],
      onSubmit(x) {
        let parent = x.parent;
        if (x.new_parent) parent = A.insert('parents', { branch: B, first_name: x.p_first, last_name: x.last_name, phone: x.p_phone }, 'Ota-ona', x.p_first).id;
        const rec = { first_name: x.first_name, last_name: x.last_name, father_name: x.father_name, phone1: x.phone1, phone2: x.phone2, gender: x.gender, birth_date: x.birth_date, parent };
        if (st) A.patch('students', st.id, rec, 'Talaba', A.studentName(st));
        else A.insert('students', { ...rec, branch: B }, 'Talaba', `${x.first_name} ${x.last_name}`);
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

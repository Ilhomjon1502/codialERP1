/* Guruhlar, Davomat, Baholash, Ota-onalar, Eksport */
(function (A) {
  const esc = A.esc;
  const fail = (e) => A.toast(e.message, 'warn');

  /* ===================================================== Guruhlar (server API: /groups/) */
  A.page('groups', {
    title: 'Guruhlar',
    section: 'groups',
    load: () => A.reloadGroups(),
    render(p, q) {
      const tab = q.tab || 'Faol';
      const all = A.vis('groups');
      const cnt = (s) => all.filter((g) => g.status === s).length;
      return `${A.head('Guruhlar', "Guruh nomi rangi — to'lish holati: qizil yomon, to'q sariq o'rtacha, ko'k yaxshi, yashil zo'r", A.can('groups', 'a') ? A.btn('Yangi guruh', 'group-new', { icon: 'plus' }) : '')}
        ${A.tabs([['Faol', 'Faol', cnt('Faol')], ['Rejada', 'Rejada', cnt('Rejada')], ['Nofaol', 'Nofaol', cnt('Nofaol')]], tab, 'groups')}
        <div class="cards">${A.sortBy(all.filter((g) => g.status === tab), (g) => A.groupName(g))
          .map((g) => {
            const f = A.groupFill(g);
            return `<a class="gcard" href="#/groups/${g.id}">
              <div class="gcard-h"><b class="t-${f.cls}">${esc(A.groupName(g))}</b>${A.badge(f.label, f.cls)}</div>
              <div class="muted small">${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}</div>
              <div class="small">Ustoz: <b>${esc(A.userName(g.teacher))}</b>${g.supporter ? ` · Yordamchi: ${esc(A.userName(g.supporter))}` : ''}</div>
              <div class="bar"><i class="bg-${f.cls}" style="width:${Math.min(100, f.pct * 100)}%"></i></div>
              <div class="small row between"><span>${f.n} / ${f.cap} talaba</span><span>${f.free} bo'sh o'rin · ${f.pctText}</span></div>
            </a>`;
          })
          .join('') || A.empty("Guruh yo'q")}</div>`;
    },
  });

  /* ---- Guruh formasi. Tekshiruvlar serverda ham bor (services.validate_group) ---- */
  A.groupForm = (g) => {
    const isNew = !g;
    const B = g ? g.branch : A.branchIds()[0];
    const staff = (roles, x) => A.S.users.filter((u) => roles.includes(u.role) && (u.status === 'Faol' || u.id === x) && (u.branches || []).includes(B));
    A.form({
      title: isNew ? 'Yangi guruh' : A.groupName(g),
      values: g ? { ...g } : { start: A.today() },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, readonly: () => !isNew && A.role() !== 'ADMIN', options: (x) => A.optList('courses', 'name', (c) => (c.status === 'Faol' && c.branches.includes(B)) || c.id === x.course), help: isNew ? '' : "Kursni faqat Admin o'zgartiradi (guruhda shartnoma bo'lmasa)" },
        { name: 'pattern', label: 'Dars kunlari', type: 'seg', required: true, show: (x) => x.course, options: (x) => A.optList('dayPatterns', 'name', (p) => (p.status || 'Faol') === 'Faol' || p.id === x.pattern) },
        { name: 'time', label: 'Dars vaqti', type: 'seg', required: true, show: (x) => x.pattern, options: (x) => A.optList('lessonTimes', (t) => `${t.start}-${t.end}`, (t) => t.branch === B && ((t.status || 'Faol') === 'Faol' || t.id === x.time)) },
        { name: 'teacher', label: 'Ustoz', type: 'select', required: true, show: (x) => x.time, options: (x) => staff(['USTOZ', 'USTOZ_YORDAMCHI'], x.teacher).map((u) => [u.id, u.full_name]) },
        { name: 'supporter', label: 'Yordamchi ustoz (ixtiyoriy)', type: 'select', show: (x) => x.teacher, options: (x) => staff(['YORDAMCHI', 'USTOZ_YORDAMCHI'], x.supporter).filter((u) => u.id !== x.teacher).map((u) => [u.id, u.full_name]), placeholder: "Yo'q" },
        {
          name: 'room', label: 'Xona', type: 'select', required: true, show: (x) => x.teacher,
          options: (x) => A.rows('rooms').filter((r) => r.branch === B && (r.status === 'Faol' || r.id === x.room)).map((r) => {
            const busy = A.rows('groups').some((o) => o.room === r.id && o.time === x.time && o.pattern === x.pattern && o.status !== 'Nofaol' && (!g || o.id !== g.id));
            return [r.id, `${r.name} (${r.capacity} o'rin)${busy ? ' — shu vaqtda band!' : ''}`];
          }),
        },
        { name: 'start', label: 'Boshlanish sana', type: 'date', required: true, show: (x) => x.room, half: true },
        { name: 'end', label: 'Tugash sana', type: 'date', show: (x) => x.room, half: true, validate: (d, x) => (d && d <= x.start ? "Boshlanish sanadan kichik bo'lolmaydi!" : '') },
        { name: 'num', label: 'Guruh raqami', type: 'computed', show: (x) => x.course, compute: (x) => (g ? `${A.courseName(x.course)} / #${g.number}` : `${A.courseName(x.course)} / avtomatik raqam`) },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.room },
      ],
      async onSubmit(x) {
        const rec = { course: x.course, pattern: x.pattern, time: x.time, teacher: x.teacher, supporter: x.supporter || null, room: x.room, start: x.start, end: x.end || null, comment: x.comment || '' };
        const saved = isNew ? await A.http.post('/groups/', rec) : await A.http.patch(`/groups/${g.id}/`, rec);
        A.putLocal('groups', saved);
        A.toast(isNew ? `Guruh yaratildi: ${saved.name}` : 'Saqlandi');
        if (isNew) A.go('groups/' + saved.id);
        else A.refresh();
      },
    });
  };
  A.act['group-new'] = () => A.groupForm(null);
  A.act['group-edit'] = (el) => A.groupForm(A.get('groups', el.dataset.id));

  /* ---- Guruh sahifasi: oylik davomat jurnali (/groups/{id}/journal/) ---- */
  let journal = null;
  A.page('groups/:id', {
    title: 'Guruh',
    section: 'groups',
    async load({ id }, q) {
      journal = await A.http.get(`/groups/${id}/journal/?month=${q.m || A.ym(A.today())}`);
      A.putLocal('groups', journal.group);
      journal.contracts.forEach(A.keepContract);
    },
    render({ id }) {
      const j = journal;
      const g = j.group;
      const f = A.groupFill(g);
      const ym = j.month;
      const today = A.today();
      const active = j.contracts.filter((c) => c.status !== 'Nofaol');
      const inactive = j.contracts.filter((c) => c.status === 'Nofaol');
      const cell = (cid, d) => {
        const s = (j.marks[cid] || {})[d];
        return s ? A.attBadge(s) : d < today ? '<span class="att att-empty">·</span>' : '';
      };
      const freq = j.frequency;
      return `<a class="back" href="#/groups">← Guruhlar</a>
        ${A.head(A.groupName(g), `${A.badge(g.status, g.status === 'Faol' ? 'green' : 'blue')} · ${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}`,
          `${A.can('attendance', 'a') && A.hasLesson(g, today) ? `<a class="btn primary" href="#/attendance?tab=take&group=${g.id}">${A.icon('check')}Davomat olish</a>` : ''}
           ${A.can('groups', 'e') ? A.btn('Tahrirlash', 'group-edit', { id, cls: 'ghost' }) : ''}`)}
        <div class="stats">
          ${A.stat("To'lish", `<span class="t-${f.cls}">${f.pctText}</span>`, `${f.label} · ${f.n}/${f.cap}`)}
          ${A.stat("Bo'sh o'rinlar", f.free)}
          ${A.stat('Ustoz', esc(A.userName(g.teacher)), g.supporter ? 'Yordamchi: ' + esc(A.userName(g.supporter)) : "Yordamchi yo'q")}
          ${A.stat(`${A.ymLabel(ym)}: dars soni`, freq ? freq.frequency : '—', freq ? (freq.status === 'Tasdiqlangan' ? 'tasdiqlangan' : 'TAKLIF — tasdiqlanmagan') : 'kiritilmagan', freq && freq.status !== 'Tasdiqlangan' ? 'warn' : '')}
        </div>
        <section class="card"><div class="row between"><h2>Davomat jurnali</h2>
          <select class="f-input" onchange="location.hash='#/groups/${id}?m='+this.value">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
          <div class="tbl-wrap"><table class="journal"><thead><tr><th>Talaba</th>${j.days.map((d) => `<th>${d.slice(8)}<br><small>${A.WD[A.isoWeekday(d)]}</small></th>`).join('')}<th>Qarz</th></tr></thead>
          <tbody>${active
            .map((c) => `<tr><td><a href="#/contracts/${c.id}" class="${c.balance > 0 ? 't-red' : ''}">${esc(c.student_data.full_name)}</a></td>${j.days.map((d) => `<td>${cell(c.id, d)}</td>`).join('')}<td class="num">${A.num(c.balance)}</td></tr>`)
            .join('')}</tbody></table></div>
          <p class="muted small">1 — keldi, 0 — sababli, X — besabab, – — nofaol, · — davomat olinmagan</p>
        </section>
        ${inactive.length ? `<section class="card"><h2>Nofaol talabalar</h2>${A.table([{ h: 'Shartnoma', f: (c) => `<a href="#/contracts/${c.id}">${esc(c.name)}</a>` }, { h: 'Tugagan', f: (c) => A.fdate(c.end) }, { h: 'Sabab', f: (c) => esc(c.stop_reason) }], inactive)}</section>` : ''}`;
    },
  });

  /* ---- Guruhlar tahlili (faol guruhlar; to'lish serverdan) ---- */
  A.page('groupAnalysis', {
    title: 'Guruhlar tahlili',
    section: 'groupAnalysis',
    load: () => A.reloadGroups(),
    render(p, q) {
      const tab = q.tab || 'status';
      const groups = A.vis('groups').filter((g) => g.status === 'Faol');
      const agg = (keyFn, labelFn) => {
        const m = A.groupBy(groups, keyFn);
        return [...m].map(([k, list]) => {
          const n = A.sum(list, (g) => A.groupFill(g).n), cap = A.sum(list, (g) => A.groupFill(g).cap);
          return { k, label: labelFn(k), groups: list, n, cap, pct: cap ? n / cap : 0 };
        });
      };
      const rows = tab === 'status' ? agg((g) => A.groupFill(g).label, (k) => k) : tab === 'teacher' ? agg((g) => g.teacher, A.userName) : agg((g) => g.course, A.courseName);
      return `${A.head('Faol guruhlar tahlili', `${groups.length} ta faol guruh`)}
        ${A.tabs([['status', "To'lish holati bo'yicha"], ['teacher', "Ustoz bo'yicha"], ['course', "Kurs bo'yicha"]], tab, 'groupAnalysis')}
        <div class="grid-2"><section class="card">${A.table(
          [
            { h: tab === 'status' ? 'Holat' : tab === 'teacher' ? 'Ustoz' : 'Kurs', f: (r) => `<b>${esc(r.label)}</b>` },
            { h: 'Guruhlar', f: (r) => r.groups.map((g) => `<a href="#/groups/${g.id}" class="t-${A.groupFill(g).cls}">${esc(A.groupName(g))}</a>`).join('<br>') },
            { h: 'Talabalar', f: (r) => `${r.n} / ${r.cap}`, cls: 'num' },
            { h: "O'rtacha to'lish", f: (r) => A.pct(r.pct), cls: 'num' },
          ],
          A.sortBy(rows, (r) => r.n, true),
        )}</section>
        <section class="card">${A.chart({ type: 'bar', data: { labels: rows.map((r) => r.label), datasets: [{ label: 'Talabalar', data: rows.map((r) => r.n), backgroundColor: A.PALETTE[0] }, { label: "Bo'sh o'rinlar", data: rows.map((r) => Math.max(0, r.cap - r.n)), backgroundColor: '#d9d9de' }] }, options: { indexAxis: 'y', scales: { x: { stacked: true }, y: { stacked: true } } } }, 280)}</section></div>`;
    },
  });

  /* ===================================================== Davomat (server API: /attendance/, /makeups/) */
  A.ui.att = { group: '', date: '', sub: false, subTeacher: '', subSupporter: '' };
  let attData = null;
  let attFresh = false; // POST javobi allaqachon yangi holat — qayta so'ramaslik uchun
  let mkPending = 0;

  A.page('attendance', {
    title: 'Davomatlar',
    section: 'attendance',
    async load(p, q) {
      const tab = q.tab || 'take';
      if (tab === 'take' && attFresh) { attFresh = false; return; }
      attData = null;
      if (tab === 'take') attData = await loadTake(q);
      else if (tab === 'absent') attData = await A.http.get(`/attendance/?month=${A.q('abs:month', A.ym(A.today()))}&status=${A.q('abs:status', '') || 'X,0'}&page=${A.q('abs:page', 1)}`);
      else if (tab === 'stats') attData = await A.http.get(`/attendance/stats/?month=${A.q('ast:month', A.ym(A.today()))}`);
      else attData = await A.http.get('/makeups/');
      if (tab === 'makeup') mkPending = attData.filter((m) => m.status === 'Kutilmoqda').length;
    },
    render(p, q) {
      const tab = q.tab || 'take';
      return `${A.head('Davomatlar', "Davomatni ustoz oladi. Menejerlar o'tgan sanalarni tuzatishi mumkin")}
        ${A.tabs([['take', 'Davomat olish'], ['absent', 'Kelmaganlar'], ['stats', 'Statistika'], ['makeup', 'Qoldirilgan darslar', mkPending || undefined]], tab, 'attendance')}
        ${tab === 'take' ? takeView() : tab === 'absent' ? absentView(attData) : tab === 'stats' ? statsView(attData) : makeupTable(attData)}`;
    },
  });

  const canTake = () => A.can('attendance', 'a');
  const isTeacherSelf = () => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role());
  const lessonMins = (g) => {
    const t = A.get('lessonTimes', g.time) || {};
    const m = (x) => { const [h, mm] = String(x || '00:00').split(':').map(Number); return h * 60 + mm; };
    return [m(t.start), m(t.end)];
  };
  // Ustoz: faqat bugun darsi bor o'z guruhlari, dars vaqti bo'yicha. Menejerlar — barcha faol guruhlar
  const takeGroups = () => {
    const d = isTeacherSelf() ? A.today() : A.ui.att.date || A.today();
    return A.vis('groups')
      .filter((g) => g.status === 'Faol' && A.hasLesson(g, d) && (!isTeacherSelf() || g.teacher === A.S.currentUser))
      .sort((a, b) => lessonMins(a)[0] - lessonMins(b)[0] || A.groupName(a).localeCompare(A.groupName(b)));
  };
  // Menejer: shu sanada darsi bor kurslar (guruhlar soni bilan)
  const takeCourses = (groups) => {
    const m = new Map();
    groups.forEach((g) => m.set(g.course, (m.get(g.course) || 0) + 1));
    return [...m].map(([id, n]) => ({ id, n, name: A.courseName(id) })).sort((a, b) => a.name.localeCompare(b.name));
  };
  // Standart guruh: hozir darsi ketayotgan (boshlanishidan 15 daqiqa oldin ham) → oxirgi 30 daqiqada tugagan → keyingisi → bugungi oxirgisi
  const nowMins = () => { const d = new Date(); return d.getHours() * 60 + d.getMinutes(); };
  const isNow = (g) => { const [a, b] = lessonMins(g); const n = nowMins(); return a - 15 <= n && n < b; };
  const currentGroup = (groups) => {
    const n = nowMins();
    return groups.find(isNow)
      || [...groups].reverse().find((g) => { const b = lessonMins(g)[1]; return b <= n && n < b + 30; })
      || groups.find((g) => lessonMins(g)[0] > n) || groups[groups.length - 1];
  };

  async function loadTake(q) {
    if (!canTake()) return null;
    const st = A.ui.att;
    if (!st.date || isTeacherSelf()) st.date = A.today();
    if (q.group) st.group = q.group;
    const groups = takeGroups();
    if (isTeacherSelf()) {
      if (groups.length === 1) st.group = groups[0].id;
      else if (!q.group && st.pickedOn !== A.today() && groups.length) st.group = currentGroup(groups).id; // o'zi tanlamagan bo'lsa — dars vaqtidagi guruh
    } else {
      // Menejer: avval kurs, keyin shu kursning shu kungi guruhi
      const picked = groups.find((g) => g.id === st.group);
      if (picked) st.course = picked.course;
      const courses = takeCourses(groups);
      if (courses.length === 1) st.course = courses[0].id;
      if (st.course && !courses.some((c) => c.id === st.course)) st.course = '';
      const inCourse = groups.filter((g) => g.course === st.course);
      if (inCourse.length === 1) st.group = inCourse[0].id;
      if (st.group && !inCourse.some((g) => g.id === st.group)) st.group = '';
    }
    if (st.group && !groups.some((g) => g.id === st.group)) st.group = '';
    if (!st.group) return null;
    return A.http.get(`/attendance/take/?group=${st.group}&date=${st.date}`);
  }

  function takeView() {
    if (!canTake()) {
      return `<div class="alert info">${A.icon('check')}<div><b>Davomatni faqat ustoz oladi.</b> Siz yordamchi sifatida guruh davomatini ko'rishingiz mumkin. Yordamchi KPI'si ustoz olgan davomat asosida avtomatik hisoblanadi.</div></div>
        ${A.vis('groups').map((g) => `<a class="btn ghost" href="#/groups/${g.id}">${esc(A.groupName(g))} jurnali</a>`).join(' ')}`;
    }
    const st = A.ui.att;
    const groups = takeGroups();
    const today = A.today();
    const s = attData;
    const managerMode = !isTeacherSelf();
    const dWd = A.WD_FULL[A.isoWeekday(st.date || today)].toLowerCase();
    const courses = managerMode ? takeCourses(groups) : [];
    const inCourse = groups.filter((g) => g.course === st.course);
    const optLabel = (x) => `${A.timeName(x.time)} · ${esc(A.groupName(x))}${st.date === today && isNow(x) ? ' · hozir dars' : ''}`;
    let html = managerMode ? `<section class="card take-head m3">
      <div class="field"><label class="lbl">1. Sana</label>
        <input type="date" class="f-input" id="att-date" value="${st.date}" max="${today}"><div class="help">O'tgan sanalarni ham tuzata olasiz (rol muddati bo'yicha)</div>
      </div>
      <div class="field"><label class="lbl">2. Kurs</label>
        ${!courses.length ? `<div class="computed muted">Bu kunda (${dWd}) dars yo'q</div>` : courses.length === 1 ? `<div class="computed">${esc(courses[0].name)} <span class="muted small">(${courses[0].n} ta guruh)</span></div>`
          : `<select class="f-input" id="att-course"><option value="">Kursni tanlang…</option>${courses.map((c) => `<option value="${c.id}" ${c.id === st.course ? 'selected' : ''}>${esc(c.name)} — ${c.n} ta guruh</option>`).join('')}</select>`}
      </div>
      <div class="field"><label class="lbl">3. Guruh</label>
        ${!st.course ? `<div class="computed muted">Avval kursni tanlang</div>` : inCourse.length === 1 ? `<div class="computed">${optLabel(inCourse[0])}</div>`
          : `<select class="f-input" id="att-group"><option value="">Guruhni tanlang…</option>${inCourse.map((x) => `<option value="${x.id}" ${x.id === st.group ? 'selected' : ''}>${optLabel(x)}</option>`).join('')}</select>`}
      </div>
    </section>` : `<section class="card take-head">
      <div class="field"><label class="lbl">1. Guruh</label>
        ${groups.length === 1 ? `<div class="computed">${esc(A.groupName(groups[0]))} · ${A.timeName(groups[0].time)} <span class="muted small">(${managerMode ? 'yagona faol guruh' : 'bugungi yagona darsingiz'} — avtomatik tanlandi)</span></div>` : `<select class="f-input" id="att-group"><option value="">Guruhni tanlang…</option>${groups
          .map((x) => `<option value="${x.id}" ${x.id === st.group ? 'selected' : ''}>${managerMode
            ? `${esc(A.groupName(x))} · ${esc(A.patternName(x.pattern))} ${A.timeName(x.time)}${A.hasLesson(x, today) ? ' · bugun dars bor' : ''}`
            : `${A.timeName(x.time)} · ${esc(A.groupName(x))}${isNow(x) ? ' · hozir dars' : ''}`}</option>`)
          .join('')}</select>`}
      </div>
      <div class="field"><label class="lbl">2. Sana</label>
        ${managerMode ? `<input type="date" class="f-input" id="att-date" value="${st.date}" max="${today}"><div class="help">Siz o'tgan sanalarni ham tuzata olasiz (≤ bugun, rol muddati bo'yicha)</div>` : `<div class="computed">${A.WD_FULL[A.isoWeekday(today)]}, ${A.fdate(today)} <span class="muted small">— ustoz faqat bugungi davomatni oladi</span></div>`}
      </div>
    </section>`;
    if (!s) return html + (groups.length || managerMode ? '' : A.empty(`Bugun (${A.WD_FULL[A.isoWeekday(today)].toLowerCase()}) darsingiz yo'q`));
    const g = s.group;
    if (s.error) {
      return html + `<div class="alert danger">${A.icon('alert')}<div><b>${esc(s.error)}</b>${managerMode && s.nearest ? `<br>Eng yaqin dars kuni: <a href="#" data-act="att-setdate" data-id="${s.nearest}">${A.fdate(s.nearest)}</a>` : ''}</div></div>`;
    }
    if (s.can_sub) {
      html += `<section class="card"><label class="check"><input type="checkbox" id="att-sub" ${st.sub ? 'checked' : ''}> 3. Darsni boshqa ustoz o'tdi (o'rindosh)</label>
        ${st.sub ? `<div class="row gap wrap">
          <select class="f-input" id="att-subt"><option value="">O'rindosh ustoz…</option>${A.S.users.filter((u) => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(u.role) && u.status === 'Faol' && u.id !== g.teacher).map((u) => `<option value="${u.id}" ${u.id === st.subTeacher ? 'selected' : ''}>${esc(u.full_name)}</option>`).join('')}</select>
          <select class="f-input" id="att-subs"><option value="">O'rindosh yordamchi (ixtiyoriy)…</option>${A.S.users.filter((u) => ['YORDAMCHI', 'USTOZ_YORDAMCHI'].includes(u.role) && u.status === 'Faol' && u.id !== g.supporter).map((u) => `<option value="${u.id}" ${u.id === st.subSupporter ? 'selected' : ''}>${esc(u.full_name)}</option>`).join('')}</select>
        </div><p class="muted small">KPI darsni amalda o'tgan kishiga yoziladi.</p>` : ''}</section>`;
    }
    // Belgilanmaganlar yuqorida — tartib ekran ochilganda bir marta belgilanadi (belgilash paytida qatorlar sakramasin)
    const key = `${g.id}|${s.date}`;
    if (st.orderKey !== key) {
      st.orderKey = key;
      st.order = [...s.rows.filter((r) => !r.att), ...s.rows.filter((r) => r.att)].map((r) => r.contract.id);
    }
    const sorted = A.sortBy(s.rows, (r) => { const i = st.order.indexOf(r.contract.id); return i < 0 ? 1e6 : i; });
    const done = s.rows.filter((r) => r.att).length;
    const allowed = s.allowed;
    html += `<section class="card att-card">
      <div class="row between wrap"><h2>${s.can_sub ? 4 : 3}. Talabalar · ${done}/${s.rows.length} belgilandi</h2>
        ${done < s.rows.length && allowed.includes('1') ? `<button class="btn" data-act="att-all">Hammasi keldi</button>` : done ? A.badge('Davomat olingan', 'green') : ''}</div>
      <div class="bar"><i class="bg-green" style="width:${s.rows.length ? (done / s.rows.length) * 100 : 0}%"></i></div>
      <ul class="att-list">${sorted
        .map(({ contract: c, att: a }) => {
          const ed = a ? A.canEdit('attendance', a) : A.canEdit('attendance', { date: s.date }, 'date', 'a');
          const btn = (code, label, cls) =>
            allowed.includes(code) ? `<button class="abtn ${cls} ${a && a.status === code ? 'on' : ''}" data-act="att-mark" data-id="${c.id}" data-s="${code}" ${!ed.ok ? `disabled title="${esc(ed.why)}"` : ''}>${label}</button>` : '';
          return `<li class="${a ? 'done' : ''}">
            <div class="att-name"><b class="${c.balance > 0 ? 't-red' : ''}">${esc(c.student_data.full_name)}</b>
              <small class="muted">${c.balance > 0 ? 'qarz ' + A.num(c.balance) : ''}${a && a.comment ? ' · ' + esc(a.comment) : ''}</small></div>
            <div class="att-btns">${btn('1', 'Keldi', 'g')}${btn('0', 'Sababli', 'y')}${btn('X', 'Besabab', 'r')}${btn('-', '–', 'n')}</div>
          </li>`;
        })
        .join('') || '<li class="muted">Bu sanada faol talaba yo\'q</li>'}</ul>
    </section>`;
    return html;
  }

  const bindTake = () => {
    const st = A.ui.att;
    const gs = document.getElementById('att-group');
    if (gs) gs.onchange = () => { st.group = gs.value; st.sub = false; st.pickedOn = A.today(); history.replaceState(null, '', '#/attendance?tab=take'); A.refresh(); };
    const cs = document.getElementById('att-course');
    if (cs) cs.onchange = () => { st.course = cs.value; st.group = ''; st.sub = false; history.replaceState(null, '', '#/attendance?tab=take'); A.refresh(); };
    const ds = document.getElementById('att-date');
    if (ds) ds.onchange = () => { st.date = ds.value; history.replaceState(null, '', '#/attendance?tab=take'); A.refresh(); };
    const sb = document.getElementById('att-sub');
    if (sb) sb.onchange = () => { st.sub = sb.checked; A.refresh(); };
    const t = document.getElementById('att-subt');
    if (t) t.onchange = () => (st.subTeacher = t.value);
    const s = document.getElementById('att-subs');
    if (s) s.onchange = () => (st.subSupporter = s.value);
  };
  A.pages.attendance.mount = (p, q) => { if ((q.tab || 'take') === 'take') bindTake(); };

  A.act['att-setdate'] = (el) => { A.ui.att.date = el.dataset.id; A.refresh(); };

  /** Belgilash serverda: qarz va KPI darhol hisoblanadi; javob — yangilangan ekran holati */
  async function postMarks(body) {
    const st = A.ui.att;
    const sub = st.sub ? { sub_teacher: st.subTeacher || null, sub_supporter: st.subSupporter || null } : {};
    attData = await A.http.post('/attendance/take/', { group: st.group, date: st.date, ...sub, ...body });
    A.putLocal('groups', attData.group);
    attFresh = true;
    A.refresh();
  }
  A.act['att-mark'] = (el) => {
    const cid = el.dataset.id, s = el.dataset.s;
    if (s === '0') {
      A.form({
        title: 'Sababli — izoh',
        fields: [{ name: 'comment', label: 'Sababi', type: 'textarea', required: true, placeholder: 'Masalan: kasal, oldindan ogohlantirdi' }],
        submit: 'Belgilash',
        onSubmit: (v) => postMarks({ marks: [{ contract: cid, status: '0', comment: v.comment }] }),
      });
      return;
    }
    return postMarks({ marks: [{ contract: cid, status: s }] });
  };
  A.act['att-all'] = async () => {
    const before = attData.rows.filter((r) => r.att).length;
    await postMarks({ all: true });
    A.toast(`${attData.rows.filter((r) => r.att).length - before} ta talaba «Keldi» deb belgilandi`);
  };

  /* ---- Kelmaganlar ---- */
  function absentView(d) {
    const ym = A.q('abs:month', A.ym(A.today()));
    const only = A.q('abs:status', '');
    const me = A.S.currentUser;
    const canC = A.can('attendance', 'e') || A.can('attendance', 'a');
    return `<div class="filters">
        <select class="f-input" data-filter="abs:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select>
        <select class="f-input" data-filter="abs:status"><option value="">Besabab va sababli</option><option value="X" ${only === 'X' ? 'selected' : ''}>Faqat besabab (X)</option><option value="0" ${only === '0' ? 'selected' : ''}>Faqat sababli (0)</option></select>
      </div>
      <p class="muted small">Bog'lanish holatini shu yerning o'zida o'zgartiring. "Gaplashildi" bo'lsa izoh majburiy. Besabab qatorda ustoz «Darsni yetkazdim» so'rovini yuborishi mumkin.</p>
      ${A.table(
        [
          { h: 'Sana', f: (a) => `${A.fdate(a.date)} <span class="muted small">${A.WD[A.isoWeekday(a.date)]}</span>` },
          { h: 'Talaba', f: (a) => `<a href="#/contracts/${a.contract}">${esc(a.student_name)}</a><br><a class="small" href="tel:+998${a.phone1}">+998 ${a.phone1}</a>` },
          { h: 'Guruh', f: (a) => esc(A.groupName(a.group)) },
          { h: 'Status', f: (a) => A.attBadge(a.status) + ' ' + A.ATT[a.status] },
          { h: "Bog'lanish holati", f: (a) => (canC ? `<select class="f-input sm" data-act-change="att-contact" data-id="${a.id}">${A.CONTACT.map((c) => `<option ${a.contact === c ? 'selected' : ''}>${c}</option>`).join('')}</select>` : esc(a.contact)) },
          { h: 'Izoh', f: (a) => esc(a.comment || '') },
          {
            h: '',
            f: (a) => {
              if (a.status !== 'X') return '';
              if (a.makeup && a.makeup !== 'Rad etildi') return A.badge(a.makeup === 'Tasdiqlandi' ? 'Yetkazildi' : "So'rov yuborilgan", 'blue');
              return a.teacher === me && isTeacherSelf() ? `<button class="btn sm" data-act="makeup-new" data-id="${a.id}">Darsni yetkazdim</button>` : '';
            },
          },
        ],
        d.results,
        { empty: "Bu oyda kelmaganlar yo'q" },
      )}${A.pager('abs', d)}`;
  }
  const absRow = (id) => (attData && attData.results ? attData.results.find((a) => a.id === id) : null);
  document.addEventListener('change', (e) => {
    const el = e.target.closest('[data-act-change="att-contact"]');
    if (!el) return;
    const a = absRow(el.dataset.id);
    const val = el.value;
    const save = (body) => A.http.patch(`/attendance/${a.id}/`, body).then((r) => { Object.assign(a, r); A.toast('Saqlandi'); A.refresh(); }, (err) => { fail(err); A.refresh(); });
    if (val === 'Gaplashildi') {
      el.value = a.contact;
      A.form({
        title: 'Gaplashildi — izoh majburiy',
        fields: [{ name: 'comment', label: 'Nima deyildi?', type: 'textarea', required: true }],
        values: { comment: a.comment },
        onSubmit: (v) => A.http.patch(`/attendance/${a.id}/`, { contact: val, comment: v.comment }).then((r) => { Object.assign(a, r); A.refresh(); }),
      });
      return;
    }
    save({ contact: val });
  });

  A.act['makeup-new'] = (el) => {
    const a = absRow(el.dataset.id);
    A.form({
      title: 'Qoldirilgan darsni yetkazish',
      intro: `<div class="note info">${esc(a.student_name)} · ${A.fdate(a.date)} da besabab qoldirgan dars. Tasdiqlansa status «Sababli»ga o'zgaradi va sizga KPI yoziladi.</div>`,
      fields: [
        { name: 'makeup_date', label: 'Dars qachon yetkazildi', type: 'date', required: true, default: A.today(), validate: (d) => (d < a.date ? "Qoldirilgan sanadan oldin bo'lishi mumkin emas" : d > A.today() ? "Kelajak sana bo'lishi mumkin emas" : '') },
        { name: 'comment', label: 'Izoh', type: 'textarea', required: true, placeholder: "Masalan: shanba kuni alohida o'tdim" },
      ],
      submit: "So'rov yuborish",
      async onSubmit(v) {
        await A.http.post('/makeups/', { attendance: a.id, makeup_date: v.makeup_date, comment: v.comment });
        A.toast("So'rov yuborildi. Menejer va administratorlar tasdiqlaydi");
        A.refresh();
      },
    });
  };

  /* ---- Qoldirilgan darslar ---- */
  A.makeupTable = makeupTable;
  function makeupTable(rows) {
    return A.table(
      [
        { h: "So'radi", f: (m) => `${esc(A.userName(m.teacher))}<br><small class="muted">${A.fdt(m.created_at)}</small>` },
        { h: 'Talaba / qoldirilgan dars', f: (m) => `<a href="#/contracts/${m.att.contract}">${esc(m.att.student_name)}</a><br><small class="muted">${esc(A.groupName(m.att.group))} · ${A.fdate(m.att.date)} · hozir: ${A.ATT[m.att.status]}</small>` },
        { h: 'Yetkazildi', f: (m) => A.fdate(m.makeup_date) },
        { h: 'Izoh', f: (m) => esc(m.comment) },
        { h: 'Holat', f: (m) => A.badge(m.status, m.status === 'Tasdiqlandi' ? 'green' : m.status === 'Rad etildi' ? 'red' : 'orange') + (m.reviewed_by ? `<br><small class="muted">${esc(A.userName(m.reviewed_by))}${m.reject_reason ? ': ' + esc(m.reject_reason) : ''}</small>` : '') },
        { h: '', f: (m) => (m.status === 'Kutilmoqda' && A.canApproveMakeup() ? `<div class="row gap"><button class="btn sm primary" data-act="makeup-ok" data-id="${m.id}">Tasdiqlash</button><button class="btn sm ghost" data-act="makeup-no" data-id="${m.id}">Rad etish</button></div>` : '') },
      ],
      rows || [],
      { empty: "So'rov yo'q" },
    );
  }
  A.act['makeup-ok'] = async (el) => {
    await A.http.post(`/makeups/${el.dataset.id}/approve/`);
    A.toast("Tasdiqlandi: status «Sababli», ustozga KPI yozildi");
    A.refresh();
  };
  A.act['makeup-no'] = (el) => {
    A.form({
      title: "So'rovni rad etish",
      fields: [{ name: 'reason', label: 'Sabab', type: 'textarea', required: true }],
      submit: 'Rad etish',
      async onSubmit(v) {
        await A.http.post(`/makeups/${el.dataset.id}/reject/`, { reason: v.reason });
        A.refresh();
      },
    });
  };

  /* ---- Statistika (serverda yig'ilgan) ---- */
  function statsView(s) {
    const ym = A.q('ast:month', A.ym(A.today()));
    const cols = (label, name, key) => [
      { h: label, f: (r) => esc(name(r[key])) },
      { h: 'Qatorlar', f: (r) => r.n, cls: 'num' },
      { h: 'Keldi', f: (r) => r.came, cls: 'num' },
      { h: 'Sababli', f: (r) => r.sab, cls: 'num' },
      { h: 'Besabab', f: (r) => r.bes, cls: 'num' },
      { h: 'Davomat %', f: (r) => `<b class="${r.came / r.n < 0.8 ? 't-red' : 't-green'}">${A.pct(r.came / r.n)}</b>`, cls: 'num' },
    ];
    const byGroup = A.sortBy(s.by_group, (r) => r.came / r.n);
    return `<div class="filters"><select class="f-input" data-filter="ast:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="grid-2"><section class="card"><h2>Guruhlar bo'yicha</h2>${A.table(cols('Guruh', A.groupName, 'group'), byGroup)}</section>
      <section class="card"><h2>Ustozlar bo'yicha</h2>${A.table(cols('Ustoz', A.userName, 'teacher'), s.by_teacher)}
      ${A.chart({ type: 'bar', data: { labels: byGroup.map((r) => A.groupName(r.group)), datasets: [{ label: 'Davomat %', data: byGroup.map((r) => Math.round((r.came / r.n) * 100)), backgroundColor: A.PALETTE[0] }] }, options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } } }, 220)}</section></div>`;
  }

  /* ===================================================== M6 umumiy: faol shartnomalar (forma ro'yxatlari uchun) */
  A.activeContracts = async () => {
    let page = 1, out = [];
    for (;;) {
      const d = await A.http.get(`/contracts/?status=Faol&page_size=200&page=${page}`);
      d.results.forEach(A.keepContract);
      out = out.concat(d.results);
      if (page >= (d.pages || 1)) return out;
      page++;
    }
  };
  const isTeacherSelf6 = () => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role());

  /* ===================================================== Baholash (talaba → ustoz): /evaluations/ */
  const CRIT = ['Mavzuni sodda tilda tushuntira oladimi?', "Darsni qiziq o'tadimi? Qiziq metodlardan foydalanadimi?", 'Barcha talabalarga adolatli yondashadimi?', 'Kerak vaqtda yordam beradimi?', 'Kamchiliklar haqida tavsiya berib, ruhlantiradimi?'];
  let evData = [];
  A.page('evaluations', {
    title: 'Baholash',
    section: 'evaluations',
    async load() {
      evData = await A.http.get('/evaluations/?' + (A.q('ev:month', '') ? `month=${A.q('ev:month')}` : ''));
    },
    render() {
      const m = A.q('ev:month', '');
      const byT = [...A.groupBy(evData, (e) => e.teacher)].map(([t, l]) => ({ t, n: l.length, avg: A.sum(l, 'total') / l.length }));
      return `${A.head('Baholash: talaba ustozni baholaydi', "5 ta mezon, har biri 0–10. Jami — 50 balldan. Javoblarni administrator kiritadi", A.can('evaluations', 'a') ? A.btn('Yangi baholash', 'eval-new', { icon: 'plus' }) : '')}
        <div class="filters"><select class="f-input" data-filter="ev:month"><option value="">Barcha oylar</option>${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === m ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
        <div class="stats">${A.sortBy(byT, (r) => r.avg, true).map((r) => A.stat(A.userName(r.t), `${r.avg.toFixed(1)} / 50`, `${r.n} ta baho`)).join('')}</div>
        ${A.table(
          [
            { h: 'Sana', f: (e) => A.fdate(e.date) },
            { h: 'Ustoz', f: (e) => esc(A.userName(e.teacher)) },
            { h: 'Talaba', f: (e) => `<a href="#/contracts/${e.contract}">${esc(e.student_name)}</a><br><small class="muted">${esc(A.groupName(e.group))}</small>` },
            ...CRIT.map((c, i) => ({ h: `${i + 1}`, f: (e) => e.scores[i], cls: 'num' })),
            { h: 'Jami', f: (e) => `<b>${e.total}</b>`, cls: 'num' },
            { h: 'Izoh', f: (e) => esc(e.comment) },
          ],
          evData,
          { empty: "Baho yo'q" },
        )}
        <ol class="muted small">${CRIT.map((c) => `<li>${esc(c)}</li>`).join('')}</ol>`;
    },
  });
  A.act['eval-new'] = async () => {
    const contracts = await A.activeContracts();
    const opts = [...Array(11).keys()].map((n) => [String(n), String(n)]);
    const byId = (id) => contracts.find((c) => c.id === id);
    A.form({
      title: 'Talaba ustozni baholaydi',
      fields: [
        { name: 'contract', label: 'Talaba', type: 'select', required: true, options: () => A.sortBy(contracts, (c) => c.student_data.full_name).map((c) => [c.id, `${c.student_data.full_name} · ${A.groupName(c.group)}`]) },
        { name: 'teacher', label: 'Ustoz', type: 'computed', show: (x) => x.contract, compute: (x) => esc(A.userName((A.get('groups', (byId(x.contract) || {}).group) || {}).teacher)) },
        ...CRIT.map((c, i) => ({ name: 's' + (i + 1), label: `${i + 1}. ${c}`, type: 'select', options: opts, required: true, show: (x) => x.contract })),
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.contract },
      ],
      async onSubmit(x) {
        await A.http.post('/evaluations/', { contract: x.contract, s1: +x.s1, s2: +x.s2, s3: +x.s3, s4: +x.s4, s5: +x.s5, comment: x.comment || '' });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };

  /* ===================================================== Ota-onalar bilan aloqa: /parent-calls/ (daraxt: filial → kurs → guruh) */
  let pcData = [];
  A.page('parentCalls', {
    title: 'Ota-onalar bilan aloqa',
    section: 'parentCalls',
    async load() {
      pcData = await A.http.get('/parent-calls/');
    },
    render() {
      const rows = A.treeFilter('pcalls', pcData);
      return `${A.head('Ota-onalar bilan aloqa', "Qo'ng'iroq va SMS havolalari talaba va vasiy telefonidan olinadi", A.can('parentCalls', 'a') ? A.btn('Yangi yozuv', 'pcall-new', { icon: 'plus' }) : '')}
        <div class="settings tree-layout">${A.treeNav('pcalls', pcData)}<div class="settings-body">${A.table(
          [
            { h: 'Sana', f: (r) => A.fdate(r.date) },
            { h: 'Talaba', f: (r) => `<a href="#/contracts/${r.contract}">${esc(r.student_name)}</a><br><small class="muted">${esc(A.groupName(r.group))}</small>` },
            { h: 'Aloqa', f: (r) => `<a href="tel:+998${r.phone1}">📞 ${r.phone1}</a> · <a href="sms:+998${r.phone1}">SMS</a>${r.phone2 ? `<br><a href="tel:+998${r.phone2}">📞 ${r.phone2}</a> · <a href="sms:+998${r.phone2}">SMS</a>` : ''}${r.parent ? `<br><small>Vasiy: <a href="tel:+998${r.parent.phone}">${esc(r.parent.first_name)} ${r.parent.phone}</a></small>` : ''}` },
            { h: 'Izoh', f: (r) => `${esc(r.comment)}${r.edited ? `<br><small class="muted">✎ ${esc(A.userName(r.updated_by))} · ${A.fdt(r.updated_at)}</small>` : ''}` },
            { h: 'Kim', f: (r) => `${esc(A.userName(r.created_by))}<br><small class="muted">${A.fdt(r.created_at)}</small>` },
            {
              h: '', f: (r) => {
                const ed = A.canEdit('parentCalls', r), del = A.canEdit('parentCalls', r, 'date', 'd');
                return `<span style="white-space:nowrap">${A.can('parentCalls', 'e') ? `<button class="btn sm ghost" data-act="pcall-edit" data-id="${r.id}" title="${ed.ok ? 'Tahrirlash' : esc(ed.why)}" ${ed.ok ? '' : 'disabled'}>✎</button>` : ''}${A.can('parentCalls', 'd') ? ` <button class="btn sm ghost" data-act="pcall-del" data-id="${r.id}" title="${del.ok ? "O'chirish" : esc(del.why)}" ${del.ok ? '' : 'disabled'}>🗑</button>` : ''}</span>`;
              },
            },
          ],
          rows,
          { empty: "Yozuv yo'q" },
        )}</div></div>`;
    },
  });
  const pcallForm = async (rec) => {
    const contracts = rec ? [] : await A.activeContracts();
    const byId = (id) => contracts.find((c) => c.id === id);
    A.form({
      title: rec ? 'Izohni tahrirlash' : 'Ota-ona bilan aloqa',
      values: rec ? { ...rec } : { date: A.today() },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, readonly: () => !!rec, resets: ['group', 'contract'], options: () => (rec ? A.optList('courses', 'name', (c) => c.id === rec.course) : A.optList('courses', 'name', (c) => contracts.some((k) => k.course === c.id))) },
        { name: 'group', label: 'Guruh', type: 'select', required: true, readonly: () => !!rec, show: (x) => x.course, resets: ['contract'], options: (x) => A.vis('groups').filter((g) => g.course === x.course && (rec ? g.id === rec.group : contracts.some((k) => k.group === g.id))).map((g) => [g.id, A.groupName(g)]) },
        { name: 'contract', label: 'Talaba', type: 'select', required: true, readonly: () => !!rec, show: (x) => x.group, options: (x) => (rec ? [[rec.contract, rec.student_name]] : A.sortBy(contracts.filter((c) => c.group === x.group), (c) => c.student_data.full_name).map((c) => [c.id, c.student_data.full_name])) },
        {
          name: 'phones', label: 'Telefonlar', type: 'computed', show: (x) => x.contract,
          compute: (x) => { const s = rec ? { phone1: rec.phone1, phone2: rec.phone2 } : (byId(x.contract) || {}).student_data || {}; return `<a href="tel:+998${s.phone1}">+998 ${s.phone1}</a>${s.phone2 ? `, <a href="tel:+998${s.phone2}">+998 ${s.phone2}</a>` : ''}${rec && rec.parent ? ` · vasiy ${esc(rec.parent.first_name)}: <a href="tel:+998${rec.parent.phone}">${rec.parent.phone}</a>` : ''}`; },
        },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.contract, validate: (t) => (t > A.today() ? "Kelajak sana bilan kiritib bo'lmaydi" : '') },
        { name: 'comment', label: 'Izoh', type: 'textarea', required: true, show: (x) => x.contract },
        { name: 'author', type: 'note', show: () => !!rec, text: () => `Qo'shgan: <b>${esc(A.userName(rec.created_by))}</b> · ${A.fdt(rec.created_at)}${rec.edited ? `<br>Oxirgi tahrir: <b>${esc(A.userName(rec.updated_by))}</b> · ${A.fdt(rec.updated_at)}` : ''}` },
      ],
      async onSubmit(x) {
        if (rec) await A.http.patch(`/parent-calls/${rec.id}/`, { date: x.date, comment: x.comment });
        else await A.http.post('/parent-calls/', { contract: x.contract, date: x.date, comment: x.comment });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['pcall-new'] = () => pcallForm(null);
  A.act['pcall-edit'] = (el) => pcallForm(pcData.find((r) => r.id === el.dataset.id));
  A.act['pcall-del'] = async (el) => {
    const r = pcData.find((x) => x.id === el.dataset.id);
    if (!(await A.confirm(`${esc(r.student_name)} — ${A.fdate(r.date)} dagi izoh o'chirilsinmi?<br><small class="muted">«${esc(r.comment)}»</small>`, "O'chirish", true))) return;
    await A.http.del(`/parent-calls/${r.id}/`);
    A.toast("O'chirildi");
    A.refresh();
  };

  /* ===================================================== Shartnoma yuklash (Excel .xlsx — serverda openpyxl) */
  A.downloadXlsx = (qs) => {
    const a = document.createElement('a');
    a.href = '/api/v1/export/contracts/?' + qs;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  A.page('export', {
    title: 'Shartnoma yuklash',
    section: 'export',
    render() {
      return `${A.head('Shartnoma yuklash', "Kurs va guruhlarni tanlang — shartnomalar ro'yxati Excel (.xlsx) faylga yuklanadi (AppSheet'dagi «Exel» boti o'rniga)")}
        <section class="card narrow">
          <div class="field"><label class="lbl">Kurs</label><select class="f-input" id="ex-c"><option value="">Tanlang…</option>${A.optList('courses').map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select></div>
          <div class="field"><label class="lbl">Guruhlar</label><div class="chips" id="ex-g"><span class="muted">Avval kursni tanlang</span></div></div>
          <button class="btn primary" id="ex-go">${A.icon('download')}Excel'ga yuklash</button>
          <p class="muted small">Faylda: talaba, telefonlar, vasiy, guruh, turi, sanalar, status, hisoblangan, to'langan, chegirma va balans.</p>
        </section>`;
    },
    mount() {
      const cs = document.getElementById('ex-c');
      const gbox = document.getElementById('ex-g');
      cs.onchange = () => {
        gbox.innerHTML = A.vis('groups').filter((g) => g.course === cs.value).map((g) => `<button type="button" class="chip on" data-g="${g.id}">${esc(A.groupName(g))} <small class="muted">${esc(g.status)}</small></button>`).join('') || '<span class="muted">Guruh yo\'q</span>';
      };
      gbox.onclick = (e) => { const b = e.target.closest('[data-g]'); if (b) b.classList.toggle('on'); };
      document.getElementById('ex-go').onclick = () => {
        const ids = [...gbox.querySelectorAll('.chip.on')].map((b) => b.dataset.g);
        if (!ids.length) return A.toast('Kamida bitta guruh tanlang', 'warn');
        A.downloadXlsx(new URLSearchParams({ groups: ids.join(',') }));
        A.toast('Fayl tayyorlanmoqda…');
      };
    },
  });
})(window.App);

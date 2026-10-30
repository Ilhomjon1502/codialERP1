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
      /* Qidiruv va filtrlar (brauzerda): nom/raqam, ustoz, yordamchi, xona, kunlar, vaqt bo'yicha qidiruv; kurs, ustoz, kunlar, xona, to'lish */
      const fq = (n) => A.q(`groups:${n}`, '');
      const words = fq('search').trim().toLowerCase().split(/\s+/).filter(Boolean);
      const match = (g) => {
        if (fq('course') && g.course !== fq('course')) return false;
        if (fq('teacher') && g.teacher !== fq('teacher') && g.supporter !== fq('teacher')) return false;
        if (fq('pattern') && g.pattern !== fq('pattern')) return false;
        if (fq('room') && g.room !== fq('room')) return false;
        if (fq('fill') && A.groupFill(g).label !== fq('fill')) return false;
        if (!words.length) return true;
        const hay = [A.groupName(g), A.userName(g.teacher), g.supporter ? A.userName(g.supporter) : '', A.roomName(g.room), A.patternName(g.pattern), A.timeName(g.time)]
          .join(' ').toLowerCase();
        return words.every((w) => (w.startsWith('#') && w.length > 1 ? String(g.number) === w.slice(1) : hay.includes(w))); // «#46» — aniq guruh raqami
      };
      const shown = all.filter(match);
      const uniq = (ids, name) => A.sortBy([...new Set(ids.filter(Boolean))].map((id) => [id, name(id)]), (o) => o[1]);
      const filters = A.filterBar('groups', [
        A.fSearch('groups', 'Guruh, ustoz, xona…'),
        A.fSelect('groups', 'course', uniq(all.map((g) => g.course), (id) => (A.get('courses', id) || {}).name || '—'), 'Barcha kurslar'),
        A.fSelect('groups', 'teacher', uniq(all.flatMap((g) => [g.teacher, g.supporter]), A.userName), 'Barcha ustozlar'),
        A.fSelect('groups', 'pattern', uniq(all.map((g) => g.pattern), A.patternName), 'Barcha kunlar'),
        A.fSelect('groups', 'room', uniq(all.map((g) => g.room), A.roomName), 'Barcha xonalar'),
        A.fSelect('groups', 'fill', ["Bo'sh", 'Yomon', "O'rtacha", 'Yaxshi', "Zo'r"].map((x) => [x, x]), "To'lish: hammasi"),
        ...(words.length || ['course', 'teacher', 'pattern', 'room', 'fill'].some(fq) ? [A.btn('Tozalash', 'groups-clear', { cls: 'ghost' })] : []),
      ]);
      const cnt = (s) => shown.filter((g) => g.status === s).length;
      return `${A.head('Guruhlar', "Guruh nomi rangi — to'lish holati: qizil yomon, to'q sariq o'rtacha, ko'k yaxshi, yashil zo'r", A.can('groups', 'a') ? A.btn('Yangi guruh', 'group-new', { icon: 'plus' }) : '')}
        ${A.tabs([['Faol', 'Faol', cnt('Faol')], ['Rejada', 'Rejada', cnt('Rejada')], ['Nofaol', 'Nofaol', cnt('Nofaol')]], tab, 'groups')}
        ${filters}
        <div class="cards">${A.sortBy(shown.filter((g) => g.status === tab), (g) => A.groupName(g))
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
          .join('') || A.empty(shown.length < all.length ? "Filtrga mos guruh yo'q" : "Guruh yo'q")}</div>`;
    },
  });
  A.act['groups-clear'] = () => {
    for (const k of ['search', 'course', 'teacher', 'pattern', 'room', 'fill']) delete A.ui.q[`groups:${k}`];
    A.refresh();
  };

  /* ---- Guruh formasi. Tekshiruvlar serverda ham bor (services.validate_group) ---- */
  /* ---- Dars vaqti: 30 daqiqa oralig'ida qo'lda tanlanadi (08:00, 08:30…). Mos vaqt yozuvi bo'lmasa yangisi o'zi yaratiladi ---- */
  A.TIME_SLOTS = [];
  for (let m = 6 * 60; m <= 23 * 60 + 30; m += 30) A.TIME_SLOTS.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`);
  A.ensureTime = async (start, end, B) => {
    const ex = A.rows('lessonTimes').find((t) => t.branch === B && t.start === start && t.end === end);
    if (ex) {
      if ((ex.status || 'Faol') !== 'Faol') A.putLocal('lessonTimes', await A.http.patch(`/lesson-times/${ex.id}/`, { status: 'Faol' }));
      return ex.id;
    }
    const t = await A.http.post('/lesson-times/', { branch: B, start, end });
    A.putLocal('lessonTimes', t);
    return t.id;
  };
  /** Mavjud vaqt yozuvidan forma qiymatlari */
  A.timeValues = (id) => {
    const t = id && A.get('lessonTimes', id);
    return t ? { new_start: t.start, new_end: t.end } : {};
  };
  /** Boshlanish va tugash — yarim soatlik tanlov (eski «g'alati» vaqt bo'lsa, u ham ro'yxatda qoladi). opts: { show, optional } */
  A.timeFields = (opts = {}) => {
    const mins = (t) => { const [h, m] = String(t).split(':').map(Number); return h * 60 + m; };
    const slots = (cur) => [...new Set([...(cur ? [cur] : []), ...A.TIME_SLOTS])].sort().map((v) => [v, v]);
    const plus2h = (t) => { const m = Math.min(mins(t) + 120, 23 * 60 + 30); return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; };
    return [
      {
        name: 'new_start', label: opts.optional ? "Ma'qul vaqt: boshlanish" : 'Dars boshlanishi', type: 'select', required: !opts.optional, half: true, show: opts.show,
        placeholder: opts.optional ? 'Tanlanmagan' : undefined, options: (x) => slots(x.new_start),
        onChange: (x) => { if (x.new_start && (!x.new_end || mins(x.new_end) <= mins(x.new_start))) x.new_end = plus2h(x.new_start); },
        validate: (d, x) => (opts.optional && !x.new_end ? 'Tugash vaqtini ham tanlang' : ''),
      },
      {
        name: 'new_end', label: opts.optional ? "Ma'qul vaqt: tugash" : 'Dars tugashi', type: 'select', required: !opts.optional, half: true, show: opts.show,
        placeholder: opts.optional ? 'Tanlanmagan' : undefined, options: (x) => slots(x.new_end),
        validate: (d, x) => (opts.optional && x.new_start && !d ? 'Tugash vaqtini tanlang' : d && x.new_start && mins(d) <= mins(x.new_start) ? "Tugash vaqti boshlanishdan keyin bo'lsin" : ''),
      },
    ];
  };
  A.groupForm = (g, preset) => {
    const isNew = !g;
    const B = g ? g.branch : A.branchIds()[0];
    const staff = (roles, x) => A.S.users.filter((u) => roles.includes(u.role) && (u.status === 'Faol' || u.id === x) && (u.branches || []).includes(B));
    const hm = (t) => { const [h, m] = String(t).split(':').map(Number); return h * 60 + m; };
    const timeOf = (x) => (x.new_start && x.new_end && hm(x.new_end) > hm(x.new_start) ? { s: hm(x.new_start), e: hm(x.new_end) } : null);
    const timeReady = (x) => !!timeOf(x);
    // Shu kun va vaqtda xona yoki ustoz band bo'lgan guruhlar (ogohlantirish, saqlashga to'sqinlik qilmaydi)
    const clashes = (x, by) => {
      const me = timeOf(x);
      const p = x.pattern && A.get('dayPatterns', x.pattern);
      if (!me || !p) return [];
      return A.rows('groups').filter((o) => {
        if ((g && o.id === g.id) || o.status === 'Nofaol') return false;
        const op = A.get('dayPatterns', o.pattern);
        const ot = A.get('lessonTimes', o.time);
        if (!op || !ot) return false;
        if (!(op.weekdays || []).some((d) => (p.weekdays || []).includes(d))) return false;
        if (!(hm(ot.start) < me.e && me.s < hm(ot.end))) return false;
        return by === 'room' ? o.room === x.room : o.teacher === x.teacher;
      });
    };
    A.form({
      title: isNew ? 'Yangi guruh' : A.groupName(g),
      values: (() => { const base = g ? { ...g } : { start: A.today(), ...(preset || {}) }; return { ...base, ...A.timeValues(base.time) }; })(),
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, readonly: () => !isNew && A.role() !== 'ADMIN', options: (x) => A.optList('courses', 'name', (c) => (c.status === 'Faol' && c.branches.includes(B)) || c.id === x.course), help: isNew ? '' : "Kursni faqat Admin o'zgartiradi (guruhda shartnoma bo'lmasa)" },
        { name: 'pattern', label: 'Dars kunlari', type: 'seg', required: true, show: (x) => x.course, options: (x) => A.optList('dayPatterns', 'name', (p) => (p.status || 'Faol') === 'Faol' || p.id === x.pattern) },
        ...A.timeFields({ show: (x) => x.pattern }),
        { name: 'teacher', label: 'Ustoz', type: 'select', required: true, show: timeReady, options: (x) => staff(['USTOZ', 'USTOZ_YORDAMCHI'], x.teacher).map((u) => [u.id, u.full_name]) },
        { name: 'supporter', label: 'Yordamchi ustoz (ixtiyoriy)', type: 'select', show: (x) => x.teacher, options: (x) => staff(['YORDAMCHI', 'USTOZ_YORDAMCHI'], x.supporter).filter((u) => u.id !== x.teacher).map((u) => [u.id, u.full_name]), placeholder: "Yo'q" },
        {
          name: 'room', label: 'Xona', type: 'select', required: true, show: (x) => x.teacher,
          options: (x) => A.rows('rooms').filter((r) => r.branch === B && (r.status === 'Faol' || r.id === x.room)).map((r) => {
            const busy = clashes({ ...x, room: r.id }, 'room').length > 0;
            return [r.id, `${r.name} (${r.capacity} o'rin)${busy ? ' — shu vaqtda band!' : ''}`];
          }),
        },
        {
          name: 'warn', type: 'note', tone: 'warn',
          show: (x) => x.room && (clashes(x, 'room').length || clashes(x, 'teacher').length),
          text: (x) => {
            const f = (o) => `${o.name} (${(A.get('lessonTimes', o.time) || {}).start}–${(A.get('lessonTimes', o.time) || {}).end})`;
            const r = clashes(x, 'room');
            const t = clashes(x, 'teacher').filter((o) => !r.includes(o));
            return `⚠️ Diqqat: ${r.length ? `shu vaqtda xonada boshqa dars bor: ${r.map(f).join('; ')}. ` : ''}${t.length ? `Ustozning shu vaqtda boshqa darsi bor: ${t.map(f).join('; ')}. ` : ''}Baribir saqlash mumkin.`;
          },
        },
        { name: 'start', label: 'Boshlanish sana', type: 'date', required: true, show: (x) => x.room, half: true },
        { name: 'end', label: 'Tugash sana', type: 'date', show: (x) => x.room, half: true, validate: (d, x) => (d && d <= x.start ? "Boshlanish sanadan kichik bo'lolmaydi!" : '') },
        { name: 'num', label: 'Guruh raqami', type: 'computed', show: (x) => x.course, compute: (x) => (g ? `${A.courseName(x.course)} / #${g.number}` : `${A.courseName(x.course)} / avtomatik raqam`) },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.room },
      ],
      async onSubmit(x) {
        const timeId = await A.ensureTime(x.new_start, x.new_end, B);
        const rec = { course: x.course, pattern: x.pattern, time: timeId, teacher: x.teacher, supporter: x.supporter || null, room: x.room, start: x.start, end: x.end || null, comment: x.comment || '' };
        const saved = isNew ? await A.http.post('/groups/', rec) : await A.http.patch(`/groups/${g.id}/`, rec);
        A.putLocal('groups', saved);
        A.toast(isNew ? `Guruh yaratildi: ${saved.name}` : 'Saqlandi');
        if (isNew) A.go('groups/' + saved.id);
        else A.refresh();
      },
    });
  };
  A.act['group-new'] = () => A.groupForm(null);
  A.act['group-del'] = async (el) => {
    const g = A.get('groups', el.dataset.id);
    if (!(await A.confirm(`${esc(A.groupName(g))} guruhi o'chirilsinmi?<br><small class="muted">Guruhda talabalar yo'q. Lid yoki davomat yozuvi bo'lsa, o'chirilmaydi.</small>`, "O'chirish", true))) return;
    try {
      await A.remove('groups', g.id);
      A.toast("Guruh o'chirildi");
      A.go('groups');
    } catch (e) {
      A.toast(e.message || "O'chirib bo'lmadi", 'warn');
    }
  };
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
        const st = s || '';
        return st || d < today ? A.attSelect({ contract: cid, group: g.id, date: d, status: st, compact: true }) : '';
      };
      const freq = j.frequency;
      return `<a class="back" href="#/groups">← Guruhlar</a>
        ${A.head(A.groupName(g), `${A.badge(g.status, g.status === 'Faol' ? 'green' : 'blue')} · ${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}`,
          `${A.can('attendance', 'a') && A.hasLesson(g, today) ? `<a class="btn primary" href="#/attendance?tab=take&group=${g.id}">${A.icon('check')}Davomat olish</a>` : ''}
           ${A.can('groups', 'e') ? A.btn('Tahrirlash', 'group-edit', { id, cls: 'ghost' }) : ''}
           ${A.can('groups', 'd') && !j.contracts.length ? A.btn("O'chirish", 'group-del', { id, cls: 'ghost' }) : ''}`)}
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
      else if (tab === 'stats') attData = await loadLedger();
      else attData = await A.http.get('/makeups/');
      if (tab === 'makeup') mkPending = attData.filter((m) => m.status === 'Kutilmoqda').length;
    },
    render(p, q) {
      const tab = q.tab || 'take';
      const me = A.me();
      const today = A.today();
      const open = A.rows('groups').filter((g) => g.status === 'Faol' && (!A.isTeacherRole() || g.teacher === me.id || g.supporter === me.id));
      const notTaken = open.filter((g) => A.hasLesson(g, today) && !A.attendanceTaken(g.id, today));
      const alertHTML = notTaken.length ? `<div class="alert info">${A.icon('check')}<div><b>Bugun davomati olinmagan guruhlar (${notTaken.length}):</b> ${notTaken
        .map((g) => `<a href="#/attendance?tab=take&group=${g.id}">${esc(A.groupName(g))}</a> <span class="muted">(${A.timeName(g.time)}, ${esc(A.userName(g.teacher))})</span>`).join(' · ')}</div></div>` : '';
      return `${A.head('Davomatlar', "Davomatni ustoz oladi. Menejerlar o'tgan sanalarni tuzatishi mumkin")}
        ${alertHTML}
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
          { h: 'Status', f: (a) => A.attSelect({ contract: a.contract, group: a.group, date: a.date, status: a.status, comment: a.comment }) },
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

  /* ---- Statistika (AppSheet'dagidek): chapda sanalar, o'ngda davomat qatorlari; filtrlar — oy, kurs, guruh, o'quvchi ---- */
  const ATT_NAME = { 1: 'Keldi', 0: 'Sababli', X: 'Besabab', '-': 'Nofaol' };
  const ATT_TONE = { 1: 'green', 0: 'orange', X: 'red', '-': 'gray' };
  let ledgerContracts = [];
  const ledgerQ = () => {
    const ym = A.q('ast:month', A.ym(A.today()));
    const course = A.q('ast:course', '');
    let group = A.q('ast:group', '');
    const g = group && A.get('groups', group);
    if (g && course && g.course !== course) group = '';
    return { ym, course, group, search: (A.q('ast:search', '') || '').trim(), contract: group ? A.q('ast:contract', '') : '', date: A.q('ast:date', '') };
  };
  async function loadLedger() {
    if (A.q('ast:view', 'rows') === 'sum') return { sum: await A.http.get(`/attendance/stats/?month=${A.q('ast:month', A.ym(A.today()))}`) };
    const f = ledgerQ();
    const base = `month=${f.ym}${f.course ? `&course=${f.course}` : ''}${f.group ? `&group=${f.group}` : ''}${f.contract ? `&contract=${f.contract}` : ''}${f.search ? `&search=${encodeURIComponent(f.search)}` : ''}`;
    const gapQ = f.contract ? `&contract=${f.contract}` : f.group ? `&group=${f.group}` : '';
    const [dates, list, gaps] = await Promise.all([
      A.http.get(`/attendance/dates/?${base}`),
      A.http.get(`/attendance/?${base}${f.date ? `&date=${f.date}` : ''}&page_size=100&page=${A.q('ast:page', 1)}`),
      gapQ ? A.http.get(`/attendance/gaps/?month=${f.ym}${gapQ}`) : Promise.resolve({ dates: [] }),
    ]);
    ledgerContracts = f.group ? (await A.http.get(`/contracts/?group=${f.group}&page_size=200`)).results : [];
    return { dates, list, gaps: gaps.dates, f };
  }
  // Bog'liq filtrlar: kurs o'zgarsa guruh/o'quvchi/sana tozalanadi, guruh o'zgarsa o'quvchi/sana, boshqasi o'zgarsa sana
  document.addEventListener('input', (e) => {
    const el = e.target.closest('[data-filter^="ast:"]');
    if (!el) return;
    const clear = { 'ast:course': ['ast:group', 'ast:contract', 'ast:date'], 'ast:group': ['ast:contract', 'ast:date'], 'ast:month': ['ast:date'], 'ast:contract': ['ast:date'], 'ast:search': ['ast:date'] }[el.dataset.filter] || [];
    clear.forEach((k) => { A.ui.q[k] = ''; });
  }, true);
  // Davomatni tuzatish: statusni bosib o'zgartiriladi, qarz va KPI darhol qayta hisoblanadi (server: bo'sh sana — «Belgilash»)
  let attRows = {};
  const ST_OPTS = [['1', '✅ Keldi'], ['0', '🟡 Sababli'], ['X', '🔴 Besabab'], ['-', '⚪ Nofaol']];
  // Jadvalning o'zida: statusni tanlash bilan saqlanadi (Sababli bo'lsa — sababi so'raladi)
  document.addEventListener('change', async (e) => {
    const sel = e.target.closest('select[data-att]');
    if (!sel) return;
    const r = attRows[sel.dataset.att];
    if (!r || !sel.value) return;
    let comment = '';
    if (sel.value === '0') {
      comment = (window.prompt(`${r.student_name}: sababli — sababini yozing`, r.comment || '') || '').trim();
      if (!comment) { sel.value = r.gap ? '' : r.status; return; }
    }
    sel.disabled = true;
    try {
      await A.http.post('/attendance/take/', { group: r.group, date: r.date, marks: [{ contract: r.contract, status: sel.value, ...(comment ? { comment } : {}) }] });
      A.toast(`${r.student_name} · ${A.fdate(r.date)}: ${ATT_NAME[sel.value]}`);
      A.refresh();
    } catch (err) {
      A.toast(err.message || 'Saqlanmadi', 'warn');
      sel.value = r.gap ? '' : r.status;
      sel.disabled = false;
    }
  });
  A.act['ast-date'] =(el) => { A.ui.q['ast:date'] = el.dataset.id; A.ui.q['ast:page'] = 1; A.refresh(); };
  A.act['ast-view'] = (el) => { A.ui.q['ast:view'] = el.dataset.id; A.refresh(); };

  function statsView(s) {
    const view = A.q('ast:view', 'rows');
    const ym = A.q('ast:month', A.ym(A.today()));
    const monthSel = `<select class="f-input" data-filter="ast:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
    const seg = `<div class="seg">${[['rows', 'Qatorlar'], ['sum', 'Jamlama']].map(([k, l]) => `<button class="${view === k ? 'on' : ''}" data-act="ast-view" data-id="${k}">${l}</button>`).join('')}</div>`;
    if (view === 'sum') return `<div class="filters">${seg}${monthSel}</div>${summaryView(s.sum)}`;

    const f = s.f;
    const courses = A.rows('courses').map((c) => [c.id, c.name]);
    const groups = A.rows('groups').filter((g) => !f.course || g.course === f.course).map((g) => [g.id, A.groupName(g)]);
    const opt = (list, cur, all) => `<option value="">${all}</option>${list.map(([k, l]) => `<option value="${esc(k)}" ${String(cur) === String(k) ? 'selected' : ''}>${esc(l)}</option>`).join('')}`;
    const stName = (c) => c.student_name || (A.get('students', c.student) || {}).full_name || `№${c.number}`;
    const students = ledgerContracts.map((c) => [c.id, stName(c)]);
    const showDebt = A.can('payments', 'v');
    const canFix = A.can('attendance', 'a') && !isTeacherSelf(); // menejerlar va administratorlar tuzata oladi (ustoz — faqat o'z bugungisini davomat olish ekranida)
    const gapSet = s.gaps || [];

    // Chapda — sanalar (AppSheet daraxti kabi)
    const nodes = [`<a class="tree-n${f.date ? '' : ' on'}" data-act="ast-date" data-id=""><span class="tree-tw"></span><span class="tree-l">Barchasi</span><span class="tree-c">${s.dates.totals.n}</span></a>`]
      .concat(s.dates.dates.map((d) => `<a class="tree-n${f.date === d.date ? ' on' : ''}" data-act="ast-date" data-id="${d.date}"><span class="tree-tw"></span><span class="tree-l">${A.fdate(d.date)} · ${A.WD[A.isoWeekday(d.date)]}</span><span class="tree-c">${d.n}</span></a>`));
    const tree = `<nav class="side-tabs tree">${nodes.join('')}</nav>`;

    // O'ngda — qatorlar; shartnoma tanlangan bo'lsa, olinmagan sanalar ham qizil qator bo'lib chiqadi
    const rows = s.list.results.map((r) => ({ ...r }));
    if (f.contract && !f.date) {
      const c = ledgerContracts.find((x) => x.id === f.contract);
      gapSet.forEach((d) => rows.push({ id: 'gap' + d, gap: true, date: d, contract: f.contract, student_name: c ? stName(c) : '', group: f.group, course: c && c.course }));
      rows.sort((a, b) => (a.date < b.date ? 1 : -1));
    }
    const patternOf = (r) => {
      const p = r.pattern ? A.get('dayPatterns', r.pattern) : null;
      const g = A.get('groups', r.group);
      return (p || (g && A.get('dayPatterns', g.pattern)) || {}).name || '';
    };
    const real = (rs) => rs.filter((r) => !r.gap);
    const cols = [
      { h: "O'quvchi", f: (r) => `<a href="#/contracts/${r.contract}">${esc(r.student_name)}</a>` },
      { h: 'Sana', f: (r) => A.fdate(r.date) },
      {
        h: 'Status',
        f: (r) => (canFix
          ? `<select class="f-input att-inline st-${r.gap ? 'gap' : r.status}" data-att="${r.id}">${r.gap ? '<option value="">Olinmagan</option>' : ''}${ST_OPTS.map(([k, l]) => `<option value="${k}" ${!r.gap && r.status === k ? 'selected' : ''}>${l}</option>`).join('')}</select>`
          : r.gap ? A.badge('Olinmagan', 'red') : A.badge(ATT_NAME[r.status] || r.status, ATT_TONE[r.status] || 'gray')),
      },
      { h: 'Kurs', f: (r) => esc(A.courseName(r.course)) },
      { h: 'Ustoz', f: (r) => (r.gap ? '' : esc(A.userName(r.teacher))) },
      { h: 'Guruh', f: (r) => esc(A.groupName(r.group)) },
      { h: 'Dars kunlari', f: (r) => esc(patternOf(r)) },
      { h: 'Ustoz KPI', f: (r) => (r.gap || r.no_freq ? '—' : A.num(r.tkpi)), cls: 'num', sum: (rs) => A.num(A.sum(real(rs), 'tkpi')) },
      { h: 'Yordamchi KPI', f: (r) => (r.gap || r.no_freq ? '—' : A.num(r.skpi)), cls: 'num', sum: (rs) => A.num(A.sum(real(rs), 'skpi')) },
      ...(showDebt ? [{ h: 'Qarz (dars narxi)', f: (r) => (r.gap || r.no_freq ? '—' : A.num(r.debt)), cls: 'num', sum: (rs) => A.num(A.sum(real(rs), 'debt')) }] : []),
    ];
    attRows = Object.fromEntries(rows.map((r) => [r.id, r]));
    const t = s.dates.totals;
    const gapBox = gapSet.length
      ? `<div class="note warn" style="margin-bottom:10px">⚠️ <b>${f.contract ? "Bu o'quvchiga davomat olinmagan" : 'Butun guruhga davomat olinmagan'} sanalar (${gapSet.length}):</b> ${gapSet.map((d) => `<span class="badge red">${A.fdate(d).slice(0, 5)}</span>`).join(' ')}</div>`
      : '';
    return `<div class="filters">${seg}${monthSel}
        <select class="f-input" data-filter="ast:course">${opt(courses, f.course, 'Barcha kurslar')}</select>
        <select class="f-input" data-filter="ast:group">${opt(groups, f.group, 'Barcha guruhlar')}</select>
        ${f.group ? `<select class="f-input" data-filter="ast:contract">${opt(students, f.contract, "Barcha o'quvchilar")}</select>` : `<input class="f-input" type="search" data-filter="ast:search" placeholder="O'quvchi ismi…" value="${esc(f.search)}">`}</div>
      <div class="settings tree-layout">${tree}<div class="settings-body">
        <div class="stats" style="margin-bottom:10px">${A.stat('Qatorlar', t.n)}${A.stat('Ustoz KPI', A.money(t.tkpi))}${A.stat('Yordamchi KPI', A.money(t.skpi))}${showDebt ? A.stat('Qarz (dars narxi)', A.money(t.debt)) : ''}</div>
        ${gapBox}${A.table(cols, rows, { empty: "Bu filtr bo'yicha davomat yo'q" })}${A.pager('ast', s.list)}</div></div>`;
  }

  /* ---- Jamlama: guruh va ustoz bo'yicha (serverda yig'ilgan) ---- */
  function summaryView(s) {
    const cols = (label, name, key) => [
      { h: label, f: (r) => esc(name(r[key])) },
      { h: 'Qatorlar', f: (r) => r.n, cls: 'num' },
      { h: 'Keldi', f: (r) => r.came, cls: 'num' },
      { h: 'Sababli', f: (r) => r.sab, cls: 'num' },
      { h: 'Besabab', f: (r) => r.bes, cls: 'num' },
      { h: 'Davomat %', f: (r) => `<b class="${r.came / r.n < 0.8 ? 't-red' : 't-green'}">${A.pct(r.came / r.n)}</b>`, cls: 'num' },
    ];
    const byGroup = A.sortBy(s.by_group, (r) => r.came / r.n);
    return `<div class="grid-2"><section class="card"><h2>Guruhlar bo'yicha</h2>${A.table(cols('Guruh', A.groupName, 'group'), byGroup)}</section>
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
            { h: 'Aloqa', f: (r) => `<a href="tel:+998${r.phone1}">📞 ${r.phone1}</a> · <a href="sms:+998${r.phone1}">SMS</a>${r.phone2 ? `<br><a href="tel:+998${r.phone2}">📞 ${r.phone2}</a> · <a href="sms:+998${r.phone2}">SMS</a>` : ''}${r.parent ? `<br><small>Vasiy${r.parent.relation ? ' (' + esc(r.parent.relation) + ')' : ''}: <a href="tel:+998${r.parent.phone}">${esc(r.parent.first_name)} ${r.parent.phone}</a></small>` : ''}` },
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

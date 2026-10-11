/* Guruhlar, Davomat, Vazifalar, Baholash, Ota-onalar, 50% chegirma, Eksport */
(function (A) {
  const esc = A.esc;

  /* ===================================================== Guruhlar */
  A.page('groups', {
    title: 'Guruhlar',
    section: 'groups',
    render(p, q) {
      const tab = q.tab || 'Faol';
      const all = A.vis('groups');
      const cnt = (s) => all.filter((g) => A.groupStatus(g) === s).length;
      return `${A.head('Guruhlar', "Guruh nomi rangi — to'lish holati: qizil yomon, to'q sariq o'rtacha, ko'k yaxshi, yashil zo'r", A.can('groups', 'a') ? A.btn('Yangi guruh', 'group-new', { icon: 'plus' }) : '')}
        ${A.tabs([['Faol', 'Faol', cnt('Faol')], ['Rejada', 'Rejada', cnt('Rejada')], ['Nofaol', 'Nofaol', cnt('Nofaol')]], tab, 'groups')}
        <div class="cards">${A.sortBy(all.filter((g) => A.groupStatus(g) === tab), (g) => A.groupName(g))
          .map((g) => {
            const f = A.groupFill(g);
            return `<a class="gcard" href="#/groups/${g.id}">
              <div class="gcard-h"><b class="t-${f.cls}">${esc(A.groupName(g))}</b>${A.badge(f.label, f.cls)}</div>
              <div class="muted small">${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}</div>
              <div class="small">Ustoz: <b>${esc(A.userName(g.teacher))}</b>${g.supporter ? ` · Yordamchi: ${esc(A.userName(g.supporter))}` : ''}</div>
              <div class="bar"><i class="bg-${f.cls}" style="width:${Math.min(100, f.pct * 100)}%"></i></div>
              <div class="small row between"><span>${f.n} / ${f.cap} talaba</span><span>${f.free} bo'sh o'rin · ${A.pct(f.pct)}</span></div>
            </a>`;
          })
          .join('') || A.empty("Guruh yo'q")}</div>`;
    },
  });

  A.groupForm = (g) => {
    const isNew = !g;
    const B = A.branchIds()[0];
    const nextNum = (course) => Math.max(0, ...A.rows('groups').filter((x) => x.branch === B && x.course === course).map((x) => x.number)) + 1;
    A.form({
      title: isNew ? 'Yangi guruh' : A.groupName(g),
      values: g ? { ...g } : { branch: B, start: A.today() },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, readonly: () => !isNew && A.role() !== 'ADMIN', options: () => A.optList('courses', 'name', (c) => c.status === 'Faol'), help: isNew ? '' : "Kursni faqat Admin o'zgartiradi" },
        { name: 'pattern', label: 'Dars kunlari', type: 'seg', required: true, show: (x) => x.course, options: () => A.optList('dayPatterns') },
        { name: 'time', label: 'Dars vaqti', type: 'seg', required: true, show: (x) => x.pattern, options: () => A.optList('lessonTimes', (t) => `${t.start}-${t.end}`, (t) => t.branch === B) },
        { name: 'teacher', label: 'Ustoz', type: 'select', required: true, show: (x) => x.time, options: () => A.S.users.filter((u) => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(u.role) && u.status === 'Faol').map((u) => [u.id, u.full_name]) },
        { name: 'supporter', label: 'Yordamchi ustoz (ixtiyoriy)', type: 'select', show: (x) => x.teacher, options: (x) => A.S.users.filter((u) => ['YORDAMCHI', 'USTOZ_YORDAMCHI'].includes(u.role) && u.id !== x.teacher).map((u) => [u.id, u.full_name]), placeholder: "Yo'q" },
        {
          name: 'room', label: 'Xona', type: 'select', required: true, show: (x) => x.teacher,
          options: (x) => A.rows('rooms').filter((r) => r.branch === B && r.status === 'Faol').map((r) => {
            const busy = A.rows('groups').some((o) => o.room === r.id && o.time === x.time && o.pattern === x.pattern && A.groupStatus(o) !== 'Nofaol' && (!g || o.id !== g.id));
            return [r.id, `${r.name} (${r.capacity} o'rin)${busy ? ' — shu vaqtda band!' : ''}`];
          }),
        },
        { name: 'start', label: 'Boshlanish sana', type: 'date', required: true, show: (x) => x.room, half: true },
        { name: 'end', label: 'Tugash sana', type: 'date', show: (x) => x.room, half: true, validate: (d, x) => (d <= x.start ? "Boshlanish sanadan kichik bo'lolmaydi!" : '') },
        { name: 'num', label: 'Guruh raqami', type: 'computed', show: (x) => x.course, compute: (x) => `${A.courseName(x.course)} / #${g ? g.number : nextNum(x.course)} (avtomatik)` },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.room },
      ],
      onSubmit(x) {
        const rec = { course: x.course, pattern: x.pattern, time: x.time, teacher: x.teacher, supporter: x.supporter, room: x.room, start: x.start, end: x.end, comment: x.comment };
        if (isNew) {
          const n = A.insert('groups', { ...rec, branch: B, number: nextNum(x.course) }, 'Guruh');
          A.toast(`Guruh yaratildi: ${A.groupName(n)}`);
          A.go('groups/' + n.id);
        } else {
          A.patch('groups', g.id, rec, 'Guruh', A.groupName(g));
          A.toast('Saqlandi');
          A.refresh();
        }
      },
    });
  };
  A.act['group-new'] = () => A.groupForm(null);
  A.act['group-edit'] = (el) => A.groupForm(A.get('groups', el.dataset.id));

  A.page('groups/:id', {
    title: 'Guruh',
    section: 'groups',
    render({ id }, q) {
      const g = A.get('groups', id);
      if (!g || !A.myGroupIds().includes(id)) return A.head('Guruh topilmadi') + A.empty("Guruh yo'q yoki sizga ko'rinmaydi");
      const f = A.groupFill(g);
      const ym = q.m || A.ym(A.today());
      const contracts = A.sortBy(A.rows('contracts').filter((c) => c.group === id), (c) => A.contractName(c));
      const active = contracts.filter((c) => A.contractStatus(c) !== 'Nofaol');
      const pat = A.get('dayPatterns', g.pattern);
      const days = A.lessonDaysInMonth(ym, pat.weekdays).filter((d) => d >= g.start);
      const att = A.rows('attendance').filter((a) => a.group === id && A.ym(a.date) === ym);
      const cell = (cid, d) => {
        const a = att.find((x) => x.contract === cid && x.date === d);
        return a ? A.attBadge(a.status) : d < A.today() ? '<span class="att att-empty">·</span>' : '';
      };
      const freq = A.freqRec(g.branch, g.pattern, g.course, ym);
      return `<a class="back" href="#/groups">← Guruhlar</a>
        ${A.head(A.groupName(g), `${A.badge(A.groupStatus(g), A.groupStatus(g) === 'Faol' ? 'green' : 'blue')} · ${esc(A.patternName(g.pattern))} · ${A.timeName(g.time)} · ${esc(A.roomName(g.room))}`,
          `${A.can('attendance', 'a') && A.hasLesson(g, A.today()) ? `<a class="btn primary" href="#/attendance?tab=take&group=${g.id}">${A.icon('check')}Davomat olish</a>` : ''}
           ${A.can('groups', 'e') ? A.btn('Tahrirlash', 'group-edit', { id, cls: 'ghost' }) : ''}`)}
        <div class="stats">
          ${A.stat("To'lish", `<span class="t-${f.cls}">${A.pct(f.pct)}</span>`, `${f.label} · ${f.n}/${f.cap}`)}
          ${A.stat("Bo'sh o'rinlar", f.free)}
          ${A.stat('Ustoz', esc(A.userName(g.teacher)), g.supporter ? 'Yordamchi: ' + esc(A.userName(g.supporter)) : "Yordamchi yo'q")}
          ${A.stat(`${A.ymLabel(ym)}: dars soni`, freq ? freq.frequency : '—', freq ? (freq.status === 'Tasdiqlangan' ? 'tasdiqlangan' : 'TAKLIF — tasdiqlanmagan') : 'kiritilmagan', freq && freq.status !== 'Tasdiqlangan' ? 'warn' : '')}
        </div>
        <section class="card"><div class="row between"><h2>Davomat jurnali</h2>
          <select class="f-input" onchange="location.hash='#/groups/${id}?m='+this.value">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
          <div class="tbl-wrap"><table class="journal"><thead><tr><th>Talaba</th>${days.map((d) => `<th>${d.slice(8)}<br><small>${A.WD[A.isoWeekday(d)]}</small></th>`).join('')}<th>Qarz</th></tr></thead>
          <tbody>${active
            .map((c) => `<tr><td><a href="#/contracts/${c.id}" class="${A.debtOf(c.id) > 0 ? 't-red' : ''}">${esc(A.studentName(c.student))}</a></td>${days.map((d) => `<td>${cell(c.id, d)}</td>`).join('')}<td class="num">${A.num(A.debtOf(c.id))}</td></tr>`)
            .join('')}</tbody></table></div>
          <p class="muted small">1 — keldi, 0 — sababli, X — besabab, – — nofaol, · — davomat olinmagan</p>
        </section>
        ${contracts.length > active.length ? `<section class="card"><h2>Nofaol talabalar</h2>${A.table([{ h: 'Shartnoma', f: (c) => `<a href="#/contracts/${c.id}">${esc(A.contractName(c))}</a>` }, { h: 'Tugagan', f: (c) => A.fdate(c.end) }, { h: 'Sabab', f: (c) => esc(c.stop_reason) }], contracts.filter((c) => A.contractStatus(c) === 'Nofaol'))}</section>` : ''}`;
    },
  });

  /* ---- Guruhlar tahlili ---- */
  A.page('groupAnalysis', {
    title: 'Guruhlar tahlili',
    section: 'groupAnalysis',
    render(p, q) {
      const tab = q.tab || 'status';
      const groups = A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol');
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
        <section class="card">${A.chart({ type: 'bar', data: { labels: rows.map((r) => r.label), datasets: [{ label: 'Talabalar', data: rows.map((r) => r.n), backgroundColor: A.PALETTE[0] }, { label: "Bo'sh o'rinlar", data: rows.map((r) => r.cap - r.n), backgroundColor: '#d9d9de' }] }, options: { indexAxis: 'y', scales: { x: { stacked: true }, y: { stacked: true } } } }, 280)}</section></div>`;
    },
  });

  /* ===================================================== Davomat */
  A.ui.att = { group: '', date: '', sub: false, subTeacher: '', subSupporter: '' };

  A.page('attendance', {
    title: 'Davomatlar',
    section: 'attendance',
    render(p, q) {
      const tab = q.tab || 'take';
      const absCount = A.vis('attendance').filter((a) => a.status === 'X' && A.ym(a.date) === A.ym(A.today()) && a.contact === "Bog'lanishga").length;
      const mk = A.rows('makeups').filter((m) => m.status === 'Kutilmoqda').length;
      return `${A.head('Davomatlar', 'Davomatni ustoz oladi. Menejerlar o\'tgan sanalarni tuzatishi mumkin')}
        ${A.tabs([['take', 'Davomat olish'], ['absent', 'Kelmaganlar', absCount || undefined], ['stats', 'Statistika'], ['makeup', 'Qoldirilgan darslar', mk || undefined]], tab, 'attendance')}
        ${tab === 'take' ? takeView(q) : tab === 'absent' ? absentView() : tab === 'stats' ? statsView() : makeupView()}`;
    },
  });

  const canTake = () => A.can('attendance', 'a');
  const isTeacherSelf = () => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role());
  const takeGroups = () => {
    const me = A.S.currentUser;
    return A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol' && (isTeacherSelf() ? g.teacher === me : true));
  };

  function takeView(q) {
    if (!canTake()) {
      return `<div class="alert info">${A.icon('check')}<div><b>Davomatni faqat ustoz oladi.</b> Siz yordamchi sifatida guruh davomatini ko'rishingiz mumkin. Yordamchi KPI'si ustoz olgan davomat asosida avtomatik hisoblanadi.</div></div>
        ${A.vis('groups').map((g) => `<a class="btn ghost" href="#/groups/${g.id}">${esc(A.groupName(g))} jurnali</a>`).join(' ')}`;
    }
    const st = A.ui.att;
    if (q.group) st.group = q.group;
    const groups = takeGroups();
    if (groups.length === 1) st.group = groups[0].id;
    if (st.group && !groups.some((g) => g.id === st.group)) st.group = '';
    const today = A.today();
    const managerMode = !isTeacherSelf() || A.isManager();
    if (!st.date || !managerMode) st.date = today;
    const g = A.get('groups', st.group);

    let html = `<section class="card take-head">
      <div class="field"><label class="lbl">1. Guruh</label>
        ${groups.length === 1 ? `<div class="computed">${esc(A.groupName(groups[0]))} <span class="muted small">(yagona faol guruhingiz — avtomatik tanlandi)</span></div>` : `<select class="f-input" id="att-group"><option value="">Guruhni tanlang…</option>${groups
          .map((x) => `<option value="${x.id}" ${x.id === st.group ? 'selected' : ''}>${esc(A.groupName(x))} · ${esc(A.patternName(x.pattern))} ${A.timeName(x.time)}${A.hasLesson(x, today) ? ' · bugun dars bor' : ''}</option>`)
          .join('')}</select>`}
      </div>
      <div class="field"><label class="lbl">2. Sana</label>
        ${managerMode ? `<input type="date" class="f-input" id="att-date" value="${st.date}" max="${today}"><div class="help">Siz o'tgan sanalarni ham tuzata olasiz (≤ bugun)</div>` : `<div class="computed">${A.WD_FULL[A.isoWeekday(today)]}, ${A.fdate(today)} <span class="muted small">— ustoz faqat bugungi davomatni oladi</span></div>`}
      </div>
    </section>`;
    if (!g) return html + (groups.length ? '' : A.empty("Sizda faol guruh yo'q"));

    // Sana tekshiruvi (AppSheet TakeAttendance.Date Valid_If)
    let err = '';
    if (st.date > today) err = "Kelajak sana bilan davomat olib bo'lmaydi";
    else if (!A.hasLesson(g, st.date)) err = `Guruhning bu sanaga darsi yo'q (${A.patternName(g.pattern)})`;
    if (err) {
      const next = (() => { for (let i = 0; i < 8; i++) { const d = A.addDays(today, -i); if (A.hasLesson(g, d)) return d; } return null; })();
      return html + `<div class="alert danger">${A.icon('alert')}<div><b>${esc(err)}</b>${managerMode && next ? `<br>Eng yaqin dars kuni: <a href="#" data-act="att-setdate" data-id="${next}">${A.fdate(next)}</a>` : ''}${!managerMode ? '<br>Demo sanani o\'zgartirish uchun yuqoridagi sana tugmasini bosing.' : ''}</div></div>`;
    }

    // O'rindosh
    const canSub = ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI'].includes(A.role());
    if (canSub) {
      html += `<section class="card"><label class="check"><input type="checkbox" id="att-sub" ${st.sub ? 'checked' : ''}> 3. Darsni boshqa ustoz o'tdi (o'rindosh)</label>
        ${st.sub ? `<div class="row gap wrap">
          <select class="f-input" id="att-subt"><option value="">O'rindosh ustoz…</option>${A.S.users.filter((u) => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(u.role) && u.id !== g.teacher).map((u) => `<option value="${u.id}" ${u.id === st.subTeacher ? 'selected' : ''}>${esc(u.full_name)}</option>`).join('')}</select>
          <select class="f-input" id="att-subs"><option value="">O'rindosh yordamchi (ixtiyoriy)…</option>${A.S.users.filter((u) => ['YORDAMCHI', 'USTOZ_YORDAMCHI'].includes(u.role) && u.id !== g.supporter).map((u) => `<option value="${u.id}" ${u.id === st.subSupporter ? 'selected' : ''}>${esc(u.full_name)}</option>`).join('')}</select>
        </div><p class="muted small">KPI darsni amalda o'tgan kishiga yoziladi.</p>` : ''}</section>`;
    }

    const contracts = A.rows('contracts').filter((c) => c.group === g.id && c.start <= st.date && (!c.end || c.end >= st.date));
    const att = A.rows('attendance').filter((a) => a.group === g.id && a.date === st.date);
    const marked = (cid) => att.find((a) => a.contract === cid);
    const list = A.sortBy(contracts, (c) => A.studentName(c.student));
    // Belgilanmaganlar yuqorida — tartib ekran ochilganda bir marta belgilanadi,
    // belgilash paytida qatorlar sakramasligi uchun (telefonda noto'g'ri bosishning oldini oladi)
    const key = `${g.id}|${st.date}`;
    if (st.orderKey !== key) {
      st.orderKey = key;
      st.order = [...list.filter((c) => !marked(c.id)), ...list.filter((c) => marked(c.id))].map((c) => c.id);
    }
    const sorted = A.sortBy(list, (c) => { const i = st.order.indexOf(c.id); return i < 0 ? 1e6 : i; });
    const done = contracts.filter((c) => marked(c.id)).length;
    const allowed = A.S.attendanceStatuses.filter((s) => s.roles.includes(A.role())).map((s) => s.code);
    const rowEdit = (a) => A.canEdit('attendance', a);

    html += `<section class="card att-card">
      <div class="row between wrap"><h2>4. Talabalar · ${done}/${contracts.length} belgilandi</h2>
        ${done < contracts.length && allowed.includes('1') ? `<button class="btn" data-act="att-all">Hammasi keldi</button>` : done ? A.badge('Davomat olingan', 'green') : ''}</div>
      <div class="bar"><i class="bg-green" style="width:${contracts.length ? (done / contracts.length) * 100 : 0}%"></i></div>
      <ul class="att-list">${sorted
        .map((c) => {
          const a = marked(c.id);
          const debt = A.debtOf(c.id);
          const ed = a ? rowEdit(a) : { ok: true };
          const btn = (code, label, cls) =>
            allowed.includes(code) ? `<button class="abtn ${cls} ${a && a.status === code ? 'on' : ''}" data-act="att-mark" data-id="${c.id}" data-s="${code}" ${a && !ed.ok ? `disabled title="${esc(ed.why)}"` : ''}>${label}</button>` : '';
          return `<li class="${a ? 'done' : ''}">
            <div class="att-name"><b class="${debt > 0 ? 't-red' : ''}">${esc(A.studentName(c.student))}</b>
              <small class="muted">${debt > 0 ? 'qarz ' + A.num(debt) : ''}${a && a.comment ? ' · ' + esc(a.comment) : ''}</small></div>
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
    if (gs) gs.onchange = () => { st.group = gs.value; st.sub = false; history.replaceState(null, '', '#/attendance?tab=take'); A.refresh(); };
    const ds = document.getElementById('att-date');
    if (ds) ds.onchange = () => { st.date = ds.value; A.refresh(); };
    const sb = document.getElementById('att-sub');
    if (sb) sb.onchange = () => { st.sub = sb.checked; A.refresh(); };
    const t = document.getElementById('att-subt');
    if (t) t.onchange = () => (st.subTeacher = t.value);
    const s = document.getElementById('att-subs');
    if (s) s.onchange = () => (st.subSupporter = s.value);
  };
  A.pages.attendance.mount = (p, q) => { if ((q.tab || 'take') === 'take') bindTake(); };

  A.act['att-setdate'] = (el) => { A.ui.att.date = el.dataset.id; A.refresh(); };

  function markAttendance(cid, status, comment) {
    const st = A.ui.att;
    const g = A.get('groups', st.group);
    const c = A.get('contracts', cid);
    const existing = A.rows('attendance').find((a) => a.group === g.id && a.contract === cid && a.date === st.date);
    const teacher = st.sub && st.subTeacher ? st.subTeacher : g.teacher;
    const supporter = st.sub && st.subSupporter ? st.subSupporter : g.supporter;
    if (existing) {
      const patch = { status, comment: comment ?? existing.comment };
      if (status === '1' || status === '-') { patch.contact = ''; }
      else if (!existing.contact) patch.contact = "Bog'lanishga";
      A.patch('attendance', existing.id, patch, 'Davomat', `${A.studentName(c.student)} ${A.fdate(st.date)}`);
      A.calcAtt(existing);
    } else {
      const a = {
        branch: g.branch, group: g.id, course: g.course, contract: cid, date: st.date, status, teacher, supporter, pattern: g.pattern,
        contact: status === 'X' || status === '0' ? "Bog'lanishga" : '', comment: comment || '',
      };
      A.calcAtt(a);
      A.insert('attendance', a, 'Davomat', `${A.studentName(c.student)} ${A.fdate(st.date)} = ${A.ATT[status]}`);
    }
    A.save();
  }
  A.act['att-mark'] = (el) => {
    const cid = el.dataset.id, s = el.dataset.s;
    if (s === '0') {
      A.form({
        title: 'Sababli — izoh',
        fields: [{ name: 'comment', label: 'Sababi', type: 'textarea', required: true, placeholder: 'Masalan: kasal, oldindan ogohlantirdi' }],
        submit: 'Belgilash',
        onSubmit: (v) => { markAttendance(cid, '0', v.comment); A.refresh(); },
      });
      return;
    }
    markAttendance(cid, s);
    A.refresh();
  };
  A.act['att-all'] = () => {
    const st = A.ui.att;
    const marked = new Set(A.rows('attendance').filter((a) => a.group === st.group && a.date === st.date).map((a) => a.contract));
    const list = A.rows('contracts').filter((c) => c.group === st.group && c.start <= st.date && (!c.end || c.end >= st.date) && !marked.has(c.id));
    list.forEach((c) => markAttendance(c.id, '1'));
    A.toast(`${list.length} ta talaba «Keldi» deb belgilandi`);
    A.refresh();
  };

  /* ---- Kelmaganlar ---- */
  function absentView() {
    const ym = A.q('abs:month', A.ym(A.today()));
    const only = A.q('abs:status', '');
    const rows = A.sortBy(
      A.vis('attendance').filter((a) => (a.status === 'X' || a.status === '0') && A.ym(a.date) === ym && (!only || a.status === only)),
      (a) => a.date, true,
    );
    const me = A.S.currentUser;
    const pendingMk = new Set(A.rows('makeups').filter((m) => m.status !== 'Rad etildi').map((m) => m.attendance));
    return `<div class="filters">
        <select class="f-input" data-filter="abs:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select>
        <select class="f-input" data-filter="abs:status"><option value="">Besabab va sababli</option><option value="X" ${only === 'X' ? 'selected' : ''}>Faqat besabab (X)</option><option value="0" ${only === '0' ? 'selected' : ''}>Faqat sababli (0)</option></select>
      </div>
      <p class="muted small">Bog'lanish holatini shu yerning o'zida o'zgartiring. "Gaplashildi" bo'lsa izoh majburiy. Besabab qatorda ustoz «Darsni yetkazdim» so'rovini yuborishi mumkin.</p>
      ${A.table(
        [
          { h: 'Sana', f: (a) => `${A.fdate(a.date)} <span class="muted small">${A.WD[A.isoWeekday(a.date)]}</span>` },
          { h: 'Talaba', f: (a) => { const c = A.get('contracts', a.contract); const st = A.get('students', c.student); return `<a href="#/contracts/${c.id}">${esc(A.studentName(st))}</a><br><a class="small" href="tel:+998${st.phone1}">+998 ${st.phone1}</a>`; } },
          { h: 'Guruh', f: (a) => esc(A.groupName(a.group)) },
          { h: 'Status', f: (a) => A.attBadge(a.status) + ' ' + A.ATT[a.status] },
          {
            h: "Bog'lanish holati",
            f: (a) => {
              const ed = A.canEdit('attendance', a);
              const canC = A.can('attendance', 'e') || A.can('attendance', 'a');
              return canC ? `<select class="f-input sm" data-act-change="att-contact" data-id="${a.id}">${A.CONTACT.map((c) => `<option ${a.contact === c ? 'selected' : ''}>${c}</option>`).join('')}</select>` : esc(a.contact);
            },
          },
          { h: 'Izoh', f: (a) => esc(a.comment || '') },
          {
            h: '',
            f: (a) => {
              if (a.status !== 'X') return '';
              if (pendingMk.has(a.id)) return A.badge("So'rov yuborilgan", 'blue');
              return a.teacher === me && ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role()) ? `<button class="btn sm" data-act="makeup-new" data-id="${a.id}">Darsni yetkazdim</button>` : '';
            },
          },
        ],
        rows,
        { empty: "Bu oyda kelmaganlar yo'q" },
      )}`;
  }
  document.addEventListener('change', (e) => {
    const el = e.target.closest('[data-act-change="att-contact"]');
    if (!el) return;
    const a = A.get('attendance', el.dataset.id);
    const val = el.value;
    if (val === 'Gaplashildi') {
      A.form({
        title: 'Gaplashildi — izoh majburiy',
        fields: [{ name: 'comment', label: 'Nima deyildi?', type: 'textarea', required: true }],
        values: { comment: a.comment },
        onSubmit: (v) => { A.patch('attendance', a.id, { contact: val, comment: v.comment }, 'Davomat', "Bog'lanish holati"); A.refresh(); },
      });
      el.value = a.contact;
      return;
    }
    A.patch('attendance', a.id, { contact: val }, 'Davomat', "Bog'lanish holati");
    A.toast('Saqlandi');
  });

  A.act['makeup-new'] = (el) => {
    const a = A.get('attendance', el.dataset.id);
    A.form({
      title: 'Qoldirilgan darsni yetkazish',
      intro: `<div class="note info">${esc(A.studentName(A.get('contracts', a.contract).student))} · ${A.fdate(a.date)} da besabab qoldirgan dars. Tasdiqlansa status «Sababli»ga o'zgaradi va sizga KPI yoziladi.</div>`,
      fields: [
        { name: 'makeup_date', label: 'Dars qachon yetkazildi', type: 'date', required: true, default: A.today(), validate: (d) => (d < a.date ? "Qoldirilgan sanadan oldin bo'lishi mumkin emas" : d > A.today() ? "Kelajak sana bo'lishi mumkin emas" : '') },
        { name: 'comment', label: 'Izoh', type: 'textarea', required: true, placeholder: "Masalan: shanba kuni alohida o'tdim" },
      ],
      submit: "So'rov yuborish",
      onSubmit(v) {
        A.insert('makeups', { attendance: a.id, teacher: A.S.currentUser, makeup_date: v.makeup_date, comment: v.comment, status: 'Kutilmoqda', reviewed_by: '', reviewed_at: null, reject_reason: '' }, "Dars yetkazish so'rovi", A.studentName(A.get('contracts', a.contract).student));
        A.toast("So'rov yuborildi. Menejerlarga Telegram xabar ketadi (haqiqiy tizimda)");
        A.refresh();
      },
    });
  };

  function makeupView() {
    const rows = A.sortBy(A.rows('makeups').filter((m) => !A.isTeacherRole() || m.teacher === A.S.currentUser), (m) => m.created_at, true);
    return makeupTable(rows);
  }
  A.makeupTable = makeupTable;
  function makeupTable(rows) {
    return A.table(
      [
        { h: "So'radi", f: (m) => `${esc(A.userName(m.teacher))}<br><small class="muted">${A.fdt(m.created_at)}</small>` },
        { h: 'Talaba / qoldirilgan dars', f: (m) => { const a = A.get('attendance', m.attendance); return `${esc(A.studentName(A.get('contracts', a.contract).student))}<br><small class="muted">${esc(A.groupName(a.group))} · ${A.fdate(a.date)} · hozir: ${A.ATT[a.status]}</small>`; } },
        { h: 'Yetkazildi', f: (m) => A.fdate(m.makeup_date) },
        { h: 'Izoh', f: (m) => esc(m.comment) },
        { h: 'Holat', f: (m) => A.badge(m.status, m.status === 'Tasdiqlandi' ? 'green' : m.status === 'Rad etildi' ? 'red' : 'orange') + (m.reviewed_by ? `<br><small class="muted">${esc(A.userName(m.reviewed_by))}${m.reject_reason ? ': ' + esc(m.reject_reason) : ''}</small>` : '') },
        { h: '', f: (m) => (m.status === 'Kutilmoqda' && A.canApproveMakeup() ? `<div class="row gap"><button class="btn sm primary" data-act="makeup-ok" data-id="${m.id}">Tasdiqlash</button><button class="btn sm ghost" data-act="makeup-no" data-id="${m.id}">Rad etish</button></div>` : '') },
      ],
      rows,
      { empty: "So'rov yo'q" },
    );
  }
  A.act['makeup-ok'] = (el) => {
    const m = A.get('makeups', el.dataset.id);
    const a = A.get('attendance', m.attendance);
    const before = a.tkpi;
    A.patch('attendance', a.id, { status: '0', comment: `Dars yetkazildi (${A.fdate(m.makeup_date)}): ${m.comment}`, contact: a.contact || 'Gaplashildi' }, 'Davomat', 'X → 0 (dars yetkazildi)');
    A.calcAtt(a);
    A.patch('makeups', m.id, { status: 'Tasdiqlandi', reviewed_by: A.S.currentUser, reviewed_at: Date.now() }, "Dars yetkazish so'rovi", 'Tasdiqlandi');
    A.toast(`Tasdiqlandi. Ustoz KPI: ${A.num(before)} → ${A.num(a.tkpi)} so'm`);
    A.refresh();
  };
  A.act['makeup-no'] = (el) => {
    const m = A.get('makeups', el.dataset.id);
    A.form({
      title: "So'rovni rad etish",
      fields: [{ name: 'reason', label: 'Sabab', type: 'textarea', required: true }],
      submit: 'Rad etish',
      onSubmit(v) {
        A.patch('makeups', m.id, { status: 'Rad etildi', reviewed_by: A.S.currentUser, reviewed_at: Date.now(), reject_reason: v.reason }, "Dars yetkazish so'rovi", 'Rad etildi');
        A.refresh();
      },
    });
  };

  /* ---- Statistika ---- */
  function statsView() {
    const ym = A.q('ast:month', A.ym(A.today()));
    const att = A.vis('attendance').filter((a) => A.ym(a.date) === ym && a.status !== '-');
    const agg = (keyFn) =>
      [...A.groupBy(att, keyFn)].map(([k, list]) => ({
        k, n: list.length, came: list.filter((a) => a.status === '1').length, sab: list.filter((a) => a.status === '0').length, bes: list.filter((a) => a.status === 'X').length,
      }));
    const byGroup = agg((a) => a.group), byTeacher = agg((a) => a.teacher);
    const cols = (label, name) => [
      { h: label, f: (r) => esc(name(r.k)) },
      { h: 'Qatorlar', f: (r) => r.n, cls: 'num' },
      { h: 'Keldi', f: (r) => r.came, cls: 'num' },
      { h: 'Sababli', f: (r) => r.sab, cls: 'num' },
      { h: 'Besabab', f: (r) => r.bes, cls: 'num' },
      { h: 'Davomat %', f: (r) => `<b class="${r.came / r.n < 0.8 ? 't-red' : 't-green'}">${A.pct(r.came / r.n)}</b>`, cls: 'num' },
    ];
    return `<div class="filters"><select class="f-input" data-filter="ast:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="grid-2"><section class="card"><h2>Guruhlar bo'yicha</h2>${A.table(cols('Guruh', A.groupName), A.sortBy(byGroup, (r) => r.came / r.n))}</section>
      <section class="card"><h2>Ustozlar bo'yicha</h2>${A.table(cols('Ustoz', A.userName), byTeacher)}
      ${A.chart({ type: 'bar', data: { labels: byGroup.map((r) => A.groupName(r.k)), datasets: [{ label: 'Davomat %', data: byGroup.map((r) => Math.round((r.came / r.n) * 100)), backgroundColor: A.PALETTE[0] }] }, options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } } }, 220)}</section></div>`;
  }

  /* ===================================================== Talaba vazifalari */
  const TASK_ST = { Rejada: 'gray', Yuklatildi: 'blue', Tamomladi: 'green', Bajarolmadi: 'orange', Bajarmadi: 'red' };
  A.page('tasks', {
    title: 'Talaba vazifalari',
    section: 'tasks',
    render() {
      const rows = A.sortBy(A.vis('tasks'), (t) => t.deadline, true);
      return `${A.head('Talaba vazifalari', 'Ustoz o\'z guruhi talabalariga vazifa beradi va baholaydi', A.can('tasks', 'a') ? A.btn('Yangi vazifa', 'task-new', { icon: 'plus' }) : '')}
        ${A.table(
          [
            { h: 'Talaba', f: (t) => esc(A.studentName(A.get('contracts', t.contract).student)) },
            { h: 'Guruh', f: (t) => esc(A.groupName(t.group)) },
            { h: 'Vazifa', f: (t) => esc(t.task) },
            { h: 'Dedlayn', f: (t) => `<span class="${t.deadline < A.today() && !['Tamomladi', 'Bajarmadi', 'Bajarolmadi'].includes(t.status) ? 't-red' : ''}">${A.fdate(t.deadline)}</span>` },
            { h: 'Status', f: (t) => A.badge(t.status, TASK_ST[t.status]) + (t.completion != null ? ` <b>${t.completion}%</b>` : '') },
            { h: 'Izoh', f: (t) => esc(t.teacher_comment || '') },
            { h: '', f: (t) => (A.can('tasks', 'e') ? `<button class="btn sm ghost" data-act="task-edit" data-id="${t.id}">Tahrirlash</button>` : '') },
          ],
          rows,
          { empty: "Vazifa yo'q" },
        )}`;
    },
  });
  A.taskForm = (t) => {
    const me = A.S.currentUser;
    const self = ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role());
    A.form({
      title: t ? 'Vazifa' : 'Yangi vazifa',
      values: t ? { ...t } : { teacher: self ? me : '', deadline: A.addDays(A.today(), 3), status: 'Rejada' },
      fields: [
        { name: 'teacher', label: 'Ustoz', type: 'select', required: true, readonly: () => self, options: () => A.S.users.filter((u) => ['USTOZ', 'USTOZ_YORDAMCHI'].includes(u.role)).map((u) => [u.id, u.full_name]), resets: ['group'] },
        { name: 'group', label: 'Guruh', type: 'select', required: true, auto: true, show: (x) => x.teacher, options: (x) => A.rows('groups').filter((g) => g.teacher === x.teacher && A.groupStatus(g) === 'Faol').map((g) => [g.id, A.groupName(g)]), resets: ['contract'] },
        { name: 'contract', label: 'Talaba', type: 'select', required: true, show: (x) => x.group, options: (x) => A.activeContractsOf(x.group).map((c) => [c.id, A.studentName(c.student)]) },
        { name: 'task', label: 'Vazifa', type: 'textarea', required: true, show: (x) => x.contract },
        { name: 'deadline', label: 'Dedlayn', type: 'date', required: true, show: (x) => x.contract, half: true },
        { name: 'status', label: 'Status', type: 'select', options: Object.keys(TASK_ST), show: (x) => x.contract, half: true },
        { name: 'completion', label: 'Bajarilish (0-100)', type: 'number', min: 0, max: 100, show: (x) => x.status === 'Tamomladi', required: (x) => x.status === 'Tamomladi', validate: (n) => (n < 0 || n > 100 ? "0 - 100 o'rtasida baho qo'yish mumkin, xolos" : '') },
        { name: 'teacher_comment', label: 'Yakuniy izoh', type: 'textarea', show: (x) => ['Tamomladi', 'Bajarmadi', 'Bajarolmadi'].includes(x.status) },
      ],
      onSubmit(x) {
        const g = A.get('groups', x.group);
        const rec = { branch: g.branch, teacher: x.teacher, course: g.course, group: x.group, contract: x.contract, task: x.task, deadline: x.deadline, status: x.status, completion: x.completion === '' ? null : x.completion, teacher_comment: x.teacher_comment };
        if (t) A.patch('tasks', t.id, rec, 'Vazifa'); else A.insert('tasks', rec, 'Vazifa');
        A.refresh();
      },
    });
  };
  A.act['task-new'] = () => A.taskForm(null);
  A.act['task-edit'] = (el) => A.taskForm(A.get('tasks', el.dataset.id));

  /* ===================================================== Baholash bo'limi (ustoz → talaba) */
  A.page('grading', {
    title: "Baholash bo'limi",
    section: 'grading',
    render() {
      const rows = A.sortBy(A.vis('gradings'), (g) => g.date, true);
      return `${A.head("Baholash bo'limi", "Ustoz guruh talabalarini baholaydi: davomat (1–20), vazifa (1–40), oy yakuni (1–500)", A.can('grading', 'a') ? A.btn('Yangi baholash', 'grading-new', { icon: 'plus' }) : '')}
        ${rows
          .map((s) => `<section class="card"><div class="row between"><h2>${esc(A.groupName(s.group))} · ${A.fdate(s.date)}</h2><span class="muted">${esc(A.userName(s.teacher))}</span></div>
          ${s.comment ? `<p class="muted">${esc(s.comment)}</p>` : ''}
          ${A.table(
            [
              { h: 'Talaba', f: (r) => esc(A.studentName(A.get('contracts', r.contract).student)) },
              { h: 'Davomat', f: (r) => r.att, cls: 'num' },
              { h: 'Vazifa', f: (r) => r.task, cls: 'num' },
              { h: 'Oy yakuni', f: (r) => r.final, cls: 'num' },
              { h: 'Jami', f: (r) => `<b>${r.att + r.task + r.final}</b>`, cls: 'num' },
            ],
            A.sortBy(s.rows, (r) => r.att + r.task + r.final, true),
          )}</section>`)
          .join('') || A.empty("Baholash yo'q")}`;
    },
  });
  A.act['grading-new'] = () => {
    const self = ['USTOZ', 'USTOZ_YORDAMCHI'].includes(A.role());
    const groups = A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol' && (!self || g.teacher === A.S.currentUser));
    const m = A.modal({
      title: 'Yangi baholash',
      wide: true,
      body: `<div class="row gap wrap"><select class="f-input" id="gr-g"><option value="">Guruh…</option>${groups.map((g) => `<option value="${g.id}">${esc(A.groupName(g))}</option>`).join('')}</select>
        <input type="date" class="f-input" id="gr-d" value="${A.today()}"><input class="f-input grow" id="gr-c" placeholder="Izoh (ixtiyoriy)"></div><div id="gr-rows"></div>`,
      footer: `<button class="btn ghost" data-close>Bekor qilish</button><button class="btn primary" id="gr-save">Saqlash</button>`,
    });
    const gs = m.el.querySelector('#gr-g');
    gs.onchange = () => {
      const list = A.activeContractsOf(gs.value);
      m.el.querySelector('#gr-rows').innerHTML = `<table class="tbl"><thead><tr><th>Talaba</th><th>Davomat (1-20)</th><th>Vazifa (1-40)</th><th>Oy yakuni (1-500)</th></tr></thead><tbody>${list
        .map((c) => `<tr data-c="${c.id}"><td>${esc(A.studentName(c.student))}</td><td><input type="number" min="1" max="20" class="f-input sm"></td><td><input type="number" min="1" max="40" class="f-input sm"></td><td><input type="number" min="1" max="500" class="f-input sm"></td></tr>`)
        .join('')}</tbody></table>`;
    };
    if (groups.length === 1) { gs.value = groups[0].id; gs.onchange(); }
    m.el.querySelector('#gr-save').onclick = () => {
      const g = A.get('groups', gs.value);
      if (!g) return A.toast('Guruhni tanlang', 'warn');
      const rows = [];
      let bad = '';
      m.el.querySelectorAll('tr[data-c]').forEach((tr) => {
        const [a, t, f] = [...tr.querySelectorAll('input')].map((i) => Number(i.value));
        if (!a && !t && !f) return;
        if (a < 1 || a > 20 || t < 1 || t > 40 || f < 1 || f > 500) bad = "Ballar ruxsat etilgan oraliqda emas (davomat 1-20, vazifa 1-40, oy yakuni 1-500)";
        rows.push({ contract: tr.dataset.c, att: a, task: t, final: f });
      });
      if (bad) return A.toast(bad, 'warn');
      if (!rows.length) return A.toast('Kamida bitta talabani baholang', 'warn');
      A.insert('gradings', { branch: g.branch, teacher: g.teacher, course: g.course, group: g.id, date: m.el.querySelector('#gr-d').value, comment: m.el.querySelector('#gr-c').value, rows }, 'Baholash', A.groupName(g));
      m.close();
      A.refresh();
    };
  };

  /* ===================================================== Baholash (talaba → ustoz) */
  const CRIT = ['Mavzuni sodda tilda tushuntira oladimi?', "Darsni qiziq o'tadimi? Qiziq metodlardan foydalanadimi?", 'Barcha talabalarga adolatli yondashadimi?', 'Kerak vaqtda yordam beradimi?', 'Kamchiliklar haqida tavsiya berib, ruhlantiradimi?'];
  A.page('evaluations', {
    title: 'Baholash',
    section: 'evaluations',
    render() {
      const rows = A.sortBy(A.vis('evaluations'), (e) => e.date, true);
      const byT = [...A.groupBy(rows, (e) => e.teacher)].map(([t, l]) => ({ t, n: l.length, avg: A.sum(l, (e) => A.sum(e.scores, (x) => x)) / l.length }));
      return `${A.head('Baholash: talaba ustozni baholaydi', '5 ta mezon, har biri 0–10. Jami — 50 balldan', A.can('evaluations', 'a') ? A.btn('Yangi baholash', 'eval-new', { icon: 'plus' }) : '')}
        <div class="alert info">${A.icon('alert')}<div>Ochiq savol (CLAUDE.md, 15-bo'lim, 12-savol): talabalar tizimga kirmaydi — bu baholashni kim kiritadi? Hozircha administrator qog'ozdan kiritadi deb olingan.</div></div>
        <div class="stats">${byT.map((r) => A.stat(A.userName(r.t), `${r.avg.toFixed(1)} / 50`, `${r.n} ta baho`)).join('')}</div>
        ${A.table(
          [
            { h: 'Sana', f: (e) => A.fdate(e.date) },
            { h: 'Ustoz', f: (e) => esc(A.userName(e.teacher)) },
            { h: 'Talaba', f: (e) => esc(A.studentName(A.get('contracts', e.contract).student)) },
            ...CRIT.map((c, i) => ({ h: `${i + 1}`, f: (e) => e.scores[i], cls: 'num' })),
            { h: 'Jami', f: (e) => `<b>${A.sum(e.scores, (x) => x)}</b>`, cls: 'num' },
            { h: 'Izoh', f: (e) => esc(e.comment) },
          ],
          rows,
        )}
        <ol class="muted small">${CRIT.map((c) => `<li>${esc(c)}</li>`).join('')}</ol>`;
    },
  });
  A.act['eval-new'] = () => {
    const opts = [...Array(11).keys()].map((n) => [String(n), String(n)]);
    A.form({
      title: 'Talaba ustozni baholaydi',
      fields: [
        { name: 'contract', label: 'Talaba', type: 'select', required: true, options: () => A.vis('contracts').filter((c) => A.contractStatus(c) === 'Faol').map((c) => [c.id, `${A.studentName(c.student)} · ${A.groupName(c.group)}`]) },
        { name: 'teacher', label: 'Ustoz', type: 'computed', show: (x) => x.contract, compute: (x) => esc(A.userName(A.get('groups', A.get('contracts', x.contract).group).teacher)) },
        ...CRIT.map((c, i) => ({ name: 's' + i, label: `${i + 1}. ${c}`, type: 'select', options: opts, required: true, show: (x) => x.contract })),
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.contract },
      ],
      onSubmit(x) {
        const c = A.get('contracts', x.contract);
        const g = A.get('groups', c.group);
        A.insert('evaluations', { branch: c.branch, date: A.today(), contract: c.id, group: g.id, teacher: g.teacher, scores: CRIT.map((_, i) => Number(x['s' + i])), comment: x.comment }, 'Ustoz baholandi', A.userName(g.teacher));
        A.refresh();
      },
    });
  };

  /* ===================================================== Ota-onalar bilan aloqa */
  A.page('parentCalls', {
    title: 'Ota-onalar bilan aloqa',
    section: 'parentCalls',
    render() {
      const rows = A.sortBy(A.vis('parentCalls'), (r) => r.date, true);
      return `${A.head('Ota-onalar bilan aloqa', "Qo'ng'iroq va SMS havolalari talaba va vasiy telefonidan olinadi", A.can('parentCalls', 'a') ? A.btn('Yangi yozuv', 'pcall-new', { icon: 'plus' }) : '')}
        ${A.table(
          [
            { h: 'Sana', f: (r) => A.fdate(r.date) },
            { h: 'Talaba', f: (r) => { const c = A.get('contracts', r.contract); return `<a href="#/contracts/${c.id}">${esc(A.studentName(c.student))}</a><br><small class="muted">${esc(A.groupName(r.group))}</small>`; } },
            { h: 'Aloqa', f: (r) => { const st = A.get('students', A.get('contracts', r.contract).student); const p = A.get('parents', st.parent); return `<a href="tel:+998${st.phone1}">📞 ${st.phone1}</a> · <a href="sms:+998${st.phone1}">SMS</a>${p ? `<br><small>Vasiy: <a href="tel:+998${p.phone}">${esc(p.first_name)} ${p.phone}</a></small>` : ''}`; } },
            { h: 'Izoh', f: (r) => esc(r.comment) },
            { h: 'Kim', f: (r) => esc(A.userName(r.created_by)) },
          ],
          rows,
          { empty: "Yozuv yo'q" },
        )}`;
    },
  });
  A.act['pcall-new'] = () =>
    A.form({
      title: 'Ota-ona bilan aloqa',
      values: { date: A.today() },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, resets: ['group'], options: () => A.optList('courses') },
        { name: 'group', label: 'Guruh', type: 'select', required: true, show: (x) => x.course, resets: ['contract'], options: (x) => A.vis('groups').filter((g) => g.course === x.course && A.groupStatus(g) === 'Faol').map((g) => [g.id, A.groupName(g)]) },
        { name: 'contract', label: 'Talaba', type: 'select', required: true, show: (x) => x.group, options: (x) => A.activeContractsOf(x.group).map((c) => [c.id, A.studentName(c.student)]) },
        { name: 'phones', label: 'Telefonlar', type: 'computed', show: (x) => x.contract, compute: (x) => { const st = A.get('students', A.get('contracts', x.contract).student); const p = A.get('parents', st.parent); return `<a href="tel:+998${st.phone1}">+998 ${st.phone1}</a>${st.phone2 ? ', ' + st.phone2 : ''}${p ? ` · vasiy ${esc(p.first_name)}: <a href="tel:+998${p.phone}">${p.phone}</a>` : ''}`; } },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.contract },
        { name: 'comment', label: 'Izoh', type: 'textarea', required: true, show: (x) => x.contract },
      ],
      onSubmit(x) {
        const g = A.get('groups', x.group);
        A.insert('parentCalls', { branch: g.branch, course: x.course, group: x.group, contract: x.contract, date: x.date, comment: x.comment }, 'Ota-ona bilan aloqa');
        A.refresh();
      },
    });

  /* ===================================================== 50% chegirmalar */
  A.page('discount50', {
    title: '50% chegirmalar',
    section: 'discount50',
    render() {
      const rows = A.sortBy(A.vis('discount50'), (r) => r.date, true);
      return `${A.head('50% chegirmalar', 'Guruhda kamida 3 ta faol talaba bo\'lishi shart. Bitta shartnomaga bir oyda bitta yozuv', A.can('discount50', 'a') ? A.btn("Qo'shish", 'd50-new', { icon: 'plus' }) : '')}
        <div class="alert warn">${A.icon('alert')}<div>Ochiq savol (CLAUDE.md, 15-bo'lim, 3-savol): 50% chegirmaning aniq qoidasi va to'lovdagi chegirma bilan bog'lanishi hali aniqlanmagan.</div></div>
        ${A.table(
          [
            { h: 'Sana', f: (r) => A.fdate(r.date) },
            { h: 'Shartnoma', f: (r) => `<a href="#/contracts/${r.contract}">${esc(A.contractName(r.contract))}</a>` },
            { h: 'Guruh', f: (r) => esc(A.groupName(r.group)) },
            { h: 'Oy', f: (r) => A.MONTHS[r.month - 1] + ' ' + r.year },
            { h: 'Guruhdagi talabalar', f: (r) => A.activeContractsOf(r.group).length, cls: 'num' },
          ],
          rows,
          { empty: "Yozuv yo'q" },
        )}`;
    },
  });
  A.act['d50-new'] = () => {
    const ym = A.ym(A.today());
    A.form({
      title: '50% chegirma',
      values: { date: A.today(), month: String(Number(ym.slice(5))) },
      fields: [
        { name: 'group', label: 'Guruh', type: 'select', required: true, resets: ['contract'], options: () => A.vis('groups').filter((g) => A.groupStatus(g) === 'Faol').map((g) => [g.id, `${A.groupName(g)} (${A.activeContractsOf(g.id).length} talaba)`]), validate: (g) => (A.activeContractsOf(g).length < 3 ? "Guruhdagi o'quvchilar soni 3 tadan kam bo'lmasligi kerak" : '') },
        { name: 'contract', label: 'Shartnoma', type: 'select', required: true, show: (x) => x.group, options: (x) => A.activeContractsOf(x.group).map((c) => [c.id, A.contractName(c)]) },
        { name: 'month', label: 'Oy', type: 'select', required: true, show: (x) => x.contract, options: A.MONTHS.map((m, i) => [String(i + 1), m]), validate: (m, x) => (A.rows('discount50').some((d) => d.contract === x.contract && d.month === Number(m) && d.year === Number(ym.slice(0, 4))) ? 'Bu shartnomaga shu oyda 50% chegirma berilgan' : '') },
        { name: 'type', label: 'Chegirma turi', type: 'computed', show: (x) => x.contract, compute: () => esc((A.rows('discountTypes').find((d) => d.is_d50) || {}).name) + ' <span class="muted small">(sozlamadagi «50% chegirma» belgisi bo\'yicha)</span>' },
      ],
      onSubmit(x) {
        const g = A.get('groups', x.group);
        A.insert('discount50', { branch: g.branch, date: A.today(), group: x.group, contract: x.contract, month: Number(x.month), year: Number(ym.slice(0, 4)), discount_type: (A.rows('discountTypes').find((d) => d.is_d50) || {}).id }, '50% chegirma', A.contractName(x.contract));
        A.refresh();
      },
    });
  };

  /* ===================================================== Shartnoma yuklash (Excel) */
  A.page('export', {
    title: 'Shartnoma yuklash',
    section: 'export',
    render() {
      return `${A.head('Shartnoma yuklash', "Kurs va guruhlarni tanlang — shartnomalar ro'yxati Excel faylga yuklanadi (AppSheet'dagi «Exel» boti o'rniga)")}
        <section class="card narrow">
          <div class="field"><label class="lbl">Kurs</label><select class="f-input" id="ex-c"><option value="">Tanlang…</option>${A.optList('courses').map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select></div>
          <div class="field"><label class="lbl">Guruhlar</label><div class="chips" id="ex-g"><span class="muted">Avval kursni tanlang</span></div></div>
          <button class="btn primary" id="ex-go">${A.icon('download')}Excel'ga yuklash</button>
          <p class="muted small">Prototipda CSV fayl yuklanadi (Excel ochadi). Haqiqiy tizimda openpyxl bilan .xlsx bo'ladi.</p>
        </section>`;
    },
    mount() {
      const cs = document.getElementById('ex-c');
      const gbox = document.getElementById('ex-g');
      cs.onchange = () => {
        gbox.innerHTML = A.vis('groups').filter((g) => g.course === cs.value).map((g) => `<button type="button" class="chip on" data-g="${g.id}">${esc(A.groupName(g))}</button>`).join('') || '<span class="muted">Guruh yo\'q</span>';
      };
      gbox.onclick = (e) => { const b = e.target.closest('[data-g]'); if (b) b.classList.toggle('on'); };
      document.getElementById('ex-go').onclick = () => {
        const ids = [...gbox.querySelectorAll('.chip.on')].map((b) => b.dataset.g);
        if (!ids.length) return A.toast('Kamida bitta guruh tanlang', 'warn');
        const rows = A.rows('contracts').filter((c) => ids.includes(c.group));
        A.downloadCSV(`shartnomalar_${A.courseName(cs.value)}.csv`, [
          ['№', 'Talaba', 'Telefon 1', 'Telefon 2', 'Guruh', 'Turi', 'Boshlanish', 'Tugash', 'Status', 'Balans'],
          ...rows.map((c) => { const st = A.get('students', c.student); return [c.number, A.studentName(st), st.phone1, st.phone2, A.groupName(c.group), c.type, c.start, c.end, A.contractStatus(c), A.debtOf(c.id)]; }),
        ]);
        A.log('export', 'Excel eksport', `${rows.length} ta shartnoma`);
        A.save();
        A.toast(`${rows.length} ta shartnoma yuklandi`);
      };
    },
  });
})(window.App);

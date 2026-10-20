/* Codial ERP — Topshiriqlar (2026-10-16): xodimlar bir-biriga topshiriq beradi, bot eslatib turadi. */
(function (A) {
  const esc = A.esc;
  const BEFORE = [['0', 'Muddat vaqtida'], ['15', '15 daqiqa oldin'], ['60', '1 soat oldin'], ['180', '3 soat oldin'], ['1440', '1 kun oldin'], ['2880', '2 kun oldin']];
  const EVERY = [['0', 'Bir marta'], ['30', 'Har 30 daqiqa'], ['60', 'Har soat'], ['180', 'Har 3 soat'], ['1440', 'Har kuni']];
  const label = (list, v) => (list.find(([k]) => k === String(v)) || [, ''])[1];
  const pad = (n) => String(n).padStart(2, '0');
  const fdt = (iso) => { const d = new Date(iso); return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const localInput = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const left = (iso) => {
    const ms = new Date(iso) - new Date();
    const m = Math.round(Math.abs(ms) / 60000);
    const span = m >= 1440 ? `${Math.floor(m / 1440)} kun ${Math.floor((m % 1440) / 60)} soat` : m >= 60 ? `${Math.floor(m / 60)} soat ${m % 60} daq` : `${m} daqiqa`;
    return ms >= 0 ? `${span} qoldi` : `${span} o'tdi`;
  };
  const remindText = (t) => {
    const who = [t.remind_assignee && 'bajaruvchiga', t.remind_giver && 'beruvchiga'].filter(Boolean).join(' va ');
    return who ? `🔔 ${who} · ${label(BEFORE, t.remind_before).toLowerCase()} · ${label(EVERY, t.remind_every).toLowerCase()}` : '🔕 eslatmasiz';
  };

  let data = { items: [], people: [] };

  A.reloadTaskSummary = async () => {
    A.S.taskSummary = A.can('staffTasks') ? await A.http.get('/tasks/summary/').catch(() => null) : null;
    A.version++;
  };

  A.page('tasks', {
    title: 'Topshiriqlar',
    section: 'staffTasks',
    async load(p, q) {
      const box = q.box || 'in';
      const status = q.status || 'Ochiq';
      const [items, people] = await Promise.all([
        A.http.get(`/tasks/?box=${box}&status=${encodeURIComponent(status)}${q.q ? `&q=${encodeURIComponent(q.q)}` : ''}`),
        data.people.length ? data.people : A.http.get('/tasks/people/'),
        A.reloadTaskSummary(),
      ]);
      data = { items, people };
    },
    render(p, q) {
      const box = q.box || 'in';
      const status = q.status || 'Ochiq';
      const sm = A.S.taskSummary || {};
      const tabs = [['in', 'Menga berilgan', sm.in_open], ['out', 'Men bergan', sm.out_open], ...(A.isTop() ? [['all', 'Barchasi']] : [])];
      const url = (o) => `#/tasks?${new URLSearchParams({ box, status, ...(q.q ? { q: q.q } : {}), ...o })}`;
      return `${A.head('Topshiriqlar', "Xodimlar bir-biriga topshiriq beradi; Telegram bot muddatni eslatib turadi", A.can('staffTasks', 'a') ? A.btn('Yangi topshiriq', 'task-new', { icon: 'plus' }) : '')}
        <div class="tabs">${tabs.map(([k, l, n]) => `<a href="${url({ box: k })}" class="${k === box ? 'on' : ''}">${l}${n ? ` <span class="cnt">${n}</span>` : ''}</a>`).join('')}</div>
        <div class="filters">
          <input class="f-input" type="search" data-filter="q" placeholder="Mavzu yoki izoh…" value="${esc(q.q || '')}">
          <div class="seg">${['Ochiq', 'Bajarildi', 'Bekor qilindi'].map((s) => `<a class="btn sm ${s === status ? 'primary' : 'ghost'}" href="${url({ status: s })}">${s}</a>`).join('')}</div>
        </div>
        ${box === 'in' && sm.in_overdue ? `<div class="alert danger">${A.icon('alert')}<div><b>${sm.in_overdue} ta topshiriqning muddati o'tgan.</b> Bajarib, «Bajarildi» deb belgilang yoki beruvchi bilan gaplashing.</div></div>` : ''}
        <div class="task-list">${data.items.map(card).join('') || A.empty(status === 'Ochiq' ? (box === 'in' ? "Sizga berilgan ochiq topshiriq yo'q 🎉" : "Ochiq topshiriq yo'q") : "Topshiriq yo'q")}</div>`;
    },
    mount(p, q) {
      if (q.open) {
        history.replaceState(null, '', location.hash.replace(/[?&]open=[^&]+/, ''));
        openTask(q.open);
      }
    },
  });

  function card(t) {
    const tone = t.status === 'Bajarildi' ? 'green' : t.status === 'Bekor qilindi' ? 'gray' : t.overdue ? 'red' : new Date(t.due_at) - new Date() < 864e5 ? 'orange' : 'blue';
    const badge = t.status === 'Ochiq' ? (t.overdue ? A.badge("Muddati o'tgan", 'red') : A.badge('Ochiq', 'blue')) : A.badge(t.status, t.status === 'Bajarildi' ? 'green' : 'gray');
    const me = A.S.currentUser;
    return `<div class="task-card tone-${tone}" data-act="task-open" data-id="${t.id}">
      <div class="task-top"><b>${esc(t.title)}</b>${badge}</div>
      ${t.description ? `<div class="task-desc">${esc(t.description)}</div>` : ''}
      <div class="task-meta">
        <span class="t-due">${A.icon('history')} ${fdt(t.due_at)}${t.status === 'Ochiq' ? ` · ${left(t.due_at)}` : ''}</span>
        <span>${A.icon('user')} ${t.assignee === me ? '<b>Siz</b>' : esc(t.assignee_name)} ← ${t.giver === me ? '<b>siz</b>' : esc(t.giver_name)}</span>
        ${t.status === 'Ochiq' ? `<span class="muted">${remindText(t)}</span>` : ''}
        ${t.status === 'Bajarildi' ? `<span class="muted">✅ ${fdt(t.done_at)}${t.done_comment ? ` · ${esc(t.done_comment)}` : ''}</span>` : ''}
        ${t.status === 'Bekor qilindi' && t.cancel_reason ? `<span class="muted">Sabab: ${esc(t.cancel_reason)}</span>` : ''}
      </div>
      ${t.can_done || t.can_edit ? `<div class="task-actions">
        ${t.can_done ? `<button class="btn sm primary" data-act="task-done" data-id="${t.id}">✅ Bajarildi</button>` : ''}
        ${t.can_edit ? `<button class="btn sm" data-act="task-extend" data-id="${t.id}">⏰ Muddatni uzaytirish</button>
          <button class="btn sm ghost" data-act="task-edit" data-id="${t.id}">✎ Tahrirlash</button>
          <button class="btn sm ghost" data-act="task-cancel" data-id="${t.id}">Bekor qilish</button>` : ''}
      </div>` : ''}
    </div>`;
  }

  const find = (id) => data.items.find((t) => String(t.id) === String(id));
  let detail = null; // ochiq turgan topshiriq oynasi — amaldan keyin yopiladi
  const reload = async () => {
    if (detail) detail.close();
    detail = null;
    await A.reloadTaskSummary();
    A.refresh();
  };

  async function openTask(id) {
    let t = find(id);
    if (!t) {
      try {
        t = await A.http.get(`/tasks/${id}/`);
      } catch (e) {
        return A.toast(e.message, 'warn');
      }
      data.items = [t, ...data.items];
    }
    detail = A.modal({ title: 'Topshiriq', body: card(t).replace('data-act="task-open"', ''), footer: '<button class="btn ghost" data-close>Yopish</button>' });
  }
  A.act['task-open'] = (el, e) => {
    if (e && e.target.closest('button')) return; // ichidagi tugma o'zi ishlaydi
    openTask(el.dataset.id);
  };

  function taskForm(t) {
    const now = new Date();
    const def = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 18, 0);
    const me = A.S.currentUser;
    A.form({
      title: t ? 'Topshiriqni tahrirlash' : 'Yangi topshiriq',
      values: t
        ? { ...t, due: localInput(new Date(t.due_at)), who: [t.remind_assignee && 'a', t.remind_giver && 'g'].filter(Boolean), remind_before: String(t.remind_before), remind_every: String(t.remind_every) }
        : { due: localInput(def), who: ['a'], remind_before: '60', remind_every: '0' },
      fields: [
        { name: 'title', label: 'Mavzu', required: true, placeholder: "Masalan: Qarzdorlarning ota-onalariga qo'ng'iroq" },
        { name: 'description', label: 'Izoh', type: 'textarea', placeholder: 'Nima qilish kerak, qanday natija kutiladi' },
        { name: 'assignee', label: 'Bajaruvchi', type: 'select', required: true, show: () => !!t, options: () => data.people.map((u) => [u.id, u.id === me ? `${u.name} (o'zim)` : u.name]) },
        { name: 'assignees', label: 'Bajaruvchilar (bir nechtasini tanlash mumkin)', type: 'chips', show: () => !t, options: () => data.people.map((u) => [u.id, u.id === me ? `${u.name} (o'zim)` : u.name]),
          help: "Har bir bajaruvchiga alohida topshiriq ochiladi — har biri o'zi «Bajarildi» bosadi" },
        { name: 'due', label: 'Qilinish muddati (sana va soat)', type: 'datetime-local', required: true, validate: (v) => (v && new Date(v) <= new Date() ? "Muddat hozirgi vaqtdan keyin bo'lishi kerak" : '') },
        { name: 'who', label: 'Telegram orqali kimga eslatilsin', type: 'chips', options: () => [['a', 'Bajaruvchiga'], ['g', 'Menga (beruvchiga)']] },
        { name: 'remind_before', label: 'Eslatish qachon boshlansin', type: 'seg', required: true, show: (x) => (x.who || []).length, options: () => BEFORE },
        { name: 'remind_every', label: 'Qanchalik tez-tez takrorlansin', type: 'seg', required: true, show: (x) => (x.who || []).length, options: () => EVERY,
          help: "Muddat o'tsa ham topshiriq bajarilmaguncha eslatib turadi. Bajarildi yoki bekor qilinsa — to'xtaydi" },
      ],
      async onSubmit(x) {
        const body = {
          title: x.title, description: x.description || '', due_at: new Date(x.due).toISOString(),
          remind_assignee: (x.who || []).includes('a'), remind_giver: (x.who || []).includes('g'),
          remind_before: Number(x.remind_before || 60), remind_every: Number(x.remind_every || 0),
        };
        if (t) {
          const saved = await A.http.patch(`/tasks/${t.id}/`, { ...body, assignee: x.assignee });
          if (saved.assignee_linked === false && saved.assignee !== A.S.currentUser) A.toast(`Saqlandi. ⚠️ ${saved.assignee_name} Telegram botga ulanmagan — unga xabar bormaydi`, 'warn');
          else A.toast('Saqlandi');
        } else {
          const ids = x.assignees || [];
          if (!ids.length) return 'Kamida bitta bajaruvchini tanlang';
          const unlinked = [];
          let done = 0;
          try {
            for (const id of ids) {
              const saved = await A.http.post('/tasks/', { ...body, assignee: id });
              done++;
              if (saved.assignee_linked === false && saved.assignee !== A.S.currentUser) unlinked.push(saved.assignee_name);
            }
          } catch (e) {
            if (done) { await reload(); throw new Error(`${done} ta topshiriq berildi, keyingisida xato: ${e.message}`); }
            throw e;
          }
          const n = ids.length > 1 ? `${ids.length} ta bajaruvchiga topshiriq berildi` : 'Topshiriq berildi — sizga va bajaruvchiga Telegram orqali xabar boradi';
          if (unlinked.length) A.toast(`${n}. ⚠️ Botga ulanmagan: ${unlinked.join(', ')} — ularga xabar bormaydi`, 'warn');
          else A.toast(n);
        }
        await reload();
      },
    });
  }
  A.act['task-new'] = () => taskForm(null);
  A.act['task-edit'] = (el) => taskForm(find(el.dataset.id));

  A.act['task-done'] = (el) => {
    const t = find(el.dataset.id);
    A.form({
      title: `Bajarildi: ${t ? t.title : ''}`,
      fields: [{ name: 'comment', label: 'Natija haqida izoh (ixtiyoriy)', type: 'textarea' }],
      submit: '✅ Bajarildi',
      async onSubmit(x) {
        await A.http.post(`/tasks/${el.dataset.id}/done/`, { comment: x.comment || '' });
        A.toast('Bajarildi — eslatmalar to‘xtadi, beruvchiga xabar boradi');
        await reload();
      },
    });
  };
  A.act['task-cancel'] = (el) => {
    A.form({
      title: 'Topshiriqni bekor qilish',
      fields: [{ name: 'reason', label: 'Sabab (ixtiyoriy)', type: 'textarea' }],
      submit: 'Bekor qilish',
      async onSubmit(x) {
        await A.http.post(`/tasks/${el.dataset.id}/cancel/`, { reason: x.reason || '' });
        A.toast('Bekor qilindi');
        await reload();
      },
    });
  };
  A.act['task-extend'] = (el) => {
    const t = find(el.dataset.id);
    const base = new Date(Math.max(new Date(t.due_at), new Date()));
    const plus = (h) => localInput(new Date(base.getTime() + h * 3600e3));
    A.form({
      title: 'Muddatni uzaytirish',
      values: { quick: '24', due: plus(24) },
      intro: `<p class="muted small">Hozirgi muddat: ${fdt(t.due_at)}. Eslatmalar yangi muddat bo'yicha qaytadan boshlanadi, bajaruvchiga xabar boradi.</p>`,
      fields: [
        { name: 'quick', label: 'Qanchaga uzaytirilsin', type: 'seg', required: true, options: () => [['3', '+3 soat'], ['24', '+1 kun'], ['72', '+3 kun'], ['168', '+1 hafta'], ['custom', 'Boshqa sana']] },
        { name: 'new', label: 'Yangi muddat', type: 'computed', show: (x) => x.quick && x.quick !== 'custom', compute: (x) => fdt(plus(Number(x.quick))) },
        { name: 'due', label: 'Yangi muddat (sana va soat)', type: 'datetime-local', required: true, show: (x) => x.quick === 'custom' },
      ],
      async onSubmit(x) {
        const due = x.quick === 'custom' ? x.due : plus(Number(x.quick));
        await A.http.patch(`/tasks/${t.id}/`, { due_at: new Date(due).toISOString() });
        A.toast('Muddat uzaytirildi');
        await reload();
      },
    });
  };
})(window.App);

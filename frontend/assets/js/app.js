/* Layout, menyu, marshrutlash va umumiy UI bo'laklari */
(function (A) {
  const esc = A.esc;

  /* ================= Ikonkalar ================= */
  const ICONS = {
    home: 'M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',
    leads: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
    file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h8',
    cash: 'M2 6h20v12H2zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M6 12h.01M18 12h.01',
    alert: 'M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
    check: 'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11',
    star: 'M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z',
    trend: 'M23 6l-9.5 9.5-5-5L1 18M17 6h6v6',
    receipt: 'M4 2v20l3-2 3 2 3-2 3 2 3-2 3 2V2l-3 2-3-2-3 2-3-2-3 2zM8 8h8M8 12h8',
    download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
    pie: 'M21.2 15.9A10 10 0 1 1 8 2.8M22 12A10 10 0 0 0 12 2v10z',
    grid: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
    percent: 'M19 5L5 19M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5',
    shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4',
    wallet: 'M20 12V8H6a2 2 0 0 1 0-4h12v4M4 6v12a2 2 0 0 0 2 2h14v-4M18 12a2 2 0 0 0 0 4h4v-4z',
    repeat: 'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3',
    bank: 'M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3',
    swap: 'M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5',
    safe: 'M3 4h18v16H3zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M7 20v2M17 20v2',
    thumbs: 'M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.3a2 2 0 0 0 2-1.7l1.4-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3',
    tasks: 'M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M9 2h6v4H9zM9 13l2 2 4-4',
    phone: 'M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z',
    sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
    sparkle: 'M12 3l1.9 5.6 5.6 1.9-5.6 1.9L12 18l-1.9-5.6-5.6-1.9 5.6-1.9zM19 3v4M17 5h4',
    history: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l4 2',
    menu: 'M3 6h18M3 12h18M3 18h18',
    bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0',
    calendar: 'M3 4h18v18H3zM16 2v4M8 2v4M3 10h18',
    plus: 'M12 5v14M5 12h14',
    logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  };
  A.icon = (name, cls = '') => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[name] || ICONS.grid}"/></svg>`;

  /* ================= Menyu (AppSheet tartibida) ================= */
  A.NAV = [
    ['dashboard', 'Bosh sahifa', 'home'], ['leads', 'Lidlar', 'leads'], ['contracts', 'Shartnomalar', 'file'],
    ['payments', "To'lovlar", 'cash'], ['debtors', 'Qarzdorlar', 'alert'], ['attendance', 'Davomatlar', 'check'],
    ['profit', 'Foyda (oyma-oy)', 'trend'], ['expenses', 'Xarajatlar', 'receipt'],
    ['export', 'Shartnoma yuklash', 'download'], ['groupAnalysis', 'Guruhlar tahlili', 'pie'], ['groups', 'Guruhlar', 'grid'],
    ['approvals', 'Tasdiqlashlar', 'shield'], ['salaries', 'Oyliklar', 'wallet'],
    ['transfers', 'Ichki pul oqimi', 'repeat'], ['creditors', 'Tashqi pul oqimi', 'bank'], ['exchange', 'Pul ayirboshlash', 'swap'],
    ['accounts', "G'aznalar", 'safe'], ['evaluations', 'Baholash (ustozni)', 'thumbs'],
    ['parentCalls', 'Ota-onalar bilan aloqa', 'phone'], ['settings', 'Sozlamalar', 'sliders'], ['ai', 'AI yordamchi', 'sparkle'],
    ['audit', 'Audit tarixi', 'history'],
  ];

  /* ================= Umumiy UI bo'laklari ================= */
  A.ui = { q: {} };
  A.q = (key, def) => (A.ui.q[key] === undefined ? def : A.ui.q[key]);

  A.head = (title, sub, actions = '') =>
    `<div class="page-head"><div><h1>${esc(title)}</h1>${sub ? `<p class="sub">${sub}</p>` : ''}</div><div class="actions">${actions}</div></div>`;
  A.btn = (label, act, opts = {}) =>
    `<button class="btn ${opts.cls || 'primary'}" data-act="${act}" ${opts.id ? `data-id="${esc(opts.id)}"` : ''} ${opts.disabled ? `disabled title="${esc(opts.title || '')}"` : ''} ${opts.extra || ''}>${opts.icon ? A.icon(opts.icon) : ''}${esc(label)}</button>`;
  A.badge = (t, tone = 'gray') => `<span class="badge ${tone}">${esc(t)}</span>`;
  A.stat = (label, value, sub = '', tone = '', href = '') =>
    `<${href ? `a href="${href}"` : 'div'} class="stat ${tone}"><div class="stat-label">${esc(label)}</div><div class="stat-value">${value}</div>${sub ? `<div class="stat-sub">${sub}</div>` : ''}</${href ? 'a' : 'div'}>`;
  A.empty = (msg) => `<div class="empty">${esc(msg)}</div>`;
  A.tabs = (items, active, base) =>
    `<nav class="tabs">${items
      .map(([k, l, n]) => `<a href="#/${base}?tab=${k}" class="${k === active ? 'on' : ''}">${esc(l)}${n !== undefined ? ` <span class="cnt">${n}</span>` : ''}</a>`)
      .join('')}</nav>`;
  /** cols: [{h, f(row), cls, sum}] */
  A.table = (cols, rows, opts = {}) => {
    if (!rows.length) return A.empty(opts.empty || "Ma'lumot yo'q");
    const foot = cols.some((c) => c.sum)
      ? `<tfoot><tr>${cols.map((c, i) => `<td class="${c.cls || ''}">${c.sum ? `<b>${c.sum(rows)}</b>` : i === 0 ? '<b>Jami</b>' : ''}</td>`).join('')}</tr></tfoot>`
      : '';
    return `<div class="tbl-wrap"><table class="tbl ${opts.cls || ''}">
      <thead><tr>${cols.map((c) => `<th class="${c.cls || ''}">${esc(c.h)}</th>`).join('')}</tr></thead>
      <tbody>${rows
        .map((r) => `<tr ${opts.rowAttr ? opts.rowAttr(r) : ''}>${cols.map((c) => `<td class="${c.cls || ''}" data-label="${esc(c.h)}">${c.f(r) ?? ''}</td>`).join('')}</tr>`)
        .join('')}</tbody>${foot}</table></div>`;
  };
  A.filterBar = (key, controls) => `<div class="filters" data-fkey="${key}">${controls.join('')}</div>`;
  A.fSearch = (key, ph = 'Qidirish…') => `<input class="f-input" type="search" data-filter="${key}:search" placeholder="${esc(ph)}" value="${esc(A.q(key + ':search', ''))}">`;
  A.fSelect = (key, name, opts, all = 'Hammasi') =>
    `<select class="f-input" data-filter="${key}:${name}"><option value="">${esc(all)}</option>${opts
      .map(([k, l]) => `<option value="${esc(k)}" ${String(A.q(key + ':' + name, '')) === String(k) ? 'selected' : ''}>${esc(l)}</option>`)
      .join('')}</select>`;
  /* ---- Daraxt filtri (AppSheet guruhlash kabi): "Barchasi" va darajalar, har tugunda son yoki summa.
     opts.levels: [{ key: (r) => qiymat, label: (k) => matn, sort?: (k) => tartib, desc?, hideSingle? }]
     hideSingle: daraja bitta qiymatli bo'lsa ko'rsatilmaydi (masalan filial bitta bo'lsa).
     Standart: filial → kurs → guruh, son bilan. ---- */
  A.TREE_BCG = [
    { key: (r) => r.branch, label: (k) => A.branchName(k), hideSingle: true },
    { key: (r) => r.course, label: (k) => A.courseName(k) },
    { key: (r) => r.group, label: (k) => A.groupName(k), sort: (k) => (A.get('groups', k) || {}).number || 0 },
  ];
  const treeSel = (key, opts) => A.q(key + ':tree', opts.def || '');
  A.treeNav = (key, rows, opts = {}) => {
    const levels = opts.levels || A.TREE_BCG, value = opts.value || ((rs) => rs.length);
    const sel = treeSel(key, opts), parts = sel ? sel.split('|') : [];
    const node = (path, label, v, depth, open) =>
      `<a class="tree-n${sel === path ? ' on' : ''}" style="padding-left:${10 + depth * 16}px" data-act="tree" data-id="${esc(key)}~${esc(path)}">` +
      `<span class="tree-tw">${open === null ? '' : open ? '▾' : '▸'}</span><span class="tree-l">${label}</span><span class="tree-c">${v}</span></a>`;
    let html = node('', 'Barchasi', value(rows), 0, null);
    const walk = (rs, li, prefix, depth) => {
      if (li >= levels.length) return;
      const L = levels[li];
      const groups = A.sortBy([...A.groupBy(rs, (r) => String(L.key(r)))], ([k]) => (L.sort ? L.sort(k) : L.label(k)), L.desc);
      if (L.hideSingle && groups.length === 1) return walk(rs, li + 1, [...prefix, groups[0][0]], depth);
      for (const [k, l] of groups) {
        const path = [...prefix, k], leaf = li === levels.length - 1;
        const open = !leaf && path.every((p, i) => parts[i] === p);
        html += node(path.join('|'), esc(L.label(k)), value(l), depth, leaf ? null : open);
        if (open) walk(l, li + 1, path, depth + 1);
      }
    };
    walk(rows, 0, [], 1);
    return `<nav class="side-tabs tree">${html}</nav>`;
  };
  /** Daraxtda tanlangan tugun bo'yicha filtrlangan qatorlar */
  A.treeFilter = (key, rows, opts = {}) => {
    const levels = opts.levels || A.TREE_BCG, sel = treeSel(key, opts), parts = sel ? sel.split('|') : [];
    return rows.filter((r) => parts.every((p, i) => String(levels[i].key(r)) === p));
  };
  /** Tanlangan tugun chuqurligi (0 = Barchasi) */
  A.treeDepth = (key, opts = {}) => { const sel = treeSel(key, opts); return sel ? sel.split('|').length : 0; };
  A.match = (text, q) => !q || String(text).toLowerCase().includes(q.toLowerCase());
  A.contractStatusBadge = (s) => A.badge(s, s === 'Faol' ? 'green' : s === 'Nofaol' ? 'red' : 'blue');
  A.attBadge = (s) => `<span class="att att-${s === '-' ? 'n' : s}">${s === '-' ? '–' : s}</span>`;
  A.moneyCell = (n, colored) => `<span class="money ${colored ? (n > 0 ? 'neg' : n < 0 ? 'pos' : '') : ''}">${A.num(n)}</span>`;
  A.monthOptions = () => {
    const out = [];
    for (let ym = '2026-09'; ym <= A.ym(A.today()); ym = A.addMonths(ym, 1)) out.push([ym, A.ymLabel(ym)]);
    return out.reverse();
  };
  A.optList = (coll, label = 'name', pred) => A.rows(coll).filter(pred || (() => true)).map((x) => [x.id, typeof label === 'function' ? label(x) : x[label]]);

  /* ---- Chart.js ---- */
  const charts = [];
  const pending = [];
  A.chart = (config, h = 240) => {
    const id = 'ch' + A.uid();
    pending.push([id, config]);
    return `<div class="chart-box" style="height:${h}px"><canvas id="${id}"></canvas></div>`;
  };
  const drawCharts = () => {
    while (charts.length) charts.pop().destroy();
    if (!window.Chart) {
      pending.splice(0).forEach(([id]) => {
        const c = document.getElementById(id);
        if (c) c.parentElement.innerHTML = '<div class="empty">Diagramma uchun internet kerak (Chart.js CDN)</div>';
      });
      return;
    }
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = '#6b6b70';
    for (const [id, cfg] of pending.splice(0)) {
      const el = document.getElementById(id);
      if (!el) continue;
      cfg.options = Object.assign({ responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } }, cfg.options || {});
      charts.push(new Chart(el, cfg));
    }
  };
  A.PALETTE = ['#F26A1B', '#1f1f23', '#2f80ed', '#27ae60', '#9b51e0', '#f2c94c', '#eb5757', '#56ccf2'];

  /* ================= Marshrutlash ================= */
  A.pages = {};
  A.page = (route, def) => (A.pages[route] = def);

  /** API'ga ulangan bo'limlar. Qolganlari o'z bosqichida ulanadi (docs/architecture.md, 5-bo'lim) */
  A.CONNECTED = new Set(['dashboard', 'settings', 'audit', 'leads', 'contracts', 'debtors', 'attendance', 'groups', 'groupAnalysis',
    'payments', 'approvals', 'accounts', 'transfers', 'creditors', 'exchange', 'expenses', 'salaries',
    'evaluations', 'parentCalls', 'export', 'profit']);
  A.MILESTONE = { ai: 'M9' };
  const PUBLIC = new Set(['set-password']);

  const parseHash = () => {
    const h = location.hash.replace(/^#\/?/, '') || 'dashboard';
    const [path, qs] = h.split('?');
    const query = Object.fromEntries(new URLSearchParams(qs || ''));
    const parts = path.split('/').filter(Boolean);
    for (const route of Object.keys(A.pages)) {
      const rp = route.split('/');
      if (rp.length !== parts.length) continue;
      const params = {};
      if (rp.every((seg, i) => (seg.startsWith(':') ? ((params[seg.slice(1)] = decodeURIComponent(parts[i])), true) : seg === parts[i]))) {
        return { route, params, query };
      }
    }
    return { route: parts[0] || null, params: {}, query };
  };
  A.go = (path) => {
    if (location.hash === '#/' + path) A.render();
    else location.hash = '#/' + path;
  };
  A.current = null;

  let renderSeq = 0;
  A.render = async () => {
    const seq = ++renderSeq;
    const app = document.getElementById('app');
    const { route, params, query } = parseHash();
    if (PUBLIC.has(route)) {
      app.innerHTML = setPasswordHTML(query);
      mountSetPassword(query);
      return;
    }
    if (!A.me()) {
      app.innerHTML = loginHTML();
      mountLogin();
      return;
    }
    if (!app.querySelector('.layout')) app.innerHTML = layoutHTML();
    const page = A.pages[route];
    const view = document.getElementById('view');
    A.current = { route, params, query, page };
    let html;
    let ok = false;
    updateChrome(page);
    if (!page) html = A.head('Sahifa topilmadi') + A.empty("Bunday sahifa yo'q");
    else if (page.section && !A.can(page.section)) {
      html = A.head("Ruxsat yo'q") + `<div class="empty">Bu bo'lim <b>${esc(A.ROLES[A.role()])}</b> roli uchun yopiq.</div>`;
    } else if (page.section && !A.CONNECTED.has(page.section)) {
      html = A.head(page.title || '') + `<div class="empty">${A.icon('history')}<p><b>Bu bo'lim ${A.MILESTONE[page.section] || 'keyingi'} bosqichida serverga ulanadi.</b></p>
        <p class="muted">Ekranlar ma'qullangan prototipdagidek bo'ladi. Hozircha Sozlamalar, Lidlar, Shartnomalar, Qarzdorlar, Davomat, Guruhlar, moliya, Oyliklar, Baholash (ustozni), Ota-onalar bilan aloqa, Shartnoma yuklash va Audit tarixi ishlaydi.</p></div>`;
    } else {
      try {
        if (page.load) {
          if (!A._keepScroll) view.innerHTML = '<div class="empty">Yuklanmoqda…</div>';
          await page.load(params, query);
          if (seq !== renderSeq) return; // bu orada boshqa sahifa ochildi
        }
        html = page.render(params, query);
        ok = true;
      } catch (e) {
        if (seq !== renderSeq) return;
        if (!(e instanceof A.ApiError)) console.error(e);
        html = A.head('Xatolik') + `<div class="empty">${esc(e.message)}</div>`;
      }
    }
    // Qidiruv/filtr maydoniga yozilayotgan bo'lsa — qayta chizilgandan keyin kursor o'sha joyida qolsin
    const act = document.activeElement;
    const focusKey = act && act.dataset && act.dataset.filter;
    const caret = focusKey && typeof act.selectionStart === 'number' ? act.selectionStart : null;
    view.innerHTML = html;
    if (focusKey) {
      const el = view.querySelector(`[data-filter="${CSS.escape(focusKey)}"]`);
      if (el) {
        el.focus();
        if (caret !== null && el.setSelectionRange) el.setSelectionRange(caret, caret);
      }
    }
    if (ok && page.mount) {
      try {
        page.mount(params, query);
      } catch (e) {
        console.error(e);
      }
    }
    drawCharts();
    if (!A._keepScroll) window.scrollTo(0, 0);
    A._keepScroll = false;
  };
  /** Joriy sahifani qayta chizish (scroll saqlanadi) */
  A.refresh = () => {
    A._keepScroll = true;
    return A.render();
  };

  /* ================= Layout ================= */
  function navHTML() {
    const pc = A.pendingCount();
    return A.NAV.filter(([sec]) => A.can(sec))
      .map(([sec, label, icon]) => `<a href="#/${sec}" data-nav="${sec}" class="${A.CONNECTED.has(sec) ? '' : 'soon'}">${A.icon(icon)}<span>${esc(label)}</span>${sec === 'approvals' && pc ? `<em class="dot">${pc}</em>` : ''}</a>`)
      .join('');
  }
  function bottomHTML() {
    const pref = ['dashboard', 'leads', 'contracts', 'payments', 'debtors', 'attendance', 'salaries', 'settings'];
    const items = pref.filter((s) => A.can(s)).slice(0, 4);
    return items
      .map((s) => {
        const n = A.NAV.find((x) => x[0] === s);
        return `<a href="#/${s}" data-nav="${s}">${A.icon(n[2])}<span>${esc(n[1].split(' ')[0])}</span></a>`;
      })
      .join('') + `<button data-act="drawer">${A.icon('menu')}<span>Menyu</span></button>`;
  }
  const isTest = () => /^(test\.|localhost|127\.)/.test(location.hostname);
  function branchLabel() {
    const mine = A.S.branches.filter((b) => A.branchIds().includes(b.id) && b.status === 'Faol');
    return mine.length === 1 ? mine[0].name : `${mine.length} ta filial`;
  }
  function layoutHTML() {
    return `<div class="layout">
      <aside class="sidebar" id="sidebar">
        <div class="brand"><span class="logo">codial<i>.</i></span><span class="brand-sub">ERP${isTest() ? ' · test' : ''}</span></div>
        <div class="branch-pill">${A.icon('home')} Filial: <b id="branch-label"></b></div>
        <nav class="nav" id="nav"></nav>
        <div class="side-foot">${isTest() ? 'Test serveri: sinov ma\'lumotlari' : 'Codial ERP'}</div>
      </aside>
      <div class="scrim" data-act="drawer-close"></div>
      <div class="main">
        <header class="topbar">
          <button class="icon-btn only-mobile" data-act="drawer" aria-label="Menyu">${A.icon('menu')}</button>
          <div class="top-title" id="top-title"></div>
          <span class="date-pill">${A.icon('calendar')}<span id="top-date"></span></span>
          <a class="icon-btn bell" href="#/approvals" id="top-bell" title="Tasdiqlashlar">${A.icon('bell')}<em class="dot" id="bell-dot" hidden></em></a>
          <button class="user-chip" data-act="account" id="user-chip"></button>
        </header>
        <main id="view" class="view"></main>
      </div>
      <nav class="bottomnav" id="bottomnav"></nav>
    </div>`;
  }
  function updateChrome(page) {
    const me = A.me();
    document.getElementById('nav').innerHTML = navHTML();
    document.getElementById('bottomnav').innerHTML = bottomHTML();
    document.getElementById('branch-label').textContent = branchLabel();
    const sec = page && page.section;
    document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('on', a.dataset.nav === sec));
    document.getElementById('top-title').textContent = page ? page.title || '' : '';
    const t = A.today();
    document.getElementById('top-date').textContent = `${A.WD[A.isoWeekday(t)]}, ${A.fdate(t)}`;
    document.getElementById('user-chip').innerHTML = `<span class="avatar">${A.initials(me.full_name)}</span><span class="uc-text"><b>${esc(me.full_name)}</b><small>${esc(A.ROLES[me.role])}</small></span>`;
    const pc = A.pendingCount();
    const dot = document.getElementById('bell-dot');
    dot.hidden = !pc;
    dot.textContent = pc;
    document.getElementById('top-bell').style.display = A.can('approvals') ? '' : 'none';
    document.body.classList.remove('drawer-open');
  }

  /* ================= Kirish (login) va parol ================= */
  function loginHTML() {
    return `<div class="login">
      <div class="login-card narrow">
        <div class="brand big"><span class="logo">codial<i>.</i></span><span class="brand-sub">ERP tizimi${isTest() ? ' · test serveri' : ''}</span></div>
        <form class="login-form" id="login-form" novalidate>
          <label class="lbl" for="lg-email">Pochta</label><input id="lg-email" type="email" autocomplete="username" placeholder="ism@codial.uz" required>
          <label class="lbl" for="lg-pass">Parol</label><input id="lg-pass" type="password" autocomplete="current-password" placeholder="••••••••" required>
          <div class="form-error" id="lg-err" hidden></div>
          <button class="btn primary block" id="lg-btn">Kirish</button>
          <button type="button" class="link-btn" id="lg-forgot">Parolni unutdingizmi?</button>
        </form>
      </div></div>`;
  }
  function mountLogin() {
    const f = document.getElementById('login-form');
    const err = document.getElementById('lg-err');
    const email = document.getElementById('lg-email');
    if (window.innerWidth > 700) email.focus();
    f.onsubmit = async (e) => {
      e.preventDefault();
      const btn = document.getElementById('lg-btn');
      err.hidden = true;
      btn.disabled = true;
      try {
        await A.http.csrf();
        await A.http.post('/auth/login/', { email: email.value.trim(), password: document.getElementById('lg-pass').value });
        await A.boot();
        if (!location.hash || location.hash === '#/' || location.hash.startsWith('#/set-password')) location.hash = '#/dashboard';
        A.render();
      } catch (ex) {
        err.textContent = ex.message;
        err.hidden = false;
        btn.disabled = false;
      }
    };
    document.getElementById('lg-forgot').onclick = () =>
      A.form({
        title: 'Parolni tiklash',
        intro: '<p class="muted">Pochtangizni yozing — unga parol o\'rnatish havolasi yuboriladi.</p>',
        values: { email: email.value.trim() },
        submit: 'Havola yuborish',
        fields: [{ name: 'email', label: 'Pochta', type: 'email', required: true }],
        async onSubmit(x) {
          await A.http.csrf();
          const r = await A.http.post('/auth/password/reset/', { email: x.email });
          A.toast(r.detail);
        },
      });
  }
  function setPasswordHTML() {
    return `<div class="login">
      <div class="login-card narrow">
        <div class="brand big"><span class="logo">codial<i>.</i></span><span class="brand-sub">Parol o'rnatish</span></div>
        <form class="login-form" id="sp-form" novalidate>
          <label class="lbl" for="sp-p1">Yangi parol</label><input id="sp-p1" type="password" autocomplete="new-password" required>
          <div class="help">Kamida 4 belgi.</div>
          <label class="lbl" for="sp-p2">Parolni takrorlang</label><input id="sp-p2" type="password" autocomplete="new-password" required>
          <div class="form-error" id="sp-err" hidden></div>
          <button class="btn primary block" id="sp-btn">Parolni saqlash</button>
          <a class="link-btn" href="#/dashboard">Kirish sahifasiga</a>
        </form>
      </div></div>`;
  }
  function mountSetPassword(q) {
    const f = document.getElementById('sp-form');
    const err = document.getElementById('sp-err');
    f.onsubmit = async (e) => {
      e.preventDefault();
      const p1 = document.getElementById('sp-p1').value, p2 = document.getElementById('sp-p2').value;
      err.hidden = true;
      if (p1 !== p2) {
        err.textContent = 'Parollar bir xil emas';
        err.hidden = false;
        return;
      }
      const btn = document.getElementById('sp-btn');
      btn.disabled = true;
      try {
        await A.http.csrf();
        const r = await A.http.post('/auth/password/set/', { uid: q.uid || '', token: q.token || '', password: p1 });
        A.toast(r.detail);
        A.S = A.emptyStore();
        location.hash = '#/dashboard';
      } catch (ex) {
        err.textContent = ex.message;
        err.hidden = false;
        btn.disabled = false;
      }
    };
  }

  /* ================= Global hodisalar ================= */
  A.act = {};
  A.act.tree = (el) => {
    const [key, path] = el.dataset.id.split('~');
    A.ui.q[key + ':tree'] = path;
    A.refresh();
  };
  A.act.drawer = () => document.body.classList.toggle('drawer-open');
  A.act['drawer-close'] = () => document.body.classList.remove('drawer-open');
  A.act.account = () => {
    const me = A.me();
    const m = A.modal({
      title: me.full_name,
      body: `<dl class="kv"><dt>Lavozim</dt><dd>${esc(A.ROLES[me.role])}</dd><dt>Pochta</dt><dd>${esc(me.email || '—')}</dd>
        <dt>Filial</dt><dd>${esc(branchLabel())}</dd></dl>
        <p class="muted small">Parolni o'zgartirish uchun «Chiqish»dan keyin kirish sahifasidagi «Parolni unutdingizmi?» havolasidan foydalaning.</p>`,
      footer: `<button class="btn ghost" data-logout>${A.icon('logout')} Chiqish</button>`,
    });
    m.el.querySelector('[data-logout]').onclick = async () => {
      try {
        await A.http.post('/auth/logout/');
      } finally {
        m.close();
        A.S = A.emptyStore();
        A.render();
      }
    };
  };
  /** Sessiya tugasa (401) — kirish sahifasiga */
  A.onSessionLost = () => {
    if (!A.S.me) return;
    A.S = A.emptyStore();
    A.toast('Sessiya tugadi. Qaytadan kiring', 'warn');
    A.render();
  };

  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    if (!el || el.disabled) return;
    const fn = A.act[el.dataset.act];
    if (fn) {
      e.preventDefault();
      Promise.resolve(fn(el, e)).catch((err) => {
        if (!(err instanceof A.ApiError)) console.error(err);
        A.toast(err.message || 'Xatolik yuz berdi', 'warn');
      });
    }
  });
  let filterTimer;
  const onFilter = (e) => {
    const el = e.target.closest('[data-filter]');
    if (!el) return;
    A.ui.q[el.dataset.filter] = el.value;
    clearTimeout(filterTimer);
    const p = A.current && A.current.page;
    const typing = e.type === 'input' && el.type === 'search';
    filterTimer = setTimeout(() => {
      const box = document.querySelector('[data-results]');
      if (p && p.results && !p.load && box) {
        box.innerHTML = p.results(A.current.params, A.current.query);
        drawCharts();
      } else A.refresh();
    }, typing ? (p && p.load ? 350 : 150) : 0);
  };
  document.addEventListener('input', onFilter);
  window.addEventListener('hashchange', () => A.render());

  window.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('app').innerHTML = '<div class="login"><div class="muted">Yuklanmoqda…</div></div>';
    try {
      await A.http.csrf();
      await A.boot();
    } catch (e) {
      A.S = A.emptyStore();
      if (e.status !== 401) A.toast(e.message, 'warn');
    }
    A.render();
  });
})(window.App);

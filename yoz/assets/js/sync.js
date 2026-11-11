/* Codial Yoz ↔ Codial darslik: o'quvchini kod bilan ulash va mashq natijalarini ERP'ga yuborish (2026-11-08).
   Ulanmagan bo'lsa Yoz avvalgidek mustaqil ishlaydi (natija faqat brauzerda). Kod darslik ilovasidan olinadi: «Klaviatura trenajori». */
(function (Y) {
  'use strict';

  const API = ((Y.config && Y.config.api) || 'https://erp.codialinfo.uz') + '/api/v1/learn/yoz';
  const LINK = 'codial-yoz-link';
  const QUEUE = 'codial-yoz-queue';
  const read = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k) || 'null'); return v === null ? d : v; } catch (e) { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* xotira yopiq */ } };
  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  const $ = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => { if (k === 'class') n.className = v; else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v); });
    kids.flat().forEach((c) => n.append(c && c.nodeType ? c : document.createTextNode(c === undefined || c === null ? '' : String(c))));
    return n;
  };

  let summary = null;
  let flushing = false;

  async function call(path, opts) {
    const link = read(LINK, null);
    const headers = { 'Content-Type': 'application/json', ...(link ? { 'X-Yoz-Token': link.token } : {}) };
    const r = await fetch(API + path, { ...opts, headers });
    let data = {};
    try { data = await r.json(); } catch (e) { /* bo'sh */ }
    if (!r.ok) { const err = new Error(data.detail || 'Xatolik'); err.status = r.status; throw err; }
    return data;
  }

  function toast(msg) {
    const t = $('div', { class: 'toast' }, msg);
    document.body.append(t);
    setTimeout(() => t.classList.add('out'), 3200);
    setTimeout(() => t.remove(), 3700);
  }

  // Ulangan o'quvchining profilini tanlaydi (yo'q bo'lsa yaratadi): natija shu profilga yoziladi.
  function useProfile(name) {
    const store = Y.store;
    if (!store) return;
    const same = store.profiles().find((p) => p.name.toLowerCase() === name.toLowerCase());
    try { if (same) store.use(same.id); else store.create(name); } catch (e) { /* ism qisqa bo'lsa — mavjud profil qoladi */ }
  }

  function restore(progress) {
    const store = Y.store;
    if (store && store.current() && progress) store.merge(store.current(), progress);
  }

  function accept(r) {
    write(LINK, { token: r.token, name: r.name, full: r.full_name, at: Date.now() });
    summary = r.summary;
    useProfile(r.name);
    restore(r.progress);  // qayerga yetgan bo'lsa — shu yerdan davom etadi
    paint();
    return r;
  }

  async function connect(code) { return accept(await call('/exchange/', { method: 'POST', body: JSON.stringify({ code }) })); }
  async function login(number, password) { return accept(await call('/login/', { method: 'POST', body: JSON.stringify({ number, password }) })); }

  // Chiqish: ulanish va navbat o'chadi; umumiy kompyuterda keyingi o'quvchi oldingisining profilida qolmasin.
  function unlink() {
    localStorage.removeItem(LINK); localStorage.removeItem(QUEUE); summary = null;
    if (Y.store) Y.store.logout();
    paint();
  }

  async function flush() {
    const link = read(LINK, null);
    const q = read(QUEUE, []);
    if (!link || !q.length || flushing) return;
    flushing = true;
    try {
      const r = await call('/sessions/', { method: 'POST', body: JSON.stringify({ sessions: q.slice(0, 100) }) });
      write(QUEUE, read(QUEUE, []).filter((x) => !q.slice(0, 100).some((y) => y.id === x.id)));
      summary = r.summary;
      paint();
    } catch (e) {
      if (e.status === 401) { localStorage.removeItem(LINK); toast("Darslik bilan ulanish eskirdi. Ilovadan yangi kod oling."); paint(); }
      // tarmoq xatosi — navbat qoladi, keyingi mashqda qayta uriniladi
    } finally { flushing = false; }
  }

  function push(lessonId, res, stars) {
    if (!read(LINK, null) || !res || !(res.ms >= 1000)) return;
    const q = read(QUEUE, []);
    q.push({ id: uid(), at: Date.now(), ms: Math.round(res.ms), wpm: res.wpm, acc: res.acc, stars: stars || 0, l: String(lessonId || '') });
    write(QUEUE, q.slice(-300));
    flush();
  }

  // Natija yozilganda ERP'ga ham yuboramiz.
  function hook() {
    const store = Y.store;
    if (!store || store.__synced) return;
    const orig = store.record;
    store.record = function (p, lessonId, res, stars) {
      const out = orig.apply(this, arguments);
      try { push(lessonId, res, stars); } catch (e) { /* ERP xatosi mashqni buzmasin */ }
      return out;
    };
    store.__synced = true;
  }

  /* ---------- ko'rinish: pastdagi «🔗 Darslik» tugmasi va oyna ---------- */
  const css = $('style', {}, `
    .ys-pill{position:fixed;left:14px;bottom:14px;z-index:60;border:0;border-radius:999px;padding:9px 14px;font:600 13px/1 inherit;color:#fff;background:#0f1b3d;box-shadow:0 6px 18px rgba(15,27,61,.3);cursor:pointer}
    .ys-pill.on{background:#22b573}
    .ys-bg{position:fixed;inset:0;z-index:70;background:rgba(8,12,28,.55);display:grid;place-items:center;padding:16px}
    .ys-box{width:min(420px,100%);background:#fff;color:#14182b;border-radius:20px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.35);font:15px/1.45 system-ui,sans-serif}
    .ys-box h3{margin:0 0 6px;font-size:18px}.ys-box p{margin:4px 0;color:#6a7288;font-size:13.5px}
    .ys-box input{width:100%;margin:12px 0;padding:14px;border:2px solid #dfe3ef;border-radius:12px;font:700 24px/1 ui-monospace,Menlo,monospace;letter-spacing:.18em;text-align:center;text-transform:uppercase}
    .ys-box input.ys-in{font:600 16px/1.2 system-ui,sans-serif;letter-spacing:0;text-transform:none;text-align:left;padding:13px 14px;margin:6px 0}
    .ys-box input:focus{outline:0;border-color:#ff8a1f}
    .ys-btn{width:100%;border:0;border-radius:12px;padding:13px;font:700 15px/1 inherit;color:#fff;background:linear-gradient(135deg,#ff8a1f,#ff5e3a);cursor:pointer}
    .ys-btn.ghost{background:#eef0f7;color:#14182b;margin-top:8px}
    .ys-err{color:#ef4a5a;font-size:13px;font-weight:600;min-height:18px}
    .ys-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0;text-align:center}.ys-stats b{display:block;font-size:18px}.ys-stats span{font-size:11.5px;color:#6a7288}
  `);
  document.head.append(css);
  const pill = $('button', { class: 'ys-pill', onclick: () => open() });

  function paint() {
    const link = read(LINK, null);
    pill.className = 'ys-pill' + (link ? ' on' : '');
    pill.textContent = link ? '✅ ' + link.name + ' · chiqish' : '🔑 Kirish';
  }

  function open(mode) {
    const link = read(LINK, null);
    const bg = $('div', { class: 'ys-bg', onclick: (e) => { if (e.target === bg) bg.remove(); } });
    const box = $('div', { class: 'ys-box' });
    if (link) {
      const s = summary;
      box.append($('h3', {}, '✅ Darslik bilan ulangan'), $('p', {}, link.full || link.name),
        s ? $('div', { class: 'ys-stats' }, $('div', {}, $('b', {}, (s.today_min || 0) + ' daq'), $('span', {}, 'bugun')), $('div', {}, $('b', {}, '🔥 ' + (s.streak || 0)), $('span', {}, 'ketma-ket kun')), $('div', {}, $('b', {}, s.best_wpm || '—'), $('span', {}, "eng yaxshi tezlik"))) : '',
        $('p', {}, "Har mashq natijasi darslik ilovasiga va ustozingizga avtomatik yuboriladi."),
        $('button', { class: 'ys-btn ghost', onclick: () => bg.remove() }, 'Yopish'),
        $('button', { class: 'ys-btn ghost', onclick: () => { if (confirm("Chiqasizmi? Natijalaringiz saqlangan, qayta kirsangiz davom etadi.")) { unlink(); bg.remove(); location.hash = '#/'; location.reload(); } } }, 'Chiqish'));
    } else if (mode === 'code') {
      const inp = $('input', { maxlength: '6', placeholder: 'KOD', autocomplete: 'off', autocapitalize: 'characters' });
      const err = $('div', { class: 'ys-err' });
      const go = $('button', { class: 'ys-btn', onclick: async () => {
        err.textContent = '';
        go.disabled = true;
        try { const r = await connect(inp.value.trim()); bg.remove(); toast('✅ Ulandingiz, ' + r.name + '! Endi natijalaringiz saqlanadi.'); location.hash = '#/map'; } catch (e) { err.textContent = e.message; go.disabled = false; }
      } }, 'Ulash');
      inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') go.click(); });
      box.append($('h3', {}, '🔗 Kod bilan ulash'), $('p', {}, "Telegramdagi darslik ilovasini oching → «Klaviatura trenajori» → ko'rsatilgan 6 belgili kodni kiriting."), inp, err, go,
        $('button', { class: 'ys-btn ghost', onclick: () => { bg.remove(); open(); } }, 'Orqaga'));
      setTimeout(() => inp.focus(), 50);
    } else {
      const num = $('input', { class: 'ys-in', inputmode: 'numeric', placeholder: 'Shartnoma raqami', autocomplete: 'username', maxlength: '9' });
      const pw = $('input', { class: 'ys-in', inputmode: 'numeric', type: 'password', placeholder: 'Parol (telefon raqamining oxirgi 4 raqami)', autocomplete: 'current-password', maxlength: '4' });
      const err = $('div', { class: 'ys-err' });
      const go = $('button', { class: 'ys-btn', onclick: async () => {
        err.textContent = '';
        go.disabled = true;
        try { const r = await login(num.value.trim(), pw.value.trim()); bg.remove(); toast('✅ Xush kelibsiz, ' + r.name + '!'); location.hash = '#/map'; } catch (e) { err.textContent = e.message; go.disabled = false; }
      } }, 'Kirish');
      [num, pw].forEach((x) => x.addEventListener('keydown', (e) => { if (e.key === 'Enter') go.click(); }));
      box.append($('h3', {}, '🔑 Kirish'), $('p', {}, "Shartnoma raqamingiz va telefon raqamingizning (yoki ota-onangiz telefonining) oxirgi 4 raqamini kiriting. Qayerga yetgan bo'lsangiz, shu yerdan davom etasiz."),
        num, pw, err, go,
        $('button', { class: 'ys-btn ghost', onclick: () => { bg.remove(); open('code'); } }, 'Darslik ilovasidagi kod bilan ulash'),
        $('button', { class: 'ys-btn ghost', onclick: () => bg.remove() }, 'Keyinroq'));
      setTimeout(() => num.focus(), 50);
    }
    bg.append(box);
    document.body.append(bg);
  }

  async function boot() {
    hook();
    document.body.append(pill);
    paint();
    const url = new URL(location.href);
    const code = url.searchParams.get('code');
    if (code) {
      url.searchParams.delete('code');
      history.replaceState(null, '', url.pathname + (url.search || '') + url.hash);
      try { const r = await connect(code); toast('✅ Darslik bilan ulandingiz, ' + r.name + '!'); location.hash = '#/map'; } catch (e) { toast(e.message); open('code'); }
    } else if (read(LINK, null)) {
      flush();
      call('/sessions/', { method: 'GET' }).then((r) => { summary = r.summary; restore(r.progress); }).catch((e) => { if (e.status === 401) { localStorage.removeItem(LINK); paint(); } });
    }
  }

  Y.sync = { connect, login, unlink, flush, push, linked: () => read(LINK, null) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})(window.Y = window.Y || {});

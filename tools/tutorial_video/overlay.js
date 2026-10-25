/* Yo'riqnoma videosi uchun sahifa ustidagi qatlam: kursor, yoritish, izoh yozuvi, sarlavha kartochkasi,
   soxta ochiladigan ro'yxat va telefon raqamlarini yashirish. Playwright add_init_script orqali qo'shiladi. */
(() => {
  if (window.__tv) return;
  const ORANGE = '#F26A1B';
  const css = `
  #tv-root, #tv-root * { box-sizing: border-box; font-family: Inter, "Segoe UI", system-ui, sans-serif; }
  #tv-root { position: fixed; inset: 0; pointer-events: none; z-index: 2147483000; }
  #tv-cursor { position: fixed; left: 0; top: 0; width: 30px; height: 30px; transform: translate(-3px,-2px);
    transition: left .75s cubic-bezier(.45,.05,.25,1), top .75s cubic-bezier(.45,.05,.25,1); filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
  #tv-ripple { position: fixed; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%; border: 3px solid ${ORANGE}; opacity: 0; }
  #tv-ripple.go { animation: tvRipple .55s ease-out; }
  @keyframes tvRipple { 0% { transform: scale(.4); opacity: 1 } 100% { transform: scale(3.2); opacity: 0 } }
  #tv-hl { position: fixed; border-radius: 10px; border: 3px solid ${ORANGE}; opacity: 0;
    box-shadow: 0 0 0 4px rgba(242,106,27,.28), 0 0 0 9999px rgba(15,18,30,.42);
    transition: left .45s ease, top .45s ease, width .45s ease, height .45s ease, opacity .3s ease; }
  #tv-hl.on { opacity: 1; animation: tvPulse 1.4s ease-in-out infinite; }
  #tv-hl.soft { box-shadow: 0 0 0 4px rgba(242,106,27,.28); }
  @keyframes tvPulse { 0%,100% { border-color: ${ORANGE} } 50% { border-color: #ffb27a } }
  #tv-tip { position: fixed; max-width: 360px; background: ${ORANGE}; color: #fff; font-weight: 700; font-size: 17px; line-height: 1.3;
    padding: 9px 14px; border-radius: 10px; box-shadow: 0 6px 18px rgba(0,0,0,.25); opacity: 0; transition: opacity .3s ease; }
  #tv-tip.on { opacity: 1; }
  #tv-tip::after { content: ""; position: absolute; width: 14px; height: 14px; background: ${ORANGE}; transform: rotate(45deg); }
  #tv-tip.below::after { top: -6px; left: var(--ax, 24px); }
  #tv-tip.above::after { bottom: -6px; left: var(--ax, 24px); }
  #tv-tip.right::after { left: -6px; top: 14px; }
  #tv-tip.left::after { right: -6px; top: 14px; }
  #tv-cap { position: fixed; left: 50%; transform: translateX(-50%); bottom: 22px; max-width: 1100px; width: max-content;
    background: rgba(17,19,28,.88); color: #fff; font-size: 23px; line-height: 1.38; font-weight: 500; text-align: center;
    padding: 12px 26px; border-radius: 14px; border-bottom: 4px solid ${ORANGE}; opacity: 0; transition: opacity .25s ease, top .3s, bottom .3s; }
  #tv-cap.on { opacity: 1; }
  #tv-cap.top { bottom: auto; top: 18px; }
  #tv-badge { position: fixed; top: 14px; right: 18px; background: rgba(17,19,28,.85); color: #fff; font-size: 14px; font-weight: 600;
    padding: 6px 12px; border-radius: 20px; opacity: 0; transition: opacity .3s; }
  #tv-badge.on { opacity: .92; }
  #tv-badge b { color: ${ORANGE}; }
  #tv-card { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity .5s ease;
    background: radial-gradient(1200px 600px at 20% 10%, #2a2f45 0%, #151824 55%, #0e1019 100%); color: #fff; }
  #tv-card.on { opacity: 1; }
  #tv-card .in { width: 980px; }
  #tv-card .kick { color: ${ORANGE}; font-weight: 800; letter-spacing: 3px; text-transform: uppercase; font-size: 20px; }
  #tv-card h1 { font-size: 58px; line-height: 1.12; margin: 12px 0 18px; font-weight: 800; }
  #tv-card .sub { font-size: 24px; color: #c9cbd6; margin-bottom: 26px; }
  #tv-card ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 12px 30px; }
  #tv-card li { font-size: 22px; color: #e9eaf0; padding-left: 34px; position: relative; opacity: 0; transform: translateY(8px); transition: all .4s ease; }
  #tv-card li.on { opacity: 1; transform: none; }
  #tv-card li::before { content: "✓"; position: absolute; left: 0; top: -1px; color: ${ORANGE}; font-weight: 900; font-size: 24px; }
  #tv-card .logo { height: 54px; margin-bottom: 28px; background: #fff; padding: 8px 14px; border-radius: 12px; }
  #tv-card .bar { height: 5px; width: 160px; background: ${ORANGE}; border-radius: 3px; margin-top: 34px; }
  #tv-dd { position: fixed; background: #fff; border-radius: 10px; box-shadow: 0 12px 34px rgba(0,0,0,.28); border: 1px solid #ddd;
    padding: 6px; max-height: 360px; overflow: hidden; opacity: 0; transition: opacity .2s; font-size: 15px; color: #222; }
  #tv-dd.on { opacity: 1; }
  #tv-dd div { padding: 8px 12px; border-radius: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #tv-dd div.sel { background: ${ORANGE}; color: #fff; font-weight: 600; }
  #tv-dd div.cur { background: #fdeee4; }
  #tv-arrow { position: fixed; font-size: 46px; color: ${ORANGE}; opacity: 0; transition: opacity .3s; text-shadow: 0 2px 6px rgba(0,0,0,.3); }
  #tv-arrow.on { opacity: 1; animation: tvBob 1s ease-in-out infinite; }
  @keyframes tvBob { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-8px) } }
  #tv-key { position: fixed; left: 50%; top: 50%; transform: translate(-50%,-50%); background: rgba(17,19,28,.9); color: #fff; padding: 22px 34px;
    border-radius: 16px; font-size: 30px; font-weight: 700; opacity: 0; transition: opacity .3s; text-align: center; max-width: 900px; border-top: 5px solid ${ORANGE}; }
  #tv-key.on { opacity: 1; }
  #tv-key small { display: block; font-size: 20px; font-weight: 500; color: #c9cbd6; margin-top: 8px; }
  #tv-img { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(15,18,30,.55);
    opacity: 0; transition: opacity .35s; }
  #tv-img.on { opacity: 1; }
  #tv-img .box { background: #fff; border-radius: 12px; padding: 10px; box-shadow: 0 18px 50px rgba(0,0,0,.4); border-top: 5px solid ${ORANGE};
    transform: scale(.96); transition: transform .35s; }
  #tv-img.on .box { transform: none; }
  #tv-img img { display: block; max-height: 78vh; max-width: 70vw; }
  #tv-img .t { font-weight: 700; color: #222; font-size: 16px; padding: 4px 4px 10px; }
  `;
  const CURSOR = `<svg viewBox="0 0 24 24" width="30" height="30"><path d="M4 2 L4 19 L8.6 14.8 L11.6 21.6 L14.6 20.3 L11.7 13.6 L18 13.6 Z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>`;

  // ---- telefon raqamlarini yashirish (9 xonali raqamlar: 90 123 •• ••)
  const PHONE = /(^|[^\d])(\+?998[\s-]?)?(\d{2})[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})(?!\d)/g;
  const mask = (s) => s.replace(PHONE, (m, pre, cc, a, b) => `${pre}${cc || ''}${a} ${b} •• ••`); // bo'linmas bo'sh joy — bir qatorda tursin
  const maskNode = (n) => {
    if (n.nodeType === 3) {
      if (/\d{2}/.test(n.nodeValue)) { const t = mask(n.nodeValue); if (t !== n.nodeValue) n.nodeValue = t; }
      return;
    }
    if (n.nodeType !== 1 || n.id === 'tv-root' || n.closest && n.closest('#tv-root')) return;
    if (['SCRIPT', 'STYLE', 'TEXTAREA'].includes(n.tagName)) return;
    const w = document.createTreeWalker(n, NodeFilter.SHOW_TEXT);
    let x;
    while ((x = w.nextNode())) {
      const p = x.parentElement;
      if (p && (p.closest('#tv-root') || ['SCRIPT', 'STYLE', 'TEXTAREA'].includes(p.tagName))) continue;
      if (/\d{2}/.test(x.nodeValue)) { const t = mask(x.nodeValue); if (t !== x.nodeValue) x.nodeValue = t; }
    }
  };
  let maskOn = true;
  // Forma maydonidagi haqiqiy raqam (tizim to'ldirgan) — faqat ko'rinishda nuqtalar; video uchun yozilgan soxta raqam (data-tv-typed) ochiq
  const maskInputs = () => {
    document.querySelectorAll('input:not([type=checkbox]):not([type=radio])').forEach((el) => {
      const hide = maskOn && !el.dataset.tvTyped && /^\+?\d{9,12}$/.test(el.value.replace(/[\s-]/g, ''));
      el.style.webkitTextSecurity = hide ? 'disc' : '';
    });
  };
  setInterval(maskInputs, 150);
  const startMask = () => {
    maskNode(document.body);
    new MutationObserver((ms) => {
      if (!maskOn) return;
      for (const m of ms) {
        if (m.type === 'characterData') maskNode(m.target);
        else m.addedNodes.forEach(maskNode);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };

  const mount = () => {
    const st = document.createElement('style');
    st.textContent = css;
    document.head.appendChild(st);
    const root = document.createElement('div');
    root.id = 'tv-root';
    root.innerHTML = `<div id="tv-hl"></div><div id="tv-tip"></div><div id="tv-dd"></div><div id="tv-arrow">⬇</div>
      <div id="tv-key"></div><div id="tv-img"></div><div id="tv-card"></div><div id="tv-cap"></div><div id="tv-badge"></div>
      <div id="tv-ripple"></div><div id="tv-cursor">${CURSOR}</div>`;
    document.body.appendChild(root);
    const c = root.querySelector('#tv-cursor');
    const pos = (window.__tvPos = window.__tvPos || { x: innerWidth * 0.62, y: innerHeight * 0.55 });
    c.style.transition = 'none';
    c.style.left = pos.x + 'px';
    c.style.top = pos.y + 'px';
    requestAnimationFrame(() => (c.style.transition = ''));
    startMask();
  };
  const $ = (id) => document.getElementById(id);

  const tv = (window.__tv = {
    ready: () => !!$('tv-root'),
    rect(sel) {
      const el = typeof sel === 'string' ? document.querySelector(sel) : sel;
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    },
    move(x, y, instant) {
      const c = $('tv-cursor');
      if (instant) { c.style.transition = 'none'; requestAnimationFrame(() => (c.style.transition = '')); }
      c.style.left = x + 'px';
      c.style.top = y + 'px';
      window.__tvPos = { x, y };
    },
    ripple(x, y) {
      const r = $('tv-ripple');
      r.style.left = x + 'px';
      r.style.top = y + 'px';
      r.classList.remove('go');
      void r.offsetWidth;
      r.classList.add('go');
    },
    highlight(r, label, opts = {}) {
      const hl = $('tv-hl'), tip = $('tv-tip');
      if (!r) { hl.className = ''; tip.className = ''; return; }
      const p = opts.pad ?? 6;
      Object.assign(hl.style, { left: r.x - p + 'px', top: r.y - p + 'px', width: r.w + 2 * p + 'px', height: r.h + 2 * p + 'px' });
      hl.className = 'on' + (opts.soft ? ' soft' : '');
      if (!label) { tip.className = ''; return; }
      tip.textContent = label;
      tip.style.left = '-9999px';
      tip.className = 'on';
      const tw = tip.offsetWidth, th = tip.offsetHeight, W = innerWidth, H = innerHeight;
      let side = opts.side;
      if (!side) side = r.x + r.w + tw + 30 < W && r.w < 320 ? 'right' : r.y + r.h + th + 30 < H - 90 ? 'below' : 'above';
      let x, y;
      if (side === 'right') { x = r.x + r.w + p + 16; y = r.y + r.h / 2 - 22; }
      else if (side === 'left') { x = r.x - p - 16 - tw; y = r.y + r.h / 2 - 22; }
      else if (side === 'below') { x = r.x + Math.min(r.w / 2, 60) - 24; y = r.y + r.h + p + 14; }
      else { x = r.x + Math.min(r.w / 2, 60) - 24; y = r.y - p - 14 - th; }
      const cx = Math.max(10, Math.min(x, W - tw - 10));
      tip.style.setProperty('--ax', Math.max(14, Math.min(tw - 28, x - cx + 24)) + 'px');
      tip.style.left = cx + 'px';
      tip.style.top = Math.max(10, Math.min(y, H - th - 10)) + 'px';
      tip.className = 'on ' + side;
    },
    clear() { $('tv-hl').className = ''; $('tv-tip').className = ''; $('tv-arrow').className = ''; $('tv-dd').className = ''; },
    caption(text, avoid) {
      const cap = $('tv-cap');
      if (!text) { cap.className = ''; return; }
      cap.textContent = text;
      const low = avoid && avoid.y + avoid.h > innerHeight - 170;
      cap.className = 'on' + (low ? ' top' : '');
    },
    capAvoid(r) { const cap = $('tv-cap'); if (cap.classList.contains('on')) cap.classList.toggle('top', !!r && r.y + r.h > innerHeight - 170); },
    badge(html) { const b = $('tv-badge'); b.innerHTML = html || ''; b.className = html ? 'on' : ''; },
    card(o) {
      const el = $('tv-card');
      if (!o) { el.className = ''; return; }
      el.innerHTML = `<div class="in"><img class="logo" src="assets/img/codial-logo.png">
        <div class="kick">${o.kick || ''}</div><h1>${o.title}</h1>${o.sub ? `<div class="sub">${o.sub}</div>` : ''}
        ${o.items ? `<ul>${o.items.map((i) => `<li>${i}</li>`).join('')}</ul>` : ''}<div class="bar"></div></div>`;
      el.className = 'on';
      el.querySelectorAll('li').forEach((li, i) => setTimeout(() => li.classList.add('on'), 600 + i * 260));
    },
    keynote(text, small) {
      const k = $('tv-key');
      if (!text) { k.className = ''; return; }
      k.innerHTML = text + (small ? `<small>${small}</small>` : '');
      k.className = 'on';
    },
    arrow(r) {
      const a = $('tv-arrow');
      if (!r) { a.className = ''; return; }
      a.style.left = r.x + r.w / 2 - 16 + 'px';
      a.style.top = r.y - 58 + 'px';
      a.className = 'on';
    },
    // Ochiladigan ro'yxatni ko'rsatish (headless brauzerda haqiqiy ro'yxat chizilmaydi)
    dropdown(sel, value) {
      const s = typeof sel === 'string' ? document.querySelector(sel) : sel;
      const dd = $('tv-dd');
      if (!s) return null;
      const r = s.getBoundingClientRect();
      const opts = [...s.options].filter((o) => o.value !== '' || !o.disabled);
      const list = opts.filter((o) => o.value !== '');
      const idx = Math.max(0, list.findIndex((o) => o.value === String(value)));
      const start = Math.max(0, Math.min(idx - 4, list.length - 9));
      const shown = list.slice(start, start + 9);
      dd.innerHTML = shown.map((o) => `<div data-v="${o.value.replace(/"/g, '&quot;')}">${o.textContent}</div>`).join('');
      dd.style.left = r.left + 'px';
      dd.style.minWidth = Math.max(r.width, 220) + 'px';
      dd.style.maxWidth = Math.max(r.width, 520) + 'px';
      const h = Math.min(360, shown.length * 37 + 12);
      dd.style.top = (r.bottom + 4 + h < innerHeight - 10 ? r.bottom + 4 : Math.max(10, r.top - h - 4)) + 'px';
      dd.className = 'on';
      maskNode(dd);
      const item = dd.querySelector(`[data-v="${CSS.escape(String(value))}"]`);
      if (!item) return null;
      item.classList.add('cur');
      const ir = item.getBoundingClientRect();
      return { x: ir.left, y: ir.top, w: ir.width, h: ir.height };
    },
    ddPick(value) {
      const it = document.querySelector(`#tv-dd [data-v="${CSS.escape(String(value))}"]`);
      if (it) { it.classList.remove('cur'); it.classList.add('sel'); }
    },
    ddHide() { $('tv-dd').className = ''; },
    setMask(on) { maskOn = on; },
    image(src, title) {
      const el = $('tv-img');
      if (!src) { el.className = ''; return; }
      el.innerHTML = `<div class="box">${title ? `<div class="t">${title}</div>` : ''}<img src="${src}"></div>`;
      el.className = 'on';
    },
  });
  // Yangi oyna (PDF chek) ochilmasin — havolasi saqlanadi, video uni rasm qilib ko'rsatadi
  window.open = (url) => { window.__tvOpened = url; return null; };
  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);
})();

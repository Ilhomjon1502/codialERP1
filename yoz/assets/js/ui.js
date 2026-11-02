/* Ko'rinish komponentlari: ekrandagi klaviatura, qo'llar, ovoz, grafik va yordamchilar. */
(function (Y) {
  'use strict';

  const ui = (Y.ui = {});

  ui.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  ui.fmtTime = function (ms) {
    const s = Math.round((ms || 0) / 1000);
    if (s < 60) return s + ' s';
    const m = Math.floor(s / 60);
    if (m < 60) return m + ' daq' + (s % 60 ? ' ' + (s % 60) + ' s' : '');
    return Math.floor(m / 60) + ' soat ' + (m % 60) + ' daq';
  };
  ui.clock = function (ms) {
    const s = Math.floor((ms || 0) / 1000);
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  };
  ui.stars = (n, max) => {
    let h = '';
    for (let i = 0; i < (max || 3); i++) h += '<span class="star' + (i < n ? ' on' : '') + '">★</span>';
    return h;
  };
  // Tugmada ko'rinadigan nom: harf — katta, bo'sh joy — «Probel».
  ui.keyName = (ch) => (ch === ' ' ? 'Probel' : ch === ';' ? 'nuqtali vergul (;)' : ch === ',' ? 'vergul (,)' : ch === '.' ? 'nuqta (.)' : ch === "'" ? "apostrof (')" : ch.toUpperCase());

  // ---------- klaviatura ----------

  ui.keyboard = function (el, opts) {
    opts = opts || {};
    el.classList.add('kb');
    el.innerHTML = Y.ROWS.map((row) => '<div class="kb-row">' + row.map((k) => {
      const f = k.f ? Y.FINGERS[k.f] : null;
      const style = 'flex-grow:' + k.w + ';' + (f ? '--fc:' + f.color : '');
      let label;
      if (k.special) label = '<span class="kl">' + ui.esc(k.label) + '</span>';
      else if (/[a-z]/.test(k.base)) label = '<span class="kl">' + k.base.toUpperCase() + '</span>';
      else label = '<span class="ks">' + ui.esc(k.shift) + '</span><span class="kl">' + ui.esc(k.base) + '</span>';
      const bump = k.id === 'f' || k.id === 'j' ? ' bump' : '';
      return '<div class="key' + (k.special ? ' sp' : '') + (f ? ' fc' : '') + bump + '" data-k="' + ui.esc(k.id) + '" style="' + style + '">' + label + '</div>';
    }).join('') + '</div>').join('');
    if (opts.colors === false) el.classList.add('plain');

    const node = (id) => el.querySelector('[data-k="' + (id === '"' ? '\\"' : id === '\\' ? '\\\\' : id) + '"]');
    let marked = [];
    return {
      // Keyingi bosiladigan belgi: tugma va kerak bo'lsa Shift yonadi.
      target(ch) {
        marked.forEach((n) => n.classList.remove('target'));
        marked = [];
        const c = ch == null ? null : Y.charKey(ch);
        if (!c) return;
        [c.key, c.shift].forEach((id) => { const n = id && node(id); if (n) { n.classList.add('target'); marked.push(n); } });
      },
      flash(id, ok) {
        const n = id && node(id);
        if (!n) return;
        const cls = ok === true ? 'hit-ok' : ok === false ? 'hit-bad' : 'hit';
        n.classList.remove('hit-ok', 'hit-bad', 'hit');
        void n.offsetWidth; // animatsiyani qayta boshlash
        n.classList.add(cls);
      },
      // Profil uchun: har harfning holati (0 — yaxshi … 1 — yomon) rang bilan.
      heat(values) {
        el.classList.add('heat');
        el.querySelectorAll('.key').forEach((n) => {
          const v = values[n.getAttribute('data-k')];
          if (v == null) { n.classList.add('nodata'); return; }
          const hue = Math.round(120 * (1 - Math.min(1, Math.max(0, v.bad))));
          n.style.background = 'hsl(' + hue + ' 70% 62%)';
          n.title = v.title || '';
        });
      },
      highlight(ids) { ids.forEach((id) => { const n = node(id); if (n) n.classList.add('home'); }); },
    };
  };

  // ---------- qo'llar ----------

  // Chap qo'l (barmoqlar yuqoriga qaragan); o'ng qo'l — uning ko'zgudagi aksi.
  const HAND = [
    ['L5', 'R5', 12, 52, 76],
    ['L4', 'R4', 44, 24, 100],
    ['L3', 'R3', 76, 10, 114],
    ['L2', 'R2', 108, 24, 100],
  ];
  function handSVG(side) {
    const idx = side === 'L' ? 0 : 1;
    // Bosh barmoq kaft ostidan chiqadi (avval chiziladi), keyin kaft, keyin to'rt barmoq.
    let h = '<g class="finger thumb" data-f="T' + side + '" transform="rotate(44 136 160)"><rect x="121" y="78" width="30" height="88" rx="15"/>' +
      '<circle cx="136" cy="92" r="8" style="fill:' + Y.FINGERS.T.color + '"/></g>' +
      '<rect class="palm" x="8" y="84" width="142" height="92" rx="42"/>';
    HAND.forEach((f) => {
      const code = f[idx];
      h += '<g class="finger" data-f="' + code + '"><rect x="' + f[2] + '" y="' + f[3] + '" width="29" height="' + f[4] + '" rx="14.5"/>' +
        '<circle cx="' + (f[2] + 14.5) + '" cy="' + (f[3] + 14) + '" r="8" style="fill:' + Y.FINGERS[code].color + '"/></g>';
    });
    return h;
  }
  ui.hands = function (el) {
    el.classList.add('hands');
    el.innerHTML = '<svg viewBox="0 0 480 186" aria-hidden="true">' +
      '<g transform="translate(14,4)">' + handSVG('L') + '</g>' +
      '<g transform="translate(466,4) scale(-1,1)">' + handSVG('R') + '</g></svg>';
    let on = [];
    return {
      finger(ch) {
        on.forEach((n) => n.classList.remove('on'));
        on = [];
        const c = ch == null ? null : Y.charKey(ch);
        if (!c) return;
        const f = Y.KEYS[c.key].f;
        // Probelni o'ng qo'l bosh barmog'i bosadi (oldingi harf chap qo'lda bo'lsa ham — oddiy qoida).
        const codes = [f === 'T' ? 'TR' : f];
        if (c.shift) codes.push(Y.KEYS[c.shift].f);
        codes.forEach((code) => el.querySelectorAll('[data-f="' + code + '"]').forEach((n) => { n.classList.add('on'); on.push(n); }));
      },
    };
  };

  // ---------- ovoz ----------

  let ac = null;
  function tone(freq, dur, type, vol, when) {
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      const t = ac.currentTime + (when || 0);
      const o = ac.createOscillator(), g = ac.createGain();
      o.type = type || 'sine';
      o.frequency.value = freq;
      g.gain.setValueAtTime(vol || 0.05, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      o.connect(g).connect(ac.destination);
      o.start(t);
      o.stop(t + dur + 0.02);
    } catch (e) { /* ovozsiz brauzer */ }
  }
  ui.sound = {
    key() { if (Y.store.settings.sound) tone(900, 0.03, 'triangle', 0.025); },
    error() { if (Y.store.settings.sound) tone(150, 0.16, 'square', 0.04); },
    done(stars) {
      if (!Y.store.settings.sound) return;
      const notes = stars ? [523, 659, 784, 1047].slice(0, stars + 1) : [330, 262];
      notes.forEach((f, i) => tone(f, 0.22, 'sine', 0.07, i * 0.12));
    },
  };

  // ---------- grafik (SVG) ----------

  // series: [{ t, wpm, raw }] — chiziq: o'rtacha tezlik, nuqtalar: shu soniyadagi tezlik.
  ui.speedChart = function (series) {
    const W = 560, H = 160, P = { l: 34, r: 10, t: 12, b: 24 };
    if (!series.length) return '';
    const maxY = Math.max(10, Math.ceil(Math.max.apply(null, series.map((s) => Math.max(s.wpm, s.raw))) / 10) * 10);
    const n = series.length;
    const x = (i) => P.l + (n === 1 ? (W - P.l - P.r) / 2 : (i * (W - P.l - P.r)) / (n - 1));
    const y = (v) => P.t + (H - P.t - P.b) * (1 - v / maxY);
    let g = '';
    for (let v = 0; v <= maxY; v += maxY / 4) {
      g += '<line class="grid" x1="' + P.l + '" x2="' + (W - P.r) + '" y1="' + y(v) + '" y2="' + y(v) + '"/>' +
        '<text class="ax" x="' + (P.l - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + Math.round(v) + '</text>';
    }
    const step = Math.max(1, Math.ceil(n / 8));
    series.forEach((s, i) => { if (i % step === 0 || i === n - 1) g += '<text class="ax" x="' + x(i) + '" y="' + (H - 6) + '" text-anchor="middle">' + s.t + 's</text>'; });
    const dots = series.map((s, i) => '<circle class="raw" cx="' + x(i) + '" cy="' + y(s.raw) + '" r="2.6"><title>' + s.t + 's: ' + s.raw + '</title></circle>').join('');
    const line = '<polyline class="avg" points="' + series.map((s, i) => x(i) + ',' + y(s.wpm)).join(' ') + '"/>';
    return '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Tezlik grafigi">' + g + dots + line + '</svg>';
  };

  // Kunlar bo'yicha ustunlar: [{ label, value(ms) }]
  ui.dayBars = function (days, goalMs) {
    const W = 560, H = 150, P = { l: 46, r: 8, t: 10, b: 24 };
    const maxV = Math.max(goalMs || 0, ...days.map((d) => d.value), 60000);
    const bw = (W - P.l - P.r) / days.length;
    const y = (v) => P.t + (H - P.t - P.b) * (1 - v / maxV);
    let g = '';
    if (goalMs) g += '<line class="goal" x1="' + P.l + '" x2="' + (W - P.r) + '" y1="' + y(goalMs) + '" y2="' + y(goalMs) + '"/>' +
      '<text class="ax" x="' + (W - P.r) + '" y="' + (y(goalMs) - 4) + '" text-anchor="end">maqsad</text>';
    days.forEach((d, i) => {
      const x = P.l + i * bw + bw * 0.18, w = bw * 0.64, top = y(d.value);
      g += '<rect class="bar' + (goalMs && d.value >= goalMs ? ' full' : '') + '" x="' + x + '" y="' + top + '" width="' + w + '" height="' + (H - P.b - top) + '" rx="4">' +
        '<title>' + d.label + ': ' + ui.fmtTime(d.value) + '</title></rect>' +
        '<text class="ax" x="' + (x + w / 2) + '" y="' + (H - 6) + '" text-anchor="middle">' + d.short + '</text>';
    });
    g += '<text class="ax" x="' + (P.l - 6) + '" y="' + (P.t + 8) + '" text-anchor="end">' + Math.round(maxV / 60000) + ' daq</text>';
    return '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Kunlik mashq">' + g + '</svg>';
  };
})(window.Y = window.Y || {});

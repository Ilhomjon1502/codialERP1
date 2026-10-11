/* Umumiy yordamchi funksiyalar */
window.App = window.App || {};
(function (A) {
  A.uid = () => Math.random().toString(16).slice(2, 10);

  A.esc = (s) =>
    String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  A.num = (n) => {
    const v = Math.round(Number(n) || 0);
    const s = String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return (v < 0 ? '−' : '') + s;
  };
  A.money = (n) => A.num(n) + " so'm";
  A.pct = (x) => Math.round((x || 0) * 100) + '%';

  A.sum = (arr, f) => arr.reduce((s, x) => s + (Number(typeof f === 'function' ? f(x) : x[f]) || 0), 0);
  A.groupBy = (arr, f) => {
    const m = new Map();
    for (const x of arr) {
      const k = f(x);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(x);
    }
    return m;
  };
  A.sortBy = (arr, f, desc) => [...arr].sort((a, b) => {
    const x = f(a), y = f(b);
    return (x > y ? 1 : x < y ? -1 : 0) * (desc ? -1 : 1);
  });

  /* ---- Sana ---- */
  const pad = (n) => String(n).padStart(2, '0');
  A.iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  A.parse = (iso) => {
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d || 1);
  };
  A.realToday = () => A.iso(new Date());
  A.addDays = (iso, n) => {
    const d = A.parse(iso);
    d.setDate(d.getDate() + n);
    return A.iso(d);
  };
  A.diffDays = (a, b) => Math.round((A.parse(b) - A.parse(a)) / 86400000);
  A.ym = (iso) => iso.slice(0, 7);
  A.addMonths = (ym, n) => {
    const [y, m] = ym.split('-').map(Number);
    const d = new Date(y, m - 1 + n, 1);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
  };
  A.isoWeekday = (iso) => {
    const w = A.parse(iso).getDay();
    return w === 0 ? 7 : w;
  };
  A.daysInMonth = (ym) => {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m, 0).getDate();
  };
  A.MONTHS = ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'];
  A.WD = ['', 'Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak'];
  A.WD_FULL = ['', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba'];
  A.ymLabel = (ym) => `${A.MONTHS[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;
  A.fdate = (iso) => (iso ? `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}` : '—');
  A.fdt = (ts) => {
    if (!ts) return '—';
    const d = new Date(ts);
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  A.lessonDaysInMonth = (ym, weekdays) => {
    const out = [];
    const n = A.daysInMonth(ym);
    for (let i = 1; i <= n; i++) {
      const iso = `${ym}-${pad(i)}`;
      if (weekdays.includes(A.isoWeekday(iso))) out.push(iso);
    }
    return out;
  };

  /* Deterministik tasodifiy sonlar (seed uchun) */
  A.rng = (seed) => {
    let a = seed >>> 0;
    return () => {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  A.initials = (name) => (name || '?').split(' ').slice(0, 2).map((s) => s[0]).join('').toUpperCase();

  A.downloadCSV = (filename, rows) => {
    const csv = rows.map((r) => r.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(';')).join('\r\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
})(window.App);

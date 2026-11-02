/* O'quvchi profillari va natijalar — faqat shu brauzerda (localStorage). Login yo'q. */
(function (Y) {
  'use strict';

  const KEY = 'codial-yoz-v1';
  const HISTORY = 200;
  Y.AVATARS = ['🦊', '🐼', '🐯', '🐸', '🐵', '🦁', '🐨', '🐰', '🐻', '🐧', '🦉', '🐙', '🐬', '🦄', '🐝', '🐢'];

  function fresh() { return { v: 1, profiles: {}, current: null, settings: { sound: true, hands: true, goalMin: 15 } }; }
  function load() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (s && s.v === 1) { s.settings = Object.assign(fresh().settings, s.settings); return s; }
    } catch (e) { /* brauzer xotirasi yopiq */ }
    return fresh();
  }
  let db = load();
  function save() { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { /* xotira to'la yoki yopiq */ } }

  // Mahalliy sana: 2026-11-02
  function ymd(d) {
    d = d || new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  const clean = (name) => String(name || '').replace(/\s+/g, ' ').trim();

  const store = (Y.store = {
    ymd,
    get settings() { return db.settings; },
    set(key, value) { db.settings[key] = value; save(); },

    profiles() { return Object.values(db.profiles).sort((a, b) => (b.lastAt || b.created) - (a.lastAt || a.created)); },
    current() { return db.current && db.profiles[db.current] ? db.profiles[db.current] : null; },
    use(id) { db.current = db.profiles[id] ? id : null; save(); },
    logout() { db.current = null; save(); },

    create(name, avatar) {
      name = clean(name);
      if (name.length < 2) throw new Error("Ism kamida 2 harf bo'lsin");
      if (name.length > 30) throw new Error('Ism juda uzun');
      if (Object.values(db.profiles).some((p) => p.name.toLowerCase() === name.toLowerCase())) throw new Error('Bu ism bilan profil bor — ro\'yxatdan tanlang');
      const p = { id: uid(), name, avatar: avatar || Y.AVATARS[0], created: Date.now(), lastAt: null, lessons: {}, keys: {}, days: {}, history: [] };
      db.profiles[p.id] = p;
      db.current = p.id;
      save();
      return p;
    },
    remove(id) { delete db.profiles[id]; if (db.current === id) db.current = null; save(); },

    lessonRec(p, id) { return (p && p.lessons[id]) || null; },
    passed(p, id) { const r = store.lessonRec(p, id); return !!(r && (r.stars >= 1 || r.done)); },

    // Dars ochiqmi: birinchisi yoki oldingisi o'tilgan bo'lsa.
    unlocked(p, lesson) {
      if (db.settings.allOpen) return true;
      const i = Y.LESSONS.indexOf(lesson);
      return i <= 0 || store.passed(p, Y.LESSONS[i - 1].id) || store.passed(p, lesson.id);
    },
    // Davom etish: birinchi o'tilmagan ochiq dars.
    nextFor(p) { return Y.LESSONS.find((l) => !store.passed(p, l.id)) || Y.LESSONS[Y.LESSONS.length - 1]; },

    // Ma'lumot darsi (slaydlar) ko'rildi.
    markDone(p, lessonId) {
      const r = p.lessons[lessonId] || (p.lessons[lessonId] = { stars: 0, wpm: 0, acc: 0, n: 0 });
      r.done = true;
      p.lastAt = Date.now();
      save();
    },

    // Mashq natijasini yozish. Natija: { first, best, newStars } — xabarlar uchun.
    record(p, lessonId, res, stars) {
      const now = Date.now();
      const r = p.lessons[lessonId] || (p.lessons[lessonId] = { stars: 0, wpm: 0, acc: 0, n: 0 });
      const out = { first: r.n === 0, best: res.wpm > r.wpm && r.n > 0, newStars: Math.max(0, stars - r.stars) };
      r.n++;
      if (stars > r.stars) r.stars = stars;
      if (res.wpm > r.wpm) r.wpm = res.wpm;
      if (res.acc > r.acc) r.acc = res.acc;
      r.lastAt = now;

      Object.keys(res.keyStats).forEach((ch) => {
        const s = res.keyStats[ch], k = p.keys[ch] || (p.keys[ch] = { n: 0, err: 0, ms: 0, timed: 0 });
        k.n += s.n; k.err += s.err; k.ms += s.ms; k.timed += s.timed;
      });

      const d = p.days[ymd()] || (p.days[ymd()] = { ms: 0, chars: 0, n: 0 });
      d.ms += res.ms; d.chars += res.chars; d.n++;

      p.history.unshift({ l: lessonId, at: now, wpm: res.wpm, acc: res.acc, ms: res.ms, stars });
      if (p.history.length > HISTORY) p.history.length = HISTORY;
      p.lastAt = now;
      save();
      return out;
    },

    summary(p) {
      const days = Object.keys(p.days);
      const totalMs = days.reduce((a, d) => a + p.days[d].ms, 0);
      const today = p.days[ymd()] ? p.days[ymd()].ms : 0;
      // Seriya: bugundan (bugun hali mashq qilinmagan bo'lsa — kechadan) orqaga ketma-ket kunlar.
      let streak = 0;
      const d = new Date();
      if (!p.days[ymd(d)]) d.setDate(d.getDate() - 1);
      while (p.days[ymd(d)]) { streak++; d.setDate(d.getDate() - 1); }
      const recs = Object.values(p.lessons);
      const tests = p.history.filter((h) => h.acc >= 90);
      return {
        totalMs,
        todayMs: today,
        streak,
        stars: recs.reduce((a, r) => a + (r.stars || 0), 0),
        passed: Y.LESSONS.filter((l) => store.passed(p, l.id)).length,
        bestWpm: tests.reduce((a, h) => Math.max(a, h.wpm), 0),
        avgAcc: p.history.length ? Math.round(p.history.slice(0, 20).reduce((a, h) => a + h.acc, 0) / Math.min(20, p.history.length)) : 0,
        attempts: p.history.length,
      };
    },

    // Natijani faylga saqlash va boshqa kompyuterda yuklash.
    exportProfile(p) { return JSON.stringify({ app: 'codial-yoz', v: 1, profile: p }); },
    importProfile(text) {
      let data;
      try { data = JSON.parse(text); } catch (e) { throw new Error('Fayl buzilgan'); }
      const p = data && data.app === 'codial-yoz' && data.profile;
      if (!p || !p.name || !p.lessons) throw new Error('Bu Codial Yoz fayli emas');
      const same = Object.values(db.profiles).find((x) => x.id === p.id || x.name.toLowerCase() === p.name.toLowerCase());
      if (same) {
        // Bir xil o'quvchi: qaysi biri ko'proq ishlagan bo'lsa — o'sha qoladi.
        if ((same.history || []).length > (p.history || []).length) throw new Error("Bu kompyuterdagi «" + same.name + "» natijasi yangiroq — fayl yuklanmadi");
        delete db.profiles[same.id];
      }
      db.profiles[p.id] = p;
      db.current = p.id;
      save();
      return p;
    },
  });
})(window.Y = window.Y || {});

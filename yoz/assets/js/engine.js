/* Yozish mexanikasi: bitta mashq (matn) bo'yicha bosishlar, vaqt va natija hisobi. DOM'ga bog'liq emas — testlanadi. */
(function (Y) {
  'use strict';

  const PAUSE_MS = 10000; // bundan uzun to'xtash ishlagan vaqtga kirmaydi

  // Darsda: xato bo'lsa, to'g'ri tugma bosilmaguncha oldinga o'tilmaydi.
  class Session {
    constructor(text, opts) {
      opts = opts || {};
      this.text = text;
      this.pauseMs = opts.pauseMs || PAUSE_MS;
      this.pos = 0;
      this.keystrokes = 0;
      this.correct = 0;
      this.errors = 0;
      this.errAt = new Set(); // xato qilingan o'rinlar
      this.keyStats = {}; // belgi → { n, err, ms, timed }
      this.wrong = {}; // qaysi belgi o'rniga nima bosildi: "a→s": 2
      this.timeline = []; // [faol ms, yozilgan belgilar, jami bosishlar]
      this.activeMs = 0;
      this.lastAt = null;
      this.done = false;
    }

    get expected() { return this.text[this.pos]; }
    get started() { return this.lastAt !== null; }

    // ch — bosilgan belgi, now — ms (performance.now yoki Date.now). Natija: { ok, done }.
    press(ch, now) {
      if (this.done) return { ok: false, done: true };
      ch = Y.normChar(ch);
      let gap = 0;
      if (this.lastAt !== null) {
        gap = now - this.lastAt;
        if (gap > 0 && gap <= this.pauseMs) this.activeMs += gap;
      }
      this.lastAt = now;
      this.keystrokes++;
      const exp = this.text[this.pos];
      const st = this.keyStats[exp] || (this.keyStats[exp] = { n: 0, err: 0, ms: 0, timed: 0 });
      if (ch === exp) {
        this.correct++;
        st.n++;
        // Harf tezligi — faqat birinchi urinishda to'g'ri bosilgan va pauzasiz holatlar bo'yicha.
        if (gap > 0 && gap <= this.pauseMs && !this.errAt.has(this.pos)) { st.ms += gap; st.timed++; }
        this.pos++;
        this.timeline.push([this.activeMs, this.pos, this.keystrokes]);
        if (this.pos >= this.text.length) this.done = true;
        return { ok: true, done: this.done };
      }
      this.errors++;
      if (!this.errAt.has(this.pos)) { this.errAt.add(this.pos); st.err++; }
      const w = exp + '→' + ch;
      this.wrong[w] = (this.wrong[w] || 0) + 1;
      this.timeline.push([this.activeMs, this.pos, this.keystrokes]);
      return { ok: false, done: false };
    }

    // Jonli ko'rsatkichlar (mashq davomida).
    live(now) {
      let ms = this.activeMs;
      if (this.lastAt !== null && !this.done) {
        const gap = now - this.lastAt;
        if (gap > 0 && gap <= this.pauseMs) ms += gap;
      }
      return { ms, wpm: wpm(this.pos, ms), acc: accuracy(this.correct, this.keystrokes) };
    }

    result() {
      const ms = Math.max(this.activeMs, 1);
      const series = perSecond(this.timeline, ms);
      return {
        chars: this.pos,
        keystrokes: this.keystrokes,
        errors: this.errors,
        errorPositions: this.errAt.size,
        ms: this.activeMs,
        wpm: round1(wpm(this.pos, ms)),
        raw: round1(wpm(this.keystrokes, ms)),
        acc: round1(accuracy(this.correct, this.keystrokes)),
        consistency: consistency(series.map((s) => s.raw)),
        series,
        keyStats: this.keyStats,
        weak: weakKeys(this.keyStats),
      };
    }
  }

  // So'z/daqiqa: 5 belgi = 1 so'z.
  function wpm(chars, ms) { return ms > 0 ? (chars / 5) / (ms / 60000) : 0; }
  function accuracy(correct, total) { return total > 0 ? (correct / total) * 100 : 100; }
  function round1(x) { return Math.round(x * 10) / 10; }

  // Har soniya: o'rtacha tezlik (shu paytgacha) va shu soniyadagi «raw» tezlik.
  function perSecond(timeline, totalMs) {
    const secs = Math.max(1, Math.ceil(totalMs / 1000));
    const out = [];
    let i = 0, prevKeys = 0, pos = 0, keys = 0;
    for (let s = 1; s <= secs; s++) {
      const edge = s * 1000;
      while (i < timeline.length && timeline[i][0] <= edge) { pos = timeline[i][1]; keys = timeline[i][2]; i++; }
      const span = Math.min(edge, totalMs) - (s - 1) * 1000;
      out.push({
        t: s,
        wpm: round1(wpm(pos, Math.min(edge, totalMs))),
        raw: span > 0 ? round1(wpm(keys - prevKeys, span)) : 0,
      });
      prevKeys = keys;
    }
    return out;
  }

  // Barqarorlik 0–100: raw tezlikning o'zgaruvchanlik koeffitsienti (CV) qanchalik kichik bo'lsa, shuncha yuqori.
  function consistency(values) {
    if (values.length < 2) return 100;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    if (mean <= 0) return 0;
    const sd = Math.sqrt(values.reduce((a, b) => a + (b - mean) * (b - mean), 0) / values.length);
    return Math.round(100 * (1 - Math.tanh(sd / mean)));
  }

  // Eng ko'p xato qilingan belgilar (bo'sh joysiz), kamayish tartibida.
  function weakKeys(stats, limit) {
    return Object.keys(stats)
      .filter((ch) => ch !== ' ' && stats[ch].err > 0)
      .sort((a, b) => stats[b].err - stats[a].err)
      .slice(0, limit || 5);
  }

  // Yulduzlar: aniqlik 90% dan past — o'tmadi (0); ★ ≥ 90; ★★ ≥ 95; ★★★ ≥ 97 va maqsad tezlik.
  Y.PASS_ACC = 90;
  function stars(res, goalWpm) {
    if (res.acc < Y.PASS_ACC) return 0;
    if (res.acc >= 97 && res.wpm >= (goalWpm || 0)) return 3;
    if (res.acc >= 95) return 2;
    return 1;
  }

  Y.Session = Session;
  Y.calc = { wpm, accuracy, perSecond, consistency, weakKeys, stars };
})(window.Y = window.Y || {});

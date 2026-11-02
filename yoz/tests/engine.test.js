// Ishga tushirish: node --test yoz/tests/
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS = path.join(__dirname, '..', 'assets', 'js');
function load(...files) {
  const ctx = { window: {} };
  vm.createContext(ctx);
  files.forEach((f) => vm.runInContext(fs.readFileSync(path.join(JS, f), 'utf8'), ctx, { filename: f }));
  return ctx.window.Y;
}
const plain = (o) => JSON.parse(JSON.stringify(o));
const Y = load('keys.js', 'engine.js', 'words_uz.js', 'lessons.js');

function typeAll(s, keys, stepMs) {
  let t = 1000;
  keys.split('').forEach((c) => { s.press(c, t); t += stepMs; });
}

test("to'g'ri yozilsa: aniqlik 100, tezlik vaqtdan", () => {
  const s = new Y.Session('asdf jkl');
  typeAll(s, 'asdf jkl', 200); // 8 belgi, 7 oraliq × 200 ms = 1,4 s
  const r = s.result();
  assert.strictEqual(s.done, true);
  assert.strictEqual(r.acc, 100);
  assert.strictEqual(r.ms, 1400);
  assert.strictEqual(r.wpm, Math.round((8 / 5) / (1400 / 60000) * 10) / 10);
});

test("xato bo'lsa oldinga o'tmaydi va aniqlik tushadi", () => {
  const s = new Y.Session('ab');
  assert.deepStrictEqual(plain(s.press('x', 0)), { ok: false, done: false });
  assert.strictEqual(s.pos, 0);
  s.press('a', 100);
  s.press('b', 200);
  const r = s.result();
  assert.strictEqual(r.keystrokes, 3);
  assert.strictEqual(r.errors, 1);
  assert.strictEqual(r.acc, 66.7);
  assert.strictEqual(s.keyStats.a.err, 1);
  assert.strictEqual(s.wrong['a→x'], 1);
  assert.deepStrictEqual(plain(r.weak), ['a']);
});

test("bir o'rinda ko'p xato — harf xatosi bir marta sanaladi", () => {
  const s = new Y.Session('a');
  s.press('s', 0); s.press('d', 100); s.press('a', 200);
  assert.strictEqual(s.keyStats.a.err, 1);
  assert.strictEqual(s.errors, 2);
});

test("10 soniyadan uzun pauza vaqtga kirmaydi", () => {
  const s = new Y.Session('abc');
  s.press('a', 0); s.press('b', 500); s.press('c', 60000);
  assert.strictEqual(s.result().ms, 500);
});

test("apostrofning hamma ko'rinishi qabul qilinadi", () => {
  ['\'', '`', 'ʻ', 'ʼ', '‘', '’'].forEach((ap) => {
    const s = new Y.Session("o'");
    s.press('o', 0);
    assert.strictEqual(s.press(ap, 100).ok, true, ap);
  });
});

test('yulduzlar', () => {
  const st = Y.calc.stars;
  assert.strictEqual(st({ acc: 89.9, wpm: 50 }, 10), 0);
  assert.strictEqual(st({ acc: 90, wpm: 5 }, 10), 1);
  assert.strictEqual(st({ acc: 96, wpm: 50 }, 10), 2);
  assert.strictEqual(st({ acc: 97, wpm: 9 }, 10), 2);
  assert.strictEqual(st({ acc: 98, wpm: 10 }, 10), 3);
});

test('barqarorlik: bir tekis tezlik — 100', () => {
  assert.strictEqual(Y.calc.consistency([40, 40, 40]), 100);
  assert.ok(Y.calc.consistency([10, 80, 5, 90]) < 50);
});

test('belgi → tugma va Shift', () => {
  assert.deepStrictEqual(plain(Y.charKey('f')), { key: 'f', shift: null });
  assert.deepStrictEqual(plain(Y.charKey('F')), { key: 'f', shift: 'ShiftRight' });
  assert.deepStrictEqual(plain(Y.charKey('J')), { key: 'j', shift: 'ShiftLeft' });
  assert.deepStrictEqual(plain(Y.charKey(' ')), { key: 'Space', shift: null });
  assert.strictEqual(Y.charKey('’').key, "'");
  assert.strictEqual(Y.codeKey('KeyA'), 'a');
  assert.strictEqual(Y.codeKey('Semicolon'), ';');
});

test("so'zlar ro'yxati faqat lotin harflari va apostrof", () => {
  assert.ok(Y.WORDS_UZ.length > 300);
  Y.WORDS_UZ.forEach((w) => assert.match(w, /^[a-z']+$/));
});

test("har darsning matni faqat ruxsat etilgan belgilardan va bo'sh emas", () => {
  let seed = 1;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  Y.LESSONS.forEach((l) => {
    if (l.kind === 'info') return;
    for (let i = 0; i < 20; i++) {
      const t = Y.makeText(l, rnd);
      assert.ok(t.length >= 20, l.id + ': matn qisqa');
      assert.ok(!/\s{2}|^\s|\s$/.test(t), l.id + ': ortiqcha bo\'sh joy');
      t.split('').forEach((c) => assert.ok(c === ' ' || l.keys.indexOf(c) >= 0, l.id + ': ruxsatsiz belgi «' + c + '» — ' + t));
      if (l.newKeys) l.newKeys.split('').forEach((c) => assert.ok(t.indexOf(c) >= 0, l.id + ': yangi harf yo\'q ' + c));
    }
  });
});

test("darslar id'si noyob, keyingi dars topiladi", () => {
  const ids = Y.LESSONS.map((l) => l.id);
  assert.strictEqual(new Set(ids).size, ids.length);
  assert.strictEqual(Y.nextLesson('0-1').id, '0-2');
  assert.strictEqual(Y.nextLesson(ids[ids.length - 1]), null);
});

test("hamma JS fayllar sintaksis jihatdan to'g'ri", () => {
  fs.readdirSync(JS).filter((f) => f.endsWith('.js')).forEach((f) => {
    assert.doesNotThrow(() => new vm.Script(fs.readFileSync(path.join(JS, f), 'utf8'), { filename: f }), f);
  });
});

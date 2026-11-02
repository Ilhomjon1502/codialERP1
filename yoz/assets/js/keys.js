/* Klaviatura xaritasi: tugmalar, barmoqlar va belgi → tugma moslashuvi (US/lotin joylashuvi). */
(function (Y) {
  'use strict';

  // Barmoq kodlari: L5 — chap jimjiloq … L2 — chap ko'rsatkich, R2 … R5 — o'ng, T — bosh barmoq.
  Y.FINGERS = {
    L5: { name: "chap jimjiloq", color: '#f28b82' },
    L4: { name: "chap nomsiz barmoq", color: '#fbbc5d' },
    L3: { name: "chap o'rta barmoq", color: '#fdd663' },
    L2: { name: "chap ko'rsatkich barmoq", color: '#81c995' },
    T: { name: 'bosh barmoq', color: '#c3cad4' },
    R2: { name: "o'ng ko'rsatkich barmoq", color: '#78d9ec' },
    R3: { name: "o'ng o'rta barmoq", color: '#8ab4f8' },
    R4: { name: "o'ng nomsiz barmoq", color: '#c58af9' },
    R5: { name: "o'ng jimjiloq", color: '#ff8bcb' },
  };

  const k = (base, shift, f) => ({ id: base, base, shift, f, w: 1 });
  const sp = (id, label, w, f) => ({ id, label, w, f: f || null, special: true });

  Y.ROWS = [
    [k('`', '~', 'L5'), k('1', '!', 'L5'), k('2', '@', 'L4'), k('3', '#', 'L3'), k('4', '$', 'L2'), k('5', '%', 'L2'),
      k('6', '^', 'R2'), k('7', '&', 'R2'), k('8', '*', 'R3'), k('9', '(', 'R4'), k('0', ')', 'R5'), k('-', '_', 'R5'),
      k('=', '+', 'R5'), sp('Backspace', '⌫', 2, 'R5')],
    [sp('Tab', 'Tab', 1.5, 'L5'), k('q', 'Q', 'L5'), k('w', 'W', 'L4'), k('e', 'E', 'L3'), k('r', 'R', 'L2'), k('t', 'T', 'L2'),
      k('y', 'Y', 'R2'), k('u', 'U', 'R2'), k('i', 'I', 'R3'), k('o', 'O', 'R4'), k('p', 'P', 'R5'), k('[', '{', 'R5'),
      k(']', '}', 'R5'), Object.assign(k('\\', '|', 'R5'), { w: 1.5 })],
    [sp('CapsLock', 'Caps', 1.75, 'L5'), k('a', 'A', 'L5'), k('s', 'S', 'L4'), k('d', 'D', 'L3'), k('f', 'F', 'L2'), k('g', 'G', 'L2'),
      k('h', 'H', 'R2'), k('j', 'J', 'R2'), k('k', 'K', 'R3'), k('l', 'L', 'R4'), k(';', ':', 'R5'), k("'", '"', 'R5'),
      sp('Enter', 'Enter', 2.25, 'R5')],
    [sp('ShiftLeft', 'Shift', 2.25, 'L5'), k('z', 'Z', 'L5'), k('x', 'X', 'L4'), k('c', 'C', 'L3'), k('v', 'V', 'L2'), k('b', 'B', 'L2'),
      k('n', 'N', 'R2'), k('m', 'M', 'R2'), k(',', '<', 'R3'), k('.', '>', 'R4'), k('/', '?', 'R5'), sp('ShiftRight', 'Shift', 2.75, 'R5')],
    [sp('CtrlL', 'Ctrl', 1.25), sp('WinL', '', 1.25), sp('AltL', 'Alt', 1.25), sp('Space', '', 6.25, 'T'),
      sp('AltR', 'Alt', 1.25), sp('WinR', '', 1.25), sp('Menu', '', 1.25), sp('CtrlR', 'Ctrl', 1.25)],
  ];

  Y.KEYS = {};
  Y.ROWS.forEach((row) => row.forEach((key) => { Y.KEYS[key.id] = key; }));

  // O'zbekcha o' va g' uchun apostrofning hamma ko'rinishi bitta tugma deb qabul qilinadi.
  Y.APOSTROPHES = "'`ʻʼ‘’";
  Y.normChar = (ch) => (Y.APOSTROPHES.indexOf(ch) >= 0 ? "'" : ch);

  // Belgi → { key, shift } — qaysi tugma va (kerak bo'lsa) qaysi Shift.
  const CHAR = { ' ': { key: 'Space', shift: null } };
  Y.ROWS.forEach((row) => row.forEach((key) => {
    if (key.special) return;
    CHAR[key.base] = { key: key.id, shift: null };
    // Shift'ni boshqa qo'l bosadi: chap qo'ldagi harf uchun o'ng Shift va aksincha.
    CHAR[key.shift] = { key: key.id, shift: key.f[0] === 'L' ? 'ShiftRight' : 'ShiftLeft' };
  }));
  Y.charKey = (ch) => CHAR[Y.normChar(ch)] || null;
  Y.charFinger = (ch) => { const c = Y.charKey(ch); return c ? Y.KEYS[c.key].f : null; };

  // KeyboardEvent.code → tugma id (ekrandagi klaviaturada bosilgan tugmani ko'rsatish uchun).
  const CODE = {
    Backquote: '`', Minus: '-', Equal: '=', BracketLeft: '[', BracketRight: ']', Backslash: '\\', Semicolon: ';',
    Quote: "'", Comma: ',', Period: '.', Slash: '/', Space: 'Space', Backspace: 'Backspace', Tab: 'Tab',
    CapsLock: 'CapsLock', Enter: 'Enter', ShiftLeft: 'ShiftLeft', ShiftRight: 'ShiftRight',
  };
  Y.codeKey = (code) => {
    if (!code) return null;
    if (CODE[code]) return CODE[code];
    if (/^Key[A-Z]$/.test(code)) return code.slice(3).toLowerCase();
    if (/^Digit\d$/.test(code)) return code.slice(5);
    return null;
  };
})(window.Y = window.Y || {});

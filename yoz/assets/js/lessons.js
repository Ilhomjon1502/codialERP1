/* Kurs: bo'limlar, darslar va mashq matnini yasash. Har urinishda matn yangidan yasaladi (yodlab olinmasin). */
(function (Y) {
  'use strict';

  const HOME = 'fjdksla;gh';
  const LEN = { intro: 55, drill: 70, words: 100, review: 130, test: 170 };
  const PUNCT = ';,.';

  // Darslar to'plami: yangi harflar uchun «tanishuv → mashq → so'zlar».
  function trio(newKeys, keys, goals, title) {
    const label = title || newKeys.toUpperCase().split('').join(' va ');
    const L = [
      { kind: 'intro', title: label, newKeys, keys, goal: goals[0] },
      { kind: 'drill', title: label + ': mashq', focus: newKeys, keys, goal: goals[1] },
    ];
    if (words(keys, newKeys).length >= 6) L.push({ kind: 'words', title: label + ": so'zlar", focus: newKeys, keys, goal: goals[2] });
    return L;
  }

  const units = [
    {
      title: 'Tayyorgarlik', icon: '🪑',
      lessons: [
        { kind: 'info', title: "To'g'ri o'tirish", slides: 'posture' },
        { kind: 'info', title: 'Barmoqlar joyi', slides: 'home' },
        { kind: 'fixed', title: 'Barmoqlar joyida', keys: HOME, goal: 4,
          text: 'asdf jkl; asdf jkl; fdsa ;lkj fdsa ;lkj asdf jkl; ff jj dd kk ss ll aa ;; asdf jkl;' },
      ],
    },
    {
      title: 'Asosiy qator', icon: '🏠',
      lessons: [].concat(
        trio('fj', 'fj', [6, 8, 10]),
        trio('dk', 'fjdk', [6, 8, 10]),
        trio('sl', 'fjdksl', [6, 8, 10]),
        trio('a;', 'fjdksla;', [6, 8, 10], 'A va ;'),
        trio('gh', HOME, [6, 9, 10]),
        [
          { kind: 'review', title: 'Takrorlash', keys: HOME, goal: 10 },
          { kind: 'test', title: "Bo'lim sinovi", keys: HOME, goal: 10 },
        ]
      ),
    },
    {
      title: 'Yuqori qator', icon: '⬆️',
      lessons: [].concat(
        trio('ei', HOME + 'ei', [8, 10, 12]),
        trio('ru', HOME + 'eiru', [8, 10, 12]),
        trio('ty', HOME + 'eiruty', [8, 10, 12]),
        [
          { kind: 'review', title: 'Takrorlash', keys: HOME + 'eiruty', goal: 12 },
          { kind: 'test', title: "Bo'lim sinovi", keys: HOME + 'eiruty', goal: 12 },
        ]
      ),
    },
    {
      title: 'Yuqori qator: O, P, Q, W', icon: '🔼',
      lessons: [].concat(
        trio('o', HOME + 'eirutyo', [10, 12, 14], 'O'),
        trio('qp', HOME + 'eirutyoqp', [10, 12, 14]),
        trio('w', HOME + 'eirutyoqpw', [10, 12, 14], 'W'),
        [
          { kind: 'review', title: 'Takrorlash', keys: HOME + 'eirutyoqpw', goal: 14 },
          { kind: 'test', title: "Bo'lim sinovi", keys: HOME + 'eirutyoqpw', goal: 14 },
        ]
      ),
    },
    {
      title: 'Pastki qator', icon: '⬇️',
      lessons: [].concat(
        trio('vm', HOME + 'eirutyoqpwvm', [10, 13, 15]),
        trio('bn', HOME + 'eirutyoqpwvmbn', [10, 13, 15]),
        trio('c,', HOME + 'eirutyoqpwvmbnc,', [10, 13, 15], 'C va vergul'),
        trio('x.', HOME + 'eirutyoqpwvmbnc,x.', [10, 13, 15], 'X va nuqta'),
        trio('z', HOME + 'eirutyoqpwvmbnc,x.z', [10, 13, 15], 'Z'),
        [
          { kind: 'review', title: 'Takrorlash', keys: HOME + 'eirutyoqpwvmbnc,x.z', goal: 15 },
          { kind: 'test', title: "Bo'lim sinovi", keys: HOME + 'eirutyoqpwvmbnc,x.z', goal: 15 },
        ]
      ),
    },
  ];

  Y.UNITS = units.map((u, ui) => Object.assign({}, u, {
    id: ui,
    lessons: u.lessons.map((l, li) => Object.assign({ id: ui + '-' + (li + 1), unit: ui, n: li + 1 }, l)),
  }));
  Y.LESSONS = [].concat.apply([], Y.UNITS.map((u) => u.lessons));
  Y.lesson = (id) => Y.LESSONS.find((l) => l.id === id) || null;
  Y.nextLesson = (id) => { const i = Y.LESSONS.findIndex((l) => l.id === id); return i >= 0 ? Y.LESSONS[i + 1] || null : null; };

  // ---------- matn yasash ----------

  function pick(arr, rnd) { return arr[Math.floor(rnd() * arr.length)]; }

  // Faqat ruxsat etilgan harflardan iborat so'zlar; focus berilsa — shu harflardan birini o'z ichiga olganlar oldinda.
  function words(keys, focus) {
    const ok = Y.WORDS_UZ.filter((w) => w.split('').every((c) => keys.indexOf(c) >= 0));
    if (!focus) return ok;
    const f = focus.split('').filter((c) => PUNCT.indexOf(c) < 0);
    return f.length ? ok.filter((w) => f.some((c) => w.indexOf(c) >= 0)) : ok;
  }

  // Harflar guruhi (2–5 belgi); focus harflari 3 barobar ko'p chiqadi; tinish belgisi faqat guruh oxirida.
  function group(keys, focus, rnd) {
    const letters = keys.split('').filter((c) => PUNCT.indexOf(c) < 0);
    const pool = letters.concat(focus ? focus.split('').filter((c) => PUNCT.indexOf(c) < 0).reduce((a, c) => a.concat([c, c]), []) : []);
    const n = 2 + Math.floor(rnd() * 4);
    let g = '';
    for (let i = 0; i < n; i++) g += pick(pool, rnd);
    const punct = (focus || keys).split('').filter((c) => PUNCT.indexOf(c) >= 0);
    if (punct.length && rnd() < (focus && punct.some((c) => focus.indexOf(c) >= 0) ? 0.5 : 0.15)) g += pick(punct, rnd);
    return g;
  }

  function fill(len, next) {
    const out = [];
    let size = 0, prev = null;
    while (size < len) {
      let t = next();
      if (t === prev) t = next();
      out.push(t); size += t.length + 1; prev = t;
    }
    return out.join(' ');
  }

  function introText(newKeys, keys, rnd) {
    const nk = newKeys.split('');
    const parts = [];
    nk.forEach((c) => parts.push(c + c + c, c + c + c));
    if (nk.length > 1) for (let i = 0; i < 4; i++) parts.push(group(newKeys, '', rnd).replace(/[;,.]$/, '') || nk[0] + nk[1]);
    const old = keys.split('').filter((c) => nk.indexOf(c) < 0 && PUNCT.indexOf(c) < 0);
    while (parts.join(' ').length < LEN.intro) {
      // Eski harf + yangi harf: «fd» «kd» — yangi harf eskilari orasida.
      const c = pick(nk, rnd);
      parts.push(old.length ? pick(old, rnd) + c + (rnd() < 0.5 ? pick(old, rnd) : c) : c + c);
    }
    return parts.join(' ');
  }

  Y.makeText = function (lesson, rnd) {
    rnd = rnd || Math.random;
    switch (lesson.kind) {
      case 'fixed':
        return lesson.text;
      case 'intro':
        return introText(lesson.newKeys, lesson.keys, rnd);
      case 'drill':
        return fill(LEN.drill, () => group(lesson.keys, lesson.focus, rnd));
      case 'words': {
        const list = words(lesson.keys, lesson.focus);
        return fill(LEN.words, () => pick(list, rnd));
      }
      case 'review':
      case 'test': {
        const list = words(lesson.keys);
        const len = LEN[lesson.kind];
        if (list.length < 6) return fill(len, () => group(lesson.keys, '', rnd));
        // Takrorlashda har 3-guruh — harflar mashqi, sinovda faqat so'zlar.
        let i = 0;
        return fill(len, () => (lesson.kind === 'review' && ++i % 3 === 0 ? group(lesson.keys, '', rnd) : pick(list, rnd)));
      }
      default:
        return '';
    }
  };

  Y.lessonWords = words;
})(window.Y = window.Y || {});

/* Sahifalar va marshrut: #/ — profil tanlash, #/map — darslar, #/l/<id> — dars, #/me — natijalarim. */
(function (Y) {
  'use strict';

  const ui = Y.ui, store = Y.store, esc = ui.esc;
  const $ = (s, r) => (r || document).querySelector(s);
  const go = (path) => { location.hash = '#/' + path; };
  let cleanup = null;

  const KIND = { info: "Ma'lumot", fixed: 'Mashq', intro: 'Yangi harflar', drill: 'Mashq', words: "So'zlar", review: 'Takrorlash', test: 'Sinov' };
  const goalMs = () => (store.settings.goalMin || 15) * 60000;

  function toast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add('out'), 2600);
    setTimeout(() => t.remove(), 3100);
  }

  function header(p, active) {
    const s = store.settings;
    return '<header class="top"><div class="top-in">' +
      '<a class="brand" href="#/map"><img src="assets/img/codial-logo.png" alt="Codial"><span>Yoz</span></a>' +
      (p ? '<nav><a href="#/map" class="' + (active === 'map' ? 'on' : '') + '">Darslar</a>' +
        '<a href="#/me" class="' + (active === 'me' ? 'on' : '') + '">Natijalarim</a></nav>' : '<nav></nav>') +
      '<button class="icon-btn" data-act="sound" title="Ovoz">' + (s.sound ? '🔊' : '🔇') + '</button>' +
      (p ? '<a class="who" href="#/" title="Boshqa o\'quvchi"><span class="av">' + esc(p.avatar) + '</span><span class="nm">' + esc(p.name) + '</span></a>' : '') +
      '</div></header>' +
      (window.matchMedia && matchMedia('(pointer: coarse)').matches && !matchMedia('(pointer: fine)').matches
        ? '<div class="mobile-note">⌨️ Mashq qilish uchun kompyuter va klaviatura kerak.</div>' : '');
  }

  // Umumiy tugmalar (sarlavhadagi ovoz).
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act="sound"]');
    if (!b) return;
    store.set('sound', !store.settings.sound);
    b.textContent = store.settings.sound ? '🔊' : '🔇';
  });

  function ring(value, max, label) {
    const r = 30, c = 2 * Math.PI * r, part = Math.min(1, max ? value / max : 0);
    return '<svg class="ring" viewBox="0 0 76 76"><circle cx="38" cy="38" r="' + r + '" class="ring-bg"/>' +
      '<circle cx="38" cy="38" r="' + r + '" class="ring-fg' + (part >= 1 ? ' full' : '') + '" stroke-dasharray="' + (c * part) + ' ' + c + '"/>' +
      '<text x="38" y="43" text-anchor="middle">' + esc(label) + '</text></svg>';
  }

  // ---------- profil tanlash ----------

  function renderProfiles() {
    const list = store.profiles();
    let avatar = Y.AVATARS[Math.floor(Math.random() * Y.AVATARS.length)];
    $('#app').innerHTML = header(null) +
      '<main class="page narrow center">' +
      '<div class="hello"><h1>Klaviaturada tez va to\'g\'ri yozishni o\'rganamiz</h1>' +
      '<p>O\'n barmoq bilan, klaviaturaga qaramasdan. Har kuni ozgina — natija tez ko\'rinadi.</p></div>' +
      (list.length ? '<h2 class="sub">Kim mashq qiladi?</h2><div class="profiles">' + list.map((p) => {
        const s = store.summary(p);
        return '<div class="pcard" data-id="' + esc(p.id) + '" tabindex="0"><span class="av">' + esc(p.avatar) + '</span>' +
          '<b>' + esc(p.name) + '</b><small>⭐ ' + s.stars + ' · ' + s.passed + ' dars' + (s.streak ? ' · 🔥 ' + s.streak : '') + '</small>' +
          '<button class="del" data-del="' + esc(p.id) + '" title="O\'chirish">×</button></div>';
      }).join('') + '<div class="pcard add" data-new tabindex="0"><span class="av">＋</span><b>Yangi o\'quvchi</b></div></div>' : '') +
      '<form class="card newp' + (list.length ? ' hidden' : '') + '" id="newp">' +
      '<label>Ismingiz<input name="name" maxlength="30" autocomplete="off" placeholder="Masalan: Ali Karimov"></label>' +
      '<div class="avatars">' + Y.AVATARS.map((a) => '<button type="button" class="avb' + (a === avatar ? ' on' : '') + '" data-av="' + a + '">' + a + '</button>').join('') + '</div>' +
      '<div class="err" id="newp-err"></div>' +
      '<button class="btn primary big">Boshlash →</button></form>' +
      '<p class="muted small">Natijalar shu kompyuterdagi brauzerda saqlanadi. Boshqa kompyuterda davom etish uchun ' +
      '«Natijalarim» sahifasidan faylni saqlab, bu yerda yuklang: ' +
      '<label class="link">fayldan yuklash<input type="file" accept=".json,application/json" id="imp" hidden></label></p>' +
      '</main>';

    const form = $('#newp');
    const open = () => { form.classList.remove('hidden'); form.name.focus(); };
    if (!list.length) setTimeout(() => form.name.focus(), 0);
    $('#app').onclick = (e) => {
      const del = e.target.closest('[data-del]');
      if (del) {
        e.stopPropagation();
        const p = store.profiles().find((x) => x.id === del.dataset.del);
        if (p && confirm('«' + p.name + '» profili va uning barcha natijalari o\'chirilsinmi?')) { store.remove(p.id); renderProfiles(); }
        return;
      }
      const card = e.target.closest('.pcard');
      if (card && card.hasAttribute('data-new')) return open();
      if (card) { store.use(card.dataset.id); go('map'); return; }
      const av = e.target.closest('[data-av]');
      if (av) {
        avatar = av.dataset.av;
        form.querySelectorAll('.avb').forEach((b) => b.classList.toggle('on', b === av));
      }
    };
    $('#app').onkeydown = (e) => { if (e.key === 'Enter' && e.target.classList.contains('pcard')) e.target.click(); };
    form.onsubmit = (e) => {
      e.preventDefault();
      try { store.create(form.name.value, avatar); go('l/' + store.nextFor(store.current()).id); }
      catch (err) { $('#newp-err').textContent = err.message; }
    };
    $('#imp').onchange = (e) => {
      const f = e.target.files[0];
      if (!f) return;
      f.text().then((txt) => {
        try { const p = store.importProfile(txt); toast('«' + p.name + '» natijalari yuklandi'); go('map'); }
        catch (err) { toast(err.message); }
      });
    };
  }

  // ---------- darslar xaritasi ----------

  function renderMap(p) {
    const s = store.summary(p);
    const next = store.nextFor(p);
    const maxStars = Y.LESSONS.filter((l) => l.kind !== 'info').length * 3;
    $('#app').innerHTML = header(p, 'map') + '<main class="page">' +
      '<section class="hero card">' +
      '<div class="hero-me"><span class="av big">' + esc(p.avatar) + '</span><div><h1>Salom, ' + esc(p.name.split(' ')[0]) + '!</h1>' +
      '<p class="muted">' + (s.todayMs >= goalMs() ? 'Bugungi maqsad bajarildi — barakalla! 🎉' : 'Bugungi maqsad: ' + store.settings.goalMin + ' daqiqa mashq.') + '</p></div></div>' +
      '<div class="hero-stats">' +
      '<div class="st">' + ring(s.todayMs, goalMs(), Math.floor(s.todayMs / 60000) + '/' + store.settings.goalMin) + '<span>bugun, daq</span></div>' +
      '<div class="st"><b>' + ui.fmtTime(s.totalMs) + '</b><span>jami mashq</span></div>' +
      '<div class="st"><b>' + s.bestWpm + '</b><span>eng yaxshi tezlik<br>so\'z/daqiqa</span></div>' +
      '<div class="st"><b>🔥 ' + s.streak + '</b><span>kun ketma-ket</span></div>' +
      '<div class="st"><b>⭐ ' + s.stars + '</b><span>' + maxStars + ' tadan</span></div>' +
      '</div>' +
      '<a class="btn primary big go" href="#/l/' + next.id + '">' + (s.passed ? 'Davom etish' : 'Boshlash') + ': ' + esc(next.title) + ' →</a>' +
      '</section>' +
      Y.UNITS.map((u) => {
        const st = u.lessons.reduce((a, l) => a + ((store.lessonRec(p, l.id) || {}).stars || 0), 0);
        const mx = u.lessons.filter((l) => l.kind !== 'info').length * 3;
        return '<section class="unit"><h2><span class="uic">' + u.icon + '</span>' + u.id + '. ' + esc(u.title) +
          (mx ? '<small>⭐ ' + st + ' / ' + mx + '</small>' : '') + '</h2><div class="tiles">' +
          u.lessons.map((l) => tile(p, l, l === next)).join('') + '</div></section>';
      }).join('') +
      '<p class="muted small center">Keyingi bo\'limlar (o\' g\', bosh harflar, raqamlar, matnlar, o\'yinlar) tez orada qo\'shiladi.</p>' +
      '</main>';
    const cur = $('.tile.current');
    if (cur && s.passed > 6) cur.scrollIntoView({ block: 'center' });
  }

  function tile(p, l, isNext) {
    const rec = store.lessonRec(p, l.id);
    const open = store.unlocked(p, l);
    const done = store.passed(p, l.id);
    const cls = 'tile k-' + l.kind + (open ? '' : ' locked') + (isNext ? ' current' : '') + (done ? ' passed' : '');
    const body = '<span class="num">' + (open ? l.n : '🔒') + '</span><span class="tt">' + esc(l.title) + '</span>' +
      '<span class="kind">' + KIND[l.kind] + '</span>' +
      (l.kind === 'info' ? '<span class="stars">' + (done ? '✓' : '') + '</span>' : '<span class="stars">' + ui.stars(rec ? rec.stars : 0) + '</span>') +
      (rec && rec.wpm ? '<span class="best">' + rec.wpm + ' so\'z/daq</span>' : '');
    return open ? '<a class="' + cls + '" href="#/l/' + l.id + '">' + body + '</a>' : '<div class="' + cls + '" title="Avval oldingi darsni o\'ting">' + body + '</div>';
  }

  // ---------- ma'lumot darslari (slaydlar) ----------

  const SLIDES = {
    posture: [
      { t: 'Xush kelibsiz! 👋', b: '<p>Bu yerda siz <b>o\'n barmoq bilan, klaviaturaga qaramasdan</b> yozishni o\'rganasiz. Avval — to\'g\'ri o\'tirish:</p>' +
        '<ul class="tips"><li>🪑 Orqangizni tik tuting, oyoqlaringiz polda tursin.</li><li>🖥️ Ekran ko\'z balandligida, 50–70 sm uzoqlikda.</li>' +
        '<li>💪 Tirsaklar taxminan to\'g\'ri burchakda, yelkalar bo\'sh.</li><li>✋ Bilaklarni stolga tiramang — barmoqlar tugmalar ustida yengil tursin.</li>' +
        '<li>👀 Ekranga qarang, klaviaturaga emas!</li></ul>' },
      { t: 'Eng muhim qoida', b: '<p class="lead">Avval <b>to\'g\'ri</b>, keyin <b>tez</b>.</p>' +
        '<ul class="tips"><li>🎯 Aniqlik 90% dan past bo\'lsa, dars o\'tilmaydi — shoshmang.</li><li>☝️ Har tugmani faqat <b>o\'z barmog\'i</b> bosadi.</li>' +
        '<li>🏠 Tugmani bosgach, barmoq yana asosiy qatorga qaytadi.</li><li>⭐ Aniq va tez yozsangiz — 3 yulduz olasiz.</li>' +
        '<li>☕ Charchasangiz, dam oling: har kuni 15 daqiqa — eng yaxshi mashq.</li></ul>' },
    ],
    home: [
      { t: 'Asosiy qator', b: '<p>Barmoqlar doim shu tugmalar ustida turadi: chap qo\'l — <b>A S D F</b>, o\'ng qo\'l — <b>J K L ;</b>. Bosh barmoqlar — <b>Probel</b> ustida.</p>', kb: 'home', hands: true },
      { t: 'F va J dagi bo\'rtiqlar', b: '<p><b>F</b> va <b>J</b> tugmalarida kichik bo\'rtiq bor — paypaslab ko\'ring! Ko\'rsatkich barmoqlaringiz ularni qaramasdan topadi. Har doim shu yerdan boshlang.</p>', kb: 'fj', hands: true },
      { t: 'Barmoq ranglari', b: '<p>Klaviaturadagi har bir rang — bitta barmoq. Masalan, sariq tugmalarni chap o\'rta barmoq bosadi. Mashq paytida keyingi tugma va barmoq yonib turadi.</p>', kb: 'all', legend: true },
    ],
  };

  function renderInfo(p, lesson) {
    const slides = SLIDES[lesson.slides];
    let i = 0;
    $('#app').innerHTML = header(p, 'map') + '<main class="page narrow"><div class="lbar"><a href="#/map" class="back">← Darslar</a>' +
      '<div class="ltitle"><small>' + lesson.unit + '-bo\'lim · ' + lesson.n + '-dars</small>' + esc(lesson.title) + '</div></div>' +
      '<section class="card slide" id="slide"></section></main>';
    const finish = () => {
      store.markDone(p, lesson.id);
      const nx = Y.nextLesson(lesson.id);
      go(nx ? 'l/' + nx.id : 'map');
    };
    const draw = () => {
      const s = slides[i];
      const last = i === slides.length - 1;
      $('#slide').innerHTML = '<h1>' + esc(s.t) + '</h1>' + s.b +
        (s.kb ? '<div class="kb-wrap"><div id="skb"></div>' + (s.hands ? '<div id="shands"></div>' : '') + '</div>' : '') +
        (s.legend ? '<div class="legend">' + Object.keys(Y.FINGERS).map((f) => '<span><i style="background:' + Y.FINGERS[f].color + '"></i>' + Y.FINGERS[f].name + '</span>').join('') + '</div>' : '') +
        '<div class="slide-nav"><button class="btn" data-prev ' + (i ? '' : 'disabled') + '>← Oldingi</button>' +
        '<span class="dots">' + slides.map((_, j) => '<i class="' + (j === i ? 'on' : '') + '"></i>').join('') + '</span>' +
        '<button class="btn primary" data-next>' + (last ? 'Tushunarli ✓' : 'Keyingi →') + '</button></div>';
      if (s.kb) {
        const kb = ui.keyboard($('#skb'), { colors: s.kb === 'all' });
        if (s.kb === 'home') kb.highlight(['a', 's', 'd', 'f', 'j', 'k', 'l', ';', 'Space']);
        if (s.kb === 'fj') kb.highlight(['f', 'j']);
        if (s.hands) {
          const hands = $('#shands');
          ui.hands(hands);
          hands.querySelectorAll('.finger').forEach((n) => { if (s.kb === 'home' || /2$/.test(n.dataset.f)) n.classList.add('on'); });
        }
      }
      $('[data-prev]').onclick = () => { if (i) { i--; draw(); } };
      $('[data-next]').onclick = () => { if (last) finish(); else { i++; draw(); } };
    };
    draw();
    const onKey = (e) => {
      if (e.key === 'Enter' || e.key === 'ArrowRight') { e.preventDefault(); $('[data-next]').click(); }
      if (e.key === 'ArrowLeft') $('[data-prev]').click();
    };
    document.addEventListener('keydown', onKey);
    cleanup = () => document.removeEventListener('keydown', onKey);
  }

  // ---------- dars (mashq) ----------

  function renderLesson(p, id) {
    const lesson = Y.lesson(id);
    if (!lesson) return go('map');
    if (!store.unlocked(p, lesson)) { toast('Bu dars hali yopiq — avval oldingisini o\'ting'); return go('map'); }
    if (lesson.kind === 'info') return renderInfo(p, lesson);

    const unit = Y.UNITS[lesson.unit];
    $('#app').innerHTML = header(p, 'map') + '<main class="page lesson">' +
      '<div class="lbar"><a href="#/map" class="back">← Darslar</a>' +
      '<div class="ltitle"><small>' + unit.id + '-bo\'lim · ' + esc(unit.title) + ' · ' + lesson.n + '-dars</small>' + esc(lesson.title) + '</div>' +
      (lesson.kind === 'intro' ? '<div class="intro">Yangi: ' + lesson.newKeys.split('').map((c) => {
        const f = Y.charFinger(c);
        return '<span class="newkey" style="--fc:' + Y.FINGERS[f].color + '"><b>' + esc(c === ';' ? ';' : c.toUpperCase()) + '</b><small>' + Y.FINGERS[f].name + '</small></span>';
      }).join('') + '</div>' : '') +
      '<div class="live"><div><b id="lv-wpm">0</b><span>so\'z/daq</span></div><div><b id="lv-acc">100%</b><span>aniqlik</span></div>' +
      '<div><b id="lv-time">0:00</b><span>vaqt</span></div></div></div>' +
      '<div class="typebox card" id="box"><div class="progress"><i id="prog"></i></div>' +
      '<div class="text-view" id="view"><div class="text-inner" id="txt"></div></div>' +
      '<div class="hint" id="hint"></div></div>' +
      '<div class="warn hidden" id="warn"></div>' +
      '<div class="kb-wrap"><div id="kb"></div><div id="hands" class="' + (store.settings.hands ? '' : 'hidden') + '"></div></div>' +
      '<div class="ltools"><label><input type="checkbox" id="opt-hands" ' + (store.settings.hands ? 'checked' : '') + '> Qo\'llarni ko\'rsatish</label>' +
      '<span class="muted">Esc — qaytadan boshlash · maqsad: aniqlik ≥ 90%' + (lesson.goal ? ', ⭐⭐⭐ uchun ' + lesson.goal + ' so\'z/daq' : '') + '</span></div>' +
      '</main><div class="modal hidden" id="result"></div>';

    const kb = ui.keyboard($('#kb'));
    const hands = ui.hands($('#hands'));
    const txt = $('#txt'), view = $('#view'), box = $('#box');
    let text, sess, spans, timer = null, resultOpen = false, passedNow = false;

    $('#opt-hands').onchange = (e) => {
      store.set('hands', e.target.checked);
      $('#hands').classList.toggle('hidden', !e.target.checked);
    };

    function warn(msg) { const w = $('#warn'); w.textContent = msg || ''; w.classList.toggle('hidden', !msg); }

    function start() {
      text = Y.makeText(lesson);
      sess = new Y.Session(text);
      let h = '';
      text.split(/( )/).forEach((tok) => {
        if (!tok) return;
        if (tok === ' ') { h += '<span class="c sp"> </span>'; return; }
        h += '<span class="w">' + tok.split('').map((c) => '<span class="c">' + esc(c) + '</span>').join('') + '</span>';
      });
      txt.innerHTML = h;
      spans = txt.querySelectorAll('.c');
      txt.style.transform = '';
      clearInterval(timer); timer = null;
      $('#lv-wpm').textContent = '0'; $('#lv-acc').textContent = '100%'; $('#lv-time').textContent = '0:00';
      $('#prog').style.width = '0';
      resultOpen = false;
      $('#result').classList.add('hidden');
      warn('');
      cursor();
    }

    function cursor() {
      const ch = text[sess.pos];
      if (spans[sess.pos]) spans[sess.pos].classList.add('cur');
      kb.target(ch);
      hands.finger(ch);
      const c = Y.charKey(ch);
      $('#hint').innerHTML = sess.started ? (c ? 'Keyingi: <b>' + esc(ui.keyName(ch)) + '</b> — ' + Y.FINGERS[Y.KEYS[c.key].f].name +
        (c.shift ? ' + ' + (c.shift === 'ShiftLeft' ? 'chap' : 'o\'ng') + ' Shift' : '') : '') :
        'Boshlash uchun <b>' + esc(ui.keyName(ch)) + '</b> tugmasini bosing — ' + Y.FINGERS[Y.charFinger(ch)].name;
      // Joriy qator ko'rinib tursin: ikkinchi qator joriy bo'lgach matn yuqoriga suriladi.
      const cur = spans[sess.pos];
      if (cur) {
        const lh = parseFloat(getComputedStyle(view).lineHeight) || 50;
        const line = Math.round((cur.getBoundingClientRect().top - txt.getBoundingClientRect().top) / lh);
        txt.style.transform = 'translateY(' + (-Math.max(0, line - 1) * lh) + 'px)';
      }
      $('#prog').style.width = (100 * sess.pos / text.length) + '%';
    }

    function tickLive() {
      const l = sess.live(performance.now());
      $('#lv-wpm').textContent = Math.round(l.wpm);
      $('#lv-acc').textContent = Math.round(l.acc) + '%';
      $('#lv-time').textContent = ui.clock(l.ms);
    }

    function onKey(e) {
      if (resultOpen) {
        if (e.key === 'Enter') { e.preventDefault(); (passedNow ? $('[data-r="next"]') || $('[data-r="retry"]') : $('[data-r="retry"]')).click(); }
        return;
      }
      if (e.ctrlKey || e.metaKey || (e.altKey && !e.getModifierState('AltGraph'))) return;
      if (e.key === 'Escape') { e.preventDefault(); start(); return; }
      const kid = Y.codeKey(e.code);
      if (e.key.length !== 1) { if (kid && kid !== 'CapsLock') kb.flash(kid); return; }
      e.preventDefault();
      if (e.repeat) return;
      if (/[Ѐ-ӿ]/.test(e.key)) { warn('Klaviatura tili ruscha. Inglizcha (EN) ga o\'tkazing: Alt+Shift yoki Win+Probel.'); return; }
      if (e.getModifierState && e.getModifierState('CapsLock') && /[a-z]/i.test(e.key)) { warn('Caps Lock yoqilgan — uni o\'chiring (chap tomondagi Caps tugmasi).'); return; }
      warn('');
      const pos = sess.pos;
      const r = sess.press(e.key, performance.now());
      kb.flash(kid, r.ok);
      if (!timer && !sess.done) timer = setInterval(tickLive, 200);
      if (r.ok) {
        ui.sound.key();
        spans[pos].classList.remove('cur', 'bad');
        spans[pos].classList.add(sess.errAt.has(pos) ? 'fix' : 'ok');
        if (r.done) return finish();
        cursor();
      } else {
        ui.sound.error();
        spans[pos].classList.add('bad');
        box.classList.remove('shake'); void box.offsetWidth; box.classList.add('shake');
      }
    }

    function finish() {
      clearInterval(timer); timer = null;
      tickLive();
      kb.target(null); hands.finger(null);
      const res = sess.result();
      const stars = Y.calc.stars(res, lesson.goal);
      const info = store.record(p, lesson.id, res, stars);
      passedNow = stars > 0;
      ui.sound.done(stars);
      showResult(res, stars, info);
    }

    function showResult(res, stars, info) {
      const next = Y.nextLesson(lesson.id);
      let title, msg;
      if (!stars) { title = 'Yana bir urinib ko\'ring'; msg = 'Aniqlik ' + res.acc + '% — o\'tish uchun kamida ' + Y.PASS_ACC + '% kerak. Shoshmang: to\'g\'ri yozish tezlikdan muhim.'; }
      else if (stars === 3) { title = 'Ajoyib!'; msg = 'Aniq ham, tez ham — hamma yulduzlar sizniki!'; }
      else if (res.acc >= 97) { title = 'Zo\'r aniqlik!'; msg = '3-yulduz uchun tezlik ' + lesson.goal + ' so\'z/daqiqa bo\'lsin — yana bir marta urinib ko\'ring.'; }
      else if (stars === 2) { title = 'Juda yaxshi!'; msg = '3-yulduz uchun aniqlik 97% va tezlik ' + lesson.goal + ' so\'z/daqiqa kerak.'; }
      else { title = 'Dars o\'tildi!'; msg = 'Ko\'proq yulduz uchun xatolarni kamaytiring: aniqlik 95% — 2 yulduz.'; }
      if (info.best) msg += ' Bu darsda yangi rekord! 🏆';
      const weak = res.weak.map((c) => '<span class="kchip">' + esc(ui.keyName(c)) + '</span>').join('');
      $('#result').innerHTML = '<div class="modal-card"><div class="r-stars' + (stars ? '' : ' none') + '">' + ui.stars(stars) + '</div>' +
        '<h2>' + esc(title) + '</h2><p class="muted">' + esc(msg) + '</p>' +
        '<div class="r-grid"><div><b>' + res.wpm + '</b><span>so\'z/daqiqa</span></div><div><b>' + res.acc + '%</b><span>aniqlik</span></div>' +
        '<div><b>' + ui.clock(res.ms) + '</b><span>vaqt</span></div><div><b>' + res.consistency + '%</b><span>barqarorlik</span></div>' +
        '<div><b>' + res.errors + '</b><span>xato bosish</span></div></div>' +
        (res.series.length > 2 ? '<div class="r-chart">' + ui.speedChart(res.series) +
          '<div class="chart-legend"><span><i class="l-avg"></i>o\'rtacha tezlik</span><span><i class="l-raw"></i>har soniyadagi tezlik</span></div></div>' : '') +
        (weak ? '<div class="r-weak">Ko\'p xato qilingan: ' + weak + '</div>' : '') +
        '<div class="r-actions"><button class="btn" data-r="retry">↻ Qayta</button>' +
        (passedNow && next ? '<button class="btn primary" data-r="next">Keyingi dars →</button>' : '') +
        '<a class="btn ghost" href="#/map">Darslar</a></div>' +
        '<p class="muted small">Enter — ' + (passedNow && next ? 'keyingi dars' : 'qayta') + '</p></div>';
      $('#result').classList.remove('hidden');
      resultOpen = true;
      $('[data-r="retry"]').onclick = start;
      const nb = $('[data-r="next"]');
      if (nb) nb.onclick = () => go('l/' + next.id);
    }

    document.addEventListener('keydown', onKey);
    const blur = () => { if (timer) { clearInterval(timer); timer = null; } };
    window.addEventListener('blur', blur);
    cleanup = () => { document.removeEventListener('keydown', onKey); window.removeEventListener('blur', blur); clearInterval(timer); };
    start();
  }

  // ---------- natijalarim ----------

  function renderMe(p) {
    const s = store.summary(p);
    const days = [];
    for (let i = 13; i >= 0; i--) {
      const d = new Date(); d.setDate(d.getDate() - i);
      const k = store.ymd(d);
      days.push({ label: d.getDate() + '.' + String(d.getMonth() + 1).padStart(2, '0'), short: String(d.getDate()), value: p.days[k] ? p.days[k].ms : 0 });
    }
    // Harflar xaritasi: xato ulushi va sekinlik birga.
    const heat = {}, rows = [];
    Object.keys(p.keys).forEach((ch) => {
      const k = p.keys[ch];
      if (ch === ' ' || k.n < 5) return;
      const err = k.err / k.n, avg = k.timed ? k.ms / k.timed : 0;
      const bad = Math.min(1, err * 5) * 0.6 + Math.min(1, Math.max(0, (avg - 250) / 750)) * 0.4;
      const c = Y.charKey(ch);
      const title = ui.keyName(ch) + ': ' + k.n + ' marta, xato ' + Math.round(err * 100) + '%' + (avg ? ', o\'rtacha ' + Math.round(avg) + ' ms' : '');
      if (c && !c.shift) heat[c.key] = { bad, title };
      rows.push({ ch, bad, err, avg, n: k.n });
    });
    const weak = rows.sort((a, b) => b.bad - a.bad).slice(0, 6).filter((r) => r.bad > 0.15);

    $('#app').innerHTML = header(p, 'me') + '<main class="page">' +
      '<section class="card me-head"><span class="av big">' + esc(p.avatar) + '</span><div><h1>' + esc(p.name) + '</h1>' +
      '<p class="muted">' + s.passed + ' / ' + Y.LESSONS.length + ' dars o\'tilgan · ' + s.attempts + ' ta mashq</p></div>' +
      '<button class="btn" id="exp">⬇ Natijamni faylga saqlash</button></section>' +
      '<div class="tiles-stat">' +
      '<div class="card st"><b>' + ui.fmtTime(s.totalMs) + '</b><span>jami mashq vaqti</span></div>' +
      '<div class="card st"><b>' + ui.fmtTime(s.todayMs) + '</b><span>bugun</span></div>' +
      '<div class="card st"><b>' + s.bestWpm + '</b><span>eng yaxshi tezlik, so\'z/daq</span></div>' +
      '<div class="card st"><b>' + (s.avgAcc || '—') + (s.avgAcc ? '%' : '') + '</b><span>o\'rtacha aniqlik (oxirgi 20)</span></div>' +
      '<div class="card st"><b>🔥 ' + s.streak + '</b><span>kun ketma-ket</span></div>' +
      '<div class="card st"><b>⭐ ' + s.stars + '</b><span>yulduz</span></div></div>' +
      '<section class="card"><h2>So\'nggi 14 kun</h2>' + ui.dayBars(days, goalMs()) + '</section>' +
      '<section class="card"><h2>Harflar xaritasi</h2><p class="muted small">Yashil — yaxshi, qizil — sekin yoki ko\'p xato. Tugma ustida turing — batafsil.</p>' +
      '<div id="heat"></div>' +
      (weak.length ? '<p>Ko\'proq mashq qiling: ' + weak.map((r) => '<span class="kchip">' + esc(ui.keyName(r.ch)) + '</span>').join('') + '</p>' : '') +
      '</section>' +
      '<section class="card"><h2>So\'nggi mashqlar</h2>' + (p.history.length ? '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Sana</th><th>Dars</th><th>Tezlik</th><th>Aniqlik</th><th>Vaqt</th><th></th></tr></thead><tbody>' +
        p.history.slice(0, 25).map((h) => {
          const l = Y.lesson(h.l), d = new Date(h.at);
          return '<tr><td>' + d.getDate() + '.' + String(d.getMonth() + 1).padStart(2, '0') + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0') +
            '</td><td>' + (l ? l.id + ' ' + esc(l.title) : esc(h.l)) + '</td><td>' + h.wpm + '</td><td>' + h.acc + '%</td><td>' + ui.clock(h.ms) + '</td><td class="stars">' + ui.stars(h.stars) + '</td></tr>';
        }).join('') + '</tbody></table></div>' : '<p class="muted">Hali mashq yo\'q. <a href="#/map">Darslarga o\'ting</a>.</p>') +
      '</section></main>';
    ui.keyboard($('#heat')).heat(heat);
    $('#exp').onclick = () => {
      const blob = new Blob([store.exportProfile(p)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'codial-yoz-' + p.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.json';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    };
  }

  // ---------- marshrut ----------

  function route() {
    if (cleanup) { cleanup(); cleanup = null; }
    $('#app').onclick = null; $('#app').onkeydown = null;
    const parts = location.hash.replace(/^#\/?/, '').split('/');
    const p = store.current();
    if (!p && parts[0]) return go('');
    if (parts[0] === 'map') renderMap(p);
    else if (parts[0] === 'l') renderLesson(p, parts[1]);
    else if (parts[0] === 'me') renderMe(p);
    else renderProfiles();
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  route();
})(window.Y = window.Y || {});

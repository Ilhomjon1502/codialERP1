/* Codial Darslik — Telegram Mini App. Server: /api/v1/learn/* (initData bilan imzolanadi, sessiyasiz).
   Sahifalar: #/ (darslar yo'li), #/lesson/N (nazariya, amaliyot, natijalar). Hisob-kitob serverda, bu yerda faqat ko'rsatiladi. */
(function () {
  const tg = window.Telegram && window.Telegram.WebApp;
  const API = '/api/v1/learn';
  const app = document.getElementById('app');
  let state = null; // {name, students: [...]}
  let cur = 0; // tanlangan talaba indeksi
  let lesson = null; // ochiq dars
  let tab = 'theory';

  /* ---------- yordamchilar ---------- */
  const el = (tag, attrs, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v === null || v === undefined) continue;
      if (k === 'class') n.className = v;
      else if (k === 'html') n.innerHTML = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) n.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return n;
  };
  const haptic = (k) => { try { tg && tg.HapticFeedback && (k === 'ok' ? tg.HapticFeedback.notificationOccurred('success') : k === 'bad' ? tg.HapticFeedback.notificationOccurred('warning') : tg.HapticFeedback.impactOccurred('light')); } catch (e) { /* ixtiyoriy */ } };
  const toast = (msg) => { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2600); };
  const fdate = (iso) => { const d = new Date(iso); return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' }); };

  async function api(path, opts = {}) {
    const headers = { 'X-Telegram-Init-Data': (tg && tg.initData) || '', ...(opts.headers || {}) };
    let r;
    try { r = await fetch(API + path, { ...opts, headers }); } catch (e) { throw new Error("Internetga ulanib bo'lmadi"); }
    let data = {};
    try { data = await r.json(); } catch (e) { /* bo'sh javob */ }
    if (!r.ok) { const err = new Error(data.detail || 'Xatolik'); err.status = r.status; throw err; }
    return data;
  }

  function ring(pct, size, stroke, color, label, sub) {
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const svg = el('div', { class: 'ring-box', style: `width:${size}px;height:${size}px` });
    svg.innerHTML = `<svg class="ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle class="bg" cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke-width="${stroke}"/>
      <circle class="fg" cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}" stroke-dasharray="${c}" stroke-dashoffset="${c}"/></svg>`;
    svg.append(el('div', { class: 'ring-label' }, el('div', {}, el('b', { style: `font-size:${Math.round(size / 3.6)}px` }, label), sub ? el('div', { class: 'small', style: 'opacity:.75' }, sub) : null)));
    requestAnimationFrame(() => requestAnimationFrame(() => { svg.querySelector('.fg').style.strokeDashoffset = c * (1 - Math.max(0, Math.min(1, pct))); }));
    return svg;
  }

  function confetti() {
    const cv = document.getElementById('confetti');
    const ctx = cv.getContext('2d');
    cv.width = innerWidth; cv.height = innerHeight;
    const colors = ['#ff8a1f', '#ff5e3a', '#22b573', '#3b82f6', '#f5c518', '#a855f7'];
    const ps = Array.from({ length: 110 }, () => ({ x: innerWidth / 2, y: innerHeight * 0.38, vx: (Math.random() - 0.5) * 14, vy: -Math.random() * 13 - 4, s: 5 + Math.random() * 6, c: colors[(Math.random() * colors.length) | 0], r: Math.random() * 6, vr: (Math.random() - 0.5) * 0.4 }));
    let t = 0;
    (function frame() {
      ctx.clearRect(0, 0, cv.width, cv.height);
      ps.forEach((p) => { p.vy += 0.35; p.x += p.vx; p.y += p.vy; p.r += p.vr; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * 0.6); ctx.restore(); });
      if (++t < 130) requestAnimationFrame(frame); else ctx.clearRect(0, 0, cv.width, cv.height);
    })();
  }

  const scoreColor = (s) => (s >= 60 ? 'var(--ok)' : 'var(--warn)');
  const student = () => state.students[cur];
  const go = (h) => { location.hash = h; };
  const nav = (h) => { if (location.hash === h) route(); else go(h); }; // hash o'zgarmasa ham sahifa qayta chiziladi

  /* ---------- bosh sahifa ---------- */
  function home() {
    lesson = null;
    if (tg) tg.BackButton.hide();
    const st = student();
    app.replaceChildren();
    const root = el('div', { class: 'fade split' });
    const side = el('div', { class: 'side' });
    const main = el('div', { class: 'main' });
    root.append(side, main);
    app.append(root);

    if (!st.lessons.length) {
      main.append(el('div', { class: 'empty card' }, el('span', { class: 'big' }, '📚'), `${st.first_name} uchun faol kurs topilmadi. Markaz administratoriga murojaat qiling.`));
      return;
    }
    const s = st.stats;
    const hero = el('div', { class: 'hero' },
      el('div', { class: 'hello' }, st.role === 'Vasiy' ? 'Farzandingiz natijalari' : 'Salom 👋'),
      el('h1', {}, st.first_name),
      el('div', { class: 'course' }, st.course),
      el('div', { class: 'hero-row' },
        ring(s.passed / s.total, 92, 9, '#ffb15c', `${s.passed}/${s.total}`, 'dars'),
        el('div', { class: 'stat' },
          el('div', { class: 'stat-box' }, el('b', {}, s.avg === null ? '—' : s.avg), el('span', {}, "o'rtacha ball")),
          el('div', { class: 'stat-box' }, el('b', {}, `${s.unlocked}`), el('span', {}, 'ochilgan dars')),
        ),
      ),
    );
    side.append(hero);

    if (state.students.length > 1) {
      side.append(el('div', { class: 'switch' }, state.students.map((x, i) => el('button', { class: i === cur ? 'on' : '', onclick: () => { cur = i; haptic(); home(); } }, x.first_name))));
    }
    side.append(typingCard(st));
    if (st.role === 'Vasiy') side.append(el('div', { class: 'banner' }, "👪 Siz vasiy sifatida kirgansiz: darslar va ballarni ko'rasiz. Vazifani o'quvchining o'zi topshiradi."));

    main.append(el('div', { class: 'section-title', style: 'margin-top:4px' }, 'Darslar'));
    const path = el('div', { class: 'path' });
    st.lessons.forEach((l) => {
      const cls = !l.unlocked ? 'locked' : l.passed ? 'done' : l.attempts > 0 ? 'retry' : '';
      const sub = !l.unlocked ? `Guruhda ${l.number}-dars o'tilgach ochiladi` : l.pending ? '⏳ AI tekshirmoqda…' : l.passed ? `Topshirildi · ${l.attempts}/${l.max_attempts} urinish` : l.attempts > 0 ? `Qayta urinish mumkin · ${l.attempts}/${l.max_attempts}` : 'Boshlashga tayyor';
      const hwMark = l.unlocked && l.homework && l.homework.enabled ? (l.homework.passed ? ' · 🏠✓' : l.homework.pending ? ' · 🏠⏳' : ' · 🏠') : '';
      path.append(el('button', { class: `lesson ${cls}`, onclick: () => { if (!l.unlocked) { haptic('bad'); toast(`🔒 ${l.number}-dars hali ochilmagan`); return; } haptic(); go(`#/lesson/${l.number}`); } },
        el('div', { class: 'node' }, !l.unlocked ? '🔒' : l.passed ? '✓' : l.number),
        el('div', { class: 't' }, el('b', {}, `${l.number}. ${l.title}`), el('span', {}, sub + hwMark)),
        l.best !== null ? el('div', { class: `score ${l.best >= s.pass_score ? 'ok' : 'bad'}` }, l.best) : el('div', { class: 'arrow' }, l.unlocked ? '›' : ''),
      ));
    });
    main.append(path);
  }

  /* ---------- klaviatura trenajori (Codial Yoz) ---------- */
  function typingCard(st) {
    const t = st.typing || {};
    const goal = 15;
    const pct = Math.min(1, (t.today_min || 0) / goal);
    const growth = t.first_wpm !== null && t.first_wpm !== undefined && t.recent_wpm !== null && t.recent_wpm !== undefined && t.sessions > 3
      ? el('div', { class: 'growth' }, `📈 ${t.first_wpm} → ${t.recent_wpm} so'z/daq`) : null;
    const card = el('div', { class: 'card yoz' },
      el('div', { class: 'yoz-head' }, el('div', { class: 'yoz-ic' }, '⌨️'), el('div', {}, el('h3', {}, 'Klaviatura trenajori'),
        el('div', { class: 'muted small' }, t.sessions ? 'Har kuni 10–15 daqiqa mashq qiling' : "Birinchi kundan boshlang: o'n barmoq bilan yozishni o'rganing"))),
      el('div', { class: 'yoz-stats' },
        el('div', {}, el('b', {}, `${t.today_min || 0}/${goal}`), el('span', {}, 'bugun, daq')),
        el('div', {}, el('b', {}, `🔥 ${t.streak || 0}`), el('span', {}, 'ketma-ket kun')),
        el('div', {}, el('b', {}, t.best_wpm || '—'), el('span', {}, "eng yaxshi, s/daq")),
        el('div', {}, el('b', {}, t.avg_acc === null || t.avg_acc === undefined ? '—' : t.avg_acc + '%'), el('span', {}, 'aniqlik'))),
      el('div', { class: 'goal' }, el('i', { style: `width:${Math.round(pct * 100)}%` })),
      growth,
      st.role === 'Talaba' ? el('button', { class: 'cta', style: 'margin-top:14px', onclick: () => { haptic(); openYoz(st); } }, t.sessions ? '⌨️ Mashq qilish' : '⌨️ Boshlash')
        : el('div', { class: 'muted small', style: 'margin-top:10px' }, "Mashqni o'quvchining o'zi qiladi, natijasi shu yerda ko'rinadi."),
      el('div', { class: 'muted small', style: 'margin-top:8px' }, "💻 Mashq kompyuterda, klaviatura bilan qilinadi."));
    return card;
  }

  async function openYoz(st) {
    let r;
    try {
      const fd = new FormData();
      fd.append('student', st.id);
      r = await api('/yoz-code/', { method: 'POST', body: fd });
    } catch (e) { toast(e.message); return; }
    const bg = el('div', { class: 'sheet-bg' });
    const sheet = el('div', { class: 'sheet' });
    const close = () => { bg.remove(); sheet.remove(); };
    bg.onclick = close;
    sheet.append(el('div', { class: 'grab' }), el('h3', {}, '⌨️ Klaviatura trenajori'),
      el('div', { class: 'muted small' }, "Bu qurilmada ochsangiz, avtomatik ulanadi. Boshqa kompyuterda ishlasangiz — quyidagi kodni kiriting."),
      el('div', { class: 'code' }, r.code.split('').join(' ')),
      el('div', { class: 'muted small', style: 'text-align:center' }, `${Math.round(r.expires_in / 60)} daqiqa amal qiladi, bir marta ishlaydi`),
      el('button', { class: 'cta', style: 'margin-top:14px', onclick: () => { location.href = r.url; } }, "⌨️ Shu qurilmada ochish"),
      el('div', { class: 'steps-how' }, el('b', {}, 'Boshqa kompyuterda:'), el('div', {}, `1. Brauzerda ${r.site.replace('https://', '')} ni oching`), el('div', {}, "2. «Darslik bilan ulash» ga yuqoridagi kodni kiriting")),
      el('button', { class: 'cta ghost', onclick: close }, 'Yopish'));
    document.body.append(bg, sheet);
  }

  /* ---------- dars sahifasi ---------- */
  async function openLesson(n) {
    app.replaceChildren(el('div', { class: 'skeleton' }), el('div', { class: 'skeleton' }), el('div', { class: 'skeleton' }));
    if (tg) { tg.BackButton.show(); }
    try { lesson = await api(`/lesson/?student=${student().id}&n=${n}`); } catch (e) {
      if (e.status === 403) { toast(e.message); return go('#/'); }
      return fatal(e.message);
    }
    tab = lesson.progress && (lesson.progress.pending || lesson.progress.homework.pending) ? 'results' : 'theory';
    drawLesson();
    window.scrollTo(0, 0);
    const waiting = [...lesson.submissions, ...lesson.homework.submissions].find((x) => x.pending);
    if (waiting) watch(waiting);
  }

  function videoPlayer(v) {
    if (!v) return null;
    if (v.kind === 'embed') return el('div', { class: 'video' }, el('iframe', { src: v.src, allow: 'fullscreen; picture-in-picture; encrypted-media', allowfullscreen: true, loading: 'lazy', title: 'Videodars',
      referrerpolicy: 'strict-origin-when-cross-origin' }));
    if (v.kind === 'file') return el('div', { class: 'video' }, el('video', { src: v.src, controls: true, playsinline: true, preload: 'metadata' }));
    return el('a', { class: 'btn-link', href: v.url, target: '_blank', rel: 'noopener', onclick: (e) => { if (tg && tg.openLink) { e.preventDefault(); tg.openLink(v.url); } } }, "🔗 Qo'shimcha material");
  }

  function prose(text) {
    const box = el('div', { class: 'prose' });
    let ul = null;
    String(text || '').split('\n').map((x) => x.trim()).filter(Boolean).forEach((line, i) => {
      if (/^[-•]\s+/.test(line)) { if (!ul) { ul = el('ul'); box.append(ul); } ul.append(el('li', {}, line.replace(/^[-•]\s+/, ''))); return; }
      ul = null;
      box.append(el('p', { class: i === 0 ? 'lead' : '' }, line));
    });
    return box.children.length ? box : el('p', { class: 'muted' }, "Hozircha mazmun kiritilmagan.");
  }

  function steps(text) {
    const lines = String(text || '').split('\n').map((x) => x.trim()).filter(Boolean);
    if (!lines.length) return el('p', { class: 'muted' }, "Topshiriq hali kiritilmagan.");
    const numbered = lines.every((l) => /^\d+[.)]\s+/.test(l));
    if (!numbered) return prose(text);
    const box = el('div', { class: 'steps' });
    lines.forEach((l, i) => box.append(el('div', { class: 'step' }, el('i', {}, i + 1), el('div', {}, l.replace(/^\d+[.)]\s+/, '')))));
    return box;
  }

  function drawLesson() {
    const L = lesson;
    const p = L.progress;
    const st = student();
    app.replaceChildren();
    const root = el('div', { class: 'fade split' });
    const side = el('div', { class: 'side' });
    const main = el('div', { class: 'main' });
    root.append(side, main);
    app.append(root);
    side.append(el('div', { class: 'top' }, el('button', { class: 'back', onclick: () => go('#/') }, '‹'), el('div', { class: 'muted small' }, st.course)));
    const badge = p.passed ? el('span', { class: 'pill ok' }, `✓ O'tdi · ${p.best}`) : p.pending ? el('span', { class: 'pill' }, '⏳ Tekshirilmoqda') : p.attempts > 0 ? el('span', { class: 'pill warn' }, `${p.best ?? 0} ball · qayta urinish`) : el('span', { class: 'pill' }, 'Yangi dars');
    side.append(el('div', { class: 'lhero', 'data-n': L.number }, el('small', {}, `${L.number}-dars`), el('h2', {}, L.title), el('div', { class: 'chips' }, badge, el('span', { class: 'pill' }, `${p.attempts}/${p.max_attempts} urinish`))));

    const tabs = el('div', { class: 'tabs' }, [['theory', '📖 Nazariya'], ['task', '🛠 Amaliyot'], ['hw', '🏠 Uy vazifasi'], ['results', `🏆 Natijalar${L.submissions.length + L.homework.submissions.length ? ' · ' + (L.submissions.length + L.homework.submissions.length) : ''}`]].map(([k, label]) => el('button', { class: tab === k ? 'on' : '', onclick: () => { tab = k; haptic(); drawLesson(); } }, label)));
    side.append(tabs);

    if (tab === 'theory') {
      const vp = videoPlayer(L.video);
      if (vp) main.append(el('div', { class: 'card video-card' }, el('h3', { class: 'v-title' }, '🎬 Videodars'), vp));
      main.append(el('div', { class: 'card' }, prose(L.summary)));
    } else if (tab === 'task') {
      main.append(el('div', { class: 'card' }, steps(L.practice)), el('div', { class: 'card muted small' }, "Ishingizni matn, rasm (skrinshot), PDF, Word (.docx) yoki Excel (.xlsx) ko'rinishida yuboring. AI ishni tekshirib, 100 ballik tizimda baholaydi. 60 va undan yuqori ball — o'tdi."));
    } else if (tab === 'hw') {
      main.append(L.homework.text ? el('div', { class: 'card' }, steps(L.homework.text)) : el('div', { class: 'card empty' }, el('span', { class: 'big' }, '🏠'), "Bu dars uchun uy vazifasi berilmagan."),
        el('div', { class: 'card muted small' }, "Uy vazifasini ham AI tekshiradi: 80 ball vazifa mazmuniga, 20 ball Codial Yoz mashqiga (10 daqiqa va undan ko'p — to'liq ball). Yozish mashqi tizimdan avtomatik hisoblanadi."));
    } else {
      if (!L.submissions.length && !L.homework.submissions.length) main.append(el('div', { class: 'card empty' }, el('span', { class: 'big' }, '📝'), "Hali vazifa topshirilmagan."));
      if (L.submissions.length) { main.append(el('div', { class: 'section-title' }, 'Amaliyot')); L.submissions.forEach((s) => main.append(attemptCard(s))); }
      if (L.homework.submissions.length) { main.append(el('div', { class: 'section-title' }, 'Uy vazifasi')); L.homework.submissions.forEach((s) => main.append(attemptCard(s))); }
    }

    const bar = el('div', { class: 'bar' }, el('div', { class: 'bar-in' }));
    const inner = bar.firstChild;
    const hw = tab === 'hw';
    const ps = hw ? p.homework : p;
    const can = hw ? L.homework.can_submit : L.can_submit;
    if (hw && !L.homework.text) inner.append(el('div', { class: 'note-bar' }, 'Uy vazifasi berilmagan'));
    else if (L.role !== 'Talaba') inner.append(el('div', { class: 'note-bar' }, "👪 Vazifani o'quvchining o'zi topshiradi"));
    else if (ps.pending) inner.append(el('div', { class: 'note-bar' }, '⏳ AI vazifangizni tekshirmoqda…'));
    else if (can) inner.append(el('button', { class: 'cta', onclick: () => { haptic(); openSheet(hw ? 'homework' : 'practice'); } }, (hw ? ps.attempts : p.attempts) > 0 ? '🔄 Qayta topshirish' : (hw ? '🏠 Uy vazifasini topshirish' : '📤 Vazifani topshirish')));
    else if (ps.passed) inner.append(el('div', { class: 'note-bar' }, hw ? '✅ Uy vazifasi topshirilgan' : '✅ Bu dars muvaffaqiyatli topshirilgan'));
    else inner.append(el('div', { class: 'note-bar' }, 'Urinishlar tugadi — ustozingizga murojaat qiling'));
    app.append(bar);
  }

  function attemptCard(s) {
    const score = s.final_score;
    const body = el('div', { class: 'info' }, el('h3', {}, `${s.attempt}-urinish`), el('div', { class: 'when' }, `${fdate(s.submitted_at)} · ${s.kind}${s.file_name ? ' · ' + s.file_name : ''}`));
    if (s.pending) body.append(el('div', { class: 'muted' }, '⏳ Tekshirilmoqda…'));
    if (s.strengths) body.append(el('div', { class: 'fb good' }, el('b', {}, '✅ Yutuqlar'), s.strengths));
    if (s.mistakes && !/jiddiy kamchilik yo'q/i.test(s.mistakes)) body.append(el('div', { class: 'fb bad' }, el('b', {}, '⚠️ Kamchiliklar'), s.mistakes));
    if (s.advice) body.append(el('div', { class: 'fb tip' }, el('b', {}, '💡 Maslahat'), s.advice));
    if (s.teacher_score !== null) body.append(el('div', { class: 'fb' }, el('b', {}, `👨‍🏫 Ustoz bahosi: ${s.teacher_score}`), s.teacher_comment || ''));
    const left = score === null || score === undefined ? el('div', { class: 'ring-box', style: 'width:64px' }) : ring(score / 100, 64, 7, scoreColor(score), score);
    return el('div', { class: 'card attempt' }, left, body);
  }

  /* ---------- topshirish oynasi ---------- */
  function openSheet(task) {
    let file = null;
    const bg = el('div', { class: 'sheet-bg' });
    const sheet = el('div', { class: 'sheet' });
    const close = () => { bg.remove(); sheet.remove(); };
    bg.onclick = close;
    const ta = el('textarea', { placeholder: "Javobingizni yozing (ixtiyoriy, agar fayl biriktirsangiz)…", maxlength: 4000 });
    const fileBox = el('div');
    const err = el('div', { class: 'err' });
    const send = el('button', { class: 'cta', style: 'margin-top:14px' }, '🚀 Yuborish');
    const paintFile = () => {
      fileBox.replaceChildren();
      if (!file) return;
      const isImg = file.type.startsWith('image/');
      const thumb = isImg ? el('img', { src: URL.createObjectURL(file), alt: '' }) : el('div', { class: 'ic' }, /pdf/i.test(file.name) ? '📕' : /xls/i.test(file.name) ? '📗' : '📘');
      fileBox.append(el('div', { class: 'file' }, thumb, el('div', { class: 'nm' }, file.name), el('button', { onclick: () => { file = null; paintFile(); } }, '✕')));
    };
    const picker = (label, icon, accept, capture) => {
      const inp = el('input', { type: 'file', accept, capture });
      inp.onchange = () => { if (inp.files[0]) { file = inp.files[0]; err.textContent = ''; paintFile(); } };
      return el('label', {}, el('span', {}, icon), label, inp);
    };
    sheet.append(el('div', { class: 'grab' }), el('h3', {}, `${lesson.number}-dars ${task === 'homework' ? 'uy vazifasi' : 'vazifasi'}`), el('div', { class: 'muted small' }, "Rasm, PDF, Word yoki Excel yuboring — yoki shunchaki yozing."),
      ta, el('div', { class: 'pick' }, picker('Rasm / skrinshot', '🖼', 'image/*'), picker('Fayl (PDF, Word, Excel)', '📎', '.pdf,.docx,.xlsx,application/pdf')), fileBox, err, send);
    send.onclick = async () => {
      if (!ta.value.trim() && !file) { err.textContent = 'Matn yozing yoki fayl biriktiring'; haptic('bad'); return; }
      if (file && file.size > 8 * 1024 * 1024) { err.textContent = 'Fayl hajmi 8 MB dan oshmasin'; return; }
      send.disabled = true; send.textContent = 'Yuborilmoqda…';
      const fd = new FormData();
      fd.append('student', student().id); fd.append('lesson', lesson.number); fd.append('task', task); fd.append('text', ta.value.trim());
      if (file) fd.append('file', file);
      try {
        const s = await api('/submit/', { method: 'POST', body: fd });
        close(); haptic('ok');
        processing(s);
      } catch (e) { err.textContent = e.message; send.disabled = false; send.textContent = '🚀 Yuborish'; haptic('bad'); }
    };
    document.body.append(bg, sheet);
  }

  /* ---------- AI baholayotgan payt va natija ---------- */
  function processing(sub) {
    if (tg) tg.BackButton.hide();
    app.replaceChildren();
    const msgs = ['Ishingiz qabul qilindi', 'AI ishni o\'qiyapti', 'Mezonlar bo\'yicha tekshirilmoqda', 'Ball hisoblanmoqda'];
    const list = el('div', { class: 'steps-live' }, msgs.map((m) => el('div', {}, '• ' + m)));
    app.append(el('div', { class: 'center fade' }, el('div', { class: 'orbit' }, el('i'), el('i'), el('i'), el('b', {}, '🤖')), el('h2', {}, 'AI tekshirmoqda…'), el('p', { class: 'muted small' }, 'Odatda 10–30 soniya oladi'), list));
    let i = 0;
    const tick = setInterval(() => { list.children[Math.min(i, msgs.length - 1)].classList.add('on'); i++; }, 1800);
    watch(sub, () => clearInterval(tick));
  }

  async function watch(sub, done) {
    const started = Date.now();
    while (Date.now() - started < 4 * 60 * 1000) {
      await new Promise((r) => setTimeout(r, 2500));
      if (!location.hash.startsWith('#/lesson') && !app.querySelector('.orbit')) return; // foydalanuvchi boshqa joyga o'tdi
      let s;
      try { s = await api(`/submission/${sub.id}/`); } catch (e) { continue; }
      if (!s.pending) { done && done(); return result(s); }
    }
    done && done();
    toast("Tekshirish kechikmoqda. Birozdan keyin 'Natijalar' bo'limini oching");
    nav('#/lesson/' + lesson.number);
  }

  async function result(s) {
    const score = s.final_score ?? 0;
    const ok = s.passed;
    haptic(ok ? 'ok' : 'bad');
    if (ok) confetti();
    app.replaceChildren();
    const wrap = el('div', { class: 'fade narrow' });
    const body = el('div', { class: 'card result' },
      el('div', { class: 'ring-wrap' }, ring(score / 100, 150, 14, scoreColor(score), score, '/ 100')),
      el('h2', {}, ok ? "🎉 Tabriklaymiz, o'tdingiz!" : 'Yana bir urinib ko\'ring 💪'),
      el('p', { class: 'muted' }, ok ? `${lesson.number}-dars vazifasi qabul qilindi` : `Urinish ${s.attempt}/${s.max_attempts}. Quyidagi maslahatlarga amal qiling.`));
    wrap.append(body);
    if (s.strengths) wrap.append(el('div', { class: 'card' }, el('div', { class: 'fb good', style: 'margin:0' }, el('b', {}, '✅ Yutuqlar'), s.strengths)));
    if (s.mistakes && !/jiddiy kamchilik yo'q/i.test(s.mistakes)) wrap.append(el('div', { class: 'card' }, el('div', { class: 'fb bad', style: 'margin:0' }, el('b', {}, '⚠️ Kamchiliklar'), s.mistakes)));
    if (s.advice) wrap.append(el('div', { class: 'card' }, el('div', { class: 'fb tip', style: 'margin:0' }, el('b', {}, '💡 Maslahat'), s.advice)));
    const bar = el('div', { class: 'bar' }, el('div', { class: 'bar-in narrow' }));
    bar.firstChild.append(el('button', { class: 'cta', onclick: async () => { await refresh(); nav('#/lesson/' + lesson.number); } }, 'Darsga qaytish'),
      el('button', { class: 'cta ghost', onclick: async () => { await refresh(); nav('#/'); } }, '📚 Barcha darslar'));
    app.append(wrap, bar);
    window.scrollTo(0, 0);
  }

  async function refresh() {
    try { const keep = student().id; state = await api('/state/'); cur = Math.max(0, state.students.findIndex((x) => x.id === keep)); } catch (e) { /* eski holat qoladi */ }
  }

  function fatal(msg) {
    if (tg) tg.BackButton.hide();
    app.replaceChildren(el('div', { class: 'center fade' }, el('div', { class: 'big', style: 'font-size:54px' }, '🔌'), el('h2', {}, 'Ochib bo\'lmadi'), el('p', { class: 'muted', style: 'margin:8px 0 18px' }, msg), el('button', { class: 'cta', style: 'max-width:260px', onclick: () => location.reload() }, 'Qayta urinish')));
  }

  /* ---------- marshrut ---------- */
  function route() {
    if (!state) return;
    const m = location.hash.match(/^#\/lesson\/(\d+)/);
    if (m) openLesson(Number(m[1]));
    else home();
    window.scrollTo(0, 0);
  }

  /* Telegram Desktop mini ilovani kichik oynada ochadi; to'liq ekran so'raladi (Bot API 8.0+). Telefonda kerak emas. */
  function fullscreenSetup() {
    const desktop = tg && !['android', 'ios'].includes(tg.platform);
    if (!desktop || typeof tg.requestFullscreen !== 'function' || !(tg.isVersionAtLeast && tg.isVersionAtLeast('8.0'))) return;
    const btn = el('button', { class: 'fs-btn', 'aria-label': 'Kattalashtirish', onclick: () => { try { if (tg.isFullscreen) tg.exitFullscreen(); else tg.requestFullscreen(); } catch (e) { /* qo'llanmaydi */ } } }, '⛶');
    const sync = () => { btn.textContent = tg.isFullscreen ? '🗗' : '⛶'; try { localStorage.setItem('learn-fs', tg.isFullscreen ? '1' : '0'); } catch (e) { /* ixtiyoriy */ } };
    tg.onEvent('fullscreenChanged', sync);
    tg.onEvent('fullscreenFailed', () => toast("To'liq ekran ishlamadi. Telegram'ni yangilang"));
    document.body.append(btn);
    let pref = null;
    try { pref = localStorage.getItem('learn-fs'); } catch (e) { /* ixtiyoriy */ }
    if (pref !== '0') { try { tg.requestFullscreen(); } catch (e) { /* qo'llanmaydi */ } } // standart: kompyuterda kattalashtirib ochiladi
  }

  async function boot() {
    if (tg) {
      tg.ready(); tg.expand(); fullscreenSetup();
      try { tg.setHeaderColor('#0f1b3d'); } catch (e) { /* eski versiya */ }
      if (tg.colorScheme === 'dark') document.documentElement.setAttribute('data-dark', '');
      tg.BackButton.onClick(() => go('#/'));
    }
    if (!tg || !tg.initData) return fatal("Bu ilovani Telegram botidagi «📚 Darslik» tugmasi orqali oching.");
    app.append(el('div', { class: 'skeleton', style: 'height:190px;border-radius:24px' }), el('div', { class: 'skeleton' }), el('div', { class: 'skeleton' }), el('div', { class: 'skeleton' }));
    try { state = await api('/state/'); } catch (e) { return fatal(e.message); }
    if (!state.students.length) return fatal("Botga ulangan talaba topilmadi.");
    window.addEventListener('hashchange', route);
    route();
  }
  boot();
})();

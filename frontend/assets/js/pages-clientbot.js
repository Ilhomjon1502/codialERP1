/* Codial ERP — Mijozlar boti (2026-10-24): o'quvchi va vasiylar Telegram boti. «Qo'ng'iroqlar va SMS» sahifasidagi «Telegram bot» tabi:
   umumiy ko'rsatkichlar, ulanganlar, ulanmagan kodlar, manba javoblari, tavsiyalar, sozlamalar.
   Server: /bot-links/ (+summary), /bot-invites/, /bot-surveys/, /bot-referrals/, /bot-config/. pages-calls.js ichidan chaqiriladi. */
(function (A) {
  const esc = A.esc;
  const BK = 'bot';
  const SUBS = [['overview', 'Umumiy'], ['links', 'Ulanganlar'], ['students', 'Talabalar'], ['surveys', 'Manba javoblari'], ['referrals', 'Tavsiyalar'], ['exits', "Ketish so'rovnomasi"], ['questions', 'Savollar'], ['quiz', 'Kurs testi'], ['quizq', 'Test savollari'], ['subs', 'Darslik: vazifalar'], ['lessons', 'Darslik: mavzular'], ['messages', 'Xabarlar'], ['config', 'Sozlamalar']];
  const REF_TONE = { Aniqlanmagan: 'orange', Kutilmoqda: 'blue', Berildi: 'green', 'Rad etildi': 'gray' };
  const fphone = (p) => (p ? `+998 ${p.slice(0, 2)} ${p.slice(2, 5)}-${p.slice(5, 7)}-${p.slice(7)}` : '');
  const fail = (e) => A.toast(e.message || 'Xatolik', 'error');

  let sum = null;
  let links = { results: [] };
  let studs = { results: [] };
  let surveys = { results: [] };
  let refs = { results: [] };
  let msgs = { results: [] };
  let exits = { results: [] };
  let exitStats = null;
  let questions = [];
  let config = [];
  let quizzes = { results: [] };
  let quizStats = null;
  let quizQs = [];
  let subsList = { results: [] };
  let lessonsList = [];

  const sub = (q) => (SUBS.some(([k]) => k === q.sub) ? q.sub : 'overview');
  const qs = (extra = {}, keys = ['search']) => {
    const p = new URLSearchParams({ page: A.q(`${BK}:page`, 1), ...extra });
    for (const k of keys) {
      const v = A.q(`${BK}:${k}`, '');
      if (v) p.set(k === 'search' ? 'q' : k, v);
    }
    return p;
  };

  A.botTab = {
    async load(q) {
      const s = sub(q);
      if (s === 'overview') sum = await A.http.get('/bot-links/summary/');
      else if (s === 'links') links = await A.http.get('/bot-links/?' + qs({}, ['search', 'role', 'active']));
      else if (s === 'students') studs = await A.http.get('/bot-students/?' + qs({}, ['search', 'linked']));
      else if (s === 'surveys') surveys = await A.http.get('/bot-surveys/?' + qs({}, ['search', 'differs']));
      else if (s === 'referrals') refs = await A.http.get('/bot-referrals/?' + qs({}, ['search', 'state']));
      else if (s === 'exits') [exits, exitStats] = await Promise.all([A.http.get('/bot-exit-surveys/?' + qs({}, ['search', 'state', 'flow'])), A.http.get('/bot-exit-surveys/stats/')]);
      else if (s === 'questions') questions = await A.http.get('/bot-questions/');
      else if (s === 'quiz') [quizzes, quizStats] = await Promise.all([A.http.get('/bot-quiz-attempts/?' + qs({}, ['search', 'state', 'passed'])), A.http.get('/bot-quiz-attempts/stats/')]);
      else if (s === 'quizq') quizQs = await A.http.get('/bot-quiz-questions/');
      else if (s === 'subs') subsList = await A.http.get('/bot-lesson-submissions/?' + qs({}, ['search', 'status', 'lesson']));
      else if (s === 'lessons') {
        const c = A.vis('courses').find((x) => /savodxon/i.test(x.name));
        lessonsList = c ? await A.http.get('/bot-textbook-lessons/?course=' + c.id) : [];
      }
      else if (s === 'messages') msgs = await A.http.get('/bot-messages/?' + qs({}, ['search', 'status']));
      else config = await A.http.get('/bot-config/');
    },
    filters(q) {
      const s = sub(q);
      if (s === 'links') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki @username…'), A.fSelect(BK, 'role', [['Talaba', "O'quvchining o'zi"], ['Vasiy', 'Vasiy']], 'Hamma'),
        A.fSelect(BK, 'active', [['1', 'Faol'], ['0', 'Uzilgan']], 'Faol va uzilgan')]);
      if (s === 'students') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'linked', [['0', 'Ulanmaganlar'], ['1', 'Ulanganlar']], 'Hammasi')]);
      if (s === 'surveys') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'differs', [['1', 'Admin manbasidan farq qiladi']], 'Hammasi')]);
      if (s === 'referrals') return A.filterBar(BK, [A.fSearch(BK, 'Lid yoki yozilgan ism…'), A.fSelect(BK, 'state', Object.keys(REF_TONE).map((k) => [k, k]), 'Barcha holatlar')]);
      if (s === 'exits') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'state', [['Tugadi', 'Javob bergan'], ['Jarayonda', 'Jarayonda'], ['Yuborildi', 'Javob bermagan']], 'Barcha holatlar'),
        A.fSelect(BK, 'flow', [['Tamomlaganlarga', 'Tamomlaganlar'], ["To'xtatganlarga", "To'xtatganlar"]], 'Hamma')]);
      if (s === 'quiz') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'state', [['Tugadi', 'Topshirgan'], ['Jarayonda', 'Jarayonda'], ['Yuborildi', 'Boshlamagan'], ['Bekor qilindi', 'Bekor qilingan']], 'Barcha holatlar'),
        A.fSelect(BK, 'passed', [['1', "O'tgan"], ['0', "O'tmagan"]], 'Hammasi')]);
      if (s === 'subs') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'status', [['Tekshirildi', 'Tekshirildi'], ['Qayta topshirish', 'Qayta topshirish'], ['Kutilmoqda', 'Kutilmoqda']], 'Barcha holatlar'),
        A.fSelect(BK, 'lesson', Array.from({ length: 12 }, (_, i) => [String(i + 1), `${i + 1}-dars`]), 'Barcha darslar')]);
      if (s === 'messages') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki matn…'), A.fSelect(BK, 'status', [['sent', 'Yuborildi'], ['pending', 'Navbatda'], ['failed', 'Xato']], 'Barcha holatlar')]);
      return '';
    },
    view(q) {
      const s = sub(q);
      const nav = `<nav class="tabs sub">${SUBS.map(([k, l]) => `<a href="#/calls?tab=bot&sub=${k}" class="${k === s ? 'on' : ''}">${esc(l)}</a>`).join('')}</nav>`;
      const body = { overview, links: linksView, students: studentsView, surveys: surveysView, referrals: refsView, exits: exitsView, questions: questionsView, quiz: quizView, quizq: quizQuestionsView, subs: subsView, lessons: lessonsView, messages: messagesView, config: configView }[s]();
      return `${nav}${A.botTab.filters(q)}${body}`;
    },
  };

  function overview() {
    const s = sum;
    if (!s) return '';
    const warn = s.configured ? '' : `<div class="alert warn">${A.icon('alert')}<div>Bot hali ulanmagan. @BotFather'da bot yarating va serverda <code>bash /srv/codial-test/deploy/set-clientbot.sh</code> ni ishga tushiring — shundan keyin lid va shartnoma SMS'lariga havola qo'shiladi.</div></div>`;
    const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');
    const r = s.referrals;
    const cards = `<div class="stats">
      ${A.stat('Ulangan talabalar', A.num(s.linked_students), `o'quvchi ${A.num(s.students)} · vasiy ${A.num(s.guardians)} · akkaunt ${A.num(s.accounts)}`, '', '#/calls?tab=bot&sub=links')}
      ${A.stat('Yuborilgan kodlar', A.num(s.invites), `${A.num(s.invited_students)} ta talaba · ulangan ${pct(s.linked_invites, s.invites)}`)}
      ${A.stat('Faol talabalar ulangan', `${A.num(s.active_linked)} / ${A.num(s.active_students)}`, `${pct(s.active_linked, s.active_students)} · hali ulanmagan: ${A.num(s.active_students - s.active_linked)}`, s.active_students > s.active_linked ? 'warn' : '', '#/calls?tab=bot&sub=students')}
      ${A.stat('Ulanmagan kodlar', A.num(s.unlinked_invites), 'SMS borgan, lekin bot ochilmagan')}
      ${A.stat('Manba javoblari', A.num(s.surveys), `admin manbasidan farqi: ${A.num(s.surveys - s.surveys_same)}`, '', '#/calls?tab=bot&sub=surveys')}
      ${A.stat('Tavsiyalar', A.num(Object.values(r).reduce((a, b) => a + b, 0)), `aniqlanmagan: ${A.num(r.Aniqlanmagan)} · kutilmoqda: ${A.num(r.Kutilmoqda)}`, r.Aniqlanmagan ? 'warn' : '', '#/calls?tab=bot&sub=referrals')}
      ${A.stat('Bot orqali yuborilgan', A.num(s.messages_sent), `oxirgi 30 kunda: ${A.num(s.messages_sent_30d)} · SMS o'rniga`, '', '#/calls?tab=bot&sub=messages')}
      ${A.stat('Xabarlar navbati', A.num(s.outbox_pending), `xato: ${A.num(s.outbox_failed)}`, s.outbox_failed ? 'danger' : '')}
    </div>`;
    const sources = A.table([{ h: 'Mijoz aytgan manba', f: (x) => esc(x.name) }, { h: 'Javoblar', cls: 'num', f: (x) => A.num(x.count) }], s.survey_sources, { empty: "Hali javob yo'q" });
    const kinds = A.table([{ h: 'Bot orqali yuborilgan xabar turi', f: (x) => esc(x.kind) }, { h: 'Soni', cls: 'num', f: (x) => A.num(x.count) }], s.messages_by_kind, { empty: "Hali xabar yuborilmagan" });
    return `${warn}${cards}
      <div class="card"><h3>SMS o'rniga botga ketgan xabarlar</h3>
        <p class="muted small">Raqam botga ulangan bo'lsa, avtomatik SMS'lar va «To'lovga tavsiya» eslatmasi SMS o'rniga botga boradi (bepul, yetkazilishi aniq). Ulanmagan raqamlarga SMS ketadi va oxirida bot havolasi bo'ladi.</p>${kinds}</div>
      <div class="card"><h3>Mijoz botda aytgan reklama manbasi</h3>
        <p class="muted small">Lid botga ulanganda «Codialni qayerdan topdingiz?» deb so'raladi. Bu administrator lid kartochkasiga kiritgan manbani o'zgartirmaydi — ikkalasi alohida saqlanadi va «Manba javoblari»da solishtiriladi.</p>${sources}</div>
      <div class="note info small">Ulanish jarayoni: yangi lid yoki shartnoma SMS'iga har raqam uchun alohida kod/havola qo'shiladi (<a href="#/calls?tab=bot&sub=config">sozlamada</a> o'chirish mumkin; avtomatik SMS qoidasi yoqilgan bo'lishi kerak).
        Bot: ${s.username ? `<b>@${esc(s.username)}</b>` : '—'}.<br>
        <b>SMS kelmasa:</b> talabaga botni topib <b>shartnoma raqamini</b> (shartnoma sahifasidagi №) yuborishni ayting — bot shartnomadagi telefonlardan birining oxirgi 4 raqamini so'raydi va ulaydi.</div>`;
  }

  function linksView() {
    return A.table([
      { h: 'Talaba', f: (l) => esc(l.student_name) },
      { h: 'Kim', f: (l) => `${A.badge(l.role || 'Tanlanmagan', l.role === 'Vasiy' ? 'blue' : l.role ? 'green' : 'gray')}${l.parent_name ? `<br><small class="muted">${esc(l.parent_name)}</small>` : ''}` },
      { h: 'Raqam', f: (l) => fphone(l.phone) },
      { h: 'Telegram', f: (l) => `${esc(l.telegram_name)}${l.username ? ` <small class="muted">@${esc(l.username)}</small>` : ''}${l.blocked ? ' ' + A.badge('Botni bloklagan', 'red') : ''}` },
      { h: 'Ulangan', f: (l) => `${A.fdt(l.linked_at)}${l.is_active ? '' : ' ' + A.badge('Uzilgan', 'gray')}` },
    ], links.results, { empty: "Hali hech kim ulanmagan" }) + A.pager(BK, links);
  }

  function studentsView() {
    const canE = A.can('clientbot', 'e');
    const state = (st) => (st.linked ? `${A.badge('Ulangan', 'green')} <small class="muted">${st.linked_roles.map(esc).join(', ')}</small>`
      : st.invited_at ? `${A.badge('Taklif yuborilgan', 'orange')} <small class="muted">${A.fdt(st.invited_at)}</small>` : A.badge('Taklif yuborilmagan', 'gray'));
    const intro = `<div class="row gap" style="margin:8px 0;align-items:center">${canE ? A.btn('Mavjud talabalarni taklif qilish', 'bot-invite-all', { icon: 'plus' }) : ''}
      <span class="muted small">Faol shartnomali talabalarning ulanmagan raqamlariga bot havolali SMS yuboradi (avval hisob ko'rsatiladi, siz tasdiqlaysiz). Ulanmagan talabaga shartnoma raqamini aytsangiz ham bo'ladi.</span></div>`;
    return intro + A.table([
      { h: 'Talaba', f: (st) => `${esc(st.full_name)}<br><small class="muted">${st.contracts_info.map(esc).join(', ')}</small>` },
      { h: 'Raqamlar', f: (st) => st.phones.map((p) => `${esc(p.who)}: ${fphone(p.phone)}`).join('<br>') },
      { h: 'Bot', f: state },
    ], studs.results, { empty: "Faol shartnomali talaba yo'q" }) + A.pager(BK, studs);
  }

  A.act['bot-invite-all'] = () => {
    const DEFAULT = "Codial o'quv markazining Telegram boti ishga tushdi: to'lov, davomat va dars jadvalingizni shu yerda ko'rasiz. Ulaning:";
    A.form({
      title: 'Mavjud talabalarni botga taklif qilish',
      submit: 'Davom etish',
      values: { text: DEFAULT },
      fields: [
        { name: 'note', type: 'note', text: () => "Faol shartnomali talabalarning <b>hamma ulanmagan raqamiga</b> (1-, 2-telefon, vasiy) SMS ketadi. Oxiriga har raqamga xos bot havolasi va kodi avtomatik qo'shiladi." },
        { name: 'text', label: 'Matn', type: 'textarea', required: true },
        { name: 'count', type: 'computed', label: '', compute: (x) => `${A.smsPlain ? `${(A.smsParts(A.smsPlain((x.text || '') + ' Telegram bot: t.me/xxxxxxxxxxxxxxxxxxxxxxxxxxxx?start=XXXXXXXX'))).parts} SMS (havola bilan)` : ''}<br><span class="small">O'rinbosarlar: <code>{ism}</code> talabaning ismi, <code>{talaba}</code> ism-familiya</span>` },
      ],
      async onSubmit(x) {
        const pv = await A.http.post('/bot-students/invite/', { text: x.text, preview: true });
        const notes = [
          pv.skipped_linked ? `${pv.skipped_linked} ta raqam allaqachon ulangan — yuborilmaydi` : '',
          pv.skipped_sent ? `${pv.skipped_sent} ta raqamga taklif avval yuborilgan — o'tkazib yuboriladi` : '',
          pv.no_phone ? `${pv.no_phone} ta talabada telefon yo'q` : '',
          pv.no_device.length ? `<b class="t-red">${pv.no_device.map(esc).join(', ')} filialida ulangan telefon yo'q</b>` : '',
        ].filter(Boolean);
        if (!pv.messages) return `Yuboriladigan SMS yo'q. ${notes.join('. ').replace(/<[^>]+>/g, '')}`;
        const ok = await A.confirm(`<b>${pv.students}</b> ta talaba, <b>${pv.messages}</b> ta raqamga SMS, jami taxminan <b>${pv.parts}</b> SMS (SIM tarifidan).
          ${notes.length ? `<br><small class="muted">${notes.join('<br>')}</small>` : ''}<br><br><i>${esc(pv.sample)}</i><br><br>Yuborilsinmi?`, 'Yuborish');
        if (!ok) return '';
        const r = await A.http.post('/bot-students/invite/', { text: x.text });
        A.toast(`Navbatga qo'yildi: ${r.messages} ta SMS. Telefon bir necha daqiqada yuboradi`);
        A.refresh();
      },
    });
  };

  function surveysView() {
    return A.table([
      { h: 'Lid', f: (s) => `<a href="#" data-act="lead-open" data-id="${s.lead}">${esc(s.student_name)}</a><br><small class="muted">${esc(s.course)}</small>` },
      { h: 'Mijoz aytgan manba', f: (s) => `<b>${esc(s.source_name)}</b>${s.referrer ? `<br><small class="muted">tavsiya: ${esc(s.referrer)}</small>` : ''}` },
      { h: 'Administrator kiritgan', f: (s) => `${esc(s.lead_source)}${s.source_name && s.source_name !== s.lead_source ? ' ' + A.badge('farq qiladi', 'orange') : ''}` },
      { h: 'Javob vaqti', f: (s) => A.fdt(s.answered_at) },
    ], surveys.results, { empty: "Hali javob yo'q" }) + A.pager(BK, surveys);
  }

  function refsView() {
    const canE = A.can('clientbot', 'e');
    return `<p class="muted small">Lid «tanishimdan eshitdim» degan bo'lsa shu yerga tushadi. Lid o'qishni boshlab to'lov qilganda (to'lovlari yig'indisi oy narxining belgilangan foizidan kam bo'lmasa) tavsiya qiluvchiga <b>bonus avtomatik beriladi</b>: uning shartnomasiga «Tavsiya bonusi» chegirmasi yoziladi va keyingi to'lovdan ayriladi, botda xabar boradi. «Aniqlanmagan» ismni talabaga bog'lang — lid allaqachon to'lov qilgan bo'lsa, bonus darrov beriladi.</p>` + A.table([
      { h: 'Lid', f: (r) => `<a href="#" data-act="lead-open" data-id="${r.lead}">${esc(r.lead_student)}</a><br><small class="muted">${A.fdt(r.created_at)}</small>` },
      { h: 'Kim tavsiya qilgan', f: (r) => (r.referrer_name ? `<b>${esc(r.referrer_name)}</b>${r.referrer_text ? `<br><small class="muted">yozilgan: ${esc(r.referrer_text)}</small>` : ''}` : `<span class="muted">yozilgan:</span> ${esc(r.referrer_text)}`) },
      { h: 'Holat', f: (r) => `${A.badge(r.state, REF_TONE[r.state])}${r.bonus ? `<br><small class="muted">bonus ${A.money(r.bonus)}${r.paid_at ? ' · ' + A.fdt(r.paid_at) : ''}</small>` : ''}${r.comment ? `<br><small class="t-red">${esc(r.comment)}</small>` : ''}` },
      { h: '', f: (r) => (canE && r.state !== 'Berildi' ? `<button class="btn sm ghost" data-act="ref-bind" data-id="${r.id}">${r.referrer_name ? "O'zgartirish" : 'Talabaga bog\'lash'}</button>${r.state !== 'Rad etildi' ? `<button class="btn sm ghost" data-act="ref-reject" data-id="${r.id}">Rad etish</button>` : ''}` : '') },
    ], refs.results, { empty: "Tavsiya yo'q" }) + A.pager(BK, refs);
  }

  A.act['ref-bind'] = (el) => {
    const r = refs.results.find((x) => String(x.id) === el.dataset.id);
    A.form({
      title: `Kim tavsiya qilgan: ${r.lead_student}`,
      values: { referrer_student: r.referrer_student || '' },
      fields: [
        { name: 'note', type: 'note', text: () => `Lid yozgan ism: <b>${esc(r.referrer_text || '—')}</b>` },
        { name: 'referrer_student', label: 'Talaba', type: 'combo', required: true, placeholder: 'Ismini yozing…',
          options: () => (r.referrer_student ? [[r.referrer_student, r.referrer_name]] : []),
          search: async (t) => (await A.http.get('/students/?page_size=20&search=' + encodeURIComponent(t))).results.map((s) => [s.id, s.full_name]) },
      ],
      async onSubmit(x) {
        await A.http.patch(`/bot-referrals/${r.id}/`, { referrer_student: x.referrer_student });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['ref-reject'] = async (el) => {
    if (!(await A.confirm("Bu tavsiya rad etilsinmi? Bonus berilmaydi.", 'Rad etish', true))) return;
    A.http.patch(`/bot-referrals/${el.dataset.id}/`, { state: 'Rad etildi' }).then(() => { A.toast('Rad etildi'); A.refresh(); }, fail);
  };

  /* ---------- Ketish so'rovnomasi (B4): shartnomasi tugagan talabaga ertasi 10:00 da yuboriladi ---------- */
  function exitsView() {
    const st = exitStats;
    const cards = st ? `<div class="stats">
      ${A.stat('Yuborilgan', A.num(st.sent), "shartnomasi tugagan, botga ulangan talabalarga")}
      ${A.stat('Javob bergan', A.num(st.done), `${st.rate}%`, st.done ? '' : 'warn')}
    </div>` : '';
    const reasonTbl = (rows, empty) => A.table([{ h: 'Sabab', f: (r) => esc(r.label) }, { h: 'Soni', cls: 'num', f: (r) => A.num(r.n) }], rows, { empty });
    const reasons = st && (st.reasons.length || st.admin_reasons.length) ? `<div class="grid-2">
      <div class="card"><h3>Talaba aytgan sabab</h3>${reasonTbl(st.reasons, "Hali javob yo'q")}</div>
      <div class="card"><h3>Shartnomada kiritilgan sabab <small class="muted">(javob bergan talabalar)</small></h3>${reasonTbl(st.admin_reasons, '—')}</div></div>` : '';
    const scales = st && st.scales.length ? `<div class="card"><h3>Baholar (o'rtacha, 5 dan)</h3>${A.table([{ h: 'Savol', f: (r) => esc(r.question) }, { h: "O'rtacha", cls: 'num', f: (r) => `<b>${r.avg}</b>` }, { h: 'Javob', cls: 'num', f: (r) => A.num(r.n) }], st.scales, { empty: '—' })}</div>` : '';
    const TONE = { Tugadi: 'green', Jarayonda: 'blue', Yuborildi: 'orange' };
    const table = A.table([
      { h: 'Talaba', f: (x) => `${esc(x.student_name)}<br><small class="muted">${esc(x.course)} · ${x.flow === 'Tamomlaganlarga' ? 'tamomlagan' : "to'xtatgan"}</small>` },
      { h: 'Shartnomada', f: (x) => esc(x.stop_reason || '—') },
      { h: 'Holat', f: (x) => `${A.badge(x.state, TONE[x.state])}${x.respondent_role ? `<br><small class="muted">${esc(x.respondent_role)} · ${A.fdt(x.completed_at)}</small>` : `<br><small class="muted">${A.fdt(x.sent_at)}</small>`}` },
      { h: 'Javoblar', f: (x) => (x.answers.length ? x.answers.map((a) => `<div class="small"><span class="muted">${esc(a.question)}</span> <b>${esc(a.answer)}</b></div>`).join('') : '<span class="muted">—</span>') },
    ], exits.results, { empty: "Hali so'rovnoma yuborilmagan. Shartnomaga tugash sanasi kiritilgach, ertasi kuni 10:00 da botga ulangan talabaga yuboriladi" });
    return `<p class="muted small">Shartnomasi tugagan (tamomlagan yoki to'xtatgan) va botga ulangan talabaga ertasi kuni 10:00 da bot qisqa savollar yuboradi; o'quvchi yoki vasiy javob beradi. Javob kelganda Bosh menejerga Telegram xabar boradi. Savollarni «Savollar» tabida o'zgartirasiz.</p>${cards}${reasons}${scales}${table}${A.pager(BK, exits)}`;
  }

  const FLOW_LABEL = { Hammasiga: 'Hammasiga', Tamomlaganlarga: 'Kursni tamomlaganlarga', "To'xtatganlarga": "To'xtatganlarga" };
  function questionsView() {
    const canA = A.can('clientbot', 'a');
    const canE = A.can('clientbot', 'e');
    const canD = A.can('clientbot', 'd');
    const table = A.table([
      { h: '№', cls: 'num', f: (q) => A.num(q.order) },
      { h: 'Savol', f: (q) => `${esc(q.text)}${q.status !== 'Faol' ? ' ' + A.badge('Nofaol', 'gray') : ''}` },
      { h: 'Turi', f: (q) => `${esc(q.kind)}${q.options.length ? `<br><small class="muted">${q.options.map(esc).join(' · ')}${q.allow_other ? ' · Boshqa (yozaman)' : ''}</small>` : ''}` },
      { h: 'Kimga', f: (q) => esc(FLOW_LABEL[q.flow] || q.flow) },
      { h: '', f: (q) => `${canE ? `<button class="btn sm ghost" data-act="q-edit" data-id="${q.id}">✎</button>` : ''}${canD ? `<button class="btn sm ghost" data-act="q-del" data-id="${q.id}">🗑</button>` : ''}` },
    ], questions, { empty: "Savol yo'q" });
    return `<div class="row gap" style="margin:8px 0;align-items:center">${canA ? A.btn("Savol qo'shish", 'q-edit', { icon: 'plus' }) : ''}
      <span class="muted small">Savollar tartib raqami bo'yicha so'raladi. Har savolni talaba o'tkazib yuborishi mumkin. O'zgarishlar faqat keyin yuboriladigan so'rovnomalarga ta'sir qiladi.</span></div>${table}`;
  }

  A.act['q-edit'] = (el) => {
    const q = el.dataset.id ? questions.find((x) => String(x.id) === el.dataset.id) : null;
    const br = A.branchIds();
    const last = (questions[questions.length - 1] || {}).order || 0;
    A.form({
      title: q ? 'Savolni tahrirlash' : 'Yangi savol',
      values: q ? { ...q, options: (q.options || []).join('\n') } : { kind: 'Tanlov', flow: 'Hammasiga', order: last + 10, status: 'Faol', branch: br[0], options: '' },
      fields: [
        { name: 'text', label: 'Savol', type: 'textarea', required: true },
        { name: 'kind', label: 'Javob turi', type: 'seg', options: [['Tanlov', 'Tanlov'], ['Baho', 'Baho 1–5'], ['Matn', 'Matn']] },
        { name: 'options', label: 'Variantlar (har birini yangi qatorga)', type: 'textarea', show: (x) => x.kind === 'Tanlov', help: () => "Kamida 2 ta, ko'pi bilan 8 ta; har biri 40 belgigacha" },
        { name: 'allow_other', label: "«Boshqa (yozaman)» varianti bo'lsin", type: 'checkbox', show: (x) => x.kind === 'Tanlov' },
        { name: 'flow', label: 'Kimga', type: 'select', options: () => Object.entries(FLOW_LABEL) },
        { name: 'order', label: 'Tartib raqami', type: 'number', min: 1, max: 999, required: true },
        { name: 'status', label: 'Holat', type: 'seg', options: [['Faol', 'Faol'], ['Nofaol', 'Nofaol']], show: () => !!q },
        { name: 'branch', label: 'Filial', type: 'select', required: true, show: () => !q && br.length > 1, options: () => br.map((id) => [id, A.branchName(id)]) },
      ],
      async onSubmit(x) {
        const body = {
          text: x.text, kind: x.kind, options: String(x.options || '').split('\n').map((t) => t.trim()).filter(Boolean), allow_other: !!x.allow_other,
          flow: x.flow, order: Number(x.order), status: x.status || 'Faol',
        };
        if (q) await A.http.patch(`/bot-questions/${q.id}/`, body);
        else await A.http.post('/bot-questions/', { ...body, branch: x.branch || br[0] });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['q-del'] = async (el) => {
    const q = questions.find((x) => String(x.id) === el.dataset.id);
    if (!(await A.confirm(`«${esc(q.text)}» savoli o'chirilsinmi? Avvalgi javoblar saqlanib qoladi.`, "O'chirish", true))) return;
    A.http.del(`/bot-questions/${q.id}/`).then(() => { A.toast("O'chirildi"); A.refresh(); }, fail);
  };

  /* ---------- Kurs testi (2026-11-06): guruh sahifasidan yuboriladi, o'quvchi botda topshiradi ---------- */
  const QZ_TONE = { Tugadi: 'green', Jarayonda: 'blue', Yuborildi: 'orange', 'Bekor qilindi': 'gray' };
  const QZ_LABEL = { Tugadi: 'Topshirgan', Jarayonda: 'Jarayonda', Yuborildi: 'Boshlamagan', 'Bekor qilindi': 'Bekor qilingan' };
  const scoreCell = (a) => (a.state === 'Tugadi' ? `<b class="${a.passed ? 't-green' : 't-red'}">${a.score}/${a.total}</b> <small class="muted">${a.percent}%</small>${a.timed_out ? ' ' + A.badge('vaqt tugadi', 'orange') : ''}` : '<span class="muted">—</span>');

  function quizView() {
    const st = quizStats;
    const cards = st ? `<div class="stats">
      ${A.stat('Yuborilgan', A.num(st.sent), `topshirgan ${A.num(st.done)} · kutayotgan ${A.num(st.waiting)}`)}
      ${A.stat("O'rtacha natija", st.avg === null ? '—' : st.avg + '%', `o'tish chegarasi ${st.pass_percent}%`)}
      ${A.stat("Testdan o'tgan", `${A.num(st.passed)} / ${A.num(st.done)}`, '', st.done && st.passed < st.done ? 'warn' : '')}
    </div>` : '';
    const hard = st && st.questions.length ? `<div class="grid-2">
      <div class="card"><h3>Eng ko'p xato qilingan savollar</h3><p class="muted small">Ustoz shu mavzularni qayta tushuntirsa bo'ladi.</p>${A.table([
        { h: 'Savol', f: (x) => esc(x.text) }, { h: 'Xato', cls: 'num', f: (x) => `<b>${x.rate}%</b> <small class="muted">${x.wrong}/${x.asked}</small>` }], st.questions, { empty: '—' })}</div>
      <div class="card"><h3>Darslar bo'yicha xato</h3>${A.table([
        { h: 'Dars', f: (x) => `${x.lesson}-dars` }, { h: 'Xato', cls: 'num', f: (x) => `<b>${x.rate}%</b> <small class="muted">${x.wrong}/${x.asked}</small>` }], st.lessons, { empty: '—' })}</div></div>` : '';
    const groups = st && st.groups.length ? `<div class="card"><h3>Guruhlar bo'yicha o'rtacha</h3>${A.table([
      { h: 'Guruh', f: (x) => esc(x.group) }, { h: 'Topshirgan', cls: 'num', f: (x) => A.num(x.n) }, { h: "O'rtacha", cls: 'num', f: (x) => `<b>${x.avg}%</b>` }], st.groups, { empty: '—' })}</div>` : '';
    const canE = A.can('clientbot', 'e');
    const table = A.table([
      { h: 'Talaba', f: (a) => `${esc(a.student_name)}<br><small class="muted">${esc(a.group_name || a.course_name)}</small>` },
      { h: 'Holat', f: (a) => `${A.badge(QZ_LABEL[a.state] || a.state, QZ_TONE[a.state])}<br><small class="muted">${A.fdt(a.finished_at || a.started_at || a.created_at)}</small>` },
      { h: 'Natija', f: scoreCell },
      { h: 'Yubordi', f: (a) => esc(a.sent_by || '—') },
      { h: '', f: (a) => `${a.state === 'Tugadi' ? `<button class="btn sm ghost" data-act="quiz-view" data-id="${a.id}">Xatolar</button>` : ''}${canE && a.state === 'Tugadi' ? `<button class="btn sm ghost" data-act="quiz-retake" data-id="${a.id}">Qayta topshirish</button>` : ''}${canE && (a.state === 'Yuborildi' || a.state === 'Jarayonda') ? `<button class="btn sm ghost" data-act="quiz-cancel" data-id="${a.id}">Bekor qilish</button>` : ''}` },
    ], quizzes.results, { empty: "Hali test yuborilmagan. Guruh sahifasidagi «📝 Test» tugmasi orqali yuboring" });
    return `<p class="muted small">Test o'quvchining o'zi uchun: u botda «📝 Test» tugmasini bosadi. Testni ustoz yoki administrator guruh sahifasidan ochadi (kurs oxirida). Har bir o'quvchi bir marta topshiradi, qayta topshirishga bu yerdan ruxsat berasiz.</p>${cards}${hard}${groups}${table}${A.pager(BK, quizzes)}`;
  }

  A.act['quiz-view'] = (el) => {
    const a = quizzes.results.find((x) => String(x.id) === el.dataset.id);
    const rows = a.review.map((r) => `<div class="card" style="margin:6px 0;padding:8px"><b>${r.n}.</b> ${esc(r.text)} <small class="muted">(${r.lesson}-dars)</small><br>
      ${r.ok ? `<span class="t-green">✅ ${esc(r.correct)}</span>` : `<span class="t-red">❌ ${r.chosen === null ? 'javob berilmagan' : esc(r.chosen)}</span><br><span class="t-green">✅ ${esc(r.correct)}</span>`}</div>`).join('');
    A.modal({ title: `${a.student_name} — ${a.score}/${a.total} (${a.percent}%)`, wide: true, body: rows });
  };
  A.act['quiz-retake'] = async (el) => {
    if (!(await A.confirm("Talabaga testni qayta topshirishga ruxsat berilsinmi? Avvalgi natija saqlanib qoladi.", 'Ruxsat berish'))) return;
    A.http.post(`/bot-quiz-attempts/${el.dataset.id}/retake/`).then((r) => { A.toast(r.sent ? 'Talabaga yuborildi' : "Yuborildi — talaba botga ulangach ko'radi"); A.refresh(); }, fail);
  };
  A.act['quiz-cancel'] = async (el) => {
    if (!(await A.confirm('Test bekor qilinsinmi? Talaba uni topshira olmaydi.', 'Bekor qilish', true))) return;
    A.http.post(`/bot-quiz-attempts/${el.dataset.id}/cancel/`).then(() => { A.toast('Bekor qilindi'); A.refresh(); }, fail);
  };

  function quizQuestionsView() {
    const canA = A.can('clientbot', 'a');
    const canE = A.can('clientbot', 'e');
    const canD = A.can('clientbot', 'd');
    const table = A.table([
      { h: 'Dars', cls: 'num', f: (q) => A.num(q.lesson) },
      { h: 'Savol', f: (q) => `${esc(q.text)}${q.status !== 'Faol' ? ' ' + A.badge('Nofaol', 'gray') : ''}<br><small class="muted">${esc(q.course_name)}</small>` },
      { h: 'Variantlar', f: (q) => q.options.map((o, i) => (i === q.correct ? `<b class="t-green">✓ ${esc(o)}</b>` : esc(o))).join('<br>') },
      { h: '', f: (q) => `${canE ? `<button class="btn sm ghost" data-act="qq-edit" data-id="${q.id}">✎</button>` : ''}${canD ? `<button class="btn sm ghost" data-act="qq-del" data-id="${q.id}">🗑</button>` : ''}` },
    ], quizQs, { empty: "Savol yo'q" });
    return `<div class="row gap" style="margin:8px 0;align-items:center">${canA ? A.btn("Savol qo'shish", 'qq-edit', { icon: 'plus' }) : ''}
      <span class="muted small">Test har safar shu savollardan tuziladi (20 tadan ko'p bo'lsa — har darsdan teng olinadi). Variantlar o'quvchiga aralashtirib ko'rsatiladi. O'zgarish faqat keyin boshlanadigan testlarga ta'sir qiladi.</span></div>${table}`;
  }

  A.act['qq-edit'] = (el) => {
    const q = el.dataset.id ? quizQs.find((x) => String(x.id) === el.dataset.id) : null;
    const courses = A.vis('courses').filter((c) => c.status === 'Faol');
    const last = (quizQs[quizQs.length - 1] || {}).order || 0;
    A.form({
      title: q ? 'Savolni tahrirlash' : 'Yangi test savoli',
      values: q ? { ...q, options: (q.options || []).join('\n'), correct: q.correct + 1 } : { course: (courses[0] || {}).id, lesson: 1, order: last + 10, status: 'Faol', options: '', correct: 1 },
      fields: [
        { name: 'course', label: 'Kurs', type: 'select', required: true, options: () => courses.map((c) => [c.id, c.name]) },
        { name: 'lesson', label: 'Dars raqami', type: 'number', min: 1, max: 99, required: true },
        { name: 'text', label: 'Savol', type: 'textarea', required: true },
        { name: 'options', label: 'Variantlar (har birini yangi qatorga, 2–6 ta)', type: 'textarea', required: true },
        { name: 'correct', label: "To'g'ri variant raqami (1 dan)", type: 'number', min: 1, max: 6, required: true },
        { name: 'explanation', label: "Izoh (xato javobdan keyin o'quvchiga ko'rsatiladi)", type: 'textarea' },
        { name: 'order', label: 'Tartib raqami', type: 'number', min: 1, max: 9999, required: true },
        { name: 'status', label: 'Holat', type: 'seg', options: [['Faol', 'Faol'], ['Nofaol', 'Nofaol']], show: () => !!q },
      ],
      async onSubmit(x) {
        const body = { course: x.course, lesson: Number(x.lesson), text: x.text, options: String(x.options || '').split('\n').map((t) => t.trim()).filter(Boolean),
          correct: Number(x.correct) - 1, explanation: x.explanation || '', order: Number(x.order), status: x.status || 'Faol' };
        if (q) await A.http.patch(`/bot-quiz-questions/${q.id}/`, body);
        else await A.http.post('/bot-quiz-questions/', body);
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['qq-del'] = async (el) => {
    const q = quizQs.find((x) => String(x.id) === el.dataset.id);
    if (!(await A.confirm(`«${esc(q.text)}» savoli o'chirilsinmi? Topshirilgan testlar natijasi saqlanib qoladi.`, "O'chirish", true))) return;
    A.http.del(`/bot-quiz-questions/${q.id}/`).then(() => { A.toast("O'chirildi"); A.refresh(); }, fail);
  };

  /* Guruh sahifasidagi «📝 Test» oynasi (pages-edu.js tugmasi) */
  A.act['group-quiz'] = async (el) => {
    const gid = el.dataset.id;
    let d;
    try { d = await A.http.get(`/groups/${gid}/quiz/`); } catch (e) { return fail(e); }
    const draw = (m) => {
      const rows = d.rows.map((r) => {
        const a = r.attempt;
        const state = a ? `${A.badge(QZ_LABEL[a.state] || a.state, QZ_TONE[a.state])} ${scoreCell(a)}` : '<span class="muted">yuborilmagan</span>';
        return `<tr><td>${esc(r.student_name)}</td><td>${r.bot ? '' : '<small class="t-red">botga ulanmagan</small>'}</td><td>${state}</td>
          <td>${d.can_send && a && a.state === 'Tugadi' ? `<button class="btn sm ghost" data-quiz-one="${r.contract}">Qayta</button>` : ''}</td></tr>`;
      }).join('');
      m.el.querySelector('.modal-body').innerHTML = `<p class="muted small">${d.questions} ta savol, ${d.minutes} daqiqa, o'tish chegarasi ${d.pass_percent}%. Test <b>o'quvchining o'zi</b> Telegram botida «📝 Test» tugmasi bilan topshiriladi; bir marta. Botga hali ulanmagan o'quvchi ulangach testni ko'radi.</p>
        <table class="tbl"><thead><tr><th>Talaba</th><th></th><th>Holat</th><th></th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="muted">Faol talaba yo\'q</td></tr>'}</tbody></table>`;
      m.el.querySelectorAll('[data-quiz-one]').forEach((b) => { b.onclick = () => send(m, b.dataset.quizOne); });
    };
    const send = async (m, contract) => {
      try {
        const r = await A.http.post(`/groups/${gid}/quiz/`, contract ? { contract } : {});
        A.toast(`Yuborildi: ${r.sent} · botga ulanmagan: ${r.waiting} · allaqachon bor: ${r.open + r.done}`);
        d = await A.http.get(`/groups/${gid}/quiz/`);
        draw(m);
      } catch (e) { fail(e); }
    };
    const m = A.modal({ title: '📝 Kurs testi', wide: true, body: '', footer: `<button class="btn ghost" data-close>Yopish</button>${d.can_send && d.available ? '<button class="btn primary" data-send-all>Hammasiga yuborish</button>' : ''}` });
    const all = m.el.querySelector('[data-send-all]');
    if (all) all.onclick = async () => { if (await A.confirm(`Guruhning hamma faol talabasiga test yuborilsinmi? (${d.questions} ta savol)`, 'Yuborish')) send(m); };
    draw(m);
  };

  /* ---------- Elektron darslik (2026-11-08): o'quvchi vazifalari, AI bahosi va ustoz bahosi ---------- */
  const SUB_TONE = { Tekshirildi: 'green', 'Qayta topshirish': 'orange', Kutilmoqda: 'blue', 'Rad etildi': 'red' };
  function subsView() {
    const canE = A.can('clientbot', 'e');
    const table = A.table([
      { h: 'Talaba', f: (x) => `${esc(x.student_name)}<br><small class="muted">${esc(x.group_name)}</small>` },
      { h: 'Dars', f: (x) => `${x.lesson_number}. ${esc(x.lesson_title)}<br><small class="muted">${x.attempt}/${x.max_attempts}-urinish · ${esc(x.submission_type)}${x.file_name ? ' · ' + esc(x.file_name) : ''}</small>` },
      { h: 'Ball', f: (x) => (x.final_score === null || x.final_score === undefined ? '<span class="muted">—</span>'
        : `<b class="${x.final_score >= 60 ? 't-green' : 't-red'}">${x.final_score}</b>${x.teacher_score !== null ? ' <small class="muted">ustoz</small>' : ` <small class="muted">AI</small>`}`) },
      { h: 'Holat', f: (x) => `${A.badge(x.status, SUB_TONE[x.status])}<br><small class="muted">${A.fdt(x.submitted_at)}</small>` },
      { h: '', f: (x) => `<button class="btn sm ghost" data-act="sub-view" data-id="${x.id}">Ko'rish</button>${canE ? `<button class="btn sm ghost" data-act="sub-grade" data-id="${x.id}">Baholash</button><button class="btn sm ghost" data-act="sub-more" data-id="${x.id}">+ Urinish</button>` : ''}` },
    ], subsList.results, { empty: "Hali vazifa topshirilmagan" });
    return `<p class="muted small">O'quvchilar botdagi «📚 Darslik» orqali topshirgan vazifalar. Ball avval AI (Gemini) tomonidan qo'yiladi, ustoz o'zgartirsa (60 va undan yuqori — o'tdi) ustoz bali hisobga olinadi. 3 ta urinish tugagan talabaga «+ Urinish» bilan yana imkon berasiz.</p>${table}${A.pager(BK, subsList)}`;
  }
  A.act['sub-view'] = (el) => {
    const x = subsList.results.find((r) => String(r.id) === el.dataset.id);
    A.modal({ title: `${x.student_name} — ${x.lesson_number}-dars`, wide: true, body: `
      <p class="small muted">${x.attempt}-urinish · ${esc(x.submission_type)} · ${A.fdt(x.submitted_at)}</p>
      ${x.content_text ? `<div class="card" style="padding:8px;white-space:pre-wrap">${esc(x.content_text)}</div>` : '<p class="muted">Matnli javob yo\'q (rasm yoki fayl yuborilgan)</p>'}
      <h4>AI xulosasi ${x.score !== null ? `(${x.score}/100)` : ''}</h4><div style="white-space:pre-wrap">${esc(x.feedback || '—')}</div>
      ${x.teacher_score !== null ? `<h4>Ustoz bahosi: ${x.teacher_score}/100</h4><div style="white-space:pre-wrap">${esc(x.teacher_comment || '')}</div>` : ''}` });
  };
  A.act['sub-grade'] = (el) => {
    const x = subsList.results.find((r) => String(r.id) === el.dataset.id);
    A.form({
      title: `Baholash: ${x.student_name}, ${x.lesson_number}-dars`,
      values: { score: x.teacher_score !== null ? x.teacher_score : (x.score !== null ? x.score : ''), comment: x.teacher_comment || '' },
      fields: [
        { name: 'note', type: 'note', text: () => `AI bahosi: <b>${x.score === null ? '—' : x.score}</b>. O'tish bali — 60.` },
        { name: 'score', label: 'Ball (0–100)', type: 'number', min: 0, max: 100, required: true },
        { name: 'comment', label: "Izoh (o'quvchi ko'rmaydi)", type: 'textarea' },
      ],
      async onSubmit(v) {
        await A.http.post(`/bot-lesson-submissions/${x.id}/grade/`, { score: Number(v.score), comment: v.comment || '' });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['sub-more'] = async (el) => {
    if (!(await A.confirm("Talabaga shu dars uchun yana 1 ta urinish berilsinmi?", 'Ruxsat berish'))) return;
    A.http.post(`/bot-lesson-submissions/${el.dataset.id}/reset_attempts/`, { extra: 1 }).then(() => { A.toast('Urinish qo\'shildi'); A.refresh(); }, fail);
  };

  function lessonsView() {
    const canE = A.can('clientbot', 'e');
    const table = A.table([
      { h: '№', cls: 'num', f: (l) => A.num(l.number) },
      { h: 'Mavzu', f: (l) => `${esc(l.title)}${l.status !== 'Faol' ? ' ' + A.badge('Nofaol', 'gray') : ''}${l.video_url ? `<br><small class="muted">${esc(l.video_url)}</small>` : ''}` },
      { h: 'Amaliyot', f: (l) => `<span class="small">${esc(String(l.practice_task || '').slice(0, 140))}${(l.practice_task || '').length > 140 ? '…' : ''}</span>` },
      { h: '', f: (l) => (canE ? `<button class="btn sm ghost" data-act="les-edit" data-id="${l.id}">✎</button>` : '') },
    ], lessonsList, { empty: "Mavzu yo'q. «Kompyuter savodxonligi» kursi tizimda bo'lishi kerak" });
    return `<p class="muted small">Botdagi «📚 Darslik» mavzulari (12 ta). Nazariya, videodars havolasi va amaliyot topshirig'ini o'zgartirsangiz, o'quvchilar darhol yangisini ko'radi. «AI baholash mezoni» — Gemini vazifani nimaga qarab baholashini aytadi.</p>${table}`;
  }
  A.act['les-edit'] = (el) => {
    const l = lessonsList.find((x) => String(x.id) === el.dataset.id);
    A.form({
      title: `${l.number}-dars: ${l.title}`,
      values: { ...l },
      fields: [
        { name: 'title', label: 'Mavzu nomi', type: 'text', required: true },
        { name: 'summary', label: 'Nazariya (konspekt)', type: 'textarea' },
        { name: 'video_url', label: 'Videodars havolasi', type: 'text' },
        { name: 'practice_task', label: "Amaliyot topshirig'i", type: 'textarea' },
        { name: 'rubric', label: 'AI baholash mezoni', type: 'textarea' },
        { name: 'status', label: 'Holat', type: 'seg', options: [['Faol', 'Faol'], ['Nofaol', 'Nofaol']] },
      ],
      async onSubmit(v) {
        await A.http.patch(`/bot-textbook-lessons/${l.id}/`, { title: v.title, summary: v.summary || '', video_url: v.video_url || '', practice_task: v.practice_task || '', rubric: v.rubric || '', status: v.status });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };

  const MSG_TONE = { sent: ['Yuborildi', 'green'], pending: ['Navbatda', 'orange'], failed: ['Xato', 'red'] };
  function messagesView() {
    return A.table([
      { h: 'Vaqt', f: (m) => `${A.fdt(m.sent_at || m.created_at)}` },
      { h: 'Kim', f: (m) => `${m.student_name ? esc(m.student_name) : '<span class="muted">—</span>'}<br><small class="muted">${m.recipient ? esc(m.recipient) + ' · ' : ''}${esc(m.telegram_name)}${m.username ? ' @' + esc(m.username) : ''}</small>` },
      { h: 'Turi', f: (m) => esc(m.kind || 'Bot') },
      { h: 'Matn', f: (m) => `<span class="small">${esc(String(m.text).replace(/&(amp|lt|gt|quot|#x27);/g, (x) => ({ '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#x27;': "'" }[x])))}</span>` },
      { h: 'Holat', f: (m) => `${A.badge(...(MSG_TONE[m.status] || [m.status, 'gray']))}${m.error ? `<br><small class="t-red">${esc(m.error)}</small>` : ''}` },
    ], msgs.results, { empty: "Hali xabar yuborilmagan" }) + A.pager(BK, msgs);
  }

  function configView() {
    const canE = A.can('clientbot', 'e');
    if (!config.length) return A.empty("Filial yo'q");
    return config.map((c) => `<div class="card"><div class="row gap" style="justify-content:space-between;align-items:center"><h3>${esc(c.branch_name)}</h3>${canE ? A.btn('Tahrirlash', 'bot-cfg', { id: c.id, cls: 'ghost' }) : ''}</div>
      <table class="tbl kv"><tbody>
        <tr><td>Lid va shartnoma SMS'iga bot havolasi</td><td>${c.invite_in_sms ? A.badge('Qo\'shiladi', 'green') : A.badge("O'chiq", 'gray')}</td></tr>
        <tr><td>To'lov va balans ma'lumotlari botda</td><td>${c.finance_in_bot ? A.badge('Yoqilgan', 'green') : A.badge("Vaqtincha o'chiq", 'orange')} <small class="muted">(to'lov kiritilganda xabar, kabinetdagi «To'lovlar» va «To'lov muddati», to'lov eslatmalari botga)</small></td></tr>
        <tr><td>Tavsiya bonusi</td><td><b>${A.money(c.referral_bonus)}</b></td></tr>
        <tr><td>Bonus uchun lid to'lovlari</td><td>oy narxining kamida <b>${c.referral_min_percent}%</b> <small class="muted">(yig'indi; bonus 0 bo'lsa — o'chiq)</small></td></tr>
        <tr><td>Start eslatmasi</td><td>har <b>${c.reminder_days}</b> kunda, ko'pi bilan <b>${c.reminder_max}</b> marta <small class="muted">(Qo'ng'iroqlar va SMS → SMS → «Botga ulanish eslatmasi» qoidasi yoqilgan bo'lsa)</small></td></tr>
      </tbody></table></div>`).join('');
  }

  A.act['bot-cfg'] = (el) => {
    const c = config.find((x) => String(x.id) === el.dataset.id);
    A.form({
      title: `Bot sozlamalari — ${c.branch_name}`,
      values: { ...c, referral_bonus: Number(c.referral_bonus) },
      fields: [
        { name: 'invite_in_sms', label: "Lid va shartnoma SMS'iga bot havolasi qo'shilsin", type: 'checkbox' },
        { name: 'finance_in_bot', label: "To'lov va balans ma'lumotlari botda ko'rsatilsin (xabar, kabinet, eslatmalar)", type: 'checkbox' },
        { name: 'referral_bonus', label: "Tavsiya bonusi (so'm)", type: 'money', required: true, min: 0 },
        { name: 'referral_min_percent', label: "Bonus uchun lid to'lovlari (oy narxining %)", type: 'number', min: 0, max: 100, required: true },
        { name: 'reminder_days', label: 'Start eslatmasi oralig\'i (kun)', type: 'number', min: 1, max: 60, required: true },
        { name: 'reminder_max', label: 'Start eslatmasi ko\'pi bilan (marta)', type: 'number', min: 0, max: 10, required: true },
      ],
      async onSubmit(x) {
        await A.http.patch(`/bot-config/${c.id}/`, {
          invite_in_sms: !!x.invite_in_sms, finance_in_bot: !!x.finance_in_bot, referral_bonus: Number(x.referral_bonus), referral_min_percent: Number(x.referral_min_percent),
          reminder_days: Number(x.reminder_days), reminder_max: Number(x.reminder_max),
        });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
})(window.App);

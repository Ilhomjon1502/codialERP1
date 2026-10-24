/* Codial ERP — Mijozlar boti (2026-10-24): o'quvchi va vasiylar Telegram boti. «Qo'ng'iroqlar va SMS» sahifasidagi «Telegram bot» tabi:
   umumiy ko'rsatkichlar, ulanganlar, ulanmagan kodlar, manba javoblari, tavsiyalar, sozlamalar.
   Server: /bot-links/ (+summary), /bot-invites/, /bot-surveys/, /bot-referrals/, /bot-config/. pages-calls.js ichidan chaqiriladi. */
(function (A) {
  const esc = A.esc;
  const BK = 'bot';
  const SUBS = [['overview', 'Umumiy'], ['links', 'Ulanganlar'], ['students', 'Talabalar'], ['surveys', 'Manba javoblari'], ['referrals', 'Tavsiyalar'], ['exits', "Ketish so'rovnomasi"], ['questions', 'Savollar'], ['messages', 'Xabarlar'], ['config', 'Sozlamalar']];
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
      if (s === 'messages') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki matn…'), A.fSelect(BK, 'status', [['sent', 'Yuborildi'], ['pending', 'Navbatda'], ['failed', 'Xato']], 'Barcha holatlar')]);
      return '';
    },
    view(q) {
      const s = sub(q);
      const nav = `<nav class="tabs sub">${SUBS.map(([k, l]) => `<a href="#/calls?tab=bot&sub=${k}" class="${k === s ? 'on' : ''}">${esc(l)}</a>`).join('')}</nav>`;
      const body = { overview, links: linksView, students: studentsView, surveys: surveysView, referrals: refsView, exits: exitsView, questions: questionsView, messages: messagesView, config: configView }[s]();
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
    return `<p class="muted small">Lid «tanishimdan eshitdim» degan bo'lsa shu yerga tushadi. Lid o'qishni boshlab birinchi to'lovini qilganda tavsiya qiluvchiga bonus beriladi (sozlamalarda miqdori). «Aniqlanmagan» ismni talabaga bog'lang.</p>` + A.table([
      { h: 'Lid', f: (r) => `<a href="#" data-act="lead-open" data-id="${r.lead}">${esc(r.lead_student)}</a><br><small class="muted">${A.fdt(r.created_at)}</small>` },
      { h: 'Kim tavsiya qilgan', f: (r) => (r.referrer_name ? `<b>${esc(r.referrer_name)}</b>${r.referrer_text ? `<br><small class="muted">yozilgan: ${esc(r.referrer_text)}</small>` : ''}` : `<span class="muted">yozilgan:</span> ${esc(r.referrer_text)}`) },
      { h: 'Holat', f: (r) => `${A.badge(r.state, REF_TONE[r.state])}${r.bonus ? `<br><small class="muted">${A.money(r.bonus)}</small>` : ''}` },
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
        <tr><td>Tavsiya bonusi</td><td><b>${A.money(c.referral_bonus)}</b></td></tr>
        <tr><td>Bonus uchun birinchi to'lov</td><td>oy narxining kamida <b>${c.referral_min_percent}%</b></td></tr>
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
        { name: 'referral_bonus', label: "Tavsiya bonusi (so'm)", type: 'money', required: true, min: 0 },
        { name: 'referral_min_percent', label: "Bonus uchun birinchi to'lov (oy narxining %)", type: 'number', min: 0, max: 100, required: true },
        { name: 'reminder_days', label: 'Start eslatmasi oralig\'i (kun)', type: 'number', min: 1, max: 60, required: true },
        { name: 'reminder_max', label: 'Start eslatmasi ko\'pi bilan (marta)', type: 'number', min: 0, max: 10, required: true },
      ],
      async onSubmit(x) {
        await A.http.patch(`/bot-config/${c.id}/`, {
          invite_in_sms: !!x.invite_in_sms, referral_bonus: Number(x.referral_bonus), referral_min_percent: Number(x.referral_min_percent),
          reminder_days: Number(x.reminder_days), reminder_max: Number(x.reminder_max),
        });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
})(window.App);

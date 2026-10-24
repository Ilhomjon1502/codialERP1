/* Codial ERP — Mijozlar boti (2026-10-24): o'quvchi va vasiylar Telegram boti. «Qo'ng'iroqlar va SMS» sahifasidagi «Telegram bot» tabi:
   umumiy ko'rsatkichlar, ulanganlar, ulanmagan kodlar, manba javoblari, tavsiyalar, sozlamalar.
   Server: /bot-links/ (+summary), /bot-invites/, /bot-surveys/, /bot-referrals/, /bot-config/. pages-calls.js ichidan chaqiriladi. */
(function (A) {
  const esc = A.esc;
  const BK = 'bot';
  const SUBS = [['overview', 'Umumiy'], ['links', 'Ulanganlar'], ['invites', 'Ulanmaganlar'], ['surveys', 'Manba javoblari'], ['referrals', 'Tavsiyalar'], ['messages', 'Xabarlar'], ['config', 'Sozlamalar']];
  const REF_TONE = { Aniqlanmagan: 'orange', Kutilmoqda: 'blue', Berildi: 'green', 'Rad etildi': 'gray' };
  const fphone = (p) => (p ? `+998 ${p.slice(0, 2)} ${p.slice(2, 5)}-${p.slice(5, 7)}-${p.slice(7)}` : '');
  const fail = (e) => A.toast(e.message || 'Xatolik', 'error');

  let sum = null;
  let links = { results: [] };
  let invites = { results: [] };
  let surveys = { results: [] };
  let refs = { results: [] };
  let msgs = { results: [] };
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
      else if (s === 'invites') invites = await A.http.get('/bot-invites/?' + qs({ linked: 0 }));
      else if (s === 'surveys') surveys = await A.http.get('/bot-surveys/?' + qs({}, ['search', 'differs']));
      else if (s === 'referrals') refs = await A.http.get('/bot-referrals/?' + qs({}, ['search', 'state']));
      else if (s === 'messages') msgs = await A.http.get('/bot-messages/?' + qs({}, ['search', 'status']));
      else config = await A.http.get('/bot-config/');
    },
    filters(q) {
      const s = sub(q);
      if (s === 'links') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki @username…'), A.fSelect(BK, 'role', [['Talaba', "O'quvchining o'zi"], ['Vasiy', 'Vasiy']], 'Hamma'),
        A.fSelect(BK, 'active', [['1', 'Faol'], ['0', 'Uzilgan']], 'Faol va uzilgan')]);
      if (s === 'invites') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki raqam…')]);
      if (s === 'surveys') return A.filterBar(BK, [A.fSearch(BK, 'Talaba…'), A.fSelect(BK, 'differs', [['1', 'Admin manbasidan farq qiladi']], 'Hammasi')]);
      if (s === 'referrals') return A.filterBar(BK, [A.fSearch(BK, 'Lid yoki yozilgan ism…'), A.fSelect(BK, 'state', Object.keys(REF_TONE).map((k) => [k, k]), 'Barcha holatlar')]);
      if (s === 'messages') return A.filterBar(BK, [A.fSearch(BK, 'Talaba yoki matn…'), A.fSelect(BK, 'status', [['sent', 'Yuborildi'], ['pending', 'Navbatda'], ['failed', 'Xato']], 'Barcha holatlar')]);
      return '';
    },
    view(q) {
      const s = sub(q);
      const nav = `<nav class="tabs sub">${SUBS.map(([k, l]) => `<a href="#/calls?tab=bot&sub=${k}" class="${k === s ? 'on' : ''}">${esc(l)}</a>`).join('')}</nav>`;
      const body = { overview, links: linksView, invites: invitesView, surveys: surveysView, referrals: refsView, messages: messagesView, config: configView }[s]();
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
      ${A.stat('Ulanmagan kodlar', A.num(s.unlinked_invites), "SMS borgan, lekin bot ochilmagan", s.unlinked_invites ? 'warn' : '', '#/calls?tab=bot&sub=invites')}
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
        Bot: ${s.username ? `<b>@${esc(s.username)}</b>` : '—'}.</div>`;
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

  function invitesView() {
    return `<p class="muted small">SMS bilan kod yuborilgan, lekin hali botga ulanmagan raqamlar.</p>` + A.table([
      { h: 'Talaba', f: (i) => esc(i.student_name) },
      { h: 'Raqam', f: (i) => fphone(i.phone) },
      { h: 'Kim', f: (i) => (i.role ? esc(i.role) : '<span class="muted">bot so\'raydi</span>') },
      { h: 'Kod yuborilgan', f: (i) => A.fdt(i.created_at) },
    ], invites.results, { empty: 'Hammasi ulangan 🎉' }) + A.pager(BK, invites);
  }

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

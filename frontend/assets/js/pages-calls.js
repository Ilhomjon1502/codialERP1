/* Codial ERP — Qo'ng'iroqlar (2026-10-19): administratorlar telefonidagi (Android ilova) qo'ng'iroqlar jurnali,
   CRM bilan solishtirilgan; statistika; qurilmalar (ulash kodi). Server: /calls/, /calls/stats/, /call-devices/. */
(function (A) {
  const esc = A.esc;
  const K = 'calls';
  const LS = { 1: "Qayta bog'lanishga", 2: 'Yangi guruhga kutyapti', 3: 'Sinov darsga yozildi', 4: 'Sinov darsga qatnashdi', 5: "O'qishni boshladi",
    6: "Ma'qul kelmadi", 7: "Ma'qul kelmadi (Sifatsiz)", 8: 'Keyinroq o\'qiydi' };
  const DIR = { Kiruvchi: ['↙', 'green'], Chiquvchi: ['↗', 'blue'], Javobsiz: ['✕', 'red'], 'Rad etilgan': ['⊘', 'red'], Bloklangan: ['⊘', 'gray'] };
  const dur = (s) => (s ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : '—');
  const durLong = (s) => (s >= 3600 ? `${Math.floor(s / 3600)} soat ${Math.floor((s % 3600) / 60)} daq` : `${Math.floor(s / 60)} daq`);
  const fphone = (p) => (p ? `+998 ${p.slice(0, 2)} ${p.slice(2, 5)}-${p.slice(5, 7)}-${p.slice(7)}` : '');

  let list = { results: [] };
  let st = null;
  let devices = [];

  const qs = (extra = {}) => {
    const q = new URLSearchParams(extra);
    for (const k of ['from', 'to', 'dir', 'known', 'first', 'search']) {
      const v = A.q(`${K}:${k}`, '');
      if (v) q.set(k === 'search' ? 'q' : k, v);
    }
    return q;
  };

  A.page('calls', {
    title: "Qo'ng'iroqlar va SMS",
    section: 'calls',
    async load(p, q) {
      const tab = q.tab || 'list';
      if (q.f !== undefined) { // statistika kartochkasidan: mos filtrni o'rnatib, havoladan olib tashlaymiz
        for (const k of ['dir', 'known', 'first', 'search']) A.ui.q[`${K}:${k}`] = '';
        const [k, v] = q.f ? q.f.split(':') : [];
        if (k) A.ui.q[`${K}:${k}`] = v;
        A.ui.q[`${K}:page`] = 1;
        history.replaceState(null, '', location.hash.replace(/[?&]f=[^&]*/, '').replace(/\?&/, '?'));
      }
      if (tab === 'stats') st = await A.http.get('/calls/stats/?' + qs());
      else if (tab === 'devices') devices = await A.http.get('/call-devices/');
      else if (tab === 'sms') await loadSms();
      else if (tab === 'smsstats') await loadSmsStats();
      else if (tab === 'bot') await A.botTab.load(q);
      else {
        list = await A.http.get('/calls/?' + qs({ page: A.q(`${K}:page`, 1) }));
        if (A.can('calls', 'a') && !devices.length) devices = await A.http.get('/call-devices/').catch(() => []);
      }
    },
    render(p, q) {
      const tab = q.tab || 'list';
      const tabs = [['list', "Qo'ng'iroqlar"], ['stats', 'Statistika'], ...(A.can('sms') ? [['sms', 'SMS'], ['smsstats', 'SMS statistikasi']] : []), ...(A.can('clientbot') ? [['bot', 'Telegram bot']] : []), ...(A.can('calls', 'a') ? [['devices', 'Qurilmalar']] : [])];
      const date = (k, ph) => `<input class="f-input" type="date" data-filter="${K}:${k}" title="${ph}" value="${esc(A.q(`${K}:${k}`, ''))}">`;
      const period = [date('from', 'Dan'), date('to', 'Gacha')];
      const filters = tab === 'list'
        ? A.filterBar(K, [A.fSearch(K, 'Raqam yoki ism…'), ...period,
          A.fSelect(K, 'dir', [['missed_open', "Javobsiz — qayta qo'ng'iroq qilinmagan"], ['missed', 'Javobsiz (hammasi)'], ['Kiruvchi', 'Kiruvchi'], ['Chiquvchi', 'Chiquvchi']], 'Barcha yo\'nalishlar'),
          A.fSelect(K, 'known', [['1', 'Bazada bor'], ['0', "Noma'lum raqamlar"]], 'Hamma raqamlar'),
          A.fSelect(K, 'first', [['1', 'Faqat birinchi marta']], 'Yangi va eski')])
        : tab === 'stats' ? A.filterBar(K, period)
          : tab === 'smsstats' ? A.filterBar(SK, [date2('from', 'Dan'), date2('to', 'Gacha')])
          : tab === 'sms' ? A.filterBar(SK, [A.fSearch(SK, 'Talaba yoki raqam…'), date2('from', 'Dan'), date2('to', 'Gacha'),
            A.fSelect(SK, 'dir', [['Kiruvchi', '↙ Kelgan SMS'], ['Chiquvchi', '↗ Yuborilgan SMS']], 'Kelgan va yuborilgan'),
            A.fSelect(SK, 'delivery', [['Yetkazildi', '✓✓ Yetkazildi'], ['Yetkazilmadi', '✕ Yetkazilmadi'], ['unknown', "Yetkazilishi noma'lum"]], 'Barcha yetkazilishlar'),
            A.fSelect(SK, 'known', [['0', "Noma'lum raqamlardan"]], 'Hamma raqamlar'),
            A.fSelect(SK, 'status', SMS_STATES.map((s) => [s, s]), 'Barcha holatlar')]) : '';
      const body = tab === 'bot' ? A.botTab.view(q) : tab === 'stats' ? statsView() : tab === 'devices' ? devicesView() : tab === 'sms' ? smsView() : tab === 'smsstats' ? smsStatsView() : listView();
      return `${A.head("Qo'ng'iroqlar va SMS", "Qabul telefonidagi qo'ng'iroqlar — tugashi bilan shu yerga tushadi. Raqam bazada bo'lsa ism va lid ma'lumoti chiqadi. SMS shu telefon orqali yuboriladi. Telegram bot — o'quvchi va vasiylar uchun")}
        ${A.tabs(tabs, tab, 'calls')}${filters}${body}`;
    },
  });

  /* ---------- Ro'yxat ---------- */
  function listView() {
    const offline = devices.filter((d) => d.status === 'Faol' && d.paired && d.last_seen_at && Date.now() - new Date(d.last_seen_at) > 6 * 3600e3);
    const warn = offline.length
      ? `<div class="alert warn">${A.icon('alert')}<div><b>${offline.map((d) => esc(d.name)).join(', ')}</b> — oxirgi aloqa ${offline.map((d) => A.fdt(d.last_seen_at)).join(', ')}. Telefonda internet va «Codial qo'ng'iroqlar» ilovasi yoqilganini tekshiring.</div></div>`
      : '';
    const canEdit = A.can('calls', 'e');
    const table = A.table(
      [
        { h: 'Vaqt', f: (c) => `${A.badge(`${DIR[c.direction][0]} ${c.direction}`, DIR[c.direction][1])}<br><small class="muted">${A.fdt(c.started_at)}</small>` },
        { h: 'Raqam', f: (c) => `<a href="tel:${esc(c.number)}" style="white-space:nowrap">${esc(c.phone ? fphone(c.phone) : c.number || 'Yashirin raqam')}</a>${c.contact_name ? `<br><small class="muted">📇 ${esc(c.contact_name)}</small>` : ''}` },
        { h: 'Kim', f: who },
        { h: 'Lid', f: (c) => (c.lead ? `${A.badge(`${c.lead_status}. ${LS[c.lead_status] || ''}`, c.lead_status === '5' ? 'green' : ['6', '7'].includes(c.lead_status) ? 'gray' : 'orange')}<br><small class="muted">${esc(c.lead_course)} · ${esc(c.lead_source)}</small>${c.lead_note_due && A.can('leads', 'a') ? `<br><button class="btn sm" data-act="call-lead-note" data-id="${c.lead}">📝 Izoh yozish</button>` : ''}` : c.has_contract ? A.badge('Shartnoma bor', 'green') : '—') },
        { h: 'Suhbat', cls: 'num', f: (c) => dur(c.duration) },
        { h: 'Holat', f: (c) => (c.missed ? (c.callback_at
          ? `<span class="t-green">✓ Qayta bog'lanildi</span><br><small class="muted">${A.fdt(c.callback_at)}${c.callback_by_name ? ` · ${esc(c.callback_by_name)}` : ' · avtomatik'}</small>`
          : `<span class="t-red">Javob berilmagan</span>${canEdit ? `<br><button class="btn sm" data-act="call-cb" data-id="${c.id}">✓ Qo'ng'iroq qilindi</button>` : ''}`) : '') },
        { h: 'Izoh', f: (c) => `${esc(c.comment)}${canEdit ? ` <a href="#" class="muted" data-act="call-note" data-id="${c.id}" title="Izoh">✎</a>` : ''}` },
      ],
      list.results,
      { empty: "Qo'ng'iroq yo'q", rowAttr: (c) => (c.missed && !c.callback_at ? 'class="row-warn"' : '') },
    );
    return `${warn}${table}${A.pager(K, list)}`;
  }

  function who(c) {
    if (c.student) {
      const name = c.lead && A.can('leads') ? `<a href="#" data-act="lead-open" data-id="${c.lead}">${esc(c.student_name)}</a>`
        : c.contract_id && A.can('contracts') ? `<a href="#/contracts/${c.contract_id}">${esc(c.student_name)}</a>` : esc(c.student_name);
      const absent = c.open_absences && c.duration > 0 && !c.missed && A.can('attendance', 'e')
        ? `<br><button class="btn sm ghost" data-act="call-absent" data-id="${c.id}">📌 Kelmagan (${c.open_absences}): Gaplashildi</button>` : '';
      return `${name}${absent}${c.parent_name ? `<br><small class="muted">vasiy: ${esc(c.parent_name)}</small>` : ''}`;
    }
    if (c.parent) return `${esc(c.parent_name)} <small class="muted">(vasiy)</small>`;
    const btn = c.phone && A.can('leads', 'a') ? `<br><button class="btn sm ghost" data-act="call-lead" data-id="${c.id}">＋ Lid yaratish</button>` : '';
    return `<span class="muted">Noma'lum</span> ${c.is_first ? A.badge('Yangi raqam', 'orange') : ''}${btn}`;
  }

  const find = (id) => list.results.find((c) => String(c.id) === String(id));
  const fail = (e) => A.toast(e.message, 'warn');

  A.act['call-cb'] = (el) => A.http.post(`/calls/${el.dataset.id}/callback/`, { done: true }).then(() => { A.toast('Belgilandi'); A.refresh(); }, fail);
  A.act['call-note'] = (el) => {
    const c = find(el.dataset.id);
    A.form({
      title: `Izoh: ${c.student_name || fphone(c.phone) || c.number}`,
      values: { comment: c.comment },
      fields: [{ name: 'comment', label: 'Izoh', type: 'textarea', placeholder: "Masalan: Frontend narxini so'radi, kechki guruh kerak" }],
      async onSubmit(x) {
        await A.http.patch(`/calls/${c.id}/`, { comment: x.comment || '' });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['call-lead-note'] = async (el) => {
    const l = await A.http.get(`/leads/${el.dataset.id}/`);
    A.callNoteForm(l, () => A.refresh());
  };
  A.act['call-absent'] = (el) => {
    const c = find(el.dataset.id);
    A.form({
      title: `Kelmagan talaba bilan gaplashildi: ${c.student_name}`,
      values: { parent_log: A.can('parentCalls', 'a') },
      fields: [
        { name: 'note', type: 'note', text: () => `Talabaning bog'lanish kutayotgan ${c.open_absences} ta kelmagan darsi «Gaplashildi» deb belgilanadi.` },
        { name: 'comment', label: 'Suhbat haqida izoh', type: 'textarea', required: true, placeholder: 'Masalan: kasal bo\'lgan, ertaga keladi' },
        { name: 'parent_log', label: "Ota-onalar bilan aloqa jurnaliga ham yozilsin", type: 'checkbox', show: () => A.can('parentCalls', 'a') },
      ],
      async onSubmit(x) {
        const r = await A.http.post(`/calls/${c.id}/absence-contact/`, { comment: x.comment, parent_log: !!x.parent_log });
        A.toast(`Belgilandi: ${r.absences} ta dars${r.parent_logs ? ", aloqa jurnaliga yozildi" : ''}`);
        A.refresh();
      },
    });
  };
  A.act['call-lead'] = async (el) => {
    const c = find(el.dataset.id);
    const free = await A.http.get('/students/?free=1&page_size=200');
    A.leadForm(null, free.results, { phone1: c.phone, comment: `Qo'ng'iroq ${A.fdt(c.started_at)} (${c.direction.toLowerCase()})${c.comment ? `: ${c.comment}` : ''}` });
  };

  /* ---------- Statistika ---------- */
  // Eng uzun / eng qisqa suhbat: kim bilan, qachon (bosilsa shu raqamning qo'ng'iroqlari ochiladi)
  const callWho = (c) => (c ? `${esc(c.name || (c.phone ? fphone(c.phone) : c.number || 'Yashirin raqam'))}${c.name && c.phone ? ` · ${fphone(c.phone)}` : ''}<br>${A.fdt(c.started_at)} · ${esc(c.direction.toLowerCase())}` : '');
  const callLink = (c) => (c && (c.phone || c.number) ? `#/calls?tab=list&f=${encodeURIComponent('search:' + (c.phone || c.number))}` : '');
  function statsView() {
    if (!st) return '';
    const s = st;
    const cards = `<div class="stats">
      ${A.stat("Jami qo'ng'iroq", A.num(s.total), `suhbat ${durLong(s.talk)}`, '', '#/calls?tab=list&f=')}
      ${A.stat('Kiruvchi (javob berilgan)', A.num(s.answered), '', '', '#/calls?tab=list&f=dir:Kiruvchi')}
      ${A.stat('Chiquvchi', A.num(s.outgoing), '', '', '#/calls?tab=list&f=dir:Chiquvchi')}
      ${A.stat('Javobsiz', A.num(s.missed), s.missed_open ? `<b>${s.missed_open}</b> tasiga hali qo'ng'iroq qilinmagan` : "hammasiga qayta qo'ng'iroq qilingan", s.missed_open ? 'danger' : '', '#/calls?tab=list&f=dir:missed')}
      ${A.stat("O'rtacha qayta javob", s.callback_minutes == null ? '—' : `${s.callback_minutes} daq`, "javobsizdan keyin qo'ng'iroq qilinguncha")}
      ${A.stat('Umumiy suhbat vaqti', durLong(s.talk), `kiruvchi ${durLong(s.talk_in)} · chiquvchi ${durLong(s.talk_out)}`)}
      ${A.stat("O'rtacha suhbat", dur(s.avg_talk), `${s.talked} ta gaplashilgan qo'ng'iroq bo'yicha`)}
      ${A.stat('Eng uzun suhbat', dur(s.longest), callWho(s.longest_call), '', callLink(s.longest_call))}
      ${A.stat('Eng qisqa suhbat', dur(s.shortest), callWho(s.shortest_call), '', callLink(s.shortest_call))}
      ${A.stat('Yangi raqamlar', A.num(s.new_numbers), `bazada yo'q: ${s.unknown}`, 'warn', '#/calls?tab=list&f=first:1')}
    </div>`;
    const hours = s.by_hour.filter((h) => h.hour >= 7 && h.hour <= 22);
    const hourChart = A.chart({
      type: 'bar',
      data: { labels: hours.map((h) => `${h.hour}:00`), datasets: [
        { label: 'Kiruvchi', data: hours.map((h) => h.in), backgroundColor: '#27ae60', stack: 's' },
        { label: 'Chiquvchi', data: hours.map((h) => h.out), backgroundColor: '#2f80ed', stack: 's' },
        { label: 'Javobsiz', data: hours.map((h) => h.missed), backgroundColor: '#eb5757', stack: 's' }] },
      options: { scales: { x: { stacked: true }, y: { stacked: true, ticks: { precision: 0 } } } },
    });
    const dayChart = s.by_day.length > 1 ? A.chart({
      type: 'line',
      data: { labels: s.by_day.map((d) => A.fdate(d.date).slice(0, 5)), datasets: [
        { label: 'Jami', data: s.by_day.map((d) => d.n), borderColor: '#F26A1B', tension: 0.3 },
        { label: 'Javobsiz', data: s.by_day.map((d) => d.missed), borderColor: '#eb5757', tension: 0.3 }] },
      options: { scales: { y: { ticks: { precision: 0 } } } },
    }, 220) : '';
    const durChart = s.talked ? A.chart({
      type: 'bar',
      data: { labels: s.by_duration.map((d) => d.label), datasets: [{ label: "Qo'ng'iroqlar", data: s.by_duration.map((d) => d.n), backgroundColor: '#F26A1B' }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { ticks: { precision: 0 } } } },
    }, 220) : '';
    const src = A.table([{ h: 'Manba', f: (r) => esc(r.name) }, { h: "Qo'ng'iroqlar", cls: 'num', f: (r) => r.n }, { h: 'Raqamlar', cls: 'num', f: (r) => r.numbers }],
      s.by_source, { empty: "Bazadagi lidlardan qo'ng'iroq yo'q" });
    const sts = A.table([{ h: 'Lid statusi', f: (r) => esc(r.label) }, { h: 'Raqamlar', cls: 'num', f: (r) => r.n }], s.by_lead_status, { empty: '—' });
    const fn = s.funnel;
    const pctOf = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');
    const funnel = fn ? `<div class="card"><h3>Qo'ng'iroq → lid → shartnoma</h3>
      <div class="conv"><div><span class="muted small">Qo'ng'iroq qilgan raqamlar</span><b>${fn.callers}</b></div>
      <div><span class="muted small">Lidi bor (${pctOf(fn.leads, fn.callers)})</span><b>${fn.leads}</b></div>
      <div><span class="muted small">O'qishni boshlagan (${pctOf(fn.started, fn.leads)})</span><b>${fn.started}</b></div>
      <div><span class="muted small">Shartnoma tuzilgan (${pctOf(fn.contracts, fn.leads)})</span><b>${fn.contracts}</b></div>
      <div><span class="muted small">Lidsiz raqamlar</span><b>${fn.no_lead}</b></div></div>
      ${A.table([{ h: 'Manba', f: (r) => esc(r.name) }, { h: 'Raqamlar', cls: 'num', f: (r) => r.callers }, { h: 'Lidlar', cls: 'num', f: (r) => r.leads }, { h: 'Boshlagan', cls: 'num', f: (r) => r.started }, { h: 'Shartnoma', cls: 'num', f: (r) => r.contracts }, { h: 'Konversiya', cls: 'num', f: (r) => pctOf(r.contracts, r.callers) }], s.funnel_by_source, { empty: "Bazadagi lidlardan qo'ng'iroq yo'q" })}</div>` : '';
    return `${cards}
      ${funnel}
      <div class="grid-2"><div class="card"><h3>Soatlar bo'yicha</h3>${hourChart}</div>${dayChart ? `<div class="card"><h3>Kunlar bo'yicha</h3>${dayChart}</div>` : ''}</div>
      ${durChart ? `<div class="grid-2"><div class="card"><h3>Suhbat davomiyligi bo'yicha</h3>${durChart}</div></div>` : ''}
      <div class="grid-2"><div class="card"><h3>Lid manbasi bo'yicha</h3>${src}</div><div class="card"><h3>Qo'ng'iroq qilganlarning lid statusi</h3>${sts}</div></div>`;
  }

  /* ---------- Qurilmalar ---------- */
  function devicesView() {
    const help = `<div class="alert info">${A.icon('phone')}<div><b>Telefonni ulash:</b> 1) telefonga «Codial qo'ng'iroqlar» ilovasini (APK) o'rnating;
      2) ilovada «Ulash kodi»ga shu yerdagi 8 belgili kodni kiriting (kod 1 soat amal qiladi); 3) ruxsatlarni bering va batareya tejashni o'chiring.
      Yangi kod olinsa, eski ulanish bekor bo'ladi.</div></div>`;
    const table = A.table(
      [
        { h: 'Qurilma', f: (d) => `<b>${esc(d.name)}</b>${d.phone ? `<br><small class="muted">${fphone(d.phone)}</small>` : ''}` },
        { h: 'Holat', f: (d) => (d.status !== 'Faol' ? A.badge('Nofaol', 'gray') : d.paired ? A.badge('Ulangan', 'green') : A.badge('Ulanmagan', 'orange')) },
        { h: 'Ulash kodi', f: (d) => (d.pair_code ? `<code class="pair-code">${d.pair_code.slice(0, 4)}-${d.pair_code.slice(4)}</code><br><small class="muted">${A.fdt(d.pair_expires_at)} gacha</small>` : '—') },
        { h: 'Oxirgi aloqa', f: (d) => `${A.fdt(d.last_seen_at)}${d.app_version ? `<br><small class="muted">v${esc(d.app_version)}</small>` : ''}` },
        { h: '', f: (d) => `<button class="btn sm" data-act="dev-code" data-id="${d.id}">Yangi kod</button>
          ${A.can('calls', 'e') ? `<button class="btn sm ghost" data-act="dev-toggle" data-id="${d.id}">${d.status === 'Faol' ? "O'chirish" : 'Yoqish'}</button>` : ''}` },
      ],
      devices, { empty: "Qurilma qo'shilmagan" },
    );
    return `${help}<div class="row gap" style="margin:8px 0">${A.btn("Qurilma qo'shish", 'dev-new', { icon: 'plus' })}</div>${table}`;
  }

  A.act['dev-new'] = () => {
    const br = A.branchIds();
    A.form({
      title: "Qo'ng'iroq qurilmasi",
      values: { branch: br[0], name: 'Qabul telefoni' },
      fields: [
        { name: 'name', label: 'Nomi', required: true },
        { name: 'phone', label: 'SIM raqami (+998 siz)', placeholder: '998204432', validate: (t) => (t && !/^\d{9}$/.test(t) ? "9 sondan iborat bo'lsin" : '') },
        { name: 'branch', label: 'Filial', type: 'select', required: true, show: () => br.length > 1, options: () => br.map((id) => [id, A.branchName(id)]) },
      ],
      async onSubmit(x) {
        const d = await A.http.post('/call-devices/', { name: x.name, phone: x.phone || '', branch: x.branch || br[0] });
        A.toast(`Qo'shildi. Ulash kodi: ${d.pair_code}`);
        A.refresh();
      },
    });
  };
  A.act['dev-code'] = (el) => {
    if (!confirm("Yangi kod olinsa, telefon qayta ulanishi kerak bo'ladi. Davom etamizmi?")) return;
    A.http.post(`/call-devices/${el.dataset.id}/pair-code/`).then((d) => { A.toast(`Ulash kodi: ${d.pair_code}`); A.refresh(); }, fail);
  };
  A.act['dev-toggle'] = (el) => {
    const d = devices.find((x) => String(x.id) === el.dataset.id);
    A.http.patch(`/call-devices/${d.id}/`, { status: d.status === 'Faol' ? 'Nofaol' : 'Faol' }).then(() => A.refresh(), fail);
  };

  /* ---------- SMS (2026-10-22): qabul telefoni orqali to'lov eslatmasi ----------
     Administrator «To'lovga tavsiya»dan tanlab yuboradi → navbat → telefondagi ilova o'z SIM'idan yuboradi. Server: /sms/, /sms-templates/ */
  const SK = 'smsj';
  const SMS_STATES = ['Navbatda', 'Yuborilmoqda', 'Yuborildi', 'Xato', 'Bekor qilindi', 'Qabul qilindi'];
  const SMS_TONE = { Navbatda: 'orange', Yuborilmoqda: 'blue', Yuborildi: 'green', Xato: 'red', 'Bekor qilindi': 'gray', 'Qabul qilindi': 'blue' };
  const MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'];
  const PH = [['talaba', 'ism-familiya'], ['ism', 'ismi'], ['kurs', 'kurs'], ['guruh', 'guruh'], ['oy', 'oy nomi'], ['summa', 'summa'], ['muddat', 'muddat']];
  const DEFAULT_TEXT = "Assalomu alaykum! {talaba}ning {oy} oyi uchun to'lovi {summa} so'm. To'lov muddati: {muddat}. Codial o'quv markazi";
  const date2 = (k, ph) => `<input class="f-input" type="date" data-filter="${SK}:${k}" title="${ph}" value="${esc(A.q(`${SK}:${k}`, ''))}">`;
  let smsList = { results: [] };
  let smsSum = null;
  let tpls = [];
  let rules = [];

  // Server bilan bir xil: o'zbekcha apostroflar GSM-7 da yo'q — bitta shunday belgi SMS narxini 2–3 barobar oshiradi
  const PLAIN = { 'ʻ': "'", 'ʼ': "'", '‘': "'", '’': "'", '`': "'", '«': '"', '»': '"', '“': '"', '”': '"', '—': '-', '–': '-', '…': '...' };
  const GSM = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà";
  const GSM_EXT = '^{}\\[~]|€';
  A.smsPlain = (t) => String(t || '').replace(/[ʻʼ‘’`«»“”—–…]/g, (c) => PLAIN[c]).trim();
  A.smsParts = (t) => {
    const chars = [...t];
    if (chars.every((c) => GSM.includes(c) || GSM_EXT.includes(c))) {
      const n = chars.reduce((s, c) => s + (GSM_EXT.includes(c) ? 2 : 1), 0);
      return { n, parts: n <= 160 ? 1 : Math.ceil(n / 153), gsm: true };
    }
    return { n: chars.length, parts: chars.length <= 70 ? 1 : Math.ceil(chars.length / 67), gsm: false };
  };
  const ctxOf = (c, month) => ({
    talaba: `${c.student_data.first_name} ${c.student_data.last_name}`.trim(), ism: c.student_data.first_name,
    kurs: A.courseName(c.course), guruh: A.groupName(c.group),
    oy: MONTHS[Number((month || c.deadline).slice(5, 7)) - 1], summa: A.num(c.to_pay), muddat: `${c.deadline.slice(8, 10)}.${c.deadline.slice(5, 7)}`,
  });
  const fill = (text, ctx) => A.smsPlain(text).replace(/\{(\w+)\}/g, (m, k) => (k in ctx ? ctx[k] : m));
  const phHelp = () => `O'rinbosarlar: ${PH.map(([k, l]) => `<code>{${k}}</code> ${l}`).join(', ')}`;
  const countHTML = (t) => {
    const p = A.smsParts(A.smsPlain(t));
    return `${p.n} belgi · <b>${p.parts}</b> SMS${p.gsm ? '' : ' <span class="t-red">(kirill yoki maxsus belgi bor — har SMS 70 belgi)</span>'}`;
  };

  async function loadSms() {
    const q = new URLSearchParams({ page: A.q(`${SK}:page`, 1) });
    for (const k of ['from', 'to', 'status', 'dir', 'known', 'delivery', 'search']) {
      const v = A.q(`${SK}:${k}`, '');
      if (v) q.set(k === 'search' ? 'q' : k, v);
    }
    [smsList, smsSum, tpls, rules] = await Promise.all([A.http.get('/sms/?' + q), A.http.get('/sms/summary/?' + q), A.http.get('/sms-templates/'),
      A.http.get('/sms-rules/')]);
  }

  function smsView() {
    const s = smsSum || { by_status: {}, waiting_devices: [] };
    const by = s.by_status;
    const stale = s.waiting_devices.filter((d) => !d.last_seen_at || Date.now() - new Date(d.last_seen_at) > 5 * 60e3);
    const warn = stale.length
      ? `<div class="alert warn">${A.icon('alert')}<div>Navbatda SMS bor, lekin <b>${stale.map((d) => esc(d.name)).join(', ')}</b> oxirgi marta ${stale.map((d) => A.fdt(d.last_seen_at)).join(', ')} da aloqaga chiqqan. Telefonda internet va «Codial qo'ng'iroqlar» ilovasi yoqilganini tekshiring — SMS telefon ulanganda ketadi.</div></div>` : '';
    const card = (st, label, tone) => A.stat(label, A.num(by[st] || 0), '', by[st] && tone ? tone : '');
    const cards = `<div class="stats">${card('Yuborildi', 'Yuborildi')}${A.stat('SMS bo\'laklari', A.num(s.parts || 0), "yuborilganlar bo'yicha (tarif shunga qarab)")}
      ${card('Navbatda', 'Navbatda', 'warn')}${card('Yuborilmoqda', 'Yuborilmoqda')}${card('Xato', 'Xato', 'danger')}</div>`;
    const canA = A.can('sms', 'a');
    const canE = A.can('sms', 'e');
    const table = A.table([
      { h: 'Vaqt', f: (m) => (m.direction === 'Kiruvchi'
        ? `${A.badge('↙ Kelgan', 'blue')}<br><small class="muted">${A.fdt(m.sent_at || m.created_at)}</small>`
        : `${A.badge('↗ Yuborilgan', 'gray')}<br><small class="muted">${A.fdt(m.created_at)} · ${esc(m.created_by_name)}</small>`) },
      { h: 'Kim', f: smsWho },
      { h: 'Matn', f: (m) => `<span class="small">${esc(m.text)}</span>${m.parts > 1 ? ` <span class="muted small">(${m.parts} SMS)</span>` : ''}` },
      { h: 'Holat', f: (m) => (m.direction === 'Kiruvchi' ? '' : `${A.badge(m.status, SMS_TONE[m.status])}${deliveryBadge(m)}${m.sent_at ? `<br><small class="muted">${A.fdt(m.sent_at)}</small>` : ''}${m.error ? `<br><small class="t-red">${esc(m.error)}</small>` : ''}${m.detail ? `<br><small class="muted" title="Telefon ma'lumoti">${esc(m.detail)}</small>` : ''}`) },
      { h: '', f: (m) => `${canA && ['Xato', 'Bekor qilindi'].includes(m.status) ? `<button class="btn sm" data-act="sms-retry" data-id="${m.id}">Qayta yuborish</button>` : ''}${canE && m.status === 'Navbatda' ? `<button class="btn sm ghost" data-act="sms-cancel" data-id="${m.id}">Bekor qilish</button>` : ''}` },
    ], smsList.results, { empty: "SMS yo'q. Yuborish: Qarzdorlar → «To'lovga tavsiya» → «SMS yuborish»" });
    const tplTable = A.table([
      { h: 'Nomi', f: (t) => `<b>${esc(t.name)}</b>${t.status !== 'Faol' ? ' ' + A.badge('Nofaol', 'gray') : ''}` },
      { h: 'Matn', f: (t) => `<span class="small">${esc(t.text)}</span><br><small class="muted">${countHTML(t.text)}</small>` },
      { h: '', f: (t) => `${canE ? `<button class="btn sm ghost" data-act="sms-tpl" data-id="${t.id}">✎</button>` : ''}${A.can('sms', 'd') ? `<button class="btn sm ghost" data-act="sms-tpl-del" data-id="${t.id}">🗑</button>` : ''}` },
    ], tpls, { empty: "Qolip yo'q — «Qolip qo'shish» bilan yarating" });
    const qBtn = canE && by['Navbatda'] ? A.btn('Navbatni bekor qilish', 'sms-cancel-all', { cls: 'ghost' }) : '';
    return `${warn}
      ${rulesView()}
      <div class="card"><div class="row gap" style="justify-content:space-between;align-items:center"><h3>SMS qoliplari (to'lov eslatmasi uchun)</h3>${canA ? A.btn("Qolip qo'shish", 'sms-tpl', { icon: 'plus' }) : ''}</div>
        <p class="muted small">Qolipni administratorlar o'zi yozadi. ${phHelp()}</p>${tplTable}</div>
      ${cards}<div class="row gap" style="margin:8px 0">${qBtn}</div>${table}${A.pager(SK, smsList)}`;
  }

  // Yetkazilish (operator xabari): yetdi / yetmadi; bo'sh — operator xabar bermagan (yuborildi, lekin yetganligi noma'lum)
  const deliveryBadge = (m) => (m.status !== 'Yuborildi' ? '' : m.delivery === 'Yetkazildi' ? ` ${A.badge('✓✓ Yetkazildi', 'green')}`
    : m.delivery === 'Yetkazilmadi' ? ` ${A.badge('✕ Yetkazilmadi', 'red')}` : ` <span class="muted small" title="Operator yetkazilganlik haqida xabar bermagan">yetkazilishi noma'lum</span>`);
  // Jurnalda «Kim»: talaba (shartnoma yoki lid havolasi), vasiy; noma'lum raqamdan kelgan SMS — «＋ Lid yaratish»
  function smsWho(m) {
    const ph = `<small class="muted">${m.recipient ? `${esc(m.recipient)} · ` : ''}${fphone(m.phone)}</small>`;
    if (m.student_name) {
      const link = m.contract ? `<a href="#/contracts/${m.contract}">${esc(m.student_name)}</a>`
        : m.lead && A.can('leads') ? `<a href="#" data-act="lead-open" data-id="${m.lead}">${esc(m.student_name)}</a>` : esc(m.student_name);
      return `${link}<br>${ph}`;
    }
    if (m.parent_name) return `${esc(m.parent_name)} <small class="muted">(vasiy)</small><br>${ph}`;
    const btn = m.direction === 'Kiruvchi' && A.can('leads', 'a') ? `<br><button class="btn sm ghost" data-act="sms-lead" data-id="${m.id}">＋ Lid yaratish</button>` : '';
    return `<span class="muted">Noma'lum</span><br>${ph}${btn}`;
  }
  A.act['sms-lead'] = async (el) => {
    const m = smsList.results.find((x) => String(x.id) === el.dataset.id);
    const free = await A.http.get('/students/?free=1&page_size=200');
    A.leadForm(null, free.results, { phone1: m.phone, comment: `SMS ${A.fdt(m.sent_at || m.created_at)}: ${m.text}`.slice(0, 500) });
  };

  /* SMS statistikasi (davr bo'yicha): holatlar, bo'laklar (tarif), kunlar, kimga, kim yubordi, SMS'dan keyin to'lov qilganlar */
  let smsSt = null;
  async function loadSmsStats() {
    const q = new URLSearchParams();
    for (const k of ['from', 'to']) {
      const v = A.q(`${SK}:${k}`, '');
      if (v) q.set(k, v);
    }
    smsSt = await A.http.get('/sms/summary/?' + q);
  }
  function smsStatsView() {
    const s = smsSt;
    if (!s) return '';
    const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');
    const cards = `<div class="stats">
      ${A.stat('Yuborildi', A.num(s.sent), `jami ${A.num(s.total)} ta SMS`, '', '#/calls?tab=sms')}
      ${A.stat('Yetkazildi', A.num(s.delivered), `${pct(s.delivered, s.sent)} · operator tasdiqlagan`)}
      ${A.stat('Yetkazilmadi', A.num(s.undelivered), `yetkazilishi noma'lum: ${A.num(Math.max(0, s.sent - s.delivered - s.undelivered))}`, s.undelivered ? 'danger' : '')}
      ${A.stat("SMS bo'laklari", A.num(s.parts), "tarif shunga qarab hisoblanadi")}
      ${A.stat('Talabalar', A.num(s.students), 'SMS olgan talabalar (shartnomalar)')}
      ${A.stat("SMS'dan keyin to'lov qildi", A.num(s.paid_after), `${pct(s.paid_after, s.students)} · ${A.money(s.paid_after_sum)}`)}
      ${A.stat('Navbatda', A.num(s.queued), 'telefon hali yubormagan', s.queued ? 'warn' : '')}
      ${A.stat('Xato', A.num(s.failed), 'qayta yuborish — SMS tabida', s.failed ? 'danger' : '')}
      ${A.stat('Kelgan SMS', A.num(s.incoming), `${A.num(s.incoming_numbers)} ta raqamdan`, '', '#/calls?tab=sms')}
      ${A.stat("Noma'lum raqamlardan", A.num(s.incoming_unknown), "bazada yo'q — yangi mijoz bo'lishi mumkin", s.incoming_unknown ? 'warn' : '')}
      ${A.stat('Eslatmaga javob yozdi', A.num(s.replied), `${pct(s.replied, s.students)} · SMS olgan talabalardan`)}
    </div>`;
    const dayChart = s.by_day.length ? A.chart({
      type: 'bar',
      data: { labels: s.by_day.map((d) => A.fdate(d.date).slice(0, 5)), datasets: [
        { label: 'Yuborildi', data: s.by_day.map((d) => d.sent), backgroundColor: '#27ae60', stack: 's' },
        { label: 'Xato', data: s.by_day.map((d) => d.failed), backgroundColor: '#eb5757', stack: 's' },
        { label: 'Kelgan', data: s.by_day.map((d) => d.incoming), backgroundColor: '#2f80ed', stack: 'in' }] },
      options: { scales: { x: { stacked: true }, y: { stacked: true, ticks: { precision: 0 } } } },
    }, 220) : A.empty("Bu davrda SMS yo'q");
    const tbl = (rows, h) => A.table([{ h, f: (r) => esc(r.label) }, { h: 'SMS', cls: 'num', f: (r) => A.num(r.n) }], rows, { empty: '—' });
    return `${cards}
      <div class="card"><h3>Kunlar bo'yicha</h3>${dayChart}</div>
      <div class="grid-2"><div class="card"><h3>Kimga (yuborilganlar)</h3>${tbl(s.by_recipient, 'Kimga')}</div>
      <div class="card"><h3>Kim yubordi</h3>${tbl(s.by_user, 'Xodim')}</div></div>
      <p class="muted small">«SMS'dan keyin to'lov qildi» — birinchi SMS kunidan keyin shartnomaga to'lov tushgan talabalar (SMS sababchi ekani shart emas).</p>`;
  }

  /* Avtomatik SMS (2026-10-23): 5 ta qoida — o'zi ketadi. Boshida o'chiq; matn va vaqtni administratorlar o'zgartiradi, yoqishdan oldin kimlarga ketishi ko'rinadi */
  // Belgi/SMS sonini namuna qiymatlar bilan hisoblaymiz (o'rinbosarning o'zi emas, haqiqiy matn uzunligi)
  const SAMPLE = { ism: 'Muhsinjon', talaba: 'Muhsinjon Karimov', kurs: 'Kompyuter savodxonligi', guruh: 'Kompyuter savodxonligi 192', oy: 'noyabr', summa: '450 000',
    muddat: '10.11', muddat_kun: '10', bonus: '75 000', kun: '5', keyingi_oy: 'dekabr', kecha: 'Kecha', sana: '21.10' };
  const ruleCount = (t) => countHTML(fill(t || '', SAMPLE));
  const RULE_ORDER = ['lead', 'contract', 'demo', 'bot_reminder', 'month_start', 'prepay_bonus', 'absence'];
  const RULE_EMOJI = { lead: '🆕', contract: '📝', demo: '🎓', bot_reminder: '🤖', month_start: '📅', prepay_bonus: '🎁', absence: '📵' };
  const ruleTime = (r) => (r.scheduled ? `${r.day ? `har oyning ${r.day}-sanasi` : 'har kuni'}, ${r.send_time || '—'}` : "voqea bo'lishi bilan");
  function rulesView() {
    if (!rules.length) return '';
    const canE = A.can('sms', 'e');
    const table = A.table([
      { h: 'Qoida', f: (r) => `${RULE_EMOJI[r.key] || ''} <b>${esc(r.label)}</b><br><small class="muted">${esc(r.when)}</small>` },
      { h: 'Matn', f: (r) => `<span class="small">${esc(r.text)}</span><br><small class="muted">${ruleCount(r.text)}</small>` },
      { h: 'Vaqti', f: (r) => `<span class="small">${esc(ruleTime(r))}</span>` },
      { h: 'Holat', f: (r) => (r.enabled ? A.badge('Yoqilgan', 'green') : A.badge("O'chiq", 'gray')) },
      { h: '', f: (r) => `<button class="btn sm ghost" data-act="rule-preview" data-id="${r.id}">Ko'rish</button>
        ${canE ? `<button class="btn sm ghost" data-act="rule-edit" data-id="${r.id}" title="Matn va vaqtni o'zgartirish">✎</button>
        <button class="btn sm ${r.enabled ? 'ghost' : 'primary'}" data-act="rule-toggle" data-id="${r.id}">${r.enabled ? "O'chirish" : 'Yoqish'}</button>` : ''}` },
    ], [...rules].sort((a, b) => RULE_ORDER.indexOf(a.key) - RULE_ORDER.indexOf(b.key)), { empty: '—' });
    return `<div class="card"><h3>Avtomatik SMS</h3>
      <p class="muted small">Bu SMS'lar o'zi ketadi (administrator bosishi shart emas). Boshida hammasi <b>o'chiq</b>: matnni tekshiring, «Ko'rish» bilan kimlarga ketishini ko'ring va yoqing.
        Yoqilishdan oldingi voqealarga SMS ketmaydi. Raqam mijozlar botiga ulangan bo'lsa, xabar SMS o'rniga <b>botga</b> boradi; ulanmaganlarga SMS ketadi va oxiriga bot havolasi qo'shiladi. Telefon aloqasiz bo'lsa yoki SMS xato bo'lsa, Bosh menejerga Telegram'dan xabar boradi.</p>${table}</div>`;
  }
  const findRule = (id) => rules.find((r) => String(r.id) === String(id));
  A.act['rule-preview'] = async (el) => {
    const r = findRule(el.dataset.id);
    const v = await A.http.get(`/sms-rules/${r.id}/preview/`).catch(fail);
    if (!v) return;
    const lines = [`<div class="note info" style="white-space:pre-wrap">${esc(v.sample)}</div><small class="muted">${countHTML(v.sample)}${v.real ? '' : ' · namuna ism va summa bilan'}</small>`];
    if (v.info) lines.push(`<p class="small muted">${esc(v.info)}</p>`);
    if (v.scheduled) {
      lines.push(v.note ? `<p class="t-red">${esc(v.note)}</p>` : `<p><b>${v.students}</b> ta talaba, <b>${v.messages}</b> ta SMS — hozir shu hisob bo'yicha ketgan bo'lardi (${esc(ruleTime(r))}).</p>`);
      if (v.names.length) lines.push(`<p class="small muted">Masalan: ${v.names.map(esc).join(', ')}${v.students > v.names.length ? ' …' : ''}</p>`);
    }
    A.modal({ title: r.label, body: lines.join(''), footer: '<button class="btn primary" data-close>Yopish</button>' });
  };
  A.act['rule-edit'] = (el) => {
    const r = findRule(el.dataset.id);
    A.form({
      title: r.label,
      values: { text: r.text, send_time: r.send_time || '', day: r.day || '' },
      fields: [
        { name: 'note', type: 'note', text: () => esc(r.when) },
        { name: 'text', label: 'Matn', type: 'textarea', required: true },
        { name: 'count', type: 'computed', label: '', compute: (x) => `${ruleCount(x.text)}<br><span class="small">O'rinbosarlar: ${r.placeholders.map((p) => `<code>{${p.key}}</code> ${esc(p.label)}`).join(', ')}</span>` },
        { name: 'send_time', label: 'Yuborish vaqti', type: 'time', required: true, show: () => r.scheduled },
        { name: 'day', label: 'Oyning kuni (1–28)', type: 'number', min: 1, max: 28, show: () => r.scheduled && r.day != null },
        { name: 'reset', type: 'note', text: () => `<a href="#" data-reset>Standart matnni qaytarish</a>` },
      ],
      async onSubmit(x) {
        const body = { text: x.text };
        if (r.scheduled) body.send_time = x.send_time;
        if (r.scheduled && r.day != null && x.day) body.day = Number(x.day);
        await A.http.patch(`/sms-rules/${r.id}/`, body);
        A.toast('Saqlandi');
        A.refresh();
      },
    });
    document.querySelector('[data-reset]')?.addEventListener('click', (e) => {
      e.preventDefault();
      const ta = document.querySelector('.modal textarea');
      if (ta) { ta.value = r.default_text; ta.dispatchEvent(new Event('input', { bubbles: true })); }
    });
  };
  A.act['rule-toggle'] = async (el) => {
    const r = findRule(el.dataset.id);
    if (r.enabled) {
      if (!(await A.confirm(`«${esc(r.label)}» o'chirilsinmi? Yangi SMS ketmaydi (navbatdagilari ketadi).`, "O'chirish", true))) return;
    } else {
      const v = await A.http.get(`/sms-rules/${r.id}/preview/`).catch(fail);
      if (!v) return;
      if (v.note) return A.toast(v.note.replace(/<[^>]+>/g, ''), 'warn');
      const now = v.scheduled ? `<br>Bugun: <b>${v.students}</b> ta talaba, <b>${v.messages}</b> ta SMS.${v.runs_today ? " <b>Vaqti allaqachon o'tgan — yoqsangiz, bugungi SMS'lar darrov navbatga qo'yiladi.</b>" : ''}` : '';
      const info = v.info ? `<br><small class="muted">${esc(v.info)}</small>` : '';
      if (!(await A.confirm(`«${esc(r.label)}» yoqilsinmi?<br><small class="muted">${esc(r.when)}</small><br><br><i>${esc(v.sample)}</i>${info}${now}`, 'Yoqish'))) return;
    }
    A.http.patch(`/sms-rules/${r.id}/`, { enabled: !r.enabled }).then(() => { A.toast(r.enabled ? "O'chirildi" : 'Yoqildi'); A.refresh(); }, fail);
  };

  const findTpl = (id) => tpls.find((t) => String(t.id) === String(id));
  A.act['sms-tpl'] = (el) => {
    const t = el.dataset.id ? findTpl(el.dataset.id) : null;
    const br = A.branchIds();
    A.form({
      title: t ? 'SMS qolipi' : 'Yangi SMS qolipi',
      values: t ? { ...t } : { name: "To'lov eslatmasi", text: DEFAULT_TEXT, status: 'Faol', branch: br[0] },
      fields: [
        { name: 'name', label: 'Nomi', required: true },
        { name: 'branch', label: 'Filial', type: 'select', required: true, show: () => !t && br.length > 1, options: () => br.map((id) => [id, A.branchName(id)]) },
        { name: 'text', label: 'Matn', type: 'textarea', required: true },
        { name: 'count', type: 'computed', label: '', compute: (x) => `${countHTML(x.text || '')}<br><span class="small">${phHelp()}</span>` },
        { name: 'status', label: 'Holat', type: 'seg', options: [['Faol', 'Faol'], ['Nofaol', 'Nofaol']], show: () => !!t },
      ],
      async onSubmit(x) {
        const body = { name: x.name, text: x.text, status: x.status || 'Faol' };
        if (t) await A.http.patch(`/sms-templates/${t.id}/`, body);
        else await A.http.post('/sms-templates/', { ...body, branch: x.branch || br[0] });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['sms-tpl-del'] = async (el) => {
    const t = findTpl(el.dataset.id);
    if (!(await A.confirm(`«${esc(t.name)}» qolipi o'chirilsinmi?`, "O'chirish", true))) return;
    A.http.del(`/sms-templates/${t.id}/`).then(() => { A.toast("O'chirildi"); A.refresh(); }, fail);
  };
  A.act['sms-retry'] = (el) => A.http.post(`/sms/${el.dataset.id}/retry/`).then(() => { A.toast('Navbatga qo\'yildi'); A.refresh(); }, fail);
  A.act['sms-cancel'] = (el) => A.http.post(`/sms/${el.dataset.id}/cancel/`).then(() => { A.toast('Bekor qilindi'); A.refresh(); }, fail);
  A.act['sms-cancel-all'] = async () => {
    if (!(await A.confirm("Navbatdagi barcha SMS bekor qilinsinmi? Telefon olib bo'lganlari baribir ketadi.", 'Bekor qilish', true))) return;
    A.http.post('/sms/cancel-all/').then((r) => { A.toast(`Bekor qilindi: ${r.cancelled} ta`); A.refresh(); }, fail);
  };

  /* «To'lovga tavsiya»dan: tanlangan talabalarga to'lov eslatmasi. Avval server hisobi (nechta raqam, nechtasi oldin olgan), keyin tasdiq. */
  A.smsDueForm = async (rows, month) => {
    if (!rows.length) return;
    const list = (await A.http.get('/sms-templates/').catch(() => [])).filter((t) => t.status === 'Faol');
    const first = list[0];
    A.form({
      title: rows.length === 1 ? `SMS: ${rows[0].student_data.full_name}` : `SMS: ${rows.length} ta talaba`,
      submit: 'Davom etish',
      values: { template: first ? first.id : '', text: first ? first.text : DEFAULT_TEXT, skip_sent: true },
      fields: [
        { name: 'who', type: 'note', text: () => `${rows.length} ta talabaning <b>hamma raqamiga</b> (1- va 2-telefon, vasiy) ${month ? MONTHS[Number(month.slice(5, 7)) - 1] + ' oyi uchun ' : ''}to'lov eslatmasi qabul telefonidan yuboriladi.` },
        { name: 'template', label: 'Qolip', type: 'select', placeholder: list.length ? 'Qolipsiz (matnni yozing)' : "Qolip yo'q — Qo'ng'iroqlar → SMS'da qo'shing", options: () => list.map((t) => [t.id, t.name]),
          onChange: (x) => { const t = list.find((y) => String(y.id) === String(x.template)); if (t) x.text = t.text; } },
        { name: 'text', label: 'Matn', type: 'textarea', required: true },
        { name: 'preview', type: 'computed', label: `Namuna (${rows[0].student_data.first_name})`, compute: (x) => {
          const msg = fill(x.text || '', ctxOf(rows[0], month));
          return `<div class="note info" style="white-space:pre-wrap">${esc(msg)}</div><small class="muted">${countHTML(msg)} · ${phHelp()}</small>`;
        } },
        { name: 'skip_sent', label: 'Shu oy SMS olgan raqamlarga qayta yuborilmasin', type: 'checkbox' },
      ],
      async onSubmit(x) {
        const body = { contracts: rows.map((c) => c.id), month, text: x.text, template: x.template || null, skip_sent: !!x.skip_sent };
        const pv = await A.http.post('/sms/dues/', { ...body, preview: true });
        const notes = [
          pv.skipped_sent ? `${pv.skipped_sent} ta raqam shu oy SMS olgan — o'tkazib yuboriladi` : '',
          pv.paid ? `${pv.paid} ta talaba to'lov qilgan yoki ro'yxatdan olingan` : '',
          pv.no_phone ? `${pv.no_phone} ta talabada telefon yo'q` : '',
          pv.no_device.length ? `<b class="t-red">${pv.no_device.map(esc).join(', ')} filialida ulangan telefon yo'q</b>` : '',
        ].filter(Boolean);
        if (!pv.messages && !pv.bot_messages) {
          return `Yuboriladigan SMS yo'q. ${notes.join('. ').replace(/<[^>]+>/g, '')}`;
        }
        const ok = await A.confirm(`<b>${pv.contracts}</b> ta talaba: <b>${pv.messages}</b> ta raqamga SMS (jami <b>${pv.parts}</b> SMS, SIM tarifidan)${pv.bot_messages ? ` va <b>${pv.bot_messages}</b> ta raqamga Telegram bot orqali (botga ulanganlar, bepul)` : ''}.
          ${notes.length ? `<br><small class="muted">${notes.join('<br>')}</small>` : ''}<br><br>Yuborilsinmi?`, 'Yuborish');
        if (!ok) return '';
        const r = await A.http.post('/sms/dues/', body);
        A.toast(`Navbatga qo'yildi: ${r.messages} ta SMS${r.bot_messages ? `, ${r.bot_messages} ta bot xabari` : ''}. Telefon bir necha daqiqada yuboradi`);
        A.refresh();
      },
    });
  };
})(window.App);

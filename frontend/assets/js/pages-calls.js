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
    title: "Qo'ng'iroqlar",
    section: 'calls',
    async load(p, q) {
      const tab = q.tab || 'list';
      if (tab === 'stats') st = await A.http.get('/calls/stats/?' + qs());
      else if (tab === 'devices') devices = await A.http.get('/call-devices/');
      else {
        list = await A.http.get('/calls/?' + qs({ page: A.q(`${K}:page`, 1) }));
        if (A.can('calls', 'a') && !devices.length) devices = await A.http.get('/call-devices/').catch(() => []);
      }
    },
    render(p, q) {
      const tab = q.tab || 'list';
      const tabs = [['list', "Qo'ng'iroqlar"], ['stats', 'Statistika'], ...(A.can('calls', 'a') ? [['devices', 'Qurilmalar']] : [])];
      const date = (k, ph) => `<input class="f-input" type="date" data-filter="${K}:${k}" title="${ph}" value="${esc(A.q(`${K}:${k}`, ''))}">`;
      const period = [date('from', 'Dan'), date('to', 'Gacha')];
      const filters = tab === 'list'
        ? A.filterBar(K, [A.fSearch(K, 'Raqam yoki ism…'), ...period,
          A.fSelect(K, 'dir', [['missed_open', "Javobsiz — qayta qo'ng'iroq qilinmagan"], ['missed', 'Javobsiz (hammasi)'], ['Kiruvchi', 'Kiruvchi'], ['Chiquvchi', 'Chiquvchi']], 'Barcha yo\'nalishlar'),
          A.fSelect(K, 'known', [['1', 'Bazada bor'], ['0', "Noma'lum raqamlar"]], 'Hamma raqamlar'),
          A.fSelect(K, 'first', [['1', 'Faqat birinchi marta']], 'Yangi va eski')])
        : tab === 'stats' ? A.filterBar(K, period) : '';
      const body = tab === 'stats' ? statsView() : tab === 'devices' ? devicesView() : listView();
      return `${A.head("Qo'ng'iroqlar", "Qabul telefonidagi qo'ng'iroqlar — tugashi bilan shu yerga tushadi. Raqam bazada bo'lsa ism va lid ma'lumoti chiqadi")}
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
        { h: 'Lid', f: (c) => (c.lead ? `${A.badge(`${c.lead_status}. ${LS[c.lead_status] || ''}`, c.lead_status === '5' ? 'green' : ['6', '7'].includes(c.lead_status) ? 'gray' : 'orange')}<br><small class="muted">${esc(c.lead_course)} · ${esc(c.lead_source)}</small>` : c.has_contract ? A.badge('Shartnoma bor', 'green') : '—') },
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
      const name = c.lead && A.can('leads') ? `<a href="#" data-act="lead-open" data-id="${c.lead}">${esc(c.student_name)}</a>` : esc(c.student_name);
      return `${name}${c.parent_name ? `<br><small class="muted">vasiy: ${esc(c.parent_name)}</small>` : ''}`;
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
  A.act['call-lead'] = async (el) => {
    const c = find(el.dataset.id);
    const free = await A.http.get('/students/?free=1&page_size=200');
    A.leadForm(null, free.results, { phone1: c.phone, comment: `Qo'ng'iroq ${A.fdt(c.started_at)} (${c.direction.toLowerCase()})${c.comment ? `: ${c.comment}` : ''}` });
  };

  /* ---------- Statistika ---------- */
  function statsView() {
    if (!st) return '';
    const s = st;
    const cards = `<div class="stats">
      ${A.stat("Jami qo'ng'iroq", A.num(s.total), `suhbat ${durLong(s.talk)}`)}
      ${A.stat('Kiruvchi (javob berilgan)', A.num(s.answered))}
      ${A.stat('Chiquvchi', A.num(s.outgoing))}
      ${A.stat('Javobsiz', A.num(s.missed), s.missed_open ? `<b>${s.missed_open}</b> tasiga hali qo'ng'iroq qilinmagan` : "hammasiga qayta qo'ng'iroq qilingan", s.missed_open ? 'danger' : '', '#/calls?tab=list')}
      ${A.stat("O'rtacha qayta javob", s.callback_minutes == null ? '—' : `${s.callback_minutes} daq`, "javobsizdan keyin qo'ng'iroq qilinguncha")}
      ${A.stat('Yangi raqamlar', A.num(s.new_numbers), `bazada yo'q: ${s.unknown}`, 'warn')}
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
    const src = A.table([{ h: 'Manba', f: (r) => esc(r.name) }, { h: "Qo'ng'iroqlar", cls: 'num', f: (r) => r.n }, { h: 'Raqamlar', cls: 'num', f: (r) => r.numbers }],
      s.by_source, { empty: "Bazadagi lidlardan qo'ng'iroq yo'q" });
    const sts = A.table([{ h: 'Lid statusi', f: (r) => esc(r.label) }, { h: 'Raqamlar', cls: 'num', f: (r) => r.n }], s.by_lead_status, { empty: '—' });
    return `${cards}
      <div class="grid-2"><div class="card"><h3>Soatlar bo'yicha</h3>${hourChart}</div>${dayChart ? `<div class="card"><h3>Kunlar bo'yicha</h3>${dayChart}</div>` : ''}</div>
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
})(window.App);

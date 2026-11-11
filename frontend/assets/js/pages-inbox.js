/* Codial ERP — Instagram/sayt lidlari (2026-11-10): reklamadan va saytdan tushgan «xom» lidlar navbati. Haqiqiy lid emas — statistika va marketolog
   KPI'siga kirmaydi. Administrator+Hisobchi (va Bosh menejer) gaplashadi: haqiqiy lidga qo'shadi, qayta aloqa vaqtini belgilaydi yoki yopadi.
   Server: /inbox-leads/ (+ summary, due, {id}/talk, {id}/link, {id}/reopen). Bosh sahifadagi «Bugungi ish» ham shu amallarni ishlatadi. */
(function (A) {
  const esc = A.esc;
  const K = 'inbox';
  const KIND = { Instagram: 'red', Facebook: 'blue', Sayt: 'green' };
  const pad = (n) => String(n).padStart(2, '0');
  const tomorrow = () => { const d = new Date(Date.now() + 864e5); d.setHours(10, 0, 0, 0); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T10:00`; };
  const fphone = (p) => (p ? `+998 ${p.slice(0, 2)} ${p.slice(2, 5)}-${p.slice(5, 7)}-${p.slice(7)}` : '');
  const tel = (p) => (p ? `<a href="tel:+998${esc(p)}">${esc(fphone(p))}</a>` : '');

  A.canInbox = () => ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI'].includes(A.role());

  let list = { results: [], count: 0 };
  let sum = { new: 0, due: 0, callback: 0 };

  const statusCell = (o) => {
    if (o.status === 'new') return A.badge('Yangi', 'orange');
    if (o.status === 'callback') {
      const late = o.callback_at && new Date(o.callback_at) <= new Date();
      return `${A.badge(late ? 'Vaqti keldi' : 'Qayta aloqa', late ? 'red' : 'blue')}<br><small class="muted">${o.callback_at ? A.fdt(o.callback_at) : ''}</small>`;
    }
    if (o.status === 'linked') return `${A.badge("Lidga qo'shildi", 'green')}<br><small class="muted">${esc(o.lead_name)}</small>`;
    return A.badge('Yopildi', 'gray');
  };
  const knownCell = (o) => (o.known ? `<span class="t-red small">⚠️ Bazada bor: ${esc(o.known.name)}</span>` : '<span class="muted">—</span>');
  const notesCell = (o) => {
    const n = o.notes || [];
    if (!n.length) return '<span class="muted">—</span>';
    const last = n[n.length - 1];
    return `<small>${esc(last.comment.slice(0, 120))}</small><br><small class="muted">${esc(last.by)} · ${A.fdt(last.at)}${n.length > 1 ? ` · ${n.length} ta izoh` : ''}</small>`;
  };
  // Telefondagi qo'ng'iroqlar bilan bog'lanish: lid tushgandan keyin shu raqamga/raqamdan bo'lgan qo'ng'iroqlar
  const DIR = { Kiruvchi: '↙', Chiquvchi: '↗', Javobsiz: '✕', 'Rad etilgan': '⊘', Bloklangan: '⊘' };
  const callsCell = (o) => {
    const c = o.calls;
    if (!c) return '<span class="muted">—</span>';
    const d = c.last_duration ? ` · ${Math.floor(c.last_duration / 60)}:${String(c.last_duration % 60).padStart(2, '0')}` : '';
    return `<small>${DIR[c.last_direction] || ''} ${esc(c.last_direction)} · ${A.fdt(c.last_at)}${d}${c.count > 1 ? ` · jami ${c.count} ta` : ''}</small>${c.note_due ? `<br>${A.badge('📞 gaplashilgan — izoh yozing', 'orange')}` : ''}`;
  };
  A.inboxCallsCell = callsCell;
  const actions = (o) => {
    if (!A.canInbox()) return '';
    const b = (act, label, cls = 'ghost') => `<button type="button" class="btn sm ${cls}" data-act="${act}" data-id="${o.id}">${label}</button>`;
    if (o.status === 'new' || o.status === 'callback') {
      return `<div class="work-act">${b('ib-talk', '💬 Gaplashdim', 'primary')}${b('ib-link', o.known && o.known.lead ? "🔗 Bazadagi lidga bog'lash" : "＋ Lidga qo'shish")}</div>`;
    }
    if (o.status === 'rejected') return b('ib-reopen', '↩️ Qayta ochish');
    return '';
  };

  A.page('inbox', {
    title: 'Instagram/sayt lidlari',
    section: 'leads',
    nav: 'inbox', // menyuda shu band yoqiladi (ruxsat — «leads» bo'limi bo'yicha, rol esa A.canInbox)
    async load(p, q) {
      const tab = q.tab || 'new';
      const qs = new URLSearchParams({ page: A.q(`${K}:page`, 1), status: tab });
      if (A.q(`${K}:search`, '')) qs.set('search', A.q(`${K}:search`));
      if (A.q(`${K}:kind`, '')) qs.set('kind', A.q(`${K}:kind`));
      [list, sum] = await Promise.all([A.http.get('/inbox-leads/?' + qs), A.http.get('/inbox-leads/summary/')]);
    },
    render(p, q) {
      if (!A.canInbox()) return A.head("Ruxsat yo'q") + `<div class="empty">Bu bo'lim faqat Bosh menejer va Administrator+Hisobchi uchun.</div>`;
      const tab = q.tab || 'new';
      const tabs = [['new', 'Yangi', sum.new], ['callback', 'Qayta aloqa', sum.callback], ['linked', "Lidga qo'shilgan", sum.linked], ['rejected', 'Yopilgan', sum.rejected]];
      const filters = A.filterBar(K, [A.fSearch(K, 'Ism, telefon yoki kurs…'), A.fSelect(K, 'kind', [['Instagram', 'Instagram'], ['Facebook', 'Facebook'], ['Sayt', 'Sayt']], 'Hamma manbalar')]);
      const cols = [
        { h: 'Tushgan', f: (o) => `<small>${A.fdt(o.received_at)}</small>` },
        { h: 'Manba', f: (o) => A.badge(o.kind, KIND[o.kind] || 'gray') },
        { h: 'Ism / telefon', f: (o) => `<b>${esc(o.name || '—')}</b><br>${tel(o.phone)}` },
        { h: 'Kurs', f: (o) => esc(o.course_name || '—') },
        { h: 'Reklama / xabar', f: (o) => `<small class="muted">${esc(o.info || '—')}</small>` },
        { h: 'Bazada', f: knownCell },
        { h: "Qo'ng'iroqlar", f: callsCell },
        { h: 'Holat', f: statusCell },
        { h: 'Oxirgi izoh', f: notesCell },
        { h: '', f: actions },
      ];
      return `${A.head('Instagram/sayt lidlari', "Reklama va saytdan tushgan lidlar. Bular haqiqiy lid emas — statistika va marketolog KPI'siga kirmaydi; gaplashib bo'lgach «Lidga qo'shish» bosiladi.")}
        ${sum.due ? `<div class="alert warn">${A.icon('alert')}<div><b>${sum.due} ta lidning qayta aloqa vaqti kelgan.</b> <a href="#/inbox?tab=callback">Ko'rish →</a></div></div>` : ''}
        ${A.tabs(tabs, tab, 'inbox')}${filters}
        ${A.table(cols, list.results, { empty: "Bu bo'limda lid yo'q ✨" })}${A.pager(K, list)}`;
    },
  });

  const getItem = (id) => A.http.get(`/inbox-leads/${id}/`);
  const fail = (e) => A.toast(e.message || 'Xatolik', 'warn');
  const done = (msg) => { A.toast(msg); A.refresh(); };

  A.act['ib-talk'] = async (el) => {
    let o;
    try { o = await getItem(el.dataset.id); } catch (e) { return fail(e); }
    A.form({
      title: `Gaplashildi: ${o.name || fphone(o.phone)}`,
      values: { result: 'cb', callback_at: tomorrow() },
      fields: [
        { name: 'note', type: 'note', text: () => 'Nima gaplashganingizni yozing. Lidga qo\'shmasangiz — qayta aloqa vaqtini belgilang: shu vaqtda bosh sahifada va botda yana chiqadi.' },
        { name: 'comment', label: 'Suhbat haqida izoh', type: 'textarea', required: true, placeholder: 'Masalan: ertaga javob beradi, ota-onasi bilan maslahatlashadi' },
        { name: 'result', label: 'Keyingi qadam', type: 'seg', options: [['cb', 'Qayta aloqa vaqti'], ['close', 'Yopish (qiziqmadi / noto\'g\'ri raqam)']] },
        { name: 'callback_at', label: 'Qayta aloqa sana va vaqti', type: 'datetime-local', show: (x) => x.result === 'cb', required: (x) => x.result === 'cb',
          validate: (t) => (t && new Date(t) < new Date(Date.now() - 6e5) ? "Bu vaqt o'tib ketgan" : '') },
      ],
      submit: 'Saqlash',
      async onSubmit(x) {
        const body = { comment: x.comment };
        if (x.result === 'close') body.close = true; else body.callback_at = x.callback_at;
        await A.http.post(`/inbox-leads/${o.id}/talk/`, body);
        done(x.result === 'close' ? 'Yopildi' : 'Qayta aloqa vaqti saqlandi');
      },
    });
  };

  const split = (full) => { const w = String(full || '').trim().split(/\s+/); return { first_name: w[0] || '', last_name: w.slice(1).join(' ') }; };
  const byName = (coll, name) => (A.rows(coll).find((r) => (r.name || '').toLowerCase().startsWith(String(name || '').toLowerCase())) || {}).id || '';

  A.act['ib-link'] = async (el) => {
    let o;
    try { o = await getItem(el.dataset.id); } catch (e) { return fail(e); }
    const link = async (leadId) => { await A.http.post(`/inbox-leads/${o.id}/link/`, { lead: leadId }); done("Lidga qo'shildi"); };
    if (o.known && o.known.lead) { // bazada shu raqamli talabaning lidi bor — yangisi ochilmaydi, shunisiga bog'lanadi
      if (await A.confirm(`Bu raqam bazada bor: <b>${esc(o.known.name)}</b>. Shu lidga bog'lansinmi?`, "Bog'lash")) {
        try { await link(o.known.lead); } catch (e) { fail(e); }
      }
      return;
    }
    const free = await A.http.get('/students/?free=1&page_size=200');
    const notes = (o.notes || []).map((n) => n.comment).join('; ');
    A.leadForm(null, free.results, {
      mode: 'new', ...split(o.name), phone1: o.phone,
      source: byName('leadSources', o.kind), course: byName('courses', o.course_name),
      comment: `${o.kind} lidi (${A.fdt(o.received_at)})${o.info ? ': ' + o.info : ''}${notes ? '. Suhbat: ' + notes : ''}`.slice(0, 500),
      onSaved: (saved) => link(saved.id).catch(fail),
    });
  };

  A.act['ib-reopen'] = async (el) => {
    try { await A.http.post(`/inbox-leads/${el.dataset.id}/reopen/`, {}); done('Qayta ochildi'); } catch (e) { fail(e); }
  };
})(window.App);

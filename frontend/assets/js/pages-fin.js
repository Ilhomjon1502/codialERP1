/* Moliya: To'lovlar, Tasdiqlashlar, G'aznalar, O'tkazmalar, Ayirboshlash, Xarajatlar, Kreditorlar (M4, server API), Foyda, Oyliklar */
(function (A) {
  const esc = A.esc;
  const ncBadge = (p) => (p.nc_status ? A.badge(p.nc_status, p.nc_status === 'Tasdiqlandi' ? 'green' : 'orange') : '');
  const cashOpts = [['CASH', 'Naqd'], ['CARD', 'Karta'], ['BANK', 'Bank']];
  const qsOf = (key, names, extra = {}) => {
    const qs = new URLSearchParams(extra);
    for (const k of names) if (A.q(`${key}:${k}`, '')) qs.set(k, A.q(`${key}:${k}`));
    return qs;
  };
  /** Pul amalidan keyin: g'azna balanslari va tasdiqlar soni serverdan yangilanadi */
  A.reloadMoney = async () => {
    const [accounts] = await Promise.all([A.http.get('/accounts/'), A.reloadPending()]);
    A.S.accounts = accounts;
    A.version++;
  };
  /** Foydalanuvchi mas'ul bo'lgan g'azna yo'q bo'lsa — bo'sh ro'yxat o'rniga tushuntirish */
  const noAccount = (name, show) => ({
    name: name + '_none', type: 'note', tone: 'warn', show,
    text: () => `Siz hech bir mos faol g'aznaning mas'uli emassiz, shuning uchun bu yerda pul qabul qilib/chiqarib bo'lmaydi.${A.isTop() ? ` <a href="#/settings?tab=accounts">Sozlamalar → G'aznalar</a> da o'zingizni g'azna mas'ullariga qo'shing.` : " Admin yoki Bosh menejerga murojaat qiling (Sozlamalar → G'aznalar → mas'ullar)."}`,
  });
  A.accBal = (id, type) => {
    const a = A.get('accounts', id) || {};
    return type ? Number((a.by_type || {})[type] || 0) : Number(a.balance || 0);
  };

  /* ===================================================== To'lovlar (server API: /payments/) */
  let pData = { results: [], by_day: {}, by_month: {}, total: 0 };
  A.page('payments', {
    title: "To'lovlar",
    section: 'payments',
    async load() {
      pData = await A.http.get('/payments/?' + qsOf('payments', ['search', 'month', 'type'], { page: A.q('payments:page', 1) }));
    },
    render() {
      return `${A.head("To'lovlar", `Guruhlash: oy → sana, jami summalar bilan · filtr bo'yicha jami: <b>${A.money(pData.total)}</b>`, (A.can('payments', 'a') ? A.btn("To'lov qabul qilish", 'pay-new', { icon: 'plus' }) : '') + A.btn('Excel', 'payments-csv', { cls: 'ghost', icon: 'download' }))}
        ${A.filterBar('payments', [A.fSearch('payments', 'Talaba, shartnoma yoki chek raqami…'), A.fSelect('payments', 'month', A.monthOptions(), 'Barcha oylar'), A.fSelect('payments', 'type', cashOpts, 'Barcha turlar')])}
        <div>${paymentGroups(pData)}${A.pager('payments', pData)}</div>`;
    },
  });
  function paymentGroups(d) {
    if (!d.results.length) return A.empty("To'lov topilmadi");
    const byM = A.groupBy(d.results, (p) => A.ym(p.date));
    return [...byM]
      .map(([ym, list]) => {
        const byD = A.groupBy(list, (p) => p.date);
        return `<section class="group-block"><h3>${A.ymLabel(ym)} <span class="muted">· ${A.money(d.by_month[ym] || 0)}</span></h3>
          ${[...byD]
            .map(([day, dl]) => `<div class="day-h">${A.fdate(day)} <span class="muted">${A.WD[A.isoWeekday(day)]}</span><b>${A.money(d.by_day[day] || 0)}</b></div>${A.table(
              [
                { h: '№', f: (p) => `<span class="muted">${p.number}</span>` },
                { h: 'Shartnoma', f: (p) => `<a href="#/contracts/${p.contract}">${esc(p.contract_name)}</a>` },
                { h: 'Summa', f: (p) => `<b>${A.num(p.amount)}</b>`, cls: 'num' },
                { h: 'Turi', f: (p) => `${p.amount ? A.CASH[p.cash_type] : '—'} ${ncBadge(p)}` },
                { h: 'Chegirma', f: (p) => (Number(p.discount) ? `${A.num(p.discount)} ${A.badge(p.disc_status, p.disc_status === 'Tasdiqlandi' ? 'green' : 'orange')}` : ''), cls: 'num' },
                { h: "G'azna / hisobchi", f: (p) => (p.cashbox ? `${esc(A.accName(p.cashbox))}<br><small class="muted">${esc(A.userName(p.accountant))}</small>` : '—') },
                { h: '', f: (p) => payActions(p) },
              ],
              dl,
            )}`)
            .join('')}</section>`;
      })
      .join('');
  }
  function payActions(p) {
    const ed = A.canEdit('payments', p);
    const del = A.canEdit('payments', p, 'date', 'd');
    return `<div class="row gap nowrap"><button class="btn sm ghost" data-act="receipt" data-id="${p.id}">Chek</button>
      ${A.can('payments', 'e') ? `<button class="btn sm ghost" data-act="pay-edit" data-id="${p.id}" ${ed.ok ? '' : `disabled title="${esc(ed.why)}"`}>✎</button>` : ''}
      ${A.can('payments', 'd') ? `<button class="btn sm ghost" data-act="pay-del" data-id="${p.id}" ${del.ok ? '' : `disabled title="${esc(del.why)}"`}>🗑</button>` : ''}</div>`;
  }
  const fetchAll = async (path, qs) => {
    qs.set('page_size', 200);
    let page = 1, out = [];
    for (;;) {
      qs.set('page', page);
      const d = await A.http.get(path + qs);
      out = out.concat(d.results);
      if (page >= (d.pages || 1)) return out;
      page++;
    }
  };
  A.act['payments-csv'] = async () => {
    const rows = await fetchAll('/payments/?', qsOf('payments', ['search', 'month', 'type']));
    A.downloadCSV('tolovlar.csv', [['№', 'Sana', 'Shartnoma', 'Summa', 'Turi', 'Chegirma', "G'azna"], ...rows.map((p) => [p.number, p.date, p.contract_name, p.amount, p.amount ? A.CASH[p.cash_type] : '', p.discount, A.accName(p.cashbox)])]);
  };

  /* ---- To'lov formasi. Tekshiruvlar serverda (finance.services._validate_payment) ---- */
  A.paymentForm = async (p, contractId) => {
    const isNew = !p;
    const top = A.isTop();
    let contracts = [];
    if (isNew && !contractId) contracts = (await A.http.get('/contracts/?page_size=200')).results;
    const cur = contractId ? await A.http.get(`/contracts/${contractId}/`) : p ? await A.http.get(`/contracts/${p.contract}/`) : null;
    if (cur) contracts = [cur];
    const cById = (id) => contracts.find((c) => c.id === id);
    const branchOf = (x) => A.get('branches', (cById(x.contract) || {}).branch) || {};
    const cashboxOpts = (x) => {
      if (!x.cash_type) return [];
      if (x.cash_type === 'CASH') return A.myAccounts().filter((a) => ['CASH', 'ALL'].includes(a.cash_type)).map((a) => [a.id, a.name]);
      const nc = branchOf(x).noncash_cashbox;
      return nc ? [[nc, A.accName(nc) + " (naqdsiz g'azna — filial sozlamasidan)"]] : [];
    };
    A.form({
      title: isNew ? "To'lov qabul qilish" : `To'lov №${p.number}`,
      values: p ? { ...p, amount: Number(p.amount), discount: Number(p.discount) || '' } : { contract: contractId || '', date: A.today(), cash_type: 'CASH', discount_type: '' },
      fields: [
        { name: 'contract', label: 'Shartnoma', type: 'select', required: true, readonly: () => !isNew || !!contractId, options: () => A.sortBy(contracts, (c) => (c.status === 'Nofaol' ? 'z' : 'a') + c.name).map((c) => [c.id, `${c.name} · ${A.groupName(c.group)} · balans ${A.num(c.balance)}${c.status === 'Nofaol' ? ' (nofaol)' : ''}`]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.contract, text: (x) => { const c = cById(x.contract); return c ? `Joriy balans: <b class="${c.balance > 0 ? 't-red' : 't-green'}">${A.money(c.balance)}</b> · ${esc(A.courseName(c.course))}` : ''; } },
        { name: 'amount', label: "To'lov miqdori", type: 'money', show: (x) => x.contract, min: 0, validate: (n) => (n < 0 ? "Manfiy summa kiritib bo'lmaydi" : '') },
        { name: 'cash_type', label: "To'lov shakli", type: 'seg', options: cashOpts, show: (x) => x.amount > 0, resets: ['cashbox', 'accountant'] },
        noAccount('cashbox', (x) => x.amount > 0 && x.cash_type && !cashboxOpts(x).length),
        { name: 'cashbox', label: "G'azna", type: 'select', auto: true, required: (x) => x.amount > 0, show: (x) => x.amount > 0 && x.cash_type && cashboxOpts(x).length, options: cashboxOpts, resets: ['accountant'], help: (x) => (x.cash_type === 'CASH' ? (top ? "Barcha faol naqd g'aznalar" : "Siz mas'ul bo'lgan faol g'aznalar") : '') },
        { name: 'accountant', label: 'Hisobchi', type: 'select', auto: true, show: (x) => x.cashbox, options: (x) => ((A.get('accounts', x.cashbox) || {}).responsible || []).map((u) => [u, A.userName(u)]) },
        { name: 'nc_note', type: 'note', tone: 'warn', show: (x) => x.amount > 0 && x.cash_type && x.cash_type !== 'CASH', text: "Naqdsiz to'lov <b>tasdiqlanmaguncha g'azna balansiga qo'shilmaydi</b>. Tasdiqlash: Admin; Bosh menejer 360 kun, Filial menejeri 7 kun ichida." },
        { name: 'discount_type', label: 'Chegirma turi (ixtiyoriy)', type: 'select', show: (x) => x.contract, placeholder: 'Chegirmasiz', options: (x) => A.rows('discountTypes').filter((d) => (top || !d.is_system) && (!d.courses.length || d.courses.includes((cById(x.contract) || {}).course))).map((d) => [d.id, `${d.name} (max ${A.num(d.max)})`]) },
        {
          name: 'discount', label: 'Chegirma summasi', type: 'money', show: (x) => x.discount_type, required: (x) => !!x.discount_type,
          validate: (n, x) => { const d = A.get('discountTypes', x.discount_type); return d && n > d.max ? `Bu chegirma turiga ${A.num(d.max)} so'mdan ortiqcha chegirma kiritib bo'lmaydi` : n <= 0 ? "Chegirma 0 dan katta bo'lsin" : ''; },
        },
        { name: 'd_note', type: 'note', tone: 'warn', show: (x) => x.discount > 0, text: 'Chegirma tasdiqlashga yuboriladi (Admin; Bosh menejer 30 kun ichida).' },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.contract, readonly: () => !top, help: () => (top ? "Admin va Bosh menejer o'tgan sanani ham kirita oladi" : 'Faqat bugungi sana bilan kiritiladi'), validate: (d) => (d > A.today() ? "Kelasi davr bilan kiritib bo'lmaydi" : '') },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.amount > 0 || x.discount > 0 },
      ],
      submit: isNew ? 'Qabul qilish va chek' : 'Saqlash',
      async onSubmit(x) {
        if (!(x.amount > 0) && !(x.discount > 0)) return "To'lov summasi yoki chegirma kiritilishi kerak";
        const amount = Number(x.amount) || 0;
        const rec = {
          amount, cash_type: amount ? x.cash_type : '', cashbox: amount && x.cash_type === 'CASH' ? x.cashbox : null, accountant: amount ? x.accountant || null : null,
          discount_type: x.discount_type || null, discount: x.discount_type ? Number(x.discount) || 0 : 0, comment: x.comment || '',
        };
        if (top || isNew) rec.date = x.date;
        const saved = isNew ? await A.http.post('/payments/', { ...rec, contract: x.contract }) : await A.http.patch(`/payments/${p.id}/`, rec);
        await A.reloadMoney();
        A.toast(isNew ? `To'lov qabul qilindi (chek №${saved.number})` : 'Saqlandi');
        A.refresh();
        if (isNew && saved.nc_status !== 'Tasdiqlashga' && saved.disc_status !== 'Tasdiqlashga') setTimeout(() => A.receipt(saved.id), 60);
      },
    });
  };
  A.act['pay-new'] = (el) => A.paymentForm(null, el.dataset.id);
  A.act['pay-edit'] = async (el) => A.paymentForm(await A.http.get(`/payments/${el.dataset.id}/`));
  A.act['pay-del'] = async (el) => {
    const p = await A.http.get(`/payments/${el.dataset.id}/`);
    if (!(await A.confirm(`${esc(p.contract_name)} — ${A.money(p.amount)} to'lovini o'chirasizmi? Moliyaviy yozuv bazadan o'chmaydi (soft delete), audit'da qoladi.`, "O'chirish", true))) return;
    await A.http.del(`/payments/${p.id}/`);
    await A.reloadMoney();
    A.refresh();
  };

  /* ---- PDF chek (serverda yaratiladi, har ochilganda joriy ma'lumot bilan) ---- */
  A.receipt = (id) => window.open(`/api/v1/payments/${id}/receipt/`, '_blank');
  A.act.receipt = async (el) => {
    const p = await A.http.get(`/payments/${el.dataset.id}/`);
    if ((p.nc_status === 'Tasdiqlashga' || p.disc_status === 'Tasdiqlashga') && !A.isManager()) {
      A.modal({ title: 'Chek', body: `<div class="alert warn">${A.icon('alert')}<div>Bu to'lov hali tasdiqlanmagan (naqdsiz yoki chegirma). Chek tasdiqlangandan keyin chiqadi. Admin, Bosh menejer va Filial menejeri uni hozir ham ko'ra oladi.</div></div>` });
      return;
    }
    A.receipt(p.id);
  };

  /* ===================================================== Tasdiqlashlar */
  let apData = {};
  A.page('approvals', {
    title: 'Tasdiqlashlar',
    section: 'approvals',
    async load(p, q) {
      const tab = q.tab || 'disc';
      await A.reloadPending();
      apData = {};
      if (tab === 'disc' && A.can('payments')) apData.rows = (await A.http.get('/payments/?disc_status=Tasdiqlashga&page_size=200')).results;
      else if (tab === 'nc' && A.can('payments')) apData.rows = (await A.http.get('/payments/?nc_status=Tasdiqlashga&page_size=200')).results;
      else if (tab === 'tr' && A.can('transfers')) apData.rows = (await A.http.get('/transfers/?status=Tasdiqlashga&page_size=200')).results;
      else if (tab === 'mk' && A.can('attendance')) apData.rows = await A.http.get('/makeups/?status=Kutilmoqda');
      else apData.rows = tab === 'freq' ? A.rows('lessonFreqs').filter((f) => f.status === 'Taklif' && A.branchIds().includes(f.branch)) : [];
    },
    render(p, q) {
      const P = A.S.pendingCounts || {};
      const tab = q.tab || 'disc';
      const items = [['disc', 'Chegirmalar', P.discounts], ['nc', "Naqdsiz to'lovlar", P.noncash], ['tr', "O'tkazmalar", P.transfers], ['mk', 'Qoldirilgan darslar', P.makeups], ['freq', 'Oydagi dars soni', P.freqs]];
      const rows = apData.rows || [];
      const btn = (act, id, ok, why) => (ok ? `<button class="btn sm primary" data-act="${act}" data-id="${id}">Tasdiqlash</button>` : `<span class="muted small" title="${esc(why)}">${esc(why)}</span>`);
      const allBtn = (act, ok) => (ok.length > 1 ? `<div class="row" style="margin:8px 0"><button class="btn primary" data-act="${act}">✅ Hammasini tasdiqlash (${ok.length})</button></div>` : '');
      let body = '';
      if (tab === 'disc') {
        body = `<p class="muted">Chegirmani Admin tasdiqlaydi, Bosh menejer — yaratilganidan keyin 30 kun ichida.</p>` + allBtn('ok-disc-all', rows.filter((x) => x.can_approve_disc)) + A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Shartnoma', f: (x) => `<a href="#/contracts/${x.contract}">${esc(x.contract_name)}</a>` },
            { h: 'Chegirma turi', f: (x) => esc((A.get('discountTypes', x.discount_type) || {}).name) },
            { h: 'Summa', f: (x) => `<b>${A.num(x.discount)}</b>`, cls: 'num' },
            { h: 'Izoh', f: (x) => esc(x.comment) },
            { h: 'Kiritdi', f: (x) => esc(A.userName(x.created_by)) },
            { h: '', f: (x) => btn('ok-disc', x.id, x.can_approve_disc, 'Faqat Admin / Bosh menejer (30 kun)') },
          ],
          rows,
          { empty: "Tasdiq kutayotgan chegirma yo'q" },
        );
      } else if (tab === 'nc') {
        body = `<p class="muted">Admin istalgan vaqtda; Bosh menejer 360 kun, Filial menejeri 7 kun ichida tasdiqlaydi. Tasdiqlangach summa g'azna balansiga qo'shiladi.</p>` + allBtn('ok-nc-all', rows.filter((x) => x.can_approve_nc)) + A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Shartnoma', f: (x) => `<a href="#/contracts/${x.contract}">${esc(x.contract_name)}</a>` },
            { h: 'Turi', f: (x) => A.CASH[x.cash_type] },
            { h: 'Summa', f: (x) => `<b>${A.num(x.amount)}</b>`, cls: 'num' },
            { h: "G'azna", f: (x) => esc(A.accName(x.cashbox)) },
            { h: '', f: (x) => btn('ok-nc', x.id, x.can_approve_nc, "Ruxsat yo'q yoki muddat o'tgan") },
          ],
          rows,
          { empty: "Tasdiq kutayotgan naqdsiz to'lov yo'q" },
        );
      } else if (tab === 'tr') {
        body = `<p class="muted">O'tkazmani qabul qiluvchi g'azna mas'uli yoki Admin tasdiqlaydi. Tasdiqlanmaguncha ikkala g'aznada ham hisobga olinmaydi.</p>` + transfersTable(rows);
      } else if (tab === 'mk') {
        body = `<p class="muted">Tasdiqlansa davomat «Besabab»dan «Sababli»ga o'zgaradi va ustozga KPI yoziladi.</p>` + A.makeupTable(rows);
      } else {
        body = `<p class="muted">Har oy 1-kuni tizim kalendar bo'yicha taklif tayyorlaydi. Menejer tekshiradi (bayramlar) va tasdiqlaydi — shundan keyin qarz va KPI hisoblanadi. <a href="#/settings?tab=freq">Sozlamalar → Oydagi dars soni →</a></p>` + A.freqTable(rows);
      }
      return `${A.head('Tasdiqlashlar', `Sizning tasdiqingiz kerak: <b>${P.total || 0}</b> ta`)}${A.tabs(items, tab, 'approvals')}${body}`;
    },
  });
  A.act['ok-disc'] = async (el) => {
    await A.http.post(`/payments/${el.dataset.id}/approve_discount/`);
    A.toast('Chegirma tasdiqlandi');
    A.refresh();
  };
  // Hammasini birdan tasdiqlash: faqat shu foydalanuvchida ruxsat bor qatorlar; har biri serverda alohida tekshiriladi
  const approveAll = async (rows, path, what) => {
    const ok = rows.filter((x) => (what === 'nc' ? x.can_approve_nc : x.can_approve_disc));
    if (!ok.length) return;
    const sum = A.sum(ok, what === 'nc' ? 'amount' : 'discount');
    if (!(await A.confirm(`${ok.length} ta ${what === 'nc' ? "naqdsiz to'lov" : 'chegirma'} (jami ${A.money(sum)}) tasdiqlansinmi?`, 'Hammasini tasdiqlash'))) return;
    let done = 0;
    const failed = [];
    for (const x of ok) {
      try {
        await A.http.post(`/payments/${x.id}/${path}/`);
        done++;
      } catch (e) {
        failed.push(e.message);
      }
    }
    await A.reloadMoney();
    A.toast(`Tasdiqlandi: ${done} ta${failed.length ? `, ${failed.length} tasi tasdiqlanmadi (${failed[0]})` : ''}`, failed.length ? 'warn' : undefined);
    A.refresh();
  };
  A.act['ok-nc-all'] = () => approveAll(apData.rows || [], 'approve_noncash', 'nc');
  A.act['ok-disc-all'] = () => approveAll(apData.rows || [], 'approve_discount', 'disc');
  A.act['ok-nc'] = async (el) => {
    const p = await A.http.post(`/payments/${el.dataset.id}/approve_noncash/`);
    await A.reloadMoney();
    A.toast(`${A.money(p.amount)} «${A.accName(p.cashbox)}» balansiga qo'shildi`);
    A.refresh();
  };

  /* ===================================================== G'aznalar (balans serverda: boshlang'ich + Σ tasdiqlangan harakatlar) */
  A.page('accounts', {
    title: "G'aznalar",
    section: 'accounts',
    load: () => A.reloadMoney(),
    render() {
      const accs = A.rows('accounts').filter((a) => a.balance !== null);
      return `${A.head("G'aznalar", "Balans = boshlang'ich qoldiq + barcha tasdiqlangan pul harakatlari (yagona jurnal)", A.can('settings', 'e') ? `<a class="btn ghost" href="#/settings?tab=accounts">G'aznalarni sozlash</a>` : '')}
        <div class="cards">${accs
          .map((a) => {
            const types = Object.keys(a.by_type || {});
            return `<a class="gcard acc" href="#/accounts/${a.id}">
              <div class="gcard-h"><b>${esc(a.name)}</b>${A.badge(A.CASH[a.cash_type], 'gray')}</div>
              <div class="big-num">${A.money(a.balance)}</div>
              ${types.map((t) => `<div class="small row between"><span>${A.CASH[t]}</span><span>${A.num(a.by_type[t])}</span></div>`).join('')}
              ${Number(a.pending) ? `<div class="small t-orange">Tasdiqlanmagan: ${A.num(a.pending)}</div>` : ''}
              <div class="muted small">Mas'ullar: ${a.responsible.map(A.userName).map(esc).join(', ') || '—'}</div>
            </a>`;
          })
          .join('') || A.empty("G'azna yo'q")}</div>`;
    },
  });
  let ledger = { results: [] };
  A.page('accounts/:id', {
    title: "G'azna",
    section: 'accounts',
    async load({ id }) {
      await A.reloadMoney();
      ledger = await A.http.get(`/accounts/${id}/ledger/?` + qsOf('led', ['month'], { page: A.q('led:page', 1) }));
    },
    render({ id }) {
      const a = A.get('accounts', id);
      const m = A.q('led:month', '');
      return `<a class="back" href="#/accounts">← G'aznalar</a>
        ${A.head(a.name, `${A.CASH[a.cash_type]} · mas'ullar: ${a.responsible.map(A.userName).map(esc).join(', ') || '—'}`)}
        <div class="stats">${A.stat('Joriy balans', A.money(a.balance))}${A.stat("Boshlang'ich qoldiq", A.money(a.initial), a.start ? 'sana: ' + A.fdate(a.start) : '')}${A.stat('Tasdiqlanmagan', A.money(a.pending), 'balansga kirmagan', Number(a.pending) ? 'warn' : '')}</div>
        <div class="filters"><select class="f-input" data-filter="led:month"><option value="">Barcha oylar</option>${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === m ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
        ${A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Manba', f: (x) => esc(x.src) },
            { h: 'Tafsilot', f: (x) => esc(x.ref) },
            { h: 'Turi', f: (x) => A.CASH[x.type] },
            { h: 'Summa', f: (x) => `<span class="${x.amount < 0 ? 't-red' : 't-green'}">${x.amount > 0 ? '+' : ''}${A.num(x.amount)}</span>`, cls: 'num' },
            { h: 'Holat', f: (x) => (x.confirmed ? '' : A.badge('tasdiqlanmagan', 'orange')) },
          ],
          ledger.results,
          { empty: "Harakat yo'q" },
        )}${A.pager('led', ledger)}`;
    },
  });

  /* ===================================================== Ichki pul oqimi (/transfers/) */
  const DIR_TONE = { Chiquvchi: 'red', Kiruvchi: 'green', Boshqa: 'gray' };
  function transfersTable(rows) {
    return A.table(
      [
        { h: 'Sana', f: (t) => A.fdate(t.date) },
        { h: "Yo'nalish", f: (t) => A.badge(t.direction, DIR_TONE[t.direction]) },
        { h: 'Kimdan', f: (t) => `${esc(A.accName(t.sender))}<br><small class="muted">${esc(A.userName(t.sender_cashier))}</small>` },
        { h: 'Kimga', f: (t) => `${esc(A.accName(t.receiver))}<br><small class="muted">${esc(A.userName(t.receiver_cashier))}</small>` },
        { h: 'Summa', f: (t) => `<b>${A.num(t.amount)}</b>`, cls: 'num' },
        { h: 'Holat', f: (t) => A.badge(t.status, t.status === 'Tasdiqlandi' ? 'green' : 'orange') + (t.confirmed_by ? `<br><small class="muted">${esc(A.userName(t.confirmed_by))}</small>` : '') },
        { h: 'Izoh', f: (t) => esc(t.comment) },
        { h: '', f: (t) => (t.status === 'Tasdiqlashga' ? (t.can_confirm ? `<button class="btn sm primary" data-act="ok-tr" data-id="${t.id}">Qabul qildim</button>` : '<span class="muted small">Qabul qiluvchi tasdiqlaydi</span>') : '') },
      ],
      rows,
      { empty: "O'tkazma yo'q" },
    );
  }
  let trData = { results: [] };
  A.page('transfers', {
    title: 'Ichki pul oqimi',
    section: 'transfers',
    async load() {
      trData = await A.http.get(`/transfers/?page=${A.q('tr:page', 1)}`);
    },
    render() {
      return `${A.head('Ichki pul oqimi', "G'aznalar orasida naqd pul o'tkazish", A.can('transfers', 'a') ? A.btn("O'tkazma", 'tr-new', { icon: 'plus' }) : '')}${transfersTable(trData.results)}${A.pager('tr', trData)}`;
    },
  });
  A.act['ok-tr'] = async (el) => {
    await A.http.post(`/transfers/${el.dataset.id}/confirm/`);
    await A.reloadMoney();
    A.toast("O'tkazma tasdiqlandi — ikkala g'azna balansi yangilandi");
    A.refresh();
  };
  A.act['tr-new'] = async () => {
    await A.reloadMoney();
    const top = A.isTop();
    A.form({
      title: "G'aznalar orasida o'tkazma",
      values: { date: A.today() },
      fields: [
        noAccount('sender', () => !A.myAccounts().length),
        { name: 'sender', label: "Yuboruvchi g'azna", type: 'select', required: true, auto: true, show: () => A.myAccounts().length, options: () => A.myAccounts().map((a) => [a.id, `${a.name} (naqd: ${A.num(A.accBal(a.id, 'CASH'))})`]), resets: ['sender_cashier', 'amount'], onChange: (x) => { if (x.sender) x.amount = A.accBal(x.sender, 'CASH'); } },
        { name: 'sender_cashier', label: "Yuboruvchi g'aznachi", type: 'select', auto: true, show: (x) => x.sender, options: (x) => (A.get('accounts', x.sender) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'cash_type', label: 'Pul shakli', type: 'computed', show: (x) => x.sender, compute: () => "Naqd (o'tkazma faqat naqd pul uchun)" },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.sender, help: (x) => `G'aznada naqd: ${A.money(A.accBal(x.sender, 'CASH'))}`, validate: (n, x) => (n <= 0 ? "0 dan katta bo'lsin" : !top && n > A.accBal(x.sender, 'CASH') ? `G'aznada ${A.num(A.accBal(x.sender, 'CASH'))} so'm pul bor` : '') },
        { name: 'receiver', label: "Qabul qiluvchi g'azna", type: 'select', required: true, show: (x) => x.amount > 0, options: (x) => A.rows('accounts').filter((a) => a.status === 'Faol' && a.id !== x.sender).map((a) => [a.id, a.name]), resets: ['receiver_cashier'] },
        { name: 'receiver_cashier', label: "Qabul qiluvchi g'aznachi", type: 'select', auto: true, show: (x) => x.receiver, options: (x) => (A.get('accounts', x.receiver) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'date', label: 'Sana', type: 'date', readonly: () => !top, show: (x) => x.receiver, help: () => (top ? '' : "Sanani faqat Admin va Bosh menejer o'zgartiradi") },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.receiver },
      ],
      async onSubmit(x) {
        await A.http.post('/transfers/', { date: x.date, sender: x.sender, sender_cashier: x.sender_cashier || null, amount: x.amount, receiver: x.receiver, receiver_cashier: x.receiver_cashier || null, comment: x.comment || '' });
        await A.reloadMoney();
        A.toast("Yuborildi. Qabul qiluvchi tasdiqlaguncha balanslar o'zgarmaydi");
        A.refresh();
      },
    });
  };

  /* ===================================================== Pul ayirboshlash (/exchanges/) */
  let xData = { results: [] };
  A.page('exchange', {
    title: 'Pul ayirboshlash',
    section: 'exchange',
    async load() {
      xData = await A.http.get(`/exchanges/?page=${A.q('xc:page', 1)}`);
    },
    render() {
      return `${A.head('Pul ayirboshlash', "Masalan kartadagi pulni naqdga aylantirish. Yo'qotish = berilgan − olingan", A.can('exchange', 'a') ? A.btn('Ayirboshlash', 'xc-new', { icon: 'plus' }) : '')}
        ${A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: "G'azna", f: (x) => esc(A.accName(x.account)) },
            { h: 'Berildi', f: (x) => `${A.num(x.amount)} ${A.CASH[x.from_type]}`, cls: 'num' },
            { h: 'Olindi', f: (x) => `${A.num(x.amount_to)} ${A.CASH[x.to_type]}`, cls: 'num' },
            { h: "Yo'qotish", f: (x) => `<span class="t-red">${A.num(x.loss)}</span>`, cls: 'num', sum: (r) => A.num(A.sum(r, (x) => Number(x.loss))) },
            { h: 'Izoh', f: (x) => esc(x.comment) },
            { h: 'Kim', f: (x) => esc(A.userName(x.created_by)) },
          ],
          xData.results,
        )}${A.pager('xc', xData)}`;
    },
  });
  A.act['xc-new'] = () =>
    A.form({
      title: 'Pul ayirboshlash',
      fields: [
        noAccount('account', () => !A.myAccounts().length),
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: () => A.myAccounts().length, options: () => A.myAccounts().map((a) => [a.id, a.name]) },
        { name: 'from_type', label: 'Pul shakli (dan)', type: 'seg', required: true, options: cashOpts, resets: ['to_type'] },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.from_type, help: (x) => (x.account ? `G'aznada: ${A.money(A.accBal(x.account, x.from_type))}` : ''), onChange: (x) => (x.amount_to = x.amount) },
        { name: 'to_type', label: 'Pul shakli (ga)', type: 'seg', required: true, show: (x) => x.amount, options: (x) => cashOpts.filter(([k]) => k !== x.from_type) },
        { name: 'amount_to', label: 'Olingan summa', type: 'money', required: true, show: (x) => x.to_type, validate: (n, x) => (n > x.amount ? `${A.num(x.amount)} dan katta bo'lolmaydi` : '') },
        { name: 'loss', label: "Yo'qotish", type: 'computed', show: (x) => x.to_type, compute: (x) => A.money((x.amount || 0) - (x.amount_to || 0)) },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.to_type },
      ],
      async onSubmit(x) {
        await A.http.post('/exchanges/', { account: x.account, from_type: x.from_type, amount: x.amount, to_type: x.to_type, amount_to: x.amount_to, comment: x.comment || '' });
        await A.reloadMoney();
        A.refresh();
      },
    });

  /* ===================================================== Xarajatlar (/expenses/) */
  let eData = { results: [] };
  A.page('expenses', {
    title: 'Xarajatlar',
    section: 'expenses',
    async load(p, q) {
      const tab = q.tab || 'date';
      const qs = qsOf('expenses', ['month', 'category']);
      if (tab === 'cat') eData = { summary: await A.http.get('/expenses/summary/?' + qs) };
      else { qs.set('page', A.q('expenses:page', 1)); eData = await A.http.get('/expenses/?' + qs); }
    },
    render(p, q) {
      const tab = q.tab || 'date';
      return `${A.head('Xarajatlar', "G'azna qoldig'idan ko'p xarajat qilib bo'lmaydi (Admin va Bosh menejerdan tashqari)", A.can('expenses', 'a') ? A.btn("Xarajat qo'shish", 'exp-new', { icon: 'plus' }) : '')}
        ${A.tabs([['date', "Sana bo'yicha"], ['cat', 'Oy → kategoriya']], tab, 'expenses')}
        ${A.filterBar('expenses', [A.fSelect('expenses', 'month', A.monthOptions(), 'Barcha oylar'), A.fSelect('expenses', 'category', A.optList('expenseCats'), 'Barcha kategoriyalar')])}
        <div>${tab === 'cat' ? expenseSummary(eData.summary) : expenseTable(eData)}</div>`;
    },
  });
  function expenseSummary(rows) {
    const byM = A.groupBy(A.sortBy(rows, (r) => r.month, true), (r) => r.month);
    return [...byM]
      .map(([ym, list]) => `<section class="group-block"><h3>${A.ymLabel(ym)} <span class="muted">· ${A.money(A.sum(list, (r) => Number(r.sum)))}</span></h3>${A.table(
        [
          { h: 'Kategoriya', f: (r) => esc(r.name) },
          { h: 'Turi', f: (r) => A.badge(r.kind, r.kind === 'Xarajat' ? 'gray' : 'blue') },
          { h: 'Soni', f: (r) => r.n, cls: 'num' },
          { h: 'Summa', f: (r) => `<b>${A.num(r.sum)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, (r) => Number(r.sum))) },
        ],
        A.sortBy(list, (r) => Number(r.sum), true),
      )}</section>`)
      .join('') || A.empty("Xarajat yo'q");
  }
  function expenseTable(d) {
    return `${d.results.length ? `<p class="muted small">Filtr bo'yicha jami: <b>${A.money(d.total)}</b></p>` : ''}${A.table(
      [
        { h: 'Sana', f: (e) => A.fdate(e.date) },
        { h: 'Kategoriya', f: (e) => esc((A.get('expenseCats', e.category) || {}).name) },
        { h: 'Nomi', f: (e) => esc(e.name) },
        { h: 'Soni × narx', f: (e) => `${e.quantity} × ${A.num(e.price)}`, cls: 'num' },
        { h: 'Jami', f: (e) => `<b>${A.num(e.total)}</b>`, cls: 'num' },
        { h: "G'azna", f: (e) => `${esc(A.accName(e.account))} · ${A.CASH[e.cash_type]}` },
        { h: 'Hisob davri', f: (e) => `${A.MONTHS[e.period_month - 1]} ${e.period_year}` },
        {
          h: '',
          f: (e) => {
            const ed = A.canEdit('expenses', e), del = A.canEdit('expenses', e, 'date', 'd');
            return `<div class="row gap nowrap">${A.can('expenses', 'e') ? `<button class="btn sm ghost" data-act="exp-edit" data-id="${e.id}" ${ed.ok ? '' : `disabled title="${esc(ed.why)}"`}>✎</button>` : ''}${A.can('expenses', 'd') ? `<button class="btn sm ghost" data-act="exp-del" data-id="${e.id}" ${del.ok ? '' : `disabled title="${esc(del.why)}"`}>🗑</button>` : ''}</div>`;
          },
        },
      ],
      d.results,
      { empty: "Xarajat yo'q" },
    )}${A.pager('expenses', d)}`;
  }
  A.expenseForm = async (e) => {
    await A.reloadMoney();
    const top = A.isTop();
    let names = [];
    const loadNames = async (cat) => { names = cat ? await A.http.get(`/expenses/names/?category=${cat}`) : []; };
    if (e) await loadNames(e.category);
    A.form({
      title: e ? 'Xarajat' : 'Yangi xarajat',
      values: e ? { ...e, price: Number(e.price), period_month: String(e.period_month) } : { date: A.today(), quantity: 1, cash_type: 'CASH' },
      fields: [
        { name: 'date', label: 'Sana', type: 'date', required: true, half: true, validate: (d) => (d > A.today() ? "Kelajak sana bo'lishi mumkin emas" : ''), onChange: (x) => { x.period_year = Number(x.date.slice(0, 4)); x.period_month = String(Number(x.date.slice(5, 7))); } },
        { name: 'category', label: 'Kategoriya', type: 'select', required: true, half: true, resets: ['name'], onChange: (x) => loadNames(x.category), options: (x) => A.rows('expenseCats').filter((c) => c.allowed_roles.includes(A.role()) || c.id === x.category).map((c) => [c.id, `${c.name}${c.kind !== 'Xarajat' ? ' · ' + c.kind : ''}`]), help: 'Faqat sizning rolingizga ruxsat berilgan kategoriyalar' },
        { name: 'name', label: 'Nomi', required: true, show: (x) => x.category, suggest: () => names, help: 'Shu kategoriyadagi oldingi nomlar taklif qilinadi' },
        { name: 'quantity', label: 'Soni', type: 'number', min: 1, required: true, show: (x) => x.name, half: true, validate: (n) => (n < 1 ? 'Kamida 1' : '') },
        { name: 'price', label: 'Narxi', type: 'money', required: true, show: (x) => x.name, half: true },
        { name: 'total', label: 'Jami summa', type: 'computed', show: (x) => x.price, compute: (x) => `<b>${A.money((x.quantity || 0) * (x.price || 0))}</b>` },
        { name: 'cash_type', label: "To'lov shakli", type: 'seg', options: cashOpts, show: (x) => x.price },
        noAccount('account', (x) => x.price && !A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type)),
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.price && A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type || a.id === x.account), options: (x) => A.myAccounts().filter((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type || a.id === x.account).map((a) => [a.id, a.name]), resets: ['cashier'] },
        { name: 'cashier', label: "G'aznachi", type: 'select', auto: true, show: (x) => x.account, options: (x) => (A.get('accounts', x.account) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.account && x.cash_type, text: (x) => `G'aznada ${A.CASH[x.cash_type].toLowerCase()}: <b>${A.money(A.accBal(x.account, x.cash_type))}</b>` },
        { name: 'period_year', label: 'Hisob davri: yil', type: 'number', show: (x) => x.price && top, half: true, default: Number(A.today().slice(0, 4)) },
        { name: 'period_month', label: 'Hisob davri: oy', type: 'select', show: (x) => x.price && top, half: true, options: A.MONTHS.map((m, i) => [String(i + 1), m]), default: String(Number(A.today().slice(5, 7))), help: "Faqat Admin va Bosh menejer o'zgartiradi" },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.price },
      ],
      async onSubmit(x) {
        const rec = { date: x.date, category: x.category, name: x.name, quantity: x.quantity, price: x.price, cash_type: x.cash_type, account: x.account, cashier: x.cashier || null, comment: x.comment || '' };
        if (top) Object.assign(rec, { period_year: Number(x.period_year), period_month: Number(x.period_month) });
        if (e) await A.http.patch(`/expenses/${e.id}/`, rec);
        else await A.http.post('/expenses/', rec);
        await A.reloadMoney();
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['exp-new'] = () => A.expenseForm(null);
  A.act['exp-edit'] = async (el) => A.expenseForm(await A.http.get(`/expenses/${el.dataset.id}/`));
  A.act['exp-del'] = async (el) => {
    if (!(await A.confirm("Xarajatni o'chirasizmi? Yozuv bazada qoladi (soft delete), g'azna balansi tiklanadi.", "O'chirish", true))) return;
    await A.http.del(`/expenses/${el.dataset.id}/`);
    await A.reloadMoney();
    A.refresh();
  };

  /* ===================================================== Kreditorlar (/creditors/, /creditor-transactions/) */
  let crData = [];
  let crDetail = null;
  A.page('creditors', {
    title: 'Tashqi pul oqimi',
    section: 'creditors',
    async load() {
      crData = await A.http.get('/creditors/');
    },
    render() {
      return `${A.head('Tashqi pul oqimi (kreditorlar)', "Joriy haqqi = boshlang'ich haqqi − Σ amallar", A.can('creditors', 'a') ? A.btn('Amal kiritish', 'ctx-new', { icon: 'plus' }) + A.btn('Kreditor', 'cred-new', { cls: 'ghost', icon: 'plus' }) : '')}
        <div class="cards">${crData
          .map((c) => `<a class="gcard" href="#/creditors/${c.id}"><div class="gcard-h"><b>${esc(c.name)}</b></div><div class="muted small">Joriy haqqi</div><div class="big-num">${A.money(c.current)}</div><div class="muted small">Boshlang'ich: ${A.num(c.initial)}</div></a>`)
          .join('') || A.empty("Kreditor yo'q")}</div>`;
    },
  });
  A.page('creditors/:id', {
    title: 'Kreditor',
    section: 'creditors',
    async load({ id }) {
      crDetail = await A.http.get(`/creditors/${id}/`);
    },
    render({ id }) {
      const c = crDetail;
      // Oldi-berdilar: chapda daraxt (Barchasi → yil → oy, har tugunda summa), standart — oxirgi oy (Hisoblangan KPI dagidek)
      const latest = c.transactions[0];
      const opts = {
        levels: [
          { key: (t) => t.date.slice(0, 4), label: (k) => k, desc: true },
          { key: (t) => t.date.slice(0, 7), label: (k) => A.ymLabel(k).split(' ')[0], sort: (k) => k, desc: true },
        ],
        value: (l) => { const v = A.sum(l, (t) => Number(t.amount)); return `<span class="${v < 0 ? 't-red' : v > 0 ? 't-green' : ''}">${v > 0 ? '+' : ''}${A.num(v)}</span>`; },
        def: latest ? `${latest.date.slice(0, 4)}|${latest.date.slice(0, 7)}` : '',
      };
      const key = 'ctx-' + id;
      const rows = A.treeFilter(key, c.transactions, opts);
      return `<a class="back" href="#/creditors">← Kreditorlar</a>${A.head(c.name, `Joriy haqqi: <b>${A.money(c.current)}</b> · boshlang'ich: ${A.num(c.initial)}`, A.can('creditors', 'a') ? A.btn('Amal kiritish', 'ctx-new', { id, icon: 'plus' }) : '')}
        <h3>Oldi-berdilar</h3>
        <div class="settings tree-layout">${A.treeNav(key, c.transactions, opts)}<div class="settings-body">${A.table(
          [
            { h: 'Sana', f: (t) => A.fdate(t.date) },
            { h: 'Summa', f: (t) => `<span class="${t.amount < 0 ? 't-red' : 't-green'}">${t.amount > 0 ? '+' : ''}${A.num(t.amount)}</span>`, cls: 'num', sum: (r) => { const v = A.sum(r, (t) => Number(t.amount)); return `${v > 0 ? '+' : ''}${A.num(v)}`; } },
            { h: 'Amal', f: (t) => (t.amount < 0 ? 'Qarz olindi' : 'Qarz qaytarildi') },
            { h: "G'azna", f: (t) => `${esc(A.accName(t.account))} · ${A.CASH[t.cash_type]}` },
            { h: 'Izoh', f: (t) => esc(t.comment) },
            { h: 'Kim', f: (t) => esc(A.userName(t.created_by)) },
          ],
          rows,
          { empty: "Amal yo'q" },
        )}<p class="muted small">«−» — qarz olindi (g'aznaga kirdi), «+» — qarz qaytarildi (g'aznadan chiqdi). Daraxtda tugun summasi — shu davrdagi amallar yig'indisi.</p></div></div>
        <h3>Izohlar</h3>${A.can('creditors', 'a') ? `<div class="row gap"><input class="f-input grow" id="cc-text" placeholder="Izoh…"><button class="btn" id="cc-add">Qo'shish</button></div>` : ''}
        <ul class="comments">${c.comments.map((x) => `<li><p>${esc(x.comment)}</p><small class="muted">${esc(A.userName(x.created_by))} · ${A.fdt(x.created_at)}</small></li>`).join('') || '<li class="muted">Izoh yo\'q</li>'}</ul>`;
    },
    mount({ id }) {
      const b = document.getElementById('cc-add');
      if (b)
        b.onclick = async () => {
          const t = document.getElementById('cc-text').value.trim();
          if (!t) return;
          await A.http.post(`/creditors/${id}/comments/`, { comment: t }).catch((e) => A.toast(e.message, 'warn'));
          A.refresh();
        };
    },
  });
  A.act['cred-new'] = () =>
    A.form({
      title: 'Yangi kreditor',
      fields: [
        { name: 'name', label: 'Nomi', required: true },
        { name: 'initial', label: "Boshlang'ich haqqi", type: 'money', help: "Yaratilgandan keyin faqat Admin o'zgartiradi" },
      ],
      async onSubmit(x) {
        await A.http.post('/creditors/', { name: x.name, initial: Number(x.initial) || 0 });
        A.refresh();
      },
    });
  A.act['ctx-new'] = async (el) => {
    await A.reloadMoney();
    const creditors = crData.length ? crData : await A.http.get('/creditors/');
    A.form({
      title: 'Kreditor amali',
      values: { creditor: el.dataset.id || '', date: A.today(), cash_type: 'CASH' },
      fields: [
        { name: 'creditor', label: 'Qarz beruvchi', type: 'select', required: true, options: () => creditors.map((c) => [c.id, c.name]) },
        { name: 'warn', type: 'note', tone: 'warn', show: (x) => x.creditor, text: "<b>Diqqat:</b> «−» belgisi — <b>qarz olish</b> (g'aznaga pul kiradi), «+» belgisi — <b>qarz qaytarish</b> (g'aznadan pul chiqadi)." },
        { name: 'amount', label: 'Summa (− olish / + qaytarish)', type: 'number', required: true, show: (x) => x.creditor, help: (x) => (x.amount < 0 ? `Qarz olinyapti: g'aznaga +${A.num(-x.amount)}` : x.amount > 0 ? `Qarz qaytarilyapti: g'aznadan −${A.num(x.amount)}` : '') },
        { name: 'cash_type', label: 'Pul shakli', type: 'seg', options: cashOpts, show: (x) => x.amount },
        noAccount('account', (x) => x.amount && !A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type)),
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.amount && A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type), options: (x) => A.myAccounts().filter((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type).map((a) => [a.id, a.name]) },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.amount, validate: (d) => (d > A.today() ? "Kelajak sana bilan kiritib bo'lmaydi" : !A.isTop() && A.diffDays(d, A.today()) > 7 ? 'Bir hafta avvalgi sanagacha kiritish mumkin, xolos' : '') },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.amount },
      ],
      async onSubmit(x) {
        await A.http.post('/creditor-transactions/', { date: x.date, creditor: x.creditor, amount: Number(x.amount), cash_type: x.cash_type, account: x.account, comment: x.comment || '' });
        await A.reloadMoney();
        A.refresh();
      },
    });
  };

  /* ===================================================== Foyda (server: /reports/profit/) */
  let prData = [];
  const profitMonths = () => {
    const all = A.monthOptions().map(([k]) => k).reverse();
    const sel = (A.ui.q['profit:months'] || all).filter((m) => all.includes(m));
    return { all, sel };
  };
  A.page('profit', {
    title: 'Foyda (oyma-oy)',
    section: 'profit',
    async load() {
      const { sel } = profitMonths();
      prData = sel.length ? await A.http.get(`/reports/profit/?months=${sel.join(',')}`) : [];
    },
    render() {
      const { all, sel } = profitMonths();
      const rows = prData.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, k === 'ym' ? v : Number(v)])));
      const tot = (k) => A.sum(rows, k);
      const cls = (n) => (n > 0 ? 't-green' : n < 0 ? 't-red' : '');
      return `${A.head('Foyda (oyma-oy)', "Foyda = to'lovlar − xarajatlar (faqat «Xarajat» turi) − hisoblangan oyliklar")}
        <div class="filters"><span class="muted">Oylar:</span><div class="chips">${all.map((m) => `<button class="chip ${sel.includes(m) ? 'on' : ''}" data-act="profit-month" data-id="${m}">${A.ymLabel(m)}</button>`).join('')}</div></div>
        <div class="stats">${A.stat("To'lovlar", `<span class="t-blue">${A.money(tot('payments'))}</span>`)}${A.stat('Xarajatlar', `<span class="t-pink">${A.money(tot('expenses'))}</span>`)}${A.stat('Hisoblangan oyliklar', A.money(tot('salaries')))}${A.stat("Ko'rilgan foyda", `<span class="${cls(tot('profit'))}">${A.money(tot('profit'))}</span>`)}</div>
        <section class="card">${A.table(
          [
            { h: 'Oy', f: (r) => `<b>${A.ymLabel(r.ym)}</b>` },
            { h: "To'lovlar", f: (r) => `<span class="t-blue">${A.num(r.payments)}</span>`, cls: 'num', sum: () => A.num(tot('payments')) },
            { h: 'Xarajatlar', f: (r) => `<span class="t-pink">${A.num(r.expenses)}</span>`, cls: 'num', sum: () => A.num(tot('expenses')) },
            { h: 'Oyliklar', f: (r) => A.num(r.salaries), cls: 'num', sum: () => A.num(tot('salaries')) },
            { h: 'Foyda', f: (r) => `<b class="${cls(r.profit)}">${A.num(r.profit)}</b>`, cls: 'num', sum: () => `<span class="${cls(tot('profit'))}">${A.num(tot('profit'))}</span>` },
            { h: 'Qayta investitsiya', f: (r) => A.num(r.reinvest), cls: 'num muted', sum: () => A.num(tot('reinvest')) },
            { h: 'Dividend', f: (r) => A.num(r.dividend), cls: 'num muted', sum: () => A.num(tot('dividend')) },
            { h: 'Tashqi qarz', f: (r) => A.num(r.debt), cls: 'num muted', sum: () => A.num(tot('debt')) },
          ],
          rows,
          { empty: 'Oy tanlang' },
        )}<p class="muted small">Qayta investitsiya, dividend va tashqi qarz foydaga kirmaydi — alohida ko'rsatiladi. To'lovlar — sana bo'yicha, xarajatlar — hisob davri bo'yicha, oyliklar — oylik belgilashdagi «Jami» (jarima ayirilgan).</p></section>
        <section class="card">${A.chart({ type: 'bar', data: { labels: rows.map((r) => A.ymLabel(r.ym)), datasets: [{ label: "To'lovlar", data: rows.map((r) => r.payments), backgroundColor: '#2f80ed' }, { label: 'Xarajatlar', data: rows.map((r) => r.expenses), backgroundColor: '#e86fa6' }, { label: 'Oyliklar', data: rows.map((r) => r.salaries), backgroundColor: '#9b9ba3' }, { label: 'Foyda', data: rows.map((r) => r.profit), backgroundColor: A.PALETTE[3], borderColor: A.PALETTE[3], type: 'line' }] } })}</section>`;
    },
  });
  A.act['profit-month'] = (el) => {
    const { all, sel } = profitMonths();
    const next = sel.includes(el.dataset.id) ? sel.filter((m) => m !== el.dataset.id) : [...sel, el.dataset.id];
    A.ui.q['profit:months'] = all.filter((m) => next.includes(m));
    A.refresh();
  };

  /* ===================================================== Statistika (server: /reports/stats/, /reports/funnel/, /reports/first-payers/) */
  let stData = {};
  A.page('stats', {
    title: 'Statistika',
    section: 'dashboard',
    async load(p, q) {
      const tab = q.tab || 'month';
      stData = {};
      if (!A.isManager()) return;
      if (tab === 'month') stData = await A.http.get(`/reports/stats/?count=${A.q('st:count', 6)}`);
      else if (tab === 'funnel') {
        const qs = new URLSearchParams();
        for (const k of ['from', 'to', 'source', 'course', 'owner']) if (A.q('fn:' + k, '')) qs.set(k, A.q('fn:' + k));
        stData = await A.http.get('/reports/funnel/?' + qs);
      } else stData = await A.http.get(`/reports/first-payers/?month=${A.q('fp:month', A.ym(A.today()))}`);
    },
    render(p, q) {
      const tab = q.tab || 'month';
      if (!A.isManager()) return A.head('Statistika') + A.empty("Hisobotlarni Admin, Bosh menejer va Filial menejeri ko'radi");
      const body = tab === 'month' ? monthStats(stData) : tab === 'funnel' ? funnelView(stData) : firstPayers(stData);
      return `${A.head('Statistika', 'Oyma-oy taqqoslash, sotuv voronkasi va birinchi marta to\'lov qilganlar')}
        ${A.tabs([['month', 'Oylik statistika'], ['funnel', 'Sotuv voronkasi'], ['first', "Birinchi to'lovchilar"]], tab, 'stats')}${body}`;
    },
  });

  function monthStats(s) {
    const months = s.months || [];
    const labels = months.map(A.ymLabel);
    const n = A.q('st:count', 6);
    const sel = `<div class="filters"><select class="f-input" data-filter="st:count">${[3, 6, 12].map((k) => `<option value="${k}" ${String(k) === String(n) ? 'selected' : ''}>Oxirgi ${k} oy</option>`).join('')}</select></div>`;
    const series = (rows, key, nameOf) => {
      const names = [...new Set(rows.map((r) => r[key]))];
      return names.map((nm, i) => ({ label: nameOf(nm), data: months.map((m) => A.sum(rows.filter((r) => r.ym === m && r[key] === nm), 'n')), backgroundColor: A.PALETTE[i % A.PALETTE.length] }));
    };
    const stacked = { scales: { x: { stacked: true }, y: { stacked: true } } };
    const reasons = [...new Set((s.contracts_stopped || []).map((r) => r.reason))];
    return `${sel}<div class="grid-2">
      <section class="card"><h2>Yangi lidlar (manba bo'yicha)</h2>${A.chart({ type: 'bar', data: { labels, datasets: series(s.leads_by_source || [], 'source', A.sourceName) }, options: stacked })}</section>
      <section class="card"><h2>Yangi lidlar (kurs bo'yicha)</h2>${A.chart({ type: 'bar', data: { labels, datasets: series(s.leads_by_course || [], 'course', A.courseName) }, options: stacked })}</section>
      <section class="card"><h2>Yangi va to'xtatilgan shartnomalar</h2>${A.chart({ type: 'bar', data: { labels, datasets: [
        { label: 'Yangi', data: s.contracts_new || [], backgroundColor: A.PALETTE[3] },
        ...reasons.map((r, i) => ({ label: `To'xtatildi: ${r}`, data: months.map((m) => A.sum((s.contracts_stopped || []).filter((x) => x.ym === m && x.reason === r), 'n')), backgroundColor: ['#eb5757', '#f2994a', '#f2c94c', '#bb6bd9', '#9b9ba3', '#6fcf97', '#56ccf2'][i % 7], stack: 'stop' }))] } })}</section>
      <section class="card"><h2>O'rtacha davomat foizi</h2>${A.chart({ type: 'line', data: { labels, datasets: [{ label: 'Keldi, %', data: (s.attendance_pct || []).map((x) => Math.round(x * 100)), borderColor: A.PALETTE[0], backgroundColor: 'rgba(242,106,27,.15)', fill: true, tension: 0.3 }] }, options: { scales: { y: { min: 0, max: 100 } } } })}
        <p class="muted small">Guruh va ustoz bo'yicha batafsil — <a href="#/attendance?tab=stats">Davomatlar → Statistika</a></p></section>
      ${s.money ? `<section class="card wide"><h2>To'lovlar, xarajatlar va foyda</h2>${A.chart({ type: 'bar', data: { labels, datasets: [
        { label: "To'lovlar", data: s.money.map((r) => Number(r.payments)), backgroundColor: '#2f80ed' },
        { label: 'Xarajatlar', data: s.money.map((r) => Number(r.expenses)), backgroundColor: '#e86fa6' },
        { label: 'Oyliklar', data: s.money.map((r) => Number(r.salaries)), backgroundColor: '#9b9ba3' },
        { label: 'Foyda', data: s.money.map((r) => Number(r.profit)), type: 'line', borderColor: A.PALETTE[3], backgroundColor: A.PALETTE[3] }] } })}
        <p class="muted small">Batafsil — <a href="#/profit">Foyda (oyma-oy)</a></p></section>` : ''}
    </div>`;
  }

  function funnelView(f) {
    const LS = A.LEAD_STATUSES;
    const owners = A.S.users.filter((u) => ['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI', 'ADMINISTRATOR', 'ADMINISTRATOR_HISOBCHI'].includes(u.role)).map((u) => [u.id, u.full_name]);
    const fdate = (k, ph) => `<input type="date" class="f-input" data-filter="fn:${k}" value="${A.q('fn:' + k, '')}" title="${ph}">`;
    const bar = (n, max) => `<div class="bar"><i class="bg-orange" style="width:${max ? (n / max) * 100 : 0}%"></i></div>`;
    const max = Math.max(1, ...(f.steps || []).map((s) => s.n));
    return `<div class="filters">${fdate('from', 'Dan')}${fdate('to', 'Gacha')}${A.fSelect('fn', 'source', A.optList('leadSources'), 'Barcha manbalar')}${A.fSelect('fn', 'course', A.optList('courses'), 'Barcha kurslar')}${A.fSelect('fn', 'owner', owners, 'Barcha xodimlar')}</div>
      <div class="stats">${A.stat('Lidlar', f.total || 0)}${A.stat('Lid → shartnoma', A.pct(f.contract_rate), `${f.contracts || 0} ta`)}${A.stat("Lid → to'lov", A.pct(f.pay_rate), `${f.paid || 0} ta`)}</div>
      <div class="grid-2"><section class="card"><h2>Bosqichlar</h2>${A.table(
        [
          { h: 'Status', f: (s) => `${s.status}. ${esc(LS[s.status])}` },
          { h: 'Lidlar', f: (s) => `<b>${s.n}</b>`, cls: 'num' },
          { h: '', f: (s) => bar(s.n, max) },
        ],
        f.steps || [],
      )}</section>
      <section class="card"><h2>O'tish foizi</h2>${A.table(
        [
          { h: 'Bosqichga yetgan', f: (s) => `${s.status}. ${esc(LS[s.status])}` },
          { h: 'Soni', f: (s) => s.reached, cls: 'num' },
          { h: 'Foiz', f: (s) => `<b>${A.pct(s.rate)}</b>`, cls: 'num' },
        ],
        f.stages || [],
      )}<p class="muted small">«Yetgan» — shu bosqich yoki undan keyingi (5-gacha) statusdagi lidlar.</p></section>
      <section class="card wide"><h2>Mas'ul xodim bo'yicha</h2>${A.table(
        [
          { h: 'Lidni kiritgan', f: (r) => esc(A.userName(r.user)) },
          { h: 'Lidlar', f: (r) => r.n, cls: 'num' },
          { h: 'Shartnoma', f: (r) => `${r.contracts} <small class="muted">(${A.pct(r.n ? r.contracts / r.n : 0)})</small>`, cls: 'num' },
          { h: "To'lov", f: (r) => `${r.paid} <small class="muted">(${A.pct(r.n ? r.paid / r.n : 0)})</small>`, cls: 'num' },
        ],
        f.by_owner || [],
        { empty: "Lid yo'q" },
      )}</section></div>`;
  }

  function firstPayers(d) {
    const m = A.q('fp:month', A.ym(A.today()));
    const kv = (o) => Object.entries(o || {}).sort((a, b) => b[1] - a[1]);
    return `<div class="filters"><select class="f-input" data-filter="fp:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === m ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      <div class="stats">${A.stat("Birinchi marta to'lov qilganlar", d.count || 0, A.ymLabel(m))}</div>
      <div class="grid-2"><section class="card"><h2>Manba bo'yicha</h2>${A.table([{ h: 'Manba', f: (r) => esc(r[0]) }, { h: 'Soni', f: (r) => r[1], cls: 'num' }], kv(d.by_source))}</section>
      <section class="card"><h2>Kurs bo'yicha</h2>${A.table([{ h: 'Kurs', f: (r) => esc(r[0]) }, { h: 'Soni', f: (r) => r[1], cls: 'num' }], kv(d.by_course))}</section>
      <section class="card wide"><h2>Ro'yxat</h2>${A.table(
        [
          { h: 'Sana', f: (r) => A.fdate(r.date) },
          { h: 'Talaba', f: (r) => `<a href="#/contracts/${r.contract}">${esc(r.student_name)}</a>` },
          { h: 'Kurs / guruh', f: (r) => `${esc(A.courseName(r.course))}<br><small class="muted">${esc(A.groupName(r.group))}</small>` },
          { h: 'Manba', f: (r) => esc(r.source_name) },
          { h: "Birinchi to'lov", f: (r) => `<b>${A.num(r.amount)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, (r) => Number(r.amount))) },
        ],
        d.rows || [],
        { empty: "Bu oyda birinchi marta to'lov qilgan talaba yo'q" },
      )}</section></div>`;
  }

  /* ===================================================== Oyliklar (server API: /salary-assignments/, /salary-payouts/, /kpi-rates/, /kpi/) */
  let salData = {};
  const KPI_LEVELS = [
    { key: (e) => e.branch, label: (k) => A.branchName(k), hideSingle: true },
    { key: (e) => e.ym.slice(0, 4), label: (k) => k, desc: true },
    { key: (e) => e.ym, label: (k) => A.ymLabel(k).split(' ')[0], sort: (k) => k, desc: true },
    { key: (e) => e.user, label: (k) => A.userName(k) },
    {
      key: (e) => `${e.group}:${e.role}`,
      label: (k) => { const [g, r] = k.split(':'); return A.groupName(g) + (r === 'YORDAMCHI' ? ' · yordamchi' : ''); },
      sort: (k) => (A.get('groups', k.split(':')[0]) || {}).number || 0,
    },
  ];
  const kpiOpts = (entries) => {
    const latest = A.sortBy(entries, (e) => e.ym, true)[0];
    return { levels: KPI_LEVELS, value: (l) => A.num(A.sum(l, (e) => Number(e.sum))), def: latest ? `${latest.branch}|${latest.ym.slice(0, 4)}|${latest.ym}` : '' };
  };
  const salTab = (q) => q.tab || (A.isManager() ? 'assign' : 'kpi');

  A.page('salaries', {
    title: 'Oyliklar',
    section: 'salaries',
    async load(p, q) {
      const tab = salTab(q);
      const ym = A.q('sal:month', A.ym(A.today()));
      salData = {};
      if (tab === 'assign') salData.rows = await A.http.get(`/salary-assignments/?month=${ym}`);
      else if (tab === 'kpi') {
        const [entries, rates] = await Promise.all([A.http.get('/kpi/'), A.http.get('/kpi-rates/')]);
        A.S.kpiRates = rates;
        A.version++;
        salData.entries = entries;
        const sel = A.q('kpi:tree', kpiOpts(entries).def);
        const parts = sel ? sel.split('|') : [];
        if (parts.length === KPI_LEVELS.length) {
          const [g, role] = parts[4].split(':');
          salData.rows = await A.http.get(`/kpi/rows/?month=${parts[2]}&user=${parts[3]}&role=${role}&group=${g}`);
        }
      } else if (tab === 'rates') {
        A.S.kpiRates = await A.http.get('/kpi-rates/');
        A.version++;
      } else if (tab === 'payout') {
        // Iyerarxik ko'rinish uchun hammasi yuklanadi (yil → oy → xodim, har tugunda summa)
        let page = 1;
        salData.payouts = [];
        for (;;) {
          const d = await A.http.get(`/salary-payouts/?page_size=200&page=${page}`);
          salData.payouts = salData.payouts.concat(d.results);
          if (page >= (d.pages || 1)) break;
          page++;
        }
      }
      else salData.rows = await A.http.get('/salary-assignments/'); // hamma oylar (hisoblangan) — daraxt: xodim → oylar
    },
    render(p, q) {
      const mgr = A.isManager();
      const tab = salTab(q);
      const tabs = mgr || A.can('salaries', 'a')
        ? [['assign', 'Oylik belgilash'], ['kpi', 'Hisoblangan KPI'], ['rates', 'KPI stavkalari'], ['payout', 'Oylik berish'], ['balance', 'Xodim balansi']]
        : [['kpi', 'Mening KPI'], ['assign', 'Mening oyligim'], ['payout', 'Olganlarim']];
      const ym = A.q('sal:month', A.ym(A.today()));
      const monthSel = `<div class="filters"><select class="f-input" data-filter="sal:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>`;
      let body = '';
      if (tab === 'assign') body = monthSel + assignView(ym, salData.rows || []);
      else if (tab === 'kpi') body = kpiView(salData.entries || [], salData.rows);
      else if (tab === 'rates') body = ratesView();
      else if (tab === 'payout') body = payoutView(salData.payouts || []);
      else body = balanceView(salData.rows || []);
      return `${A.head('Oyliklar', "Jami = belgilangan + bonus + KPI (qo'lda) + ustoz KPI + yordamchi KPI − jarima")}${A.tabs(tabs, tab, 'salaries')}${body}`;
    },
  });
  const canAssign = () => A.can('salaries', 'e') && A.isManager();

  function assignView(ym, rows) {
    return `${canAssign() ? `<div class="row gap">${A.btn('Oylik belgilash', 'sa-new', { icon: 'plus' })}${A.btn("O'tgan oydan nusxa", 'sa-copy', { cls: 'ghost', id: ym })}</div>` : ''}
      ${A.table(
        [
          { h: 'Xodim', f: (s) => `<b>${esc(A.userName(s.user))}</b><br><small class="muted">${esc(A.ROLES[(A.get('users', s.user) || {}).role] || '')}</small>` },
          { h: 'Belgilangan', f: (s) => A.num(s.fixed), cls: 'num' },
          { h: 'Bonus', f: (s) => A.num(s.bonus), cls: 'num' },
          { h: "KPI (qo'lda)", f: (s) => A.num(s.kpi), cls: 'num' },
          { h: 'Ustoz KPI', f: (s) => A.num(s.tkpi), cls: 'num' },
          { h: 'Yordamchi KPI', f: (s) => A.num(s.skpi), cls: 'num' },
          { h: 'Jarima', f: (s) => (Number(s.fine) ? `<span class="t-red">−${A.num(s.fine)}</span>` : '0'), cls: 'num' },
          { h: 'Jami', f: (s) => `<b>${A.num(s.total)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (s) => Number(s.total))) },
          { h: 'Berildi', f: (s) => A.num(s.given), cls: 'num', sum: (r) => A.num(A.sum(r, (s) => Number(s.given))) },
          { h: 'Avvalgi oydan', f: (s) => A.num(s.carried), cls: 'num' },
          { h: 'Yakuniy balans', f: (s) => `<b class="${s.final > 0 ? 't-orange' : s.final < 0 ? 't-red' : ''}">${A.num(s.final)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (s) => Number(s.final))) },
          { h: '', f: (s) => `<div class="row gap nowrap"><button class="btn sm ghost" data-act="bal-open" data-id="${s.id}" title="Batafsil">›</button>${canAssign() ? `<button class="btn sm ghost" data-act="sa-edit" data-id="${s.id}">✎</button>` : ''}</div>` },
        ],
        A.sortBy(rows, (s) => A.userName(s.user)),
        { empty: 'Bu oy uchun oylik belgilanmagan' },
      )}
      <p class="muted small">«Avvalgi oydan» — barcha oldingi oylardagi (jami − berilgan) yig'indisi, yillar oralig'ida ham. Ustoz va yordamchi KPI davomatdan avtomatik. Jarima jamidan ayiriladi (AppSheet'da ayirilmagan edi).</p>`;
  }
  A.salaryForm = (s, ym) => {
    const B = s ? s.branch : A.branchIds()[0];
    const [y0, m0] = (ym || A.ym(A.today())).split('-').map(Number);
    const num = (v) => Number(v) || 0;
    A.form({
      title: s ? `Oylik: ${A.userName(s.user)} · ${A.MONTHS[s.month - 1]} ${s.year}` : 'Oylik belgilash',
      values: s ? { ...s, month: String(s.month), fixed: num(s.fixed), bonus: num(s.bonus), kpi: num(s.kpi), fine: num(s.fine) } : { year: y0, month: String(m0), fixed: 0, bonus: 0, kpi: 0, fine: 0 },
      fields: [
        { name: 'user', label: 'Xodim', type: 'select', required: true, readonly: () => !!s, options: () => A.S.users.filter((u) => u.role !== 'ADMIN' && u.role !== 'BOSHQA' && (u.status === 'Faol' || (s && u.id === s.user)) && (u.branches || []).includes(B)).map((u) => [u.id, `${u.full_name} · ${A.ROLES[u.role]}`]) },
        { name: 'year', label: 'Yil', type: 'number', required: true, half: true, show: (x) => x.user, readonly: () => !!s },
        { name: 'month', label: 'Oy', type: 'select', required: true, half: true, show: (x) => x.user, readonly: () => !!s, options: A.MONTHS.map((m, i) => [String(i + 1), m]) },
        { name: 'fixed', label: 'Belgilangan oylik', type: 'money', half: true, show: (x) => x.month },
        { name: 'bonus', label: 'Bonus', type: 'money', half: true, show: (x) => x.month },
        { name: 'kpi', label: "KPI (qo'lda)", type: 'money', half: true, show: (x) => x.month },
        { name: 'fine', label: 'Jarima', type: 'money', half: true, show: (x) => x.month },
        {
          name: 'auto', label: 'Avtomatik (davomatdan)', type: 'computed', show: (x) => x.month && x.user,
          compute: (x) => (s ? `Ustoz KPI: <b>${A.num(s.tkpi)}</b> · Yordamchi KPI: <b>${A.num(s.skpi)}</b><br>Jami: <b>${A.money(num(x.fixed) + num(x.bonus) + num(x.kpi) + num(s.tkpi) + num(s.skpi) - num(x.fine))}</b>` : 'Ustoz va yordamchi KPI saqlangandan keyin davomatdan avtomatik qo\'shiladi'),
        },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.month },
      ],
      async onSubmit(x) {
        const rec = { fixed: num(x.fixed), bonus: num(x.bonus), kpi: num(x.kpi), fine: num(x.fine), comment: x.comment || '' };
        if (s) await A.http.patch(`/salary-assignments/${s.id}/`, rec);
        else await A.http.post('/salary-assignments/', { ...rec, user: x.user, year: Number(x.year), month: Number(x.month) });
        A.toast('Saqlandi');
        A.refresh();
      },
    });
  };
  A.act['sa-new'] = () => A.salaryForm(null, A.q('sal:month', A.ym(A.today())));
  A.act['sa-edit'] = (el) => A.salaryForm((salData.rows || []).find((s) => s.id === el.dataset.id));
  A.act['sa-copy'] = async (el) => {
    const r = await A.http.post('/salary-assignments/copy/', { month: el.dataset.id });
    A.toast(r.created ? `${r.created} ta xodimga oylik nusxalandi (belgilangan summa)` : "Nusxalanadigan yangi yozuv yo'q");
    A.refresh();
  };

  /* Hisoblangan KPI: chapda daraxt (yil → oy → xodim → guruh, KPI summasi bilan), o'ngda jadval (serverda yig'ilgan) */
  function kpiView(entries, leafRows) {
    const opts = kpiOpts(entries);
    const sel = A.treeFilter('kpi', entries, opts);
    const manyMonths = new Set(sel.map((r) => r.ym)).size > 1;
    const table = A.table(
      [
        ...(manyMonths ? [{ h: 'Oy', f: (r) => A.ymLabel(r.ym) }] : []),
        { h: 'Xodim', f: (r) => `<b>${esc(A.userName(r.user))}</b>` },
        { h: 'Rol', f: (r) => A.badge(r.role === 'USTOZ' ? 'Ustoz' : 'Yordamchi', r.role === 'USTOZ' ? 'blue' : 'gray') },
        { h: 'Guruh', f: (r) => esc(A.groupName(r.group)) },
        { h: 'Stavka', f: (r) => { const k = A.rateFor(r.branch, r.user, r.role, r.course, r.ym); return k ? (k.type === 'Foiz' ? `${Number(k.percent)}% narxdan` : `${A.num(k.fixed)} / talaba / oy`) : '<span class="t-red">belgilanmagan</span>'; } },
        { h: 'Dars qatorlari', f: (r) => `${r.n} <small class="muted">(KPI: ${r.paid})</small>`, cls: 'num' },
        { h: 'KPI', f: (r) => `<b>${A.num(r.sum)}</b>${r.pending ? ` ${A.badge(r.pending + ' ta kutilmoqda', 'orange')}` : ''}`, cls: 'num', sum: (rr) => A.num(A.sum(rr, (r) => Number(r.sum))) },
      ],
      A.sortBy(A.sortBy(sel, (r) => `${A.userName(r.user)}|${r.role}|${A.groupName(r.group)}`), (r) => r.ym, true),
      { empty: "KPI yo'q" },
    );
    const detail = leafRows
      ? `<h3>Davomat qatorlari</h3>${A.table(
          [
            { h: 'Sana', f: (a) => A.fdate(a.date) },
            { h: 'Shartnoma', f: (a) => `<a href="#/contracts/${a.contract}">${esc(a.student_name)} №${a.contract_number}</a>` },
            { h: 'Status', f: (a) => A.attBadge(a.status) },
            { h: 'KPI', f: (a) => { const v = (A.q('kpi:tree', '').split('|')[4] || '').endsWith('YORDAMCHI') ? a.skpi : a.tkpi; return v === null ? A.badge('kutilmoqda', 'orange') : A.num(v); }, cls: 'num' },
          ],
          leafRows,
        )}`
      : '';
    return `<div class="settings tree-layout">${A.treeNav('kpi', entries, opts)}<div class="settings-body">${table}${detail}
    <p class="muted small">KPI har bir davomat qatori uchun: O'zgarmas — stavka ÷ oydagi dars soni; Foiz — foiz × kurs narxi ÷ oydagi dars soni. Besabab (X), Nofaol (–) va Grant shartnomalar uchun KPI yozilmaydi. «Kutilmoqda» — oydagi dars soni hali tasdiqlanmagan.</p></div></div>`;
  }

  function ratesView() {
    const rows = A.sortBy(A.rows('kpiRates'), (k) => A.userName(k.user) + k.effective_from);
    const canE = canAssign();
    const cur = A.ym(A.today());
    return `${canE ? `<div class="row gap">${A.btn("Stavka qo'shish", 'rate-new', { icon: 'plus' })}${A.btn("O'tgan oy stavkalarini nusxalash", 'rate-copy', { cls: 'ghost' })}</div>` : ''}
      <p class="muted small">Stavka «amal qilish oyi» bilan saqlanadi: oy uchun shu oyda amalda bo'lgan oxirgi yozuv olinadi. Stavka faqat o'zgarganda yangi yozuv qo'shiladi. Saqlanganda tegishli davomat qatorlaridagi KPI qayta hisoblanadi.</p>
      ${A.table(
        [
          { h: 'Xodim', f: (k) => esc(A.userName(k.user)) },
          { h: 'Rol', f: (k) => (k.role_type === 'USTOZ' ? 'Ustoz' : 'Yordamchi') },
          { h: 'Kurs', f: (k) => esc(A.courseName(k.course)) },
          { h: 'Amal qiladi', f: (k) => A.ymLabel(k.effective_from) + ' dan' },
          { h: 'Kelishuv', f: (k) => (k.type === 'Foiz' ? `Foiz: <b>${Number(k.percent)}%</b>` : `O'zgarmas: <b>${A.num(k.fixed)}</b>`) },
          { h: 'Holat', f: (k) => { const c = A.rateFor(k.branch, k.user, k.role_type, k.course, cur); return c && c.id === k.id ? A.badge('amalda', 'green') : k.effective_from > cur ? A.badge('kelajakda', 'blue') : A.badge('tarix', 'gray'); } },
          { h: '', f: (k) => (canE ? `<div class="row gap nowrap"><button class="btn sm ghost" data-act="rate-edit" data-id="${k.id}">✎</button><button class="btn sm ghost" data-act="rate-del" data-id="${k.id}">🗑</button></div>` : '') },
        ],
        rows,
        { empty: "Stavka yo'q" },
      )}`;
  }
  A.rateForm = (k) => {
    const B = k ? k.branch : A.branchIds()[0];
    A.form({
      title: k ? `KPI stavkasi: ${A.userName(k.user)}` : 'KPI stavkasi',
      values: k ? { ...k, fixed: Number(k.fixed), percent: Number(k.percent) } : { role_type: 'USTOZ', effective_from: A.ym(A.today()), type: 'Foiz' },
      fields: [
        { name: 'role_type', label: 'Kim uchun', type: 'seg', options: [['USTOZ', 'Ustoz'], ['YORDAMCHI', 'Yordamchi']], resets: ['user'], readonly: () => !!k },
        { name: 'user', label: 'Xodim', type: 'select', required: true, readonly: () => !!k, options: (x) => A.S.users.filter((u) => (x.role_type === 'USTOZ' ? ['USTOZ', 'USTOZ_YORDAMCHI'] : ['YORDAMCHI', 'USTOZ_YORDAMCHI']).includes(u.role) && (u.branches || []).includes(B)).map((u) => [u.id, u.full_name]) },
        { name: 'course', label: 'Kurs', type: 'select', required: true, show: (x) => x.user, readonly: () => !!k, options: () => A.optList('courses', 'name', (c) => c.branches.includes(B)) },
        { name: 'effective_from', label: 'Amal qilish oyi', type: 'month', required: true, show: (x) => x.course },
        { name: 'type', label: 'Kelishuv turi', type: 'seg', options: ["O'zgarmas", 'Foiz'], show: (x) => x.course },
        { name: 'fixed', label: "O'zgarmas summa (1 talaba uchun oyiga)", type: 'money', required: (x) => x.type === "O'zgarmas", show: (x) => x.type === "O'zgarmas" },
        { name: 'percent', label: 'Foiz (0-100)', type: 'number', min: 0, max: 100, required: (x) => x.type === 'Foiz', show: (x) => x.type === 'Foiz', validate: (n) => (n < 0 || n > 100 ? "0-100 oralig'ida" : '') },
      ],
      async onSubmit(x) {
        const rec = { effective_from: x.effective_from, type: x.type, fixed: Number(x.fixed) || 0, percent: Number(x.percent) || 0 };
        const r = k ? await A.http.patch(`/kpi-rates/${k.id}/`, rec) : await A.http.post('/kpi-rates/', { ...rec, user: x.user, role_type: x.role_type, course: x.course });
        A.toast(`Saqlandi. ${r.recalculated} ta davomat qatori qayta hisoblandi`);
        A.refresh();
      },
    });
  };
  A.act['rate-new'] = () => A.rateForm(null);
  A.act['rate-edit'] = (el) => A.rateForm(A.get('kpiRates', el.dataset.id));
  A.act['rate-del'] = async (el) => {
    if (!(await A.confirm("Stavkani o'chirasizmi? Tegishli davomat qatorlarida KPI qayta hisoblanadi.", "O'chirish", true))) return;
    await A.http.del(`/kpi-rates/${el.dataset.id}/`);
    A.refresh();
  };
  A.act['rate-copy'] = () => A.toast("«Amal qilish oyi» mantiqida o'tgan oy stavkalari yangi oyda ham avtomatik amal qiladi — nusxalash shart emas. Faqat o'zgargan stavkani yangi oydan kiriting.", 'warn');

  // Oylik berish — «Hisoblangan KPI» kabi iyerarxik: Barchasi → yil → oy → xodim, har tugunda berilgan summa.
  // Oy — qaysi oy uchun berilgan (davr), AppSheet'dagidek; pul berilgan sana jadvalda ko'rinadi.
  const spPeriod = (s) => `${s.year}-${String(s.month).padStart(2, '0')}`;
  const SP_LEVELS = [
    { key: (s) => String(s.year), label: (k) => k, desc: true },
    { key: spPeriod, label: (k) => A.ymLabel(k).split(' ')[0], sort: (k) => k, desc: true },
    { key: (s) => s.user, label: (k) => A.userName(k) },
  ];
  function payoutView(rows) {
    const latest = A.sortBy(rows, (s) => `${spPeriod(s)}|${s.date}`, true)[0];
    const opts = { levels: SP_LEVELS, value: (l) => A.num(A.sum(l, (s) => Number(s.amount))), def: latest ? `${latest.year}|${spPeriod(latest)}` : '' };
    const sel = A.treeFilter('sp', rows, opts);
    const table = A.table(
      [
        { h: 'Sana', f: (s) => A.fdate(s.date) },
        { h: 'Xodim', f: (s) => esc(A.userName(s.user)) },
        { h: 'Davr', f: (s) => `${A.MONTHS[s.month - 1]} ${s.year}` },
        { h: 'Turi', f: (s) => esc(s.type) },
        { h: 'Summa', f: (s) => `<b>${A.num(s.amount)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (s) => Number(s.amount))) },
        { h: "G'azna", f: (s) => `${esc(A.accName(s.account))} · ${A.CASH[s.cash_type]}` },
        { h: 'Berdi', f: (s) => esc(A.userName(s.cashier)) },
        { h: 'Izoh', f: (s) => esc(s.comment || '') },
        { h: '', f: (s) => { const del = A.canEdit('salaries', s, 'date', 'd'); return A.can('salaries', 'd') ? `<button class="btn sm ghost" data-act="sp-del" data-id="${s.id}" ${del.ok ? '' : `disabled title="${esc(del.why)}"`}>🗑</button>` : ''; } },
      ],
      A.sortBy(sel, (s) => s.date, true),
      { empty: "Yozuv yo'q" },
    );
    return `${A.can('salaries', 'a') ? `<div class="row gap" style="margin-bottom:8px">${A.btn('Oylik berish', 'sp-new', { icon: 'plus' })}</div>` : ''}
      <div class="settings tree-layout">${A.treeNav('sp', rows, opts)}<div class="settings-body">${table}</div></div>`;
  }
  A.act['sp-new'] = async () => {
    const top = A.isTop();
    const B = A.branchIds()[0];
    const [, all] = await Promise.all([A.reloadMoney(), A.http.get('/salary-assignments/')]);
    const prevYm = A.addMonths(A.ym(A.today()), -1);
    const [y0, m0] = prevYm.split('-').map(Number);
    const find = (x) => all.find((z) => z.user === x.user && z.year === Number(x.year) && z.month === Number(x.month));
    A.form({
      title: 'Oylik berish',
      values: { year: y0, month: String(m0), date: A.today(), type: "O'zgarmas", cash_type: 'CASH' },
      fields: [
        { name: 'user', label: 'Xodim', type: 'select', required: true, options: () => A.S.users.filter((u) => u.role !== 'ADMIN' && u.role !== 'BOSHQA' && (u.branches || []).includes(B)).map((u) => [u.id, u.full_name]) },
        { name: 'year', label: 'Yil', type: 'number', half: true, show: (x) => x.user },
        { name: 'month', label: 'Oy', type: 'select', half: true, show: (x) => x.user, options: A.MONTHS.map((m, i) => [String(i + 1), m]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.user && x.month, text: (x) => { const s = find(x); return s ? `Jami: ${A.num(s.total)} · berilgan: ${A.num(s.given)} · <b>qoldiq: ${A.money(s.final)}</b>` : 'Bu oy uchun oylik belgilanmagan'; } },
        { name: 'type', label: 'Oylik turi', type: 'seg', options: ["O'zgarmas", 'Bonus', 'KPI'], show: (x) => x.user },
        { name: 'cash_type', label: "To'lov turi", type: 'seg', options: cashOpts, show: (x) => x.user, resets: ['account'] },
        noAccount('account', (x) => x.user && !A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type)),
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.user && A.myAccounts().some((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type), options: (x) => A.myAccounts().filter((a) => a.cash_type === 'ALL' || a.cash_type === x.cash_type).map((a) => [a.id, a.name]) },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.account, help: (x) => `G'aznada: ${A.money(A.accBal(x.account, x.cash_type))}`, validate: (n, x) => (n <= 0 ? "0 dan katta bo'lsin" : !top && n > A.accBal(x.account, x.cash_type) ? `G'aznada ${A.num(A.accBal(x.account, x.cash_type))} so'm pul bor` : '') },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.account, readonly: () => !top, help: () => (top ? '' : 'Faqat bugungi sana bilan') },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.account },
      ],
      async onSubmit(x) {
        await A.http.post('/salary-payouts/', { user: x.user, year: Number(x.year), month: Number(x.month), date: x.date, type: x.type, amount: x.amount, cash_type: x.cash_type, account: x.account, comment: x.comment || '' });
        await A.reloadMoney();
        A.toast('Oylik berildi');
        A.refresh();
      },
    });
  };
  A.act['sp-del'] = async (el) => {
    if (!(await A.confirm("Oylik berish yozuvini o'chirasizmi? Pul g'azna balansiga qaytadi, yozuv audit'da qoladi.", "O'chirish", true))) return;
    await A.http.del(`/salary-payouts/${el.dataset.id}/`);
    await A.reloadMoney();
    A.refresh();
  };

  A.act['bal-left'] = () => { A.ui.balLeft = !A.ui.balLeft; A.refresh(); };
  // Xodim balansi — daraxt: Barchasi → xodim (har tugunda yakuniy balans). «Barchasi» — har xodimning oxirgi davri; xodim tanlansa — uning oylari
  const BAL_LEVELS = [{ key: (r) => r.user, label: (k) => A.userName(k) }];
  const periodNo = (r) => r.year * 100 + r.month;
  const latestPerUser = (rs) => [...A.groupBy(rs, (r) => r.user)].map(([, l]) => A.sortBy(l, periodNo, true)[0]);
  const balCls2 = (n) => (n > 0 ? 't-orange' : n < 0 ? 't-red' : '');
  function balanceView(all) {
    // Ishdan ketgan xodimlar standart holda yashirin (qoldig'i bo'lsa — eslatma va ko'rsatish havolasi)
    const isLeft = (r) => ((A.get('users', r.user) || {}).status || 'Faol') !== 'Faol';
    const left = latestPerUser(all.filter(isLeft));
    const rows = A.ui.balLeft ? all : all.filter((r) => !isLeft(r));
    const owed = left.filter((r) => Number(r.final));
    const note = left.length
      ? `<p class="muted small">Ishdan ketgan ${left.length} ta xodim ${A.ui.balLeft ? "ko'rsatilgan" : 'yashirilgan'}${owed.length ? ` (shulardan ${owed.length} tasida qoldiq bor: ${A.num(A.sum(owed, (r) => Number(r.final)))} so'm)` : ''}. <a href="#" data-act="bal-left">${A.ui.balLeft ? 'Yashirish' : "Ko'rsatish"}</a></p>`
      : '';
    const opts = { levels: BAL_LEVELS, value: (rs) => A.num(A.sum(latestPerUser(rs), (r) => Number(r.final))) };
    const sel = A.treeFilter('bal', rows, opts);
    const single = A.treeDepth('bal', opts) > 0; // bitta xodim tanlangan — oylar bo'yicha tarix
    const cols = [
      ...(single ? [] : [{ h: 'Xodim', f: (r) => `<b>${esc(A.userName(r.user))}</b><br><small class="muted">${esc(A.ROLES[(A.get('users', r.user) || {}).role] || '')}</small>` }]),
      { h: single ? 'Davr' : 'Oxirgi davr', f: (r) => `${A.MONTHS[r.month - 1]} ${r.year}` },
      { h: 'Avvalgi oylardan', f: (r) => A.num(r.carried), cls: 'num' },
      { h: 'Shu oy jami', f: (r) => A.num(r.total), cls: 'num' },
      { h: 'Berilgan', f: (r) => A.num(r.given), cls: 'num' },
      { h: 'Yakuniy balans', f: (r) => `<b class="${balCls2(Number(r.final))}">${A.num(r.final)}</b>`, cls: 'num', sum: single ? undefined : (rr) => A.num(A.sum(rr, (r) => Number(r.final))) },
      { h: '', f: () => '<span class="muted">›</span>' },
    ];
    const shown = single ? A.sortBy(sel, periodNo, true) : A.sortBy(latestPerUser(sel), (r) => A.userName(r.user));
    return `${note}<div class="settings tree-layout">${A.treeNav('bal', rows, opts)}<div class="settings-body">${A.table(cols, shown, {
      rowAttr: (r) => `class="row-link" data-act="bal-open" data-id="${r.id}" title="Batafsil ko'rish"`, empty: 'Oylik belgilanmagan' })}
    <p class="muted small">Qatorni bosing — shu oyning hisob-kitobi va olingan pullar ochiladi.</p></div></div>`;
  }

  /* Xodim balansi: tanlangan oy bo'yicha batafsil hisob-kitob (serverdan /breakdown/) */
  const balWord = (n) => (n > 0 ? 'xodim haqdor (markaz berishi kerak)' : n < 0 ? 'xodim qarzdor (ortiqcha olgan)' : 'hisob teng');
  const balCls = (n) => (n > 0 ? 't-orange' : n < 0 ? 't-red' : 't-green');
  A.act['bal-open'] = async (el) => {
    const d = await A.http.get(`/salary-assignments/${el.dataset.id}/breakdown/`);
    const sa = d.assignment, c = sa, history = d.history, payouts = d.payouts;
    const u = A.get('users', sa.user) || {};
    const period = `${A.MONTHS[sa.month - 1]} ${sa.year}`;
    const line = (label, v, opts = {}) => `<tr><td>${label}</td><td class="num ${opts.cls || ''}">${opts.minus && Number(v) ? '− ' : ''}${A.num(v)}</td></tr>`;
    const body = `
      <div class="detail-top"><span class="muted">${esc(A.ROLES[u.role] || '')} · ${esc(A.branchName(sa.branch))}</span></div>
      ${history.length > 1 ? `<div class="filters">${history.map((h) => `<button class="btn sm ${h.id === sa.id ? 'primary' : 'ghost'}" data-act="bal-open" data-id="${h.id}">${A.MONTHS[h.month - 1]} ${h.year}</button>`).join('')}</div>` : ''}
      <div class="stats">
        ${A.stat('Avvalgi oylardan', `<span class="${balCls(c.carried)}">${A.num(c.carried)}</span>`, balWord(c.carried))}
        ${A.stat(`${period} hisoblangan`, A.num(c.total), 'oylik + bonus + KPI − jarima')}
        ${A.stat('Shu oy berilgan', A.num(c.given), `${payouts.length} ta to'lov`)}
        ${A.stat('Yakuniy balans', `<span class="${balCls(c.final)}">${A.num(c.final)}</span>`, balWord(c.final), c.final > 0 ? 'warn' : c.final < 0 ? 'danger' : '')}
      </div>
      <h3>${period}: hisoblangan oylik</h3>
      <div class="tbl-wrap"><table class="tbl"><tbody>
        ${line("Belgilangan oylik (o'zgarmas)", sa.fixed)}
        ${line('Bonus', sa.bonus)}
        ${line("KPI (qo'lda kiritilgan)", sa.kpi)}
        ${line('Ustoz KPI <small class="muted">(davomatdan)</small>', c.tkpi)}
        ${line('Yordamchi KPI <small class="muted">(davomatdan)</small>', c.skpi)}
        ${line('Jarima', sa.fine, { minus: true, cls: Number(sa.fine) ? 't-red' : '' })}
      </tbody><tfoot><tr><td><b>Jami hisoblangan</b></td><td class="num"><b>${A.num(c.total)}</b></td></tr></tfoot></table></div>
      ${sa.comment ? `<p class="muted small">Izoh: ${esc(sa.comment)}</p>` : ''}
      <h3>${period} uchun berilgan pullar</h3>
      ${A.table(
        [
          { h: 'Sana', f: (p) => A.fdate(p.date) },
          { h: 'Turi', f: (p) => esc(p.type) },
          { h: 'Summa', f: (p) => `<b>${A.num(p.amount)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, (p) => Number(p.amount))) },
          { h: "G'azna", f: (p) => `${esc(A.accName(p.account))} · ${A.CASH[p.cash_type]}` },
          { h: 'Berdi', f: (p) => esc(A.userName(p.cashier)) },
          { h: 'Izoh', f: (p) => esc(p.comment || '') },
        ],
        payouts,
        { empty: 'Bu oy uchun hali pul berilmagan' },
      )}
      <h3>Yakuniy balans</h3>
      <div class="tbl-wrap"><table class="tbl"><tbody>
        ${line(`Avvalgi oylardan qoldiq${Number(sa.opening) ? ' <small class="muted">(boshlang\'ich qoldiq bilan)</small>' : ''}`, c.carried, { cls: balCls(c.carried) })}
        ${line(`+ ${period} hisoblangan`, c.total)}
        ${line(`− ${period} berilgan`, c.given)}
      </tbody><tfoot><tr><td><b>Yakuniy balans</b> <small class="muted">— ${balWord(c.final)}</small></td><td class="num"><b class="${balCls(c.final)}">${A.num(c.final)}</b></td></tr></tfoot></table></div>
      ${history.length > 1 ? `<h3>Oylar bo'yicha tarix</h3>${A.table(
        [
          { h: 'Davr', f: (h) => `${A.MONTHS[h.month - 1]} ${h.year}` },
          { h: 'Hisoblangan', f: (h) => A.num(h.total), cls: 'num' },
          { h: 'Berilgan', f: (h) => A.num(h.given), cls: 'num' },
          { h: "Oy qoldig'i", f: (h) => { const x = Number(h.total) - Number(h.given); return `<span class="${balCls(x)}">${A.num(x)}</span>`; }, cls: 'num' },
          { h: 'Yakuniy balans', f: (h) => `<b class="${balCls(h.final)}">${A.num(h.final)}</b>`, cls: 'num' },
        ],
        history,
        { rowAttr: (h) => `class="row-link" data-act="bal-open" data-id="${h.id}"` },
      )}` : ''}`;
    el.closest('.overlay')?.remove(); // oy almashtirilganda eski oyna yopiladi
    A.modal({ title: `${u.full_name || A.userName(sa.user)} — xodim balansi`, wide: true, body });
  };
})(window.App);

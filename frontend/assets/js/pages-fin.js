/* Moliya: To'lovlar, Tasdiqlashlar, G'aznalar, O'tkazmalar, Ayirboshlash, Xarajatlar, Kreditorlar, Foyda, Oyliklar */
(function (A) {
  const esc = A.esc;
  const ncBadge = (p) => (p.nc_status ? A.badge(p.nc_status, p.nc_status === 'Tasdiqlandi' ? 'green' : 'orange') : '');
  const cashOpts = [['CASH', 'Naqd'], ['CARD', 'Karta'], ['BANK', 'Bank']];

  /* ===================================================== To'lovlar */
  A.page('payments', {
    title: "To'lovlar",
    section: 'payments',
    render() {
      return `${A.head("To'lovlar", 'Guruhlash: yil → oy → sana, jami summalar bilan', (A.can('payments', 'a') ? A.btn("To'lov qabul qilish", 'pay-new', { icon: 'plus' }) : '') + A.btn('Excel', 'payments-csv', { cls: 'ghost', icon: 'download' }))}
        ${A.filterBar('payments', [A.fSearch('payments', 'Talaba yoki shartnoma…'), A.fSelect('payments', 'month', A.monthOptions(), 'Barcha oylar'), A.fSelect('payments', 'type', cashOpts, 'Barcha turlar')])}
        <div data-results>${this.results()}</div>`;
    },
    results() {
      const s = A.q('payments:search', ''), m = A.q('payments:month', ''), t = A.q('payments:type', '');
      const rows = A.vis('payments').filter((p) => (!m || A.ym(p.date) === m) && (!t || p.cash_type === t) && A.match(A.contractName(p.contract), s));
      if (!rows.length) return A.empty("To'lov topilmadi");
      const byM = A.groupBy(A.sortBy(rows, (p) => p.date + p.created_at, true), (p) => A.ym(p.date));
      return [...byM]
        .map(([ym, list]) => {
          const byD = A.groupBy(list, (p) => p.date);
          return `<section class="group-block"><h3>${A.ymLabel(ym)} <span class="muted">· ${list.length} ta · ${A.money(A.sum(list, 'amount'))}</span></h3>
          ${[...byD]
            .map(([d, dl]) => `<div class="day-h">${A.fdate(d)} <span class="muted">${A.WD[A.isoWeekday(d)]}</span><b>${A.money(A.sum(dl, 'amount'))}</b></div>${A.table(
              [
                { h: 'Shartnoma', f: (p) => `<a href="#/contracts/${p.contract}">${esc(A.contractName(p.contract))}</a>` },
                { h: 'Summa', f: (p) => `<b>${A.num(p.amount)}</b>`, cls: 'num' },
                { h: 'Turi', f: (p) => `${A.CASH[p.cash_type]} ${ncBadge(p)}` },
                { h: 'Chegirma', f: (p) => (p.discount ? `${A.num(p.discount)} ${A.badge(p.disc_status, p.disc_status === 'Tasdiqlandi' ? 'green' : 'orange')}` : ''), cls: 'num' },
                { h: "G'azna / hisobchi", f: (p) => `${esc(A.accName(p.cashbox))}<br><small class="muted">${esc(A.userName(p.accountant))}</small>` },
                { h: '', f: (p) => payActions(p) },
              ],
              dl,
            )}`)
            .join('')}</section>`;
        })
        .join('');
    },
  });
  const payLocked = (p) => p.disc_status === 'Tasdiqlandi' || p.nc_status === 'Tasdiqlandi';
  function payActions(p) {
    const ed = A.canEdit('payments', { ...p, locked: payLocked(p) });
    const del = A.canEdit('payments', { ...p, locked: payLocked(p) }, 'date', 'd');
    return `<div class="row gap nowrap"><button class="btn sm ghost" data-act="receipt" data-id="${p.id}">Chek</button>
      ${A.can('payments', 'e') ? `<button class="btn sm ghost" data-act="pay-edit" data-id="${p.id}" ${ed.ok ? '' : `disabled title="${esc(ed.why)}"`}>✎</button>` : ''}
      ${A.can('payments', 'd') ? `<button class="btn sm ghost" data-act="pay-del" data-id="${p.id}" ${del.ok ? '' : `disabled title="${esc(del.why)}"`}>🗑</button>` : ''}</div>`;
  }
  A.act['payments-csv'] = () =>
    A.downloadCSV('tolovlar.csv', [['Sana', 'Shartnoma', 'Summa', 'Turi', 'Chegirma', "G'azna"], ...A.vis('payments').map((p) => [p.date, A.contractName(p.contract), p.amount, A.CASH[p.cash_type], p.discount, A.accName(p.cashbox)])]);

  A.paymentForm = (p, contractId) => {
    const isNew = !p;
    const top = A.isTop();
    const B = A.branchIds()[0];
    const branch = A.get('branches', B);
    const cashboxOpts = (x) => {
      if (!x.cash_type) return [];
      if (x.cash_type === 'CASH') return A.myAccounts().map((a) => [a.id, a.name]);
      return [[branch.noncash_cashbox, A.accName(branch.noncash_cashbox) + ' (naqdsiz g\'azna — sozlamadan)']];
    };
    A.form({
      title: isNew ? "To'lov qabul qilish" : "To'lovni tahrirlash",
      values: p ? { ...p } : { contract: contractId || '', date: A.today(), cash_type: 'CASH', discount_type: '', accountant: A.S.currentUser },
      fields: [
        { name: 'contract', label: 'Shartnoma', type: 'select', required: true, readonly: () => !isNew, options: () => A.sortBy(A.vis('contracts'), (c) => (A.contractStatus(c) === 'Nofaol' ? 'z' : 'a') + A.contractName(c)).map((c) => [c.id, `${A.contractName(c)} · ${A.groupName(c.group)} · balans ${A.num(A.debtOf(c.id))}${A.contractStatus(c) === 'Nofaol' ? ' (nofaol)' : ''}`]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.contract, text: (x) => { const d = A.debtOf(x.contract); const c = A.get('contracts', x.contract); return `Joriy balans: <b class="${d > 0 ? 't-red' : 't-green'}">${A.money(d)}</b> · oylik narx: ${A.money(A.priceFor(c.branch, c.course, A.ym(A.today())))}`; } },
        { name: 'amount', label: "To'lov miqdori", type: 'money', show: (x) => x.contract, min: 0, validate: (n) => (n < 0 ? "Manfiy summa — ochiq savol (15-bo'lim, 8). Prototipda ruxsat yo'q" : '') },
        { name: 'cash_type', label: "To'lov shakli", type: 'seg', options: cashOpts, show: (x) => x.amount > 0, resets: ['cashbox', 'accountant'] },
        { name: 'cashbox', label: "G'azna", type: 'select', auto: true, required: (x) => x.amount > 0, show: (x) => x.amount > 0 && x.cash_type, options: cashboxOpts, resets: ['accountant'], help: (x) => (x.cash_type === 'CASH' ? "Siz mas'ul bo'lgan faol g'aznalar" : '') },
        { name: 'accountant', label: 'Hisobchi', type: 'select', auto: true, show: (x) => x.cashbox, options: (x) => ((A.get('accounts', x.cashbox) || {}).responsible || []).map((u) => [u, A.userName(u)]) },
        { name: 'nc_note', type: 'note', tone: 'warn', show: (x) => x.amount > 0 && x.cash_type && x.cash_type !== 'CASH', text: "Naqdsiz to'lov <b>tasdiqlanmaguncha g'azna balansiga qo'shilmaydi</b>. Tasdiqlash: Admin; Bosh menejer 360 kun, Filial menejeri 7 kun ichida." },
        { name: 'discount_type', label: 'Chegirma turi (ixtiyoriy)', type: 'select', show: (x) => x.contract, placeholder: "Chegirmasiz", options: () => A.rows('discountTypes').filter((d) => top || !d.is_system).map((d) => [d.id, `${d.name} (max ${A.num(d.max)})`]) },
        {
          name: 'discount', label: 'Chegirma summasi', type: 'money', show: (x) => x.discount_type, required: (x) => !!x.discount_type,
          validate: (n, x) => { const d = A.get('discountTypes', x.discount_type); return d && n > d.max ? `Bu chegirma turiga ${A.num(d.max)} so'mdan ortiqcha chegirma kiritib bo'lmaydi` : n <= 0 ? "Chegirma 0 dan katta bo'lsin" : ''; },
        },
        { name: 'd_note', type: 'note', tone: 'warn', show: (x) => x.discount > 0, text: 'Chegirma tasdiqlashga yuboriladi (Admin; Bosh menejer 30 kun ichida).' },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.contract, readonly: () => !top, help: () => (top ? "Admin va Bosh menejer o'tgan sanani ham kirita oladi" : 'Faqat bugungi sana bilan kiritiladi'), validate: (d) => (d > A.today() ? "Kelasi davr bilan kiritib bo'lmaydi" : '') },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.amount > 0 || x.discount > 0 },
      ],
      submit: isNew ? 'Qabul qilish va chek' : 'Saqlash',
      onSubmit(x) {
        if (!(x.amount > 0) && !(x.discount > 0)) return "To'lov summasi yoki chegirma kiritilishi kerak";
        const c = A.get('contracts', x.contract);
        const amount = Number(x.amount) || 0;
        const rec = {
          branch: c.branch, contract: c.id, date: x.date, amount, cash_type: amount ? x.cash_type : '',
          discount_type: x.discount_type, discount: Number(x.discount) || 0,
          cashbox: amount ? x.cashbox : '', accountant: amount ? x.accountant : '', comment: x.comment,
        };
        if (isNew || p.discount !== rec.discount || p.discount_type !== rec.discount_type) {
          rec.disc_status = rec.discount ? 'Tasdiqlashga' : '';
          rec.disc_by = '';
        }
        if (isNew || p.cash_type !== rec.cash_type || p.amount !== rec.amount) {
          rec.nc_status = amount && rec.cash_type !== 'CASH' ? 'Tasdiqlashga' : '';
          rec.nc_by = '';
        }
        let id;
        if (isNew) id = A.insert('payments', rec, "To'lov", `${A.contractName(c)}: ${A.num(amount)}`).id;
        else { A.patch('payments', p.id, rec, "To'lov", A.contractName(c)); id = p.id; }
        A.toast(isNew ? "To'lov qabul qilindi" : 'Saqlandi');
        A.refresh();
        if (isNew) setTimeout(() => A.receipt(id), 60);
      },
    });
  };
  A.act['pay-new'] = (el) => A.paymentForm(null, el.dataset.id);
  A.act['pay-edit'] = (el) => A.paymentForm(A.get('payments', el.dataset.id));
  A.act['pay-del'] = async (el) => {
    const p = A.get('payments', el.dataset.id);
    if (!(await A.confirm(`${A.contractName(p.contract)} — ${A.money(p.amount)} to'lovini o'chirasizmi? Moliyaviy yozuv bazadan o'chmaydi (soft delete), audit'da qoladi.`, "O'chirish", true))) return;
    A.softDelete('payments', p.id, "To'lov", A.contractName(p.contract));
    A.refresh();
  };

  /* ---- PDF chek (prototipda chop etiladigan ko'rinish) ---- */
  A.receipt = (id) => {
    const p = A.get('payments', id);
    const c = A.get('contracts', p.contract);
    const pending = p.nc_status === 'Tasdiqlashga' || p.disc_status === 'Tasdiqlashga';
    if (pending && !['ADMIN', 'BOSH_MENEJER', 'FILIAL_MENEJERI'].includes(A.role())) {
      A.modal({ title: 'Chek', body: `<div class="alert warn">${A.icon('alert')}<div>Bu to'lov hali tasdiqlanmagan (naqdsiz yoki chegirma). Chek tasdiqlangandan keyin chiqadi. Admin, Bosh menejer va Filial menejeri uni hozir ham ko'ra oladi.</div></div>` });
      return;
    }
    const m = A.modal({
      title: "To'lov cheki",
      body: `<div class="receipt" id="receipt">
        <div class="r-head"><span class="logo">codial<i>.</i></span><div>IT o'quv markazi · ${esc(A.branchName(p.branch))} filiali<br>Farg'ona sh.</div></div>
        <h3>TO'LOV CHEKI № ${esc(p.id.toUpperCase())}</h3>
        <table>
          <tr><td>Sana</td><td>${A.fdate(p.date)} ${A.fdt(p.created_at).slice(11)}</td></tr>
          <tr><td>Talaba</td><td>${esc(A.studentName(c.student))}</td></tr>
          <tr><td>Shartnoma</td><td>№${c.number} · ${esc(A.groupName(c.group))}</td></tr>
          <tr><td>To'lov shakli</td><td>${p.amount ? A.CASH[p.cash_type] : '—'}</td></tr>
          ${p.discount ? `<tr><td>Chegirma</td><td>${A.money(p.discount)} (${esc((A.get('discountTypes', p.discount_type) || {}).name)})</td></tr>` : ''}
          <tr class="big"><td>Summa</td><td>${A.money(p.amount)}</td></tr>
          <tr><td>To'lovdan keyingi balans</td><td>${A.money(A.debtOf(c.id))}</td></tr>
          <tr><td>Qabul qildi</td><td>${esc(A.userName(p.created_by))}</td></tr>
        </table>
        ${pending ? '<p class="r-warn">TASDIQLANMAGAN</p>' : ''}
        <p class="r-foot">Rahmat! Savollar bo'yicha: +998 73 000 00 00</p>
      </div>`,
      footer: `<button class="btn ghost" data-close>Yopish</button><button class="btn primary" id="r-print">${A.icon('download')}PDF / chop etish</button>`,
    });
    m.el.querySelector('#r-print').onclick = () => {
      document.body.classList.add('printing');
      window.print();
      setTimeout(() => document.body.classList.remove('printing'), 500);
    };
  };
  A.act.receipt = (el) => A.receipt(el.dataset.id);

  /* ===================================================== Tasdiqlashlar */
  A.page('approvals', {
    title: 'Tasdiqlashlar',
    section: 'approvals',
    render(p, q) {
      const P = A.pending();
      const tab = q.tab || 'disc';
      const items = [
        ['disc', 'Chegirmalar', P.discounts.length],
        ['nc', "Naqdsiz to'lovlar", P.noncash.length],
        ['tr', "O'tkazmalar", P.transfers.length],
        ['mk', 'Qoldirilgan darslar', P.makeups.length],
        ['freq', 'Oydagi dars soni', P.freqs.length],
      ];
      let body = '';
      const btn = (act, id, ok, why) => (ok ? `<button class="btn sm primary" data-act="${act}" data-id="${id}">Tasdiqlash</button>` : `<span class="muted small" title="${esc(why)}">${esc(why)}</span>`);
      if (tab === 'disc') {
        body = `<p class="muted">Chegirmani Admin tasdiqlaydi, Bosh menejer — yaratilganidan keyin 30 kun ichida.</p>` + A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Shartnoma', f: (x) => `<a href="#/contracts/${x.contract}">${esc(A.contractName(x.contract))}</a>` },
            { h: 'Chegirma turi', f: (x) => esc((A.get('discountTypes', x.discount_type) || {}).name) },
            { h: 'Summa', f: (x) => `<b>${A.num(x.discount)}</b>`, cls: 'num' },
            { h: 'Izoh', f: (x) => esc(x.comment) },
            { h: 'Kiritdi', f: (x) => esc(A.userName(x.created_by)) },
            { h: '', f: (x) => btn('ok-disc', x.id, A.canApproveDiscount(x), 'Faqat Admin / Bosh menejer (30 kun)') },
          ],
          P.discounts,
          { empty: "Tasdiq kutayotgan chegirma yo'q" },
        );
      } else if (tab === 'nc') {
        body = `<p class="muted">Admin istalgan vaqtda; Bosh menejer 360 kun, Filial menejeri 7 kun ichida tasdiqlaydi. Tasdiqlangach summa g'azna balansiga qo'shiladi.</p>` + A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Shartnoma', f: (x) => `<a href="#/contracts/${x.contract}">${esc(A.contractName(x.contract))}</a>` },
            { h: 'Turi', f: (x) => A.CASH[x.cash_type] },
            { h: 'Summa', f: (x) => `<b>${A.num(x.amount)}</b>`, cls: 'num' },
            { h: "G'azna", f: (x) => esc(A.accName(x.cashbox)) },
            { h: '', f: (x) => btn('ok-nc', x.id, A.canApproveNoncash(x), "Ruxsat yo'q yoki muddat o'tgan") },
          ],
          P.noncash,
          { empty: "Tasdiq kutayotgan naqdsiz to'lov yo'q" },
        );
      } else if (tab === 'tr') {
        body = `<p class="muted">O'tkazmani qabul qiluvchi g'azna mas'uli yoki Admin tasdiqlaydi. Tasdiqlanmaguncha ikkala g'aznada ham hisobga olinmaydi.</p>` + transfersTable(P.transfers);
      } else if (tab === 'mk') {
        body = `<p class="muted">Tasdiqlansa davomat «Besabab»dan «Sababli»ga o'zgaradi va ustozga KPI yoziladi.</p>` + A.makeupTable(P.makeups);
      } else {
        body = `<p class="muted">Har oy 1-kuni tizim kalendar bo'yicha taklif tayyorlaydi. Menejer tekshiradi (bayramlar) va tasdiqlaydi — shundan keyin qarz va KPI hisoblanadi.</p>` + A.freqTable(P.freqs);
      }
      return `${A.head('Tasdiqlashlar', `Sizning tasdiqingiz kerak: <b>${A.pendingCount()}</b> ta`)}${A.tabs(items, tab, 'approvals')}${body}`;
    },
  });
  A.act['ok-disc'] = (el) => {
    const p = A.get('payments', el.dataset.id);
    A.patch('payments', p.id, { disc_status: 'Tasdiqlandi', disc_by: A.S.currentUser, disc_at: Date.now() }, 'Chegirma tasdiqlandi', A.contractName(p.contract));
    A.toast('Chegirma tasdiqlandi');
    A.refresh();
  };
  A.act['ok-nc'] = (el) => {
    const p = A.get('payments', el.dataset.id);
    A.patch('payments', p.id, { nc_status: 'Tasdiqlandi', nc_by: A.S.currentUser, nc_at: Date.now() }, "Naqdsiz to'lov tasdiqlandi", A.contractName(p.contract));
    A.toast(`${A.money(p.amount)} «${A.accName(p.cashbox)}» balansiga qo'shildi`);
    A.refresh();
  };

  /* ===================================================== G'aznalar */
  A.page('accounts', {
    title: "G'aznalar",
    section: 'accounts',
    render() {
      const accs = A.rows('accounts');
      return `${A.head("G'aznalar", "Balans = boshlang'ich qoldiq + barcha tasdiqlangan pul harakatlari (yagona jurnal)", A.can('accounts', 'a') ? A.btn("G'azna qo'shish", 'acc-new', { icon: 'plus' }) : '')}
        <div class="cards">${accs
          .map((a) => {
            const types = a.cash_type === 'ALL' ? ['CASH', 'CARD', 'BANK'] : [...new Set([a.cash_type, ...A.ledger().filter((m) => m.account === a.id).map((m) => m.type)])];
            const pend = A.pendingOf(a.id);
            return `<a class="gcard acc" href="#/accounts/${a.id}">
              <div class="gcard-h"><b>${esc(a.name)}</b>${A.badge(A.CASH[a.cash_type], 'gray')}</div>
              <div class="big-num">${A.money(A.balance(a.id))}</div>
              ${types.map((t) => `<div class="small row between"><span>${A.CASH[t]}</span><span>${A.num(A.balance(a.id, t))}</span></div>`).join('')}
              ${pend ? `<div class="small t-orange">Tasdiqlanmagan: ${A.num(pend)}</div>` : ''}
              <div class="muted small">Mas'ullar: ${a.responsible.map(A.userName).map(esc).join(', ')}</div>
            </a>`;
          })
          .join('')}</div>
        <div class="alert info">${A.icon('alert')}<div>Ochiq savol (15-bo'lim, 5): «Hammasi» (All) turidagi g'aznada balans har bir to'lov turi bo'yicha alohida ko'rsatilsinmi? Prototipda ikkalasi ham ko'rsatilgan.</div></div>`;
    },
  });
  A.page('accounts/:id', {
    title: "G'azna",
    section: 'accounts',
    render({ id }) {
      const a = A.get('accounts', id);
      const m = A.q('led:month', '');
      const rows = A.ledger().filter((x) => x.account === id && (!m || A.ym(x.date) === m));
      return `<a class="back" href="#/accounts">← G'aznalar</a>
        ${A.head(a.name, `${A.CASH[a.cash_type]} · mas'ullar: ${a.responsible.map(A.userName).map(esc).join(', ')}`, A.can('accounts', 'e') ? A.btn('Tahrirlash', 'acc-edit', { id, cls: 'ghost' }) : '')}
        <div class="stats">${A.stat('Joriy balans', A.money(A.balance(id)))}${A.stat("Boshlang'ich qoldiq", A.money(a.initial), 'import sanasi: ' + A.fdate(a.start))}${A.stat('Tasdiqlanmagan', A.money(A.pendingOf(id)), "balansga kirmagan", A.pendingOf(id) ? 'warn' : '')}</div>
        <div class="filters"><select class="f-input" data-filter="led:month"><option value="">Barcha oylar</option>${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === m ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
        ${A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: 'Manba', f: (x) => esc(x.src) },
            { h: 'Tafsilot', f: (x) => esc(x.ref) },
            { h: 'Turi', f: (x) => A.CASH[x.type] },
            { h: 'Summa', f: (x) => `<span class="${x.amount < 0 ? 't-red' : 't-green'}">${x.amount > 0 ? '+' : ''}${A.num(x.amount)}</span>`, cls: 'num', sum: (r) => A.num(A.sum(r.filter((x) => x.confirmed), 'amount')) },
            { h: 'Holat', f: (x) => (x.confirmed ? '' : A.badge('tasdiqlanmagan', 'orange')) },
          ],
          rows,
          { empty: "Harakat yo'q" },
        )}`;
    },
  });
  A.accountForm = (a) =>
    A.form({
      title: a ? a.name : "Yangi g'azna",
      values: a ? { ...a } : { cash_type: 'CASH', responsible: [], status: 'Faol', initial: 0, start: A.today() },
      fields: [
        { name: 'name', label: 'Nomi', required: true, validate: (n) => (A.rows('accounts').some((x) => x.name === n && (!a || x.id !== a.id)) ? "Avval qo'shilgan" : '') },
        { name: 'cash_type', label: 'Pul shakli', type: 'seg', options: [['CASH', 'Naqd'], ['CARD', 'Karta'], ['BANK', 'Bank'], ['ALL', 'Hammasi']] },
        { name: 'responsible', label: "Mas'ul shaxslar", type: 'chips', readonly: () => !A.isTop(), options: () => A.S.users.filter((u) => ['ADMIN', 'BOSH_MENEJER', 'ADMINISTRATOR_HISOBCHI', 'HISOBCHI'].includes(u.role)).map((u) => [u.id, u.full_name]), help: () => (A.isTop() ? '' : "Mas'ullarni faqat Admin va Bosh menejer o'zgartiradi") },
        { name: 'initial', label: "Boshlang'ich balans", type: 'money' },
        { name: 'start', label: 'Boshlanish sana', type: 'date', validate: (d) => (d > A.today() ? 'Faqat bugun yoki avvalgi sanalarni tanlang' : '') },
        { name: 'status', label: 'Status', type: 'seg', options: ['Faol', 'Nofaol'] },
      ],
      onSubmit(x) {
        const rec = { name: x.name, cash_type: x.cash_type, responsible: x.responsible, initial: Number(x.initial) || 0, start: x.start, status: x.status };
        if (a) A.patch('accounts', a.id, rec, "G'azna", a.name); else A.insert('accounts', rec, "G'azna", x.name);
        A.refresh();
      },
    });
  A.act['acc-new'] = () => A.accountForm(null);
  A.act['acc-edit'] = (el) => A.accountForm(A.get('accounts', el.dataset.id));

  /* ===================================================== Ichki pul oqimi */
  const direction = (t) => {
    const me = A.S.currentUser;
    if ((A.get('accounts', t.sender) || {}).responsible.includes(me)) return ['Chiquvchi', 'red'];
    if ((A.get('accounts', t.receiver) || {}).responsible.includes(me)) return ['Kiruvchi', 'green'];
    return ['Boshqa', 'gray'];
  };
  function transfersTable(rows) {
    return A.table(
      [
        { h: 'Sana', f: (t) => A.fdate(t.date) },
        { h: "Yo'nalish", f: (t) => { const [d, c] = direction(t); return A.badge(d, c); } },
        { h: 'Kimdan', f: (t) => `${esc(A.accName(t.sender))}<br><small class="muted">${esc(A.userName(t.sender_cashier))}</small>` },
        { h: 'Kimga', f: (t) => `${esc(A.accName(t.receiver))}<br><small class="muted">${esc(A.userName(t.receiver_cashier))}</small>` },
        { h: 'Summa', f: (t) => `<b>${A.num(t.amount)}</b>`, cls: 'num' },
        { h: 'Holat', f: (t) => A.badge(t.status, t.status === 'Tasdiqlandi' ? 'green' : 'orange') + (t.confirmed_by ? `<br><small class="muted">${esc(A.userName(t.confirmed_by))}</small>` : '') },
        { h: 'Izoh', f: (t) => esc(t.comment) },
        { h: '', f: (t) => (t.status === 'Tasdiqlashga' ? (A.canApproveTransfer(t) ? `<button class="btn sm primary" data-act="ok-tr" data-id="${t.id}">Qabul qildim</button>` : '<span class="muted small">Qabul qiluvchi tasdiqlaydi</span>') : '') },
      ],
      rows,
      { empty: "O'tkazma yo'q" },
    );
  }
  A.page('transfers', {
    title: 'Ichki pul oqimi',
    section: 'transfers',
    render() {
      return `${A.head("Ichki pul oqimi", "G'aznalar orasida naqd pul o'tkazish", A.can('transfers', 'a') ? A.btn("O'tkazma", 'tr-new', { icon: 'plus' }) : '')}${transfersTable(A.sortBy(A.rows('transfers'), (t) => t.date, true))}`;
    },
  });
  A.act['ok-tr'] = (el) => {
    const t = A.get('transfers', el.dataset.id);
    A.patch('transfers', t.id, { status: 'Tasdiqlandi', confirmed_by: A.S.currentUser, confirmed_at: Date.now() }, "O'tkazma tasdiqlandi", `${A.accName(t.sender)} → ${A.accName(t.receiver)}`);
    A.toast("O'tkazma tasdiqlandi — ikkala g'azna balansi yangilandi");
    A.refresh();
  };
  A.act['tr-new'] = () => {
    const top = A.isTop();
    A.form({
      title: "G'aznalar orasida o'tkazma",
      values: { date: A.today(), cash_type: 'CASH' },
      fields: [
        { name: 'sender', label: "Yuboruvchi g'azna", type: 'select', required: true, auto: true, options: () => A.myAccounts().map((a) => [a.id, `${a.name} (naqd: ${A.num(A.balance(a.id, 'CASH'))})`]), resets: ['sender_cashier', 'amount'], onChange: (x) => { if (x.sender) x.amount = A.balance(x.sender, 'CASH'); } },
        { name: 'sender_cashier', label: "Yuboruvchi g'aznachi", type: 'select', auto: true, show: (x) => x.sender, options: (x) => (A.get('accounts', x.sender) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'cash_type', label: 'Pul shakli', type: 'computed', show: (x) => x.sender, compute: () => 'Naqd (o\'tkazma faqat naqd pul uchun)' },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.sender, help: (x) => `G'aznada naqd: ${A.money(A.balance(x.sender, 'CASH'))}`, validate: (n, x) => (n <= 0 ? "0 dan katta bo'lsin" : !top && n > A.balance(x.sender, 'CASH') ? `G'aznada ${A.num(A.balance(x.sender, 'CASH'))} so'm pul bor` : '') },
        { name: 'receiver', label: "Qabul qiluvchi g'azna", type: 'select', required: true, show: (x) => x.amount > 0, options: (x) => A.rows('accounts').filter((a) => a.status === 'Faol' && a.id !== x.sender).map((a) => [a.id, a.name]), resets: ['receiver_cashier'] },
        { name: 'receiver_cashier', label: "Qabul qiluvchi g'aznachi", type: 'select', auto: true, show: (x) => x.receiver, options: (x) => (A.get('accounts', x.receiver) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'date', label: 'Sana', type: 'date', readonly: () => !top, show: (x) => x.receiver, help: () => (top ? '' : "Sanani faqat Admin va Bosh menejer o'zgartiradi") },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.receiver },
      ],
      onSubmit(x) {
        A.insert('transfers', { date: x.date, sender: x.sender, sender_cashier: x.sender_cashier, cash_type: 'CASH', amount: x.amount, receiver: x.receiver, receiver_cashier: x.receiver_cashier, status: 'Tasdiqlashga', confirmed_by: '', comment: x.comment }, "O'tkazma", `${A.accName(x.sender)} → ${A.accName(x.receiver)}`);
        A.toast("Yuborildi. Qabul qiluvchi tasdiqlaguncha balanslar o'zgarmaydi");
        A.refresh();
      },
    });
  };

  /* ===================================================== Pul ayirboshlash */
  A.page('exchange', {
    title: 'Pul ayirboshlash',
    section: 'exchange',
    render() {
      return `${A.head('Pul ayirboshlash', "Masalan kartadagi pulni naqdga aylantirish. Yo'qotish = berilgan − olingan", A.can('exchange', 'a') ? A.btn('Ayirboshlash', 'xc-new', { icon: 'plus' }) : '')}
        ${A.table(
          [
            { h: 'Sana', f: (x) => A.fdate(x.date) },
            { h: "G'azna", f: (x) => esc(A.accName(x.account)) },
            { h: 'Berildi', f: (x) => `${A.num(x.amount)} ${A.CASH[x.from_type]}`, cls: 'num' },
            { h: 'Olindi', f: (x) => `${A.num(x.amount_to)} ${A.CASH[x.to_type]}`, cls: 'num' },
            { h: "Yo'qotish", f: (x) => `<span class="t-red">${A.num(x.amount - x.amount_to)}</span>`, cls: 'num', sum: (r) => A.num(A.sum(r, (x) => x.amount - x.amount_to)) },
            { h: 'Kim', f: (x) => esc(A.userName(x.created_by)) },
          ],
          A.sortBy(A.rows('exchanges'), (x) => x.date, true),
        )}`;
    },
  });
  A.act['xc-new'] = () =>
    A.form({
      title: 'Pul ayirboshlash',
      fields: [
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, options: () => A.myAccounts().map((a) => [a.id, a.name]) },
        { name: 'from_type', label: 'Pul shakli (dan)', type: 'seg', required: true, options: cashOpts, resets: ['to_type'] },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.from_type, onChange: (x) => (x.amount_to = x.amount) },
        { name: 'to_type', label: 'Pul shakli (ga)', type: 'seg', required: true, show: (x) => x.amount, options: (x) => cashOpts.filter(([k]) => k !== x.from_type) },
        { name: 'amount_to', label: 'Olingan summa', type: 'money', required: true, show: (x) => x.to_type, validate: (n, x) => (n > x.amount ? `${A.num(x.amount)} dan katta bo'lolmaydi` : '') },
        { name: 'loss', label: "Yo'qotish", type: 'computed', show: (x) => x.to_type, compute: (x) => A.money((x.amount || 0) - (x.amount_to || 0)) },
      ],
      onSubmit(x) {
        A.insert('exchanges', { account: x.account, date: A.today(), from_type: x.from_type, amount: x.amount, to_type: x.to_type, amount_to: x.amount_to }, 'Ayirboshlash');
        A.refresh();
      },
    });

  /* ===================================================== Xarajatlar */
  A.page('expenses', {
    title: 'Xarajatlar',
    section: 'expenses',
    render(p, q) {
      const tab = q.tab || 'date';
      return `${A.head('Xarajatlar', "G'azna qoldig'idan ko'p xarajat qilib bo'lmaydi (Admin va Bosh menejerdan tashqari)", A.can('expenses', 'a') ? A.btn('Xarajat qo\'shish', 'exp-new', { icon: 'plus' }) : '')}
        ${A.tabs([['date', "Sana bo'yicha"], ['cat', "Oy → kategoriya"]], tab, 'expenses')}
        ${A.filterBar('expenses', [A.fSelect('expenses', 'month', A.monthOptions(), 'Barcha oylar'), A.fSelect('expenses', 'cat', A.optList('expenseCats'), 'Barcha kategoriyalar')])}
        <div data-results>${this.results(p, q)}</div>`;
    },
    results(p, q) {
      const tab = q.tab || 'date';
      const m = A.q('expenses:month', ''), cat = A.q('expenses:cat', '');
      const rows = A.vis('expenses').filter((e) => (!m || `${e.period_year}-${String(e.period_month).padStart(2, '0')}` === m) && (!cat || e.category === cat));
      const total = (e) => e.quantity * e.price;
      if (tab === 'cat') {
        const byM = A.groupBy(A.sortBy(rows, (e) => e.period_year * 100 + e.period_month, true), (e) => `${e.period_year}-${String(e.period_month).padStart(2, '0')}`);
        return [...byM]
          .map(([ym, list]) => `<section class="group-block"><h3>${A.ymLabel(ym)} <span class="muted">· ${A.money(A.sum(list, total))}</span></h3>${A.table(
            [
              { h: 'Kategoriya', f: (r) => esc(r.name) },
              { h: 'Turi', f: (r) => A.badge(r.kind, r.kind === 'Xarajat' ? 'gray' : 'blue') },
              { h: 'Soni', f: (r) => r.n, cls: 'num' },
              { h: 'Summa', f: (r) => `<b>${A.num(r.sum)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, 'sum')) },
            ],
            A.sortBy([...A.groupBy(list, (e) => e.category)].map(([c, l]) => { const ct = A.get('expenseCats', c); return { name: ct.name, kind: ct.kind, n: l.length, sum: A.sum(l, total) }; }), (r) => r.sum, true),
          )}</section>`)
          .join('') || A.empty("Xarajat yo'q");
      }
      return A.table(
        [
          { h: 'Sana', f: (e) => A.fdate(e.date) },
          { h: 'Kategoriya', f: (e) => esc((A.get('expenseCats', e.category) || {}).name) },
          { h: 'Nomi', f: (e) => esc(e.name) },
          { h: 'Soni × narx', f: (e) => `${e.quantity} × ${A.num(e.price)}`, cls: 'num' },
          { h: 'Jami', f: (e) => `<b>${A.num(total(e))}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, total)) },
          { h: "G'azna", f: (e) => `${esc(A.accName(e.account))} · ${A.CASH[e.cash_type]}` },
          { h: 'Hisob davri', f: (e) => `${A.MONTHS[e.period_month - 1]} ${e.period_year}` },
          { h: '', f: (e) => { const ed = A.canEdit('expenses', e); return A.can('expenses', 'e') ? `<button class="btn sm ghost" data-act="exp-edit" data-id="${e.id}" ${ed.ok ? '' : `disabled title="${esc(ed.why)}"`}>✎</button>` : ''; } },
        ],
        A.sortBy(rows, (e) => e.date, true),
        { empty: "Xarajat yo'q" },
      );
    },
  });
  A.expenseForm = (e) => {
    const top = A.isTop();
    const B = A.branchIds()[0];
    A.form({
      title: e ? 'Xarajat' : 'Yangi xarajat',
      values: e ? { ...e } : { date: A.today(), quantity: 1, cash_type: 'CASH', cashier: A.S.currentUser },
      fields: [
        { name: 'date', label: 'Sana', type: 'date', required: true, half: true, validate: (d) => (d > A.today() ? "Kelajak sana bo'lishi mumkin emas" : ''), onChange: (x) => { x.period_year = Number(x.date.slice(0, 4)); x.period_month = Number(x.date.slice(5, 7)); } },
        { name: 'category', label: 'Kategoriya', type: 'select', required: true, half: true, resets: ['name'], options: () => A.rows('expenseCats').filter((c) => c.allowed_roles.includes(A.role())).map((c) => [c.id, `${c.name}${c.kind !== 'Xarajat' ? ' · ' + c.kind : ''}`]), help: "Faqat sizning rolingizga ruxsat berilgan kategoriyalar" },
        { name: 'name', label: 'Nomi', required: true, show: (x) => x.category, suggest: (x) => [...new Set(A.rows('expenses').filter((y) => y.category === x.category).map((y) => y.name))], help: "Shu kategoriyadagi oldingi nomlar taklif qilinadi" },
        { name: 'quantity', label: 'Soni', type: 'number', min: 1, required: true, show: (x) => x.name, half: true, validate: (n) => (n < 1 ? "Kamida 1" : '') },
        { name: 'price', label: 'Narxi', type: 'money', required: true, show: (x) => x.name, half: true },
        { name: 'total', label: 'Jami summa', type: 'computed', show: (x) => x.price, compute: (x) => `<b>${A.money((x.quantity || 0) * (x.price || 0))}</b>` },
        { name: 'cash_type', label: "To'lov shakli", type: 'seg', options: cashOpts, show: (x) => x.price },
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.price, options: () => A.myAccounts().map((a) => [a.id, a.name]), resets: ['cashier'] },
        { name: 'cashier', label: "G'aznachi", type: 'select', auto: true, show: (x) => x.account, options: (x) => (A.get('accounts', x.account) || { responsible: [] }).responsible.map((u) => [u, A.userName(u)]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.account && x.cash_type, text: (x) => `G'aznada ${A.CASH[x.cash_type].toLowerCase()}: <b>${A.money(A.balance(x.account, x.cash_type))}</b>` },
        { name: 'period_year', label: 'Hisob davri: yil', type: 'number', show: (x) => x.price && top, half: true, default: Number(A.today().slice(0, 4)) },
        { name: 'period_month', label: 'Hisob davri: oy', type: 'select', show: (x) => x.price && top, half: true, options: A.MONTHS.map((m, i) => [String(i + 1), m]), default: String(Number(A.today().slice(5, 7))), help: "Faqat Admin va Bosh menejer o'zgartiradi" },
        { name: 'comment', label: "Qo'shimcha izoh", type: 'textarea', show: (x) => x.price },
      ],
      onSubmit(x) {
        const total = x.quantity * x.price;
        const bal = A.balance(x.account, x.cash_type) + (e && e.account === x.account && e.cash_type === x.cash_type ? e.quantity * e.price : 0);
        if (!top && total > bal) return bal <= 0 ? "G'aznada pul yo'q" : `G'aznada ${A.num(bal)} so'm pul bor`;
        const py = top ? Number(x.period_year) : Number(x.date.slice(0, 4));
        const pm = top ? Number(x.period_month) : Number(x.date.slice(5, 7));
        const rec = { branch: B, date: x.date, category: x.category, name: x.name, quantity: x.quantity, price: x.price, cash_type: x.cash_type, account: x.account, cashier: x.cashier, period_year: py, period_month: pm, comment: x.comment };
        if (e) A.patch('expenses', e.id, rec, 'Xarajat', x.name); else A.insert('expenses', rec, 'Xarajat', `${x.name}: ${A.num(total)}`);
        A.refresh();
      },
    });
  };
  A.act['exp-new'] = () => A.expenseForm(null);
  A.act['exp-edit'] = (el) => A.expenseForm(A.get('expenses', el.dataset.id));

  /* ===================================================== Kreditorlar */
  const creditorNow = (c) => c.initial - A.sum(A.rows('creditorTx').filter((t) => t.creditor === c.id), 'amount');
  A.page('creditors', {
    title: 'Tashqi pul oqimi',
    section: 'creditors',
    render() {
      return `${A.head('Tashqi pul oqimi (kreditorlar)', 'Joriy haqqi = boshlang\'ich haqqi − Σ amallar', (A.can('creditors', 'a') ? A.btn('Amal kiritish', 'ctx-new', { icon: 'plus' }) + A.btn('Kreditor', 'cred-new', { cls: 'ghost', icon: 'plus' }) : ''))}
        <div class="cards">${A.rows('creditors')
          .map((c) => `<a class="gcard" href="#/creditors/${c.id}"><div class="gcard-h"><b>${esc(c.name)}</b></div><div class="muted small">Joriy haqqi</div><div class="big-num">${A.money(creditorNow(c))}</div><div class="muted small">Boshlang'ich: ${A.num(c.initial)}</div></a>`)
          .join('')}</div>`;
    },
  });
  A.page('creditors/:id', {
    title: 'Kreditor',
    section: 'creditors',
    render({ id }) {
      const c = A.get('creditors', id);
      const tx = A.sortBy(A.rows('creditorTx').filter((t) => t.creditor === id), (t) => t.date, true);
      const cm = A.sortBy(A.rows('creditorComments').filter((t) => t.creditor === id), (t) => t.created_at, true);
      return `<a class="back" href="#/creditors">← Kreditorlar</a>${A.head(c.name, `Joriy haqqi: <b>${A.money(creditorNow(c))}</b>`, A.btn('Amal kiritish', 'ctx-new', { id, icon: 'plus' }))}
        <h3>Oldi-berdilar</h3>${A.table(
          [
            { h: 'Sana', f: (t) => A.fdate(t.date) },
            { h: 'Summa', f: (t) => `<span class="${t.amount < 0 ? 't-red' : 't-green'}">${t.amount > 0 ? '+' : ''}${A.num(t.amount)}</span>`, cls: 'num' },
            { h: 'Amal', f: (t) => (t.amount < 0 ? 'Qarz olindi' : 'Qarz qaytarildi') },
            { h: "G'azna", f: (t) => `${esc(A.accName(t.account))} · ${A.CASH[t.cash_type]}` },
            { h: 'Izoh', f: (t) => esc(t.comment) },
          ],
          tx,
        )}
        <h3>Izohlar</h3><div class="row gap"><input class="f-input grow" id="cc-text" placeholder="Izoh…"><button class="btn" id="cc-add">Qo'shish</button></div>
        <ul class="comments">${cm.map((x) => `<li><p>${esc(x.comment)}</p><small class="muted">${esc(A.userName(x.created_by))} · ${A.fdt(x.created_at)}</small></li>`).join('')}</ul>`;
    },
    mount({ id }) {
      document.getElementById('cc-add').onclick = () => {
        const t = document.getElementById('cc-text').value.trim();
        if (!t) return;
        A.insert('creditorComments', { creditor: id, comment: t }, 'Kreditor izohi');
        A.refresh();
      };
    },
  });
  A.act['cred-new'] = () =>
    A.form({
      title: 'Yangi kreditor',
      fields: [
        { name: 'name', label: 'Nomi', required: true, validate: (n) => (A.rows('creditors').some((c) => c.name === n) ? "Avval qo'shilgan nom" : '') },
        { name: 'initial', label: "Boshlang'ich haqqi", type: 'money', help: "Yaratilgandan keyin faqat Admin o'zgartiradi" },
      ],
      onSubmit(x) { A.insert('creditors', { name: x.name, initial: Number(x.initial) || 0 }, 'Kreditor', x.name); A.refresh(); },
    });
  A.act['ctx-new'] = (el) =>
    A.form({
      title: 'Kreditor amali',
      values: { creditor: el.dataset.id || '', date: A.today(), cash_type: 'CASH', cashier: A.S.currentUser },
      fields: [
        { name: 'creditor', label: 'Qarz beruvchi', type: 'select', required: true, options: () => A.optList('creditors') },
        { name: 'warn', type: 'note', tone: 'warn', show: (x) => x.creditor, text: '<b>Diqqat:</b> «−» belgisi — <b>qarz olish</b> (g\'aznaga pul kiradi), «+» belgisi — <b>qarz qaytarish</b> (g\'aznadan pul chiqadi).' },
        { name: 'amount', label: 'Summa (− olish / + qaytarish)', type: 'number', required: true, show: (x) => x.creditor, help: (x) => (x.amount < 0 ? `Qarz olinyapti: g'aznaga +${A.num(-x.amount)}` : x.amount > 0 ? `Qarz qaytarilyapti: g'aznadan −${A.num(x.amount)}` : '') },
        { name: 'cash_type', label: 'Pul shakli', type: 'seg', options: cashOpts, show: (x) => x.amount },
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.amount, options: () => A.myAccounts().map((a) => [a.id, a.name]) },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.amount, validate: (d) => (d > A.today() ? "Kelajak sana bilan kiritib bo'lmaydi" : A.diffDays(d, A.today()) > 7 ? 'Bir hafta avvalgi sanagacha kiritish mumkin, xolos' : ''), help: "Taxmin: oxirgi 7 kun (AppSheet formulasi buzilgan — 15-bo'lim, 2-savol)" },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.amount },
      ],
      onSubmit(x) {
        A.insert('creditorTx', { date: x.date, creditor: x.creditor, amount: Number(x.amount), cash_type: x.cash_type, account: x.account, cashier: A.S.currentUser, comment: x.comment }, 'Kreditor amali', (A.get('creditors', x.creditor) || {}).name);
        A.refresh();
      },
    });

  /* ===================================================== Foyda */
  A.page('profit', {
    title: 'Foyda (oyma-oy)',
    section: 'profit',
    render() {
      const all = A.monthOptions().map(([k]) => k).reverse();
      let sel = A.ui.q['profit:months'] || all;
      sel = sel.filter((m) => all.includes(m));
      const pays = A.rows('payments');
      const exps = A.rows('expenses');
      const per = (ym) => {
        const y = Number(ym.slice(0, 4)), m = Number(ym.slice(5, 7));
        const e = exps.filter((x) => x.period_year === y && x.period_month === m);
        const byKind = (k) => A.sum(e.filter((x) => (A.get('expenseCats', x.category) || {}).kind === k), (x) => x.quantity * x.price);
        const p = A.sum(pays.filter((x) => A.ym(x.date) === ym), 'amount');
        const sal = A.sum(A.rows('salaryAssign').filter((s) => s.year === y && s.month === m), (s) => A.salaryBase(s).total);
        const exp = byKind('Xarajat');
        return { ym, p, exp, sal, profit: p - exp - sal, reinv: byKind('Qayta investitsiya'), div: byKind('Dividend'), debt: byKind('Tashqi qarz') };
      };
      const rows = sel.map(per);
      const tot = (k) => A.sum(rows, k);
      const cls = (n) => (n > 0 ? 't-green' : n < 0 ? 't-red' : '');
      return `${A.head('Foyda (oyma-oy)', "Foyda = to'lovlar − xarajatlar (faqat «Xarajat» turi) − hisoblangan oyliklar")}
        <div class="filters"><span class="muted">Oylar:</span><div class="chips">${all.map((m) => `<button class="chip ${sel.includes(m) ? 'on' : ''}" data-act="profit-month" data-id="${m}">${A.ymLabel(m)}</button>`).join('')}</div></div>
        <div class="stats">${A.stat("To'lovlar", `<span class="t-blue">${A.money(tot('p'))}</span>`)}${A.stat('Xarajatlar', `<span class="t-pink">${A.money(tot('exp'))}</span>`)}${A.stat('Hisoblangan oyliklar', A.money(tot('sal')))}${A.stat("Ko'rilgan foyda", `<span class="${cls(tot('profit'))}">${A.money(tot('profit'))}</span>`)}</div>
        <section class="card">${A.table(
          [
            { h: 'Oy', f: (r) => `<b>${A.ymLabel(r.ym)}</b>` },
            { h: "To'lovlar", f: (r) => `<span class="t-blue">${A.num(r.p)}</span>`, cls: 'num', sum: () => A.num(tot('p')) },
            { h: 'Xarajatlar', f: (r) => `<span class="t-pink">${A.num(r.exp)}</span>`, cls: 'num', sum: () => A.num(tot('exp')) },
            { h: 'Oyliklar', f: (r) => A.num(r.sal), cls: 'num', sum: () => A.num(tot('sal')) },
            { h: 'Foyda', f: (r) => `<b class="${cls(r.profit)}">${A.num(r.profit)}</b>`, cls: 'num', sum: () => `<span class="${cls(tot('profit'))}">${A.num(tot('profit'))}</span>` },
            { h: 'Qayta investitsiya', f: (r) => A.num(r.reinv), cls: 'num muted', sum: () => A.num(tot('reinv')) },
            { h: 'Dividend', f: (r) => A.num(r.div), cls: 'num muted', sum: () => A.num(tot('div')) },
            { h: 'Tashqi qarz', f: (r) => A.num(r.debt), cls: 'num muted', sum: () => A.num(tot('debt')) },
          ],
          rows,
        )}<p class="muted small">Qayta investitsiya, dividend va tashqi qarz foydaga kirmaydi — alohida ko'rsatiladi (AppSheet'dagi qattiq yozilgan «10f01992» kategoriyasi o'rniga kategoriya turi ishlatiladi).</p></section>
        <section class="card">${A.chart({ type: 'bar', data: { labels: rows.map((r) => A.ymLabel(r.ym)), datasets: [{ label: "To'lovlar", data: rows.map((r) => r.p), backgroundColor: '#2f80ed' }, { label: 'Xarajatlar', data: rows.map((r) => r.exp), backgroundColor: '#e86fa6' }, { label: 'Oyliklar', data: rows.map((r) => r.sal), backgroundColor: '#9b9ba3' }, { label: 'Foyda', data: rows.map((r) => r.profit), backgroundColor: A.PALETTE[3], type: 'line' }] } })}</section>`;
    },
  });
  A.act['profit-month'] = (el) => {
    const all = A.monthOptions().map(([k]) => k);
    let sel = A.ui.q['profit:months'] || all;
    sel = sel.includes(el.dataset.id) ? sel.filter((m) => m !== el.dataset.id) : [...sel, el.dataset.id];
    A.ui.q['profit:months'] = sel.sort();
    A.refresh();
  };

  /* ===================================================== Oyliklar */
  A.page('salaries', {
    title: 'Oyliklar',
    section: 'salaries',
    render(p, q) {
      const mgr = A.isManager();
      const tab = q.tab || (mgr ? 'assign' : 'kpi');
      const tabs = mgr || A.can('salaries', 'a')
        ? [['assign', 'Oylik belgilash'], ['kpi', 'Hisoblangan KPI'], ['rates', 'KPI stavkalari'], ['payout', 'Oylik berish'], ['balance', 'Xodim balansi']]
        : [['kpi', 'Mening KPI'], ['assign', 'Mening oyligim'], ['payout', 'Olganlarim']];
      const ym = A.q('sal:month', A.ym(A.today()));
      const monthSel = `<div class="filters"><select class="f-input" data-filter="sal:month">${A.monthOptions().map(([k, l]) => `<option value="${k}" ${k === ym ? 'selected' : ''}>${l}</option>`).join('')}</select></div>`;
      let body = '';
      if (tab === 'assign') body = monthSel + assignView(ym);
      else if (tab === 'kpi') body = kpiView();
      else if (tab === 'rates') body = ratesView();
      else if (tab === 'payout') body = payoutView();
      else body = balanceView();
      return `${A.head('Oyliklar', 'Jami = belgilangan + bonus + KPI (qo\'lda) + ustoz KPI + yordamchi KPI − jarima')}${A.tabs(tabs, tab, 'salaries')}${body}`;
    },
  });

  function assignView(ym) {
    const y = Number(ym.slice(0, 4)), m = Number(ym.slice(5, 7));
    const rows = A.vis('salaryAssign').filter((s) => s.year === y && s.month === m);
    const canA = A.can('salaries', 'a') && A.isManager();
    return `${canA ? `<div class="row gap">${A.btn('Oylik belgilash', 'sa-new', { icon: 'plus' })}${A.btn("O'tgan oydan nusxa", 'sa-copy', { cls: 'ghost', id: ym })}</div>` : ''}
      ${A.table(
        [
          { h: 'Xodim', f: (s) => `<b>${esc(A.userName(s.user))}</b><br><small class="muted">${esc(A.ROLES[(A.get('users', s.user) || {}).role])}</small>` },
          { h: 'Belgilangan', f: (s) => A.num(s.fixed), cls: 'num' },
          { h: 'Bonus', f: (s) => A.num(s.bonus), cls: 'num' },
          { h: 'KPI (qo\'lda)', f: (s) => A.num(s.kpi), cls: 'num' },
          { h: 'Ustoz KPI', f: (s) => A.num(A.salaryCalc(s).tkpi), cls: 'num' },
          { h: 'Yordamchi KPI', f: (s) => A.num(A.salaryCalc(s).skpi), cls: 'num' },
          { h: 'Jarima', f: (s) => (s.fine ? `<span class="t-red">−${A.num(s.fine)}</span>` : '0'), cls: 'num' },
          { h: 'Jami', f: (s) => `<b>${A.num(A.salaryCalc(s).total)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (s) => A.salaryCalc(s).total)) },
          { h: 'Berildi', f: (s) => A.num(A.salaryCalc(s).given), cls: 'num', sum: (r) => A.num(A.sum(r, (s) => A.salaryCalc(s).given)) },
          { h: 'Avvalgi oydan', f: (s) => A.num(A.salaryCalc(s).carried), cls: 'num' },
          { h: 'Yakuniy balans', f: (s) => `<b class="${A.salaryCalc(s).final > 0 ? 't-orange' : ''}">${A.num(A.salaryCalc(s).final)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, (s) => A.salaryCalc(s).final)) },
          { h: '', f: (s) => (canA ? `<button class="btn sm ghost" data-act="sa-edit" data-id="${s.id}">✎</button>` : '') },
        ],
        A.sortBy(rows, (s) => A.userName(s.user)),
        { empty: "Bu oy uchun oylik belgilanmagan" },
      )}
      <p class="muted small">«Avvalgi oydan» — barcha oldingi oylardagi (jami − berilgan) yig'indisi, yillar oralig'ida ham. Jarima jamidan ayiriladi (AppSheet'da ayirilmagan edi).</p>`;
  }
  A.salaryForm = (s, ym) => {
    const B = A.branchIds()[0];
    const [y0, m0] = (ym || A.ym(A.today())).split('-').map(Number);
    A.form({
      title: s ? `Oylik: ${A.userName(s.user)}` : 'Oylik belgilash',
      values: s ? { ...s, month: String(s.month) } : { year: y0, month: String(m0), fixed: 0, bonus: 0, kpi: 0, fine: 0 },
      fields: [
        { name: 'user', label: 'Xodim', type: 'select', required: true, readonly: () => !!s, options: () => A.S.users.filter((u) => u.role !== 'ADMIN' && u.status === 'Faol').map((u) => [u.id, `${u.full_name} · ${A.ROLES[u.role]}`]) },
        { name: 'year', label: 'Yil', type: 'number', required: true, half: true, show: (x) => x.user },
        { name: 'month', label: 'Oy', type: 'select', required: true, half: true, show: (x) => x.user, options: A.MONTHS.map((m, i) => [String(i + 1), m]), validate: (m, x) => (!s && A.rows('salaryAssign').some((z) => z.branch === B && z.user === x.user && z.year === Number(x.year) && z.month === Number(m)) ? 'Bu xodimga shu oy uchun oylik belgilangan' : '') },
        { name: 'fixed', label: 'Belgilangan oylik', type: 'money', half: true, show: (x) => x.month },
        { name: 'bonus', label: 'Bonus', type: 'money', half: true, show: (x) => x.month },
        { name: 'kpi', label: "KPI (qo'lda)", type: 'money', half: true, show: (x) => x.month },
        { name: 'fine', label: 'Jarima', type: 'money', half: true, show: (x) => x.month },
        { name: 'auto', label: 'Avtomatik (davomatdan)', type: 'computed', show: (x) => x.month && x.user, compute: (x) => { const b = A.salaryBase({ branch: B, user: x.user, year: Number(x.year), month: Number(x.month), fixed: x.fixed, bonus: x.bonus, kpi: x.kpi, fine: x.fine }); return `Ustoz KPI: <b>${A.num(b.tkpi)}</b> · Yordamchi KPI: <b>${A.num(b.skpi)}</b><br>Jami: <b>${A.money(b.total)}</b>`; } },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.month },
      ],
      onSubmit(x) {
        const rec = { branch: B, user: x.user, year: Number(x.year), month: Number(x.month), fixed: +x.fixed || 0, bonus: +x.bonus || 0, kpi: +x.kpi || 0, fine: +x.fine || 0, comment: x.comment };
        if (s) A.patch('salaryAssign', s.id, rec, 'Oylik belgilash', A.userName(s.user)); else A.insert('salaryAssign', rec, 'Oylik belgilash', A.userName(x.user));
        A.refresh();
      },
    });
  };
  A.act['sa-new'] = () => A.salaryForm(null, A.q('sal:month', A.ym(A.today())));
  A.act['sa-edit'] = (el) => A.salaryForm(A.get('salaryAssign', el.dataset.id));
  A.act['sa-copy'] = (el) => {
    const ym = el.dataset.id;
    const prev = A.addMonths(ym, -1);
    const [y, m] = ym.split('-').map(Number), [py, pm] = prev.split('-').map(Number);
    let n = 0;
    for (const s of A.rows('salaryAssign').filter((s) => s.year === py && s.month === pm)) {
      if (A.rows('salaryAssign').some((z) => z.user === s.user && z.branch === s.branch && z.year === y && z.month === m)) continue;
      A.S.salaryAssign.push({ id: 'sa' + A.uid(), branch: s.branch, user: s.user, year: y, month: m, fixed: s.fixed, bonus: 0, kpi: 0, fine: 0, comment: '', created_by: A.S.currentUser, created_at: Date.now() });
      n++;
    }
    A.log('create', 'Oylik belgilash', `${A.ymLabel(prev)} → ${A.ymLabel(ym)} nusxa: ${n} ta`);
    A.save();
    A.toast(n ? `${n} ta xodimga oylik nusxalandi` : "Nusxalanadigan yangi yozuv yo'q");
    A.refresh();
  };

  /* Hisoblangan KPI: chapda daraxt (yil → oy → xodim → guruh, KPI summasi bilan), o'ngda jadval */
  const KPI_LEVELS = [
    { key: (e) => e.a.branch, label: (k) => A.branchName(k), hideSingle: true },
    { key: (e) => e.ym.slice(0, 4), label: (k) => k, desc: true },
    { key: (e) => e.ym, label: (k) => A.ymLabel(k).split(' ')[0], sort: (k) => k, desc: true },
    { key: (e) => e.user, label: (k) => A.userName(k) },
    {
      key: (e) => `${e.a.group}:${e.role}`,
      label: (k) => { const [g, r] = k.split(':'); return A.groupName(g) + (r === 'YORDAMCHI' ? ' · yordamchi' : ''); },
      sort: (k) => (A.get('groups', k.split(':')[0]) || {}).number || 0,
    },
  ];
  function kpiView() {
    const me = A.S.currentUser, mine = A.isTeacherRole();
    // Har bir davomat qatoridan ustoz KPI va yordamchi KPI alohida yozuv bo'ladi
    const entries = [];
    for (const a of A.vis('attendance')) {
      const ym = A.ym(a.date);
      if (a.teacher && (!mine || a.teacher === me)) entries.push({ a, ym, user: a.teacher, role: 'USTOZ', kpi: a.tkpi || 0 });
      if (a.supporter && (!mine || a.supporter === me)) entries.push({ a, ym, user: a.supporter, role: 'YORDAMCHI', kpi: a.skpi || 0 });
    }
    const latest = A.sortBy(entries, (e) => e.ym, true)[0];
    // Standart: oxirgi oy ochiq turadi
    const opts = { levels: KPI_LEVELS, value: (l) => A.num(A.sum(l, 'kpi')), def: latest ? `${latest.a.branch}|${latest.ym.slice(0, 4)}|${latest.ym}` : '' };
    const sel = A.treeFilter('kpi', entries, opts);
    const leaf = A.treeDepth('kpi', opts) === KPI_LEVELS.length;
    // Jadval: oy + xodim + rol + guruh bo'yicha yig'indi
    const rows = [...A.groupBy(sel, (e) => `${e.ym}|${e.user}|${e.role}|${e.a.group}`)].map(([, l]) => {
      const e = l[0], grp = A.get('groups', e.a.group);
      return { ym: e.ym, user: e.user, role: e.role, group: e.a.group, n: l.length, paid: l.filter((x) => x.kpi > 0).length, sum: A.sum(l, 'kpi'), rate: A.rateFor(grp.branch, e.user, e.role, grp.course, e.ym), pending: l.filter((x) => x.a.no_freq).length };
    });
    const manyMonths = new Set(rows.map((r) => r.ym)).size > 1;
    const table = A.table(
      [
        ...(manyMonths ? [{ h: 'Oy', f: (r) => A.ymLabel(r.ym) }] : []),
        { h: 'Xodim', f: (r) => `<b>${esc(A.userName(r.user))}</b>` },
        { h: 'Rol', f: (r) => A.badge(r.role === 'USTOZ' ? 'Ustoz' : 'Yordamchi', r.role === 'USTOZ' ? 'blue' : 'gray') },
        { h: 'Guruh', f: (r) => esc(A.groupName(r.group)) },
        { h: 'Stavka', f: (r) => (r.rate ? (r.rate.type === 'Foiz' ? `${r.rate.percent}% narxdan` : `${A.num(r.rate.fixed)} / talaba / oy`) : '<span class="t-red">belgilanmagan</span>') },
        { h: 'Dars qatorlari', f: (r) => `${r.n} <small class="muted">(KPI: ${r.paid})</small>`, cls: 'num' },
        { h: 'KPI', f: (r) => `<b>${A.num(r.sum)}</b>${r.pending ? ` ${A.badge(r.pending + ' ta kutilmoqda', 'orange')}` : ''}`, cls: 'num', sum: (rr) => A.num(A.sum(rr, 'sum')) },
      ],
      A.sortBy(A.sortBy(rows, (r) => `${A.userName(r.user)}|${r.role}|${A.groupName(r.group)}`), (r) => r.ym, true),
      { empty: "KPI yo'q" },
    );
    // Guruh tanlansa, AppSheet'dagidek har bir davomat qatori ham chiqadi
    const detail = leaf
      ? `<h3>Davomat qatorlari</h3>${A.table(
          [
            { h: 'Sana', f: (e) => A.fdate(e.a.date) },
            { h: 'Shartnoma', f: (e) => `<a href="#/contracts/${e.a.contract}">${esc(A.contractName(e.a.contract))}</a>` },
            { h: 'Status', f: (e) => A.attBadge(e.a.status) },
            { h: 'KPI', f: (e) => (e.a.no_freq ? A.badge('kutilmoqda', 'orange') : A.num(e.kpi)), cls: 'num', sum: (rr) => A.num(A.sum(rr, 'kpi')) },
          ],
          A.sortBy(sel, (e) => e.a.date, true),
        )}`
      : '';
    return `<div class="settings tree-layout">${A.treeNav('kpi', entries, opts)}<div class="settings-body">${table}${detail}
    <p class="muted small">KPI har bir davomat qatori uchun: O'zgarmas — stavka ÷ oydagi dars soni; Foiz — foiz × kurs narxi ÷ oydagi dars soni. Besabab (X), Nofaol (–) va Grant shartnomalar uchun KPI yozilmaydi. «Kutilmoqda» — oydagi dars soni hali tasdiqlanmagan.</p></div></div>`;
  }

  function ratesView() {
    const rows = A.sortBy(A.vis('kpiRates'), (k) => A.userName(k.user) + k.effective_from);
    const canE = A.can('salaries', 'e');
    return `${canE ? `<div class="row gap">${A.btn('Stavka qo\'shish', 'rate-new', { icon: 'plus' })}${A.btn("O'tgan oy stavkalarini nusxalash", 'rate-copy', { cls: 'ghost' })}</div>` : ''}
      <p class="muted small">Stavka «amal qilish sanasi» bilan saqlanadi: oy uchun shu oyda amalda bo'lgan oxirgi yozuv olinadi. Stavka faqat o'zgarganda yangi yozuv qo'shiladi.</p>
      ${A.table(
        [
          { h: 'Xodim', f: (k) => esc(A.userName(k.user)) },
          { h: 'Rol', f: (k) => (k.role_type === 'USTOZ' ? 'Ustoz' : 'Yordamchi') },
          { h: 'Kurs', f: (k) => esc(A.courseName(k.course)) },
          { h: 'Amal qiladi', f: (k) => A.ymLabel(k.effective_from) + ' dan' },
          { h: 'Kelishuv', f: (k) => (k.type === 'Foiz' ? `Foiz: <b>${k.percent}%</b>` : `O'zgarmas: <b>${A.num(k.fixed)}</b>`) },
          { h: 'Holat', f: (k) => { const cur = A.rateFor(k.branch, k.user, k.role_type, k.course, A.ym(A.today())); return cur && cur.id === k.id ? A.badge('amalda', 'green') : k.effective_from > A.ym(A.today()) ? A.badge('kelajakda', 'blue') : A.badge('tarix', 'gray'); } },
        ],
        rows,
      )}`;
  }
  A.act['rate-new'] = () => {
    const B = A.branchIds()[0];
    A.form({
      title: 'KPI stavkasi',
      values: { role_type: 'USTOZ', effective_from: A.ym(A.today()), type: 'Foiz' },
      fields: [
        { name: 'role_type', label: 'Kim uchun', type: 'seg', options: [['USTOZ', 'Ustoz'], ['YORDAMCHI', 'Yordamchi']], resets: ['user'] },
        { name: 'user', label: 'Xodim', type: 'select', required: true, options: (x) => A.S.users.filter((u) => (x.role_type === 'USTOZ' ? ['USTOZ', 'USTOZ_YORDAMCHI'] : ['YORDAMCHI', 'USTOZ_YORDAMCHI']).includes(u.role)).map((u) => [u.id, u.full_name]) },
        { name: 'course', label: 'Kurs', type: 'select', required: true, show: (x) => x.user, options: () => A.optList('courses') },
        { name: 'effective_from', label: 'Amal qilish oyi', type: 'month', required: true, show: (x) => x.course },
        { name: 'type', label: 'Kelishuv turi', type: 'seg', options: ["O'zgarmas", 'Foiz'], show: (x) => x.course },
        { name: 'fixed', label: "O'zgarmas summa (1 talaba uchun oyiga)", type: 'money', required: (x) => x.type === "O'zgarmas", show: (x) => x.type === "O'zgarmas" },
        { name: 'percent', label: 'Foiz (0-100)', type: 'number', min: 0, max: 100, required: (x) => x.type === 'Foiz', show: (x) => x.type === 'Foiz', validate: (n) => (n < 0 || n > 100 ? '0-100 oralig\'ida' : '') },
      ],
      onSubmit(x) {
        if (A.rows('kpiRates').some((k) => k.user === x.user && k.role_type === x.role_type && k.course === x.course && k.effective_from === x.effective_from)) return 'Shu oy uchun bu stavka mavjud';
        A.insert('kpiRates', { branch: B, user: x.user, role_type: x.role_type, course: x.course, effective_from: x.effective_from, type: x.type, fixed: +x.fixed || 0, percent: +x.percent || 0 }, 'KPI stavkasi', A.userName(x.user));
        const n = A.recalc((a) => A.ym(a.date) >= x.effective_from && a.course === x.course && (a.teacher === x.user || a.supporter === x.user));
        A.save();
        A.toast(`Saqlandi. ${n} ta davomat qatori qayta hisoblandi`);
        A.refresh();
      },
    });
  };
  A.act['rate-copy'] = () => A.toast("«Amal qilish sanasi» mantiqida o'tgan oy stavkalari yangi oyda ham avtomatik amal qiladi — nusxalash shart emas. Tugma o'zgarish kiritish uchun shablon sifatida qoldirilgan.", 'warn');

  function payoutView() {
    const rows = A.sortBy(A.vis('salaryPayouts'), (s) => s.date, true);
    return `${A.can('salaries', 'a') ? `<div class="row gap">${A.btn('Oylik berish', 'sp-new', { icon: 'plus' })}</div>` : ''}${A.table(
      [
        { h: 'Sana', f: (s) => A.fdate(s.date) },
        { h: 'Xodim', f: (s) => esc(A.userName(s.user)) },
        { h: 'Davr', f: (s) => `${A.MONTHS[s.month - 1]} ${s.year}` },
        { h: 'Turi', f: (s) => esc(s.type) },
        { h: 'Summa', f: (s) => `<b>${A.num(s.amount)}</b>`, cls: 'num', sum: (r) => A.num(A.sum(r, 'amount')) },
        { h: "G'azna", f: (s) => `${esc(A.accName(s.account))} · ${A.CASH[s.cash_type]}` },
        { h: 'Berdi', f: (s) => esc(A.userName(s.cashier)) },
      ],
      rows,
      { empty: "Yozuv yo'q" },
    )}`;
  }
  A.act['sp-new'] = () => {
    const top = A.isTop();
    const B = A.branchIds()[0];
    const [y0, m0] = A.ym(A.addMonths(A.ym(A.today()), -1)).split('-').map(Number);
    A.form({
      title: 'Oylik berish',
      values: { year: y0, month: String(m0), date: A.today(), type: "O'zgarmas", cash_type: 'CASH', cashier: A.S.currentUser },
      fields: [
        { name: 'user', label: 'Xodim', type: 'select', required: true, options: () => A.S.users.filter((u) => u.role !== 'ADMIN').map((u) => [u.id, u.full_name]) },
        { name: 'year', label: 'Yil', type: 'number', half: true, show: (x) => x.user },
        { name: 'month', label: 'Oy', type: 'select', half: true, show: (x) => x.user, options: A.MONTHS.map((m, i) => [String(i + 1), m]) },
        { name: 'bal', type: 'note', tone: 'info', show: (x) => x.user && x.month, text: (x) => { const s = A.rows('salaryAssign').find((z) => z.user === x.user && z.year === Number(x.year) && z.month === Number(x.month)); if (!s) return "Bu oy uchun oylik belgilanmagan"; const c = A.salaryCalc(s); return `Jami: ${A.num(c.total)} · berilgan: ${A.num(c.given)} · <b>qoldiq: ${A.money(c.final)}</b>`; } },
        { name: 'type', label: 'Oylik turi', type: 'seg', options: ["O'zgarmas", 'Bonus', 'KPI'], show: (x) => x.user },
        { name: 'cash_type', label: "To'lov turi", type: 'seg', options: cashOpts, show: (x) => x.user },
        { name: 'account', label: "G'azna", type: 'select', required: true, auto: true, show: (x) => x.user, options: () => A.myAccounts().map((a) => [a.id, a.name]) },
        { name: 'amount', label: 'Summa', type: 'money', required: true, show: (x) => x.account, help: (x) => `G'aznada: ${A.money(A.balance(x.account, x.cash_type))}`, validate: (n, x) => (!top && n > A.balance(x.account, x.cash_type) ? `G'aznada ${A.num(A.balance(x.account, x.cash_type))} so'm pul bor` : '') },
        { name: 'date', label: 'Sana', type: 'date', show: (x) => x.account, readonly: () => !top },
        { name: 'comment', label: 'Izoh', type: 'textarea', show: (x) => x.account },
      ],
      onSubmit(x) {
        A.insert('salaryPayouts', { branch: B, user: x.user, year: Number(x.year), month: Number(x.month), date: x.date, type: x.type, amount: x.amount, cash_type: x.cash_type, account: x.account, cashier: A.S.currentUser, comment: x.comment }, 'Oylik berish', `${A.userName(x.user)}: ${A.num(x.amount)}`);
        A.refresh();
      },
    });
  };

  function balanceView() {
    const users = A.S.users.filter((u) => u.role !== 'ADMIN');
    const rows = users.map((u) => {
      const list = A.sortBy(A.vis('salaryAssign').filter((s) => s.user === u.id), (s) => s.year * 100 + s.month, true);
      const last = list[0];
      return { u, last, calc: last ? A.salaryCalc(last) : null };
    }).filter((r) => r.last);
    return `${A.table(
      [
        { h: 'Xodim', f: (r) => `<b>${esc(r.u.full_name)}</b><br><small class="muted">${esc(A.ROLES[r.u.role])}</small>` },
        { h: 'Oxirgi davr', f: (r) => `${A.MONTHS[r.last.month - 1]} ${r.last.year}` },
        { h: 'Avvalgi oylardan', f: (r) => A.num(r.calc.carried), cls: 'num' },
        { h: 'Shu oy jami', f: (r) => A.num(r.calc.total), cls: 'num' },
        { h: 'Berilgan', f: (r) => A.num(r.calc.given), cls: 'num' },
        { h: 'Yakuniy balans', f: (r) => `<b class="${r.calc.final > 0 ? 't-orange' : ''}">${A.num(r.calc.final)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, (r) => r.calc.final)) },
        { h: '', f: () => '<span class="muted">›</span>' },
      ],
      rows,
      { rowAttr: (r) => `class="row-link" data-act="bal-open" data-id="${r.last.id}" title="Batafsil ko'rish"` },
    )}
    <p class="muted small">Qatorni bosing — xodimning oylar bo'yicha hisob-kitobi va olgan pullari ochiladi.</p>`;
  }

  /* Xodim balansi: tanlangan oy bo'yicha batafsil hisob-kitob (qoldiq, belgilangan oylik, KPI, berilgan pullar, yakuniy balans) */
  const balWord = (n) => (n > 0 ? 'xodim haqdor (markaz berishi kerak)' : n < 0 ? "xodim qarzdor (ortiqcha olgan)" : 'hisob teng');
  const balCls = (n) => (n > 0 ? 't-orange' : n < 0 ? 't-red' : 't-green');
  A.act['bal-open'] = (el) => {
    const sa = A.get('salaryAssign', el.dataset.id);
    const u = A.get('users', sa.user);
    const c = A.salaryCalc(sa);
    const history = A.sortBy(A.rows('salaryAssign').filter((x) => x.user === sa.user && x.branch === sa.branch), (x) => x.year * 100 + x.month, true);
    const payouts = A.sortBy(A.rows('salaryPayouts').filter((p) => p.branch === sa.branch && p.user === sa.user && p.year === sa.year && p.month === sa.month), (p) => p.date);
    const period = `${A.MONTHS[sa.month - 1]} ${sa.year}`;
    const line = (label, v, opts = {}) => `<tr><td>${label}</td><td class="num ${opts.cls || ''}">${opts.minus && v ? '− ' : ''}${A.num(v)}</td></tr>`;
    const body = `
      <div class="detail-top"><span class="muted">${esc(A.ROLES[u.role])} · ${esc(A.branchName(sa.branch))}</span></div>
      ${history.length > 1 ? `<div class="filters">${history.map((h) => `<button class="btn sm ${h.id === sa.id ? 'primary' : 'ghost'}" data-act="bal-open" data-id="${h.id}">${A.MONTHS[h.month - 1]} ${h.year}</button>`).join('')}</div>` : ''}
      <div class="stats">
        ${A.stat('Avvalgi oylardan', `<span class="${balCls(c.carried)}">${A.num(c.carried)}</span>`, balWord(c.carried))}
        ${A.stat(`${period} hisoblangan`, A.num(c.total), 'oylik + bonus + KPI − jarima')}
        ${A.stat('Shu oy berilgan', A.num(c.given), `${payouts.length} ta to'lov`)}
        ${A.stat('Yakuniy balans', `<span class="${balCls(c.final)}">${A.num(c.final)}</span>`, balWord(c.final), c.final > 0 ? 'warn' : c.final < 0 ? 'danger' : '')}
      </div>
      <h3>${period}: hisoblangan oylik</h3>
      <div class="tbl-wrap"><table class="tbl"><tbody>
        ${line('Belgilangan oylik (o\'zgarmas)', sa.fixed || 0)}
        ${line('Bonus', sa.bonus || 0)}
        ${line('KPI (qo\'lda kiritilgan)', sa.kpi || 0)}
        ${line(`Ustoz KPI <small class="muted">(davomatdan)</small>`, c.tkpi)}
        ${line(`Yordamchi KPI <small class="muted">(davomatdan)</small>`, c.skpi)}
        ${line('Jarima', sa.fine || 0, { minus: true, cls: sa.fine ? 't-red' : '' })}
      </tbody><tfoot><tr><td><b>Jami hisoblangan</b></td><td class="num"><b>${A.num(c.total)}</b></td></tr></tfoot></table></div>
      ${sa.comment ? `<p class="muted small">Izoh: ${esc(sa.comment)}</p>` : ''}
      <h3>${period} uchun berilgan pullar</h3>
      ${A.table(
        [
          { h: 'Sana', f: (p) => A.fdate(p.date) },
          { h: 'Turi', f: (p) => esc(p.type) },
          { h: 'Summa', f: (p) => `<b>${A.num(p.amount)}</b>`, cls: 'num', sum: (rr) => A.num(A.sum(rr, 'amount')) },
          { h: "G'azna", f: (p) => `${esc(A.accName(p.account))} · ${A.CASH[p.cash_type]}` },
          { h: 'Berdi', f: (p) => esc(A.userName(p.cashier)) },
          { h: 'Izoh', f: (p) => esc(p.comment || '') },
        ],
        payouts,
        { empty: "Bu oy uchun hali pul berilmagan" },
      )}
      <h3>Yakuniy balans</h3>
      <div class="tbl-wrap"><table class="tbl"><tbody>
        ${line('Avvalgi oylardan qoldiq', c.carried, { cls: balCls(c.carried) })}
        ${line(`+ ${period} hisoblangan`, c.total)}
        ${line(`− ${period} berilgan`, c.given)}
      </tbody><tfoot><tr><td><b>Yakuniy balans</b> <small class="muted">— ${balWord(c.final)}</small></td><td class="num"><b class="${balCls(c.final)}">${A.num(c.final)}</b></td></tr></tfoot></table></div>
      ${history.length > 1 ? `<h3>Oylar bo'yicha tarix</h3>${A.table(
        [
          { h: 'Davr', f: (h) => `${A.MONTHS[h.month - 1]} ${h.year}` },
          { h: 'Hisoblangan', f: (h) => A.num(A.salaryBase(h).total), cls: 'num' },
          { h: 'Berilgan', f: (h) => A.num(A.salaryBase(h).given), cls: 'num' },
          { h: 'Oy qoldig\'i', f: (h) => { const b = A.salaryBase(h); const d = b.total - b.given; return `<span class="${balCls(d)}">${A.num(d)}</span>`; }, cls: 'num' },
          { h: 'Yakuniy balans', f: (h) => { const f = A.salaryCalc(h).final; return `<b class="${balCls(f)}">${A.num(f)}</b>`; }, cls: 'num' },
        ],
        history,
        { rowAttr: (h) => `class="row-link" data-act="bal-open" data-id="${h.id}"` },
      )}` : ''}`;
    el.closest('.overlay')?.remove(); // oy almashtirilganda eski oyna yopiladi
    A.modal({ title: `${u.full_name} — xodim balansi`, wide: true, body });
  };
})(window.App);

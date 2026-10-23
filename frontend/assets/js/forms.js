/* Modal oynalar, xabarlar va bosqichma-bosqich forma (AppSheet Show_If / Valid_If / Reset_If mantig'i). onSubmit async bo'lishi mumkin */
(function (A) {
  const esc = A.esc;

  /* ================= Modal ================= */
  A.modal = ({ title, body, footer = '', wide = false, onClose }) => {
    const root = document.getElementById('modal-root');
    const ov = document.createElement('div');
    ov.className = 'overlay';
    ov.innerHTML = `
      <div class="modal ${wide ? 'wide' : ''}" role="dialog" aria-modal="true">
        <div class="modal-head"><h3>${esc(title)}</h3><button class="icon-btn" data-close aria-label="Yopish">✕</button></div>
        <div class="modal-body">${body}</div>
        ${footer ? `<div class="modal-foot">${footer}</div>` : ''}
      </div>`;
    root.appendChild(ov);
    document.body.classList.add('no-scroll');
    const close = () => {
      ov.remove();
      if (!root.children.length) document.body.classList.remove('no-scroll');
      onClose && onClose();
    };
    ov.addEventListener('click', (e) => {
      if (e.target === ov || e.target.closest('[data-close]')) close();
    });
    return { el: ov.querySelector('.modal'), close };
  };

  A.toast = (msg, tone = 'ok') => {
    const t = document.createElement('div');
    t.className = 'toast ' + tone;
    t.textContent = msg;
    document.getElementById('toasts').appendChild(t);
    setTimeout(() => t.classList.add('out'), 2600);
    setTimeout(() => t.remove(), 3000);
  };

  A.confirm = (msg, ok = 'Tasdiqlash', danger = false) =>
    new Promise((resolve) => {
      let done = false;
      const m = A.modal({
        title: 'Tasdiqlang',
        body: `<p>${msg}</p>`,
        footer: `<button class="btn ghost" data-close>Bekor qilish</button><button class="btn ${danger ? 'danger' : 'primary'}" data-ok>${esc(ok)}</button>`,
        onClose: () => !done && resolve(false),
      });
      m.el.querySelector('[data-ok]').onclick = () => { done = true; m.close(); resolve(true); };
    });

  /* ================= Forma ================= */
  const isEmpty = (v) => v === null || v === undefined || v === '' || (Array.isArray(v) && v.length === 0);
  const call = (x, v, d) => (typeof x === 'function' ? x(v) : x === undefined ? d : x);

  A.form = (cfg) => {
    const fields = cfg.fields;
    const v = { ...(cfg.values || {}) };
    for (const f of fields) if (v[f.name] === undefined && f.default !== undefined) v[f.name] = call(f.default, v);

    const m = A.modal({
      title: cfg.title,
      wide: cfg.wide,
      body: `${cfg.intro || ''}<form class="form" novalidate>
          <div class="form-error" hidden></div>
          ${fields.map((f) => `<div class="field ${f.type === 'note' ? 'note-field' : ''} ${f.half ? 'half' : ''}" data-f="${f.name}"></div>`).join('')}
        </form>`,
      footer: `<button class="btn ghost" data-close>Bekor qilish</button><button class="btn primary" data-submit>${esc(cfg.submit || 'Saqlash')}</button>`,
    });
    const form = m.el.querySelector('form');
    const wrap = (name) => form.querySelector(`[data-f="${CSS.escape(name)}"]`);
    const byName = Object.fromEntries(fields.map((f) => [f.name, f]));

    const optionsOf = (f) => (call(f.options, v, []) || []).map((o) => (Array.isArray(o) ? o : [o, o]));
    const visible = (f) => !!call(f.show, v, true);

    /* ---- 'combo' (qidiriladigan tanlov) ---- */
    const labels = {};
    const comboLabel = (f, val) => {
      if (isEmpty(val)) return '';
      const hit = optionsOf(f).find(([k]) => String(k) === String(val));
      return hit ? hit[1] : labels[`${f.name}:${val}`] || '';
    };
    let comboSeq = 0;
    async function comboFill(w, f, q) {
      const list = w.querySelector('.combo-list');
      if (!list) return;
      const seq = ++comboSeq;
      let opts;
      try {
        opts = f.search ? await f.search(q.trim()) : optionsOf(f).filter(([, l]) => l.toLowerCase().includes(q.trim().toLowerCase()));
      } catch (err) {
        opts = [];
      }
      if (seq !== comboSeq) return;
      opts = (opts || []).map((o) => (Array.isArray(o) ? o : [o, o]));
      for (const [k, l] of opts) labels[`${f.name}:${k}`] = l;
      list.innerHTML = opts.length
        ? opts.map(([k, l]) => `<button type="button" class="combo-opt ${String(v[f.name]) === String(k) ? 'on' : ''}" data-opt="${esc(k)}">${esc(l)}</button>`).join('')
        : `<div class="combo-empty">${q.trim() ? 'Hech narsa topilmadi' : 'Variant yo\'q'}</div>`;
      list.hidden = false;
    }
    let comboTimer = null;
    const comboClose = () => form.querySelectorAll('.combo-list').forEach((l) => { l.hidden = true; });

    function controlHTML(f) {
      const val = v[f.name];
      const ro = call(f.readonly, v, false);
      const req = call(f.required, v, false);
      const label = f.label ? `<label class="lbl">${esc(f.label)}${req ? ' <span class="req">*</span>' : ''}</label>` : '';
      const help = f.help ? `<div class="help">${call(f.help, v)}</div>` : '';
      const err = '<div class="err" hidden></div>';
      switch (f.type) {
        case 'note':
          return `<div class="note ${f.tone || 'info'}">${call(f.text, v)}</div>`;
        case 'computed':
          return `${label}<div class="computed">${call(f.compute, v) ?? '—'}</div>${help}`;
        case 'select': {
          const opts = optionsOf(f);
          return `${label}<select ${ro ? 'disabled' : ''}><option value="">${esc(f.placeholder || 'Tanlang…')}</option>${opts
            .map(([k, l]) => `<option value="${esc(k)}" ${String(val) === String(k) ? 'selected' : ''}>${esc(l)}</option>`)
            .join('')}</select>${help}${err}`;
        }
        case 'combo': {
          // yozib qidiriladigan tanlov: f.search(q) — serverdan [[id, nom], …] (bo'lmasa f.options ichidan)
          const cur = comboLabel(f, val);
          return `${label}<div class="combo"><input type="text" class="combo-in" value="${esc(cur)}" ${ro ? 'readonly' : ''} placeholder="${esc(f.placeholder || 'Yozib qidiring…')}" autocomplete="off"><div class="combo-list" hidden></div></div>${help}${err}`;
        }
        case 'seg': {
          const opts = optionsOf(f);
          return `${label}<div class="seg ${f.big ? 'big' : ''}">${opts
            .map(([k, l]) => `<button type="button" class="${String(val) === String(k) ? 'on' : ''}" data-val="${esc(k)}" ${ro ? 'disabled' : ''}>${esc(l)}</button>`)
            .join('')}</div>${help}${err}`;
        }
        case 'chips': {
          const opts = optionsOf(f);
          const cur = val || [];
          return `${label}<div class="chips">${opts
            .map(([k, l]) => `<button type="button" class="chip ${cur.includes(k) ? 'on' : ''}" data-val="${esc(k)}" ${ro ? 'disabled' : ''}>${esc(l)}</button>`)
            .join('') || '<span class="muted">Variant yo\'q</span>'}</div>${help}${err}`;
        }
        case 'textarea':
          return `${label}<textarea rows="3" placeholder="${esc(f.placeholder || '')}" ${ro ? 'readonly' : ''}>${esc(val ?? '')}</textarea>${help}${err}`;
        case 'checkbox':
          return `<label class="check"><input type="checkbox" ${val ? 'checked' : ''} ${ro ? 'disabled' : ''}> ${esc(f.label)}</label>${help}${err}`;
        default: {
          const t = f.type === 'money' || f.type === 'number' ? 'number' : f.type || 'text';
          const attrs = [
            f.min !== undefined ? `min="${call(f.min, v)}"` : '',
            f.max !== undefined ? `max="${call(f.max, v)}"` : '',
            f.type === 'money' ? 'step="1000" inputmode="numeric"' : '',
            ro ? 'readonly' : '',
            f.placeholder ? `placeholder="${esc(f.placeholder)}"` : '',
          ].join(' ');
          const moneyHint = f.type === 'money' ? `<div class="help money-hint">${val ? A.money(val) : ''}</div>` : '';
          const sugg = f.suggest ? call(f.suggest, v, []) : [];
          const listId = sugg.length ? 'dl' + A.uid() : '';
          const dl = sugg.length ? `<datalist id="${listId}">${sugg.map((s) => `<option value="${esc(s)}">`).join('')}</datalist>` : '';
          return `${label}<input type="${t}" value="${esc(val ?? '')}" ${attrs} ${listId ? `list="${listId}"` : ''}>${dl}${moneyHint}${help}${err}`;
        }
      }
    }

    function refresh() {
      for (const f of fields) {
        const w = wrap(f.name);
        let show = visible(f);
        if (show && f.auto && (f.type === 'select' || f.type === 'seg')) {
          const opts = optionsOf(f);
          if (opts.length === 1) {
            if (String(v[f.name] ?? '') !== String(opts[0][0])) { v[f.name] = opts[0][0]; f.onChange && f.onChange(v); }
            show = false;
          }
        }
        w.hidden = !show;
        if (!show) continue;
        const dynamic = ['note', 'computed', 'select', 'combo', 'seg', 'chips', 'checkbox'].includes(f.type) || f.readonly || f.required || f.help || f.suggest;
        const sig = JSON.stringify([
          f.suggest ? call(f.suggest, v, []) : null,
          f.type === 'select' || f.type === 'seg' || f.type === 'chips' ? optionsOf(f) : null,
          f.type === 'note' ? call(f.text, v) : null,
          f.type === 'computed' ? call(f.compute, v) : null,
          ['select', 'combo', 'seg', 'chips', 'checkbox'].includes(f.type) ? v[f.name] : null,
          call(f.readonly, v, false), call(f.required, v, false), f.help ? call(f.help, v) : null,
        ]);
        if (!w.dataset.init || (dynamic && w.dataset.sig !== sig)) {
          const errEl = w.querySelector('.err');
          const errText = errEl && !errEl.hidden ? errEl.textContent : '';
          w.innerHTML = controlHTML(f);
          if (errText) { const e2 = w.querySelector('.err'); if (e2) { e2.textContent = errText; e2.hidden = false; } }
          w.dataset.init = '1';
          w.dataset.sig = sig;
        } else {
          const inp = f.type === 'combo' ? null : w.querySelector('input:not([type=checkbox]),textarea');
          if (inp && document.activeElement !== inp && inp.value !== String(v[f.name] ?? '')) inp.value = v[f.name] ?? '';
          const mh = w.querySelector('.money-hint');
          if (mh) mh.textContent = v[f.name] ? A.money(v[f.name]) : '';
        }
      }
    }

    function clearDeps(name, seen = new Set()) {
      const f = byName[name];
      if (!f || !f.resets || seen.has(name)) return;
      seen.add(name);
      for (const r of f.resets) {
        v[r] = Array.isArray(v[r]) ? [] : '';
        clearDeps(r, seen);
      }
    }
    function setVal(name, val) {
      const f = byName[name];
      v[name] = val;
      clearDeps(name);
      f.onChange && f.onChange(v);
      const e = wrap(name).querySelector('.err');
      if (e) e.hidden = true;
      refresh();
    }

    form.addEventListener('input', (e) => {
      const w = e.target.closest('[data-f]');
      if (!w) return;
      const f = byName[w.dataset.f];
      if (['select', 'checkbox'].includes(f.type)) return;
      if (f.type === 'combo') {
        clearTimeout(comboTimer);
        const q = e.target.value;
        comboTimer = setTimeout(() => comboFill(w, f, q), 220);
        return;
      }
      let val = e.target.value;
      if (f.type === 'number' || f.type === 'money') val = val === '' ? '' : Number(val);
      setVal(f.name, val);
    });
    form.addEventListener('change', (e) => {
      const w = e.target.closest('[data-f]');
      if (!w) return;
      const f = byName[w.dataset.f];
      if (f.type === 'select') setVal(f.name, e.target.value);
      if (f.type === 'checkbox') setVal(f.name, e.target.checked);
    });
    form.addEventListener('focusin', (e) => {
      const w = e.target.closest('[data-f]');
      const f = w && byName[w.dataset.f];
      if (!f || f.type !== 'combo' || !e.target.classList.contains('combo-in') || e.target.readOnly) return;
      e.target.select();
      comboFill(w, f, '');
    });
    form.addEventListener('focusout', (e) => {
      const w = e.target.closest('[data-f]');
      const f = w && byName[w.dataset.f];
      if (!f || f.type !== 'combo' || !e.target.classList.contains('combo-in')) return;
      setTimeout(() => {
        if (w.contains(document.activeElement)) return;
        clearTimeout(comboTimer);
        comboSeq++;
        comboClose();
        // tanlanmagan matn qoldirilmasin: tanlangan qiymat nomi qaytadi
        if (isEmpty(v[f.name]) || !e.target.isConnected) { if (e.target.isConnected) e.target.value = ''; }
        else e.target.value = comboLabel(f, v[f.name]);
      }, 150);
    });
    form.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && e.target.classList && e.target.classList.contains('combo-in')) { e.stopPropagation(); comboClose(); }
      if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('combo-in')) {
        e.preventDefault();
        const first = e.target.closest('.combo').querySelector('.combo-opt');
        if (first) first.click();
      }
    });
    form.addEventListener('mousedown', (e) => { if (e.target.closest('.combo-list')) e.preventDefault(); });
    form.addEventListener('click', (e) => {
      const o = e.target.closest('button[data-opt]');
      if (o) {
        const w = o.closest('[data-f]');
        comboSeq++;
        setVal(w.dataset.f, o.dataset.opt);
        return;
      }
      const b = e.target.closest('button[data-val]');
      if (!b) return;
      const w = b.closest('[data-f]');
      const f = byName[w.dataset.f];
      const val = b.dataset.val;
      if (f.type === 'seg') setVal(f.name, String(v[f.name]) === val && !f.required ? '' : val);
      if (f.type === 'chips') {
        const cur = [...(v[f.name] || [])];
        const i = cur.indexOf(val);
        if (i >= 0) cur.splice(i, 1); else cur.push(val);
        setVal(f.name, cur);
      }
    });
    form.addEventListener('submit', (e) => { e.preventDefault(); submit(); });
    m.el.querySelector('[data-submit]').addEventListener('click', submit);

    let busy = false;
    async function submit() {
      if (busy) return;
      let bad = false;
      const out = { ...v };
      for (const f of fields) {
        const w = wrap(f.name);
        if (w.hidden) {
          if (!f.auto && !f.keepHidden) out[f.name] = Array.isArray(v[f.name]) ? [] : '';
          continue;
        }
        if (['note', 'computed'].includes(f.type)) continue;
        let msg = '';
        if (call(f.required, v, false) && isEmpty(v[f.name])) msg = "Majburiy maydon";
        else if (f.validate && !isEmpty(v[f.name])) msg = f.validate(v[f.name], v) || '';
        const errEl = w.querySelector('.err');
        if (errEl) { errEl.textContent = msg; errEl.hidden = !msg; }
        if (msg) bad = true;
      }
      const fe = form.querySelector('.form-error');
      if (bad) {
        fe.textContent = "Formada xatolar bor — qizil bilan belgilangan maydonlarni tekshiring.";
        fe.hidden = false;
        const first = form.querySelector('.err:not([hidden])');
        first && first.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
      const btn = m.el.querySelector('[data-submit]');
      busy = true;
      btn.disabled = true;
      let res;
      try {
        res = await cfg.onSubmit(out);
      } catch (err) {
        busy = false;
        btn.disabled = false;
        showServerErrors(err, fe);
        return;
      }
      busy = false;
      btn.disabled = false;
      if (typeof res === 'string') {
        fe.textContent = res;
        fe.hidden = false;
        return;
      }
      m.close();
    }

    /** Server xatolari: {"maydon": ["..."]} — tegishli maydon ostida, qolganlari forma tepasida */
    function showServerErrors(err, fe) {
      const data = err && err.data;
      let shown = false;
      if (data && typeof data === 'object' && !data.detail) {
        for (const [k, val] of Object.entries(data)) {
          const w = byName[k] && wrap(k);
          const e = w && !w.hidden && w.querySelector('.err');
          if (e) { e.textContent = Array.isArray(val) ? val.join(' ') : String(val); e.hidden = false; shown = true; }
        }
      }
      fe.textContent = shown ? "Formada xatolar bor — qizil bilan belgilangan maydonlarni tekshiring." : (err && err.message) || 'Xatolik yuz berdi';
      fe.hidden = false;
      if (!(err instanceof A.ApiError)) console.error(err);
    }

    refresh();
    const firstInput = form.querySelector('.field:not([hidden]) input:not([readonly]), .field:not([hidden]) select');
    if (firstInput && window.innerWidth > 700) firstInput.focus();
    return m;
  };
})(window.App);

/* Server bilan aloqa: /api/v1, sessiya + CSRF (bir domen). Ma'lumotnomalar kirgandan keyin bir marta yuklanadi (bootstrap). */
(function (A) {
  const BASE = '/api/v1';

  const cookie = (name) => {
    const c = document.cookie.split('; ').find((x) => x.startsWith(name + '='));
    return c ? decodeURIComponent(c.slice(name.length + 1)) : '';
  };

  /** Server javobidagi xatoni bitta matnga aylantirish ({"detail": ...} yoki {"maydon": ["..."]}) */
  A.errText = (data, status) => {
    if (!data) return status >= 500 ? "Serverda xatolik. Birozdan keyin qayta urinib ko'ring" : 'Xatolik yuz berdi';
    if (typeof data === 'string') return data;
    if (data.detail) return Array.isArray(data.detail) ? data.detail.join(' ') : String(data.detail);
    const first = Object.values(data)[0];
    if (first !== undefined) return Array.isArray(first) ? first.join(' ') : String(first);
    return 'Xatolik yuz berdi';
  };

  class ApiError extends Error {
    constructor(status, data) {
      super(A.errText(data, status));
      this.status = status;
      this.data = data;
    }
  }
  A.ApiError = ApiError;

  async function request(method, path, body) {
    const opts = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (method !== 'GET') opts.headers['X-CSRFToken'] = cookie('csrftoken');
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(BASE + path, opts);
    } catch (e) {
      throw new ApiError(0, { detail: "Server bilan aloqa yo'q. Internetni tekshiring" });
    }
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (res.status === 401 && !path.startsWith('/auth/') && A.onSessionLost) A.onSessionLost();
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }
  A.http = {
    get: (path) => request('GET', path),
    post: (path, body = {}) => request('POST', path, body),
    patch: (path, body) => request('PATCH', path, body),
    del: (path) => request('DELETE', path),
    csrf: () => request('GET', '/auth/csrf/'),
  };

  /* ---- Front-end to'plamlari ↔ API manzillari ---- */
  A.ENDPOINT = {
    branches: 'branches', courses: 'courses', rooms: 'rooms', dayPatterns: 'day-patterns', lessonTimes: 'lesson-times',
    coursePrices: 'course-prices', lessonFreqs: 'lesson-frequencies', discountTypes: 'discount-types', expenseCats: 'expense-categories',
    leadSources: 'lead-sources', attendanceStatuses: 'attendance-statuses', accounts: 'accounts', users: 'users', roles: 'roles',
    leads: 'leads', students: 'students', parents: 'parents',
    groups: 'groups', contracts: 'contracts', attendance: 'attendance', makeups: 'makeups',
    evaluations: 'evaluations', parentCalls: 'parent-calls',
    payments: 'payments', transfers: 'transfers', exchanges: 'exchanges', expenses: 'expenses', creditors: 'creditors',
  };
  const url = (coll, id) => `/${A.ENDPOINT[coll]}/${id !== undefined ? encodeURIComponent(id) + '/' : ''}`;
  const keyOf = (coll) => (coll === 'roles' ? 'code' : 'id');

  /** Keshdagi yozuvni almashtirish yoki qo'shish */
  A.putLocal = (coll, rec) => {
    const k = keyOf(coll);
    const list = A.S[coll] || (A.S[coll] = []);
    const i = list.findIndex((x) => x[k] === rec[k]);
    if (i >= 0) list[i] = rec;
    else list.push(rec);
    A.version++;
    return rec;
  };
  A.create = async (coll, data) => A.putLocal(coll, await A.http.post(url(coll), data));
  A.update = async (coll, id, data) => A.putLocal(coll, await A.http.patch(url(coll, id), data));
  A.remove = async (coll, id) => {
    await A.http.del(url(coll, id));
    A.S[coll] = (A.S[coll] || []).filter((x) => x[keyOf(coll)] !== id);
    A.version++;
  };

  /** Tasdiq kutayotganlar soni (qo'ng'iroqcha va Tasdiqlashlar) — serverda, foydalanuvchi tasdiqlay oladiganlari */
  A.reloadPending = async () => {
    A.S.pendingCounts = await A.http.get('/approvals/');
    A.version++;
  };

  /** Kirgandan keyin: joriy xodim, rollar, muddatlar va barcha ma'lumotnomalar */
  A.boot = async () => {
    const b = await A.http.get('/bootstrap/');
    A.S = Object.assign(A.emptyStore(), b, { currentUser: b.me.id });
    A.version++;
    await A.reloadPending().catch(() => {});
  };
})(window.App);

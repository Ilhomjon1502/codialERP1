# Front-end

Ma'qullangan prototip (`prototype/`) ekranlari, server API'siga (`/api/v1/`) ulangan. Framework va build yo'q — oddiy HTML, CSS, JS.

- Lokalda Django uni o'zi beradi: `backend` da `runserver` → http://localhost:8000.
- Serverda Nginx bu papkani to'g'ridan-to'g'ri beradi (`deploy/nginx/`).
- O'zgartirgandan keyin `index.html` dagi `?v=` qiymatini almashtiring, aks holda brauzer eski faylni ko'rsatadi.

## Qanday ishlaydi

| Fayl | Vazifasi |
|---|---|
| `assets/js/api.js` | Server bilan aloqa: sessiya + CSRF, xatolar, `A.create / A.update / A.remove`, kirgandan keyin `A.boot()` (ma'lumotnomalar keshi) |
| `assets/js/core.js` | Kesh (`A.S`), ruxsatlar (`A.can` — rol matritsasi serverdan), tahrirlash muddatlari (serverdan), nomlar |
| `assets/js/app.js` | Layout, menyu, kirish va parol o'rnatish sahifalari, marshrutlash. `A.CONNECTED` — serverga ulangan bo'limlar |
| `assets/js/forms.js` | Bosqichma-bosqich forma; server xatolari tegishli maydon ostida chiqadi |
| `assets/js/pages-admin.js` | Sozlamalar, Audit tarixi, Bosh sahifa (M1) |
| `pages-crm.js`, `pages-edu.js`, `pages-fin.js` | Prototip ekranlari — o'z bosqichida (M2–M7) API'ga ulanadi |

Sahifa ma'lumotni serverdan olishi kerak bo'lsa, `A.page('nom', { load: async () => {...}, render() {...} })` — `load` har chizishdan oldin chaqiriladi.

**Hisob-kitob va tekshiruv faqat serverda.** Front-end faqat ko'rsatadi va tugmalarni yashiradi; ruxsat va muddatlarni server baribir tekshiradi.

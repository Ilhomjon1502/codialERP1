# ERP xavfsizlik tekshiruvi — 2026-11-02

Doira: https://erp.codialinfo.uz (Django + DRF, Docker, Nginx, Hetzner `77.42.9.23`). Kod ko'rib chiqildi, server faqat o'qish
rejimida tekshirildi, loginga urinishlar cheklovi haqiqiy yo'l (Nginx → Gunicorn) orqali sinaldi. Sinov uchun soxta pochta
(`no-such-user@example.invalid`) ishlatildi, hech qanday haqiqiy akkaunt bloklanmadi.

## Topilmalar

| # | Daraja | Topilma | Holat |
|---|---|---|---|
| 1 | **Yuqori** | **Loginga urinishlar cheklovi aylanib o'tiladi.** (a) DRF `NUM_PROXIES` berilmagani uchun mijoz o'zi yozgan `X-Forwarded-For` hisob kaliti bo'lib qoladi: har so'rovda boshqa qiymat yuborilsa, cheklov hech qachon ishlamaydi (sinov: 45 urinish → 45 ta `400`, birortasi `429` emas). (b) Hisob `LocMemCache`da, Gunicorn 3 ta ishchi: «10/daq» amalda 30/daq (sinov: 29 ta o'tdi, keyin `429`). Parol 4 belgigacha bo'lishi mumkin bo'lgani uchun bu parolni terib topishga yo'l ochadi | **Tuzatildi va serverga joylandi** (2026-11-03, commit 0672a58) |
| 2 | O'rta | Parol siyosati: kamida 4 belgi (buyurtmachi qarori 2026-10-13). Hisob qulfi bilan hujum sekinlashadi (bir pochtaga 8 urinish / 15 daq), lekin raqamli 4 xonali parol kuchsiz | Qaror kerak: kamida Bosh menejer, Asoschi, Administrator+Hisobchi uchun 8 belgi |
| 3 | O'rta | Zaxira nusxalar faqat shu serverda (`/srv/backups`, 30 kun). Server buzilsa yoki yo'qolsa ma'lumot ham, zaxira ham yo'qoladi (talabalar shaxsiy ma'lumoti, to'lovlar) | Tashqi nusxa kerak (Hetzner snapshot yoki Storage Box) |
| 4 | Past | Nginx: `Server: nginx/1.24.0` versiyasi ko'rinadi; `limit_req` yo'q; HSTS faqat API javoblarida va 30 kun; CSP yo'q | Sozlanadi |
| 5 | Past | Serverda yadro yangilangan, qayta ishga tushirish kutilmoqda (`reboot-required`); 18 paket yangilanishi (xavfsizlik bo'yicha 0) | Qisqa texnik tanaffusda |
| 6 | Past | `/admin/login/` tashqaridan ochiq, urinishlar cheklanmagan. Lekin faol `is_staff`/`is_superuser` akkaunt **yo'q** (0 ta), demak kirib bo'lmaydi | Xohlansa Nginx'da yopiladi |
| 7 | Past | SSH `X11Forwarding yes` (ahamiyatsiz) | Ixtiyoriy |

## Yaxshi holatdagilar

- Firewall (ufw): kirish faqat 22, 80, 443; PostgreSQL va bot konteynerlari tashqariga ochilmagan, Gunicorn faqat `127.0.0.1`.
- SSH: faqat kalit bilan, parol bilan kirish o'chirilgan, `fail2ban` faol (so'nggi sutkada 1328 ta SSH hujumi urinishi bo'lgan).
- `deploy/.env` ruxsati `600`, zaxira papkasi `700`; `DEBUG=False`; `SECRET_KEY` uzunligi tekshiriladi.
- HTTPS majburiy (HTTP → HTTPS 301), TLS 1.2/1.3, xavfsiz cookie'lar, CSRF himoyasi (tokensiz POST → `403`), `X-Frame-Options: DENY`.
- Barcha ma'lumot API'lari kirishsiz `401` qaytaradi; `/api/docs`, `/api/schema` faqat admin uchun.
- `.git`, `.env`, `deploy/`, `backend/` yo'llari tashqaridan **ochilmaydi** (Nginx faqat `frontend/` papkasini beradi).
- Telegram Mini App kirishi: `initData` HMAC bilan tekshiriladi, 24 soatdan eski qabul qilinmaydi.
- Qo'ng'iroq qurilmalari tokeni bazada faqat SHA-256 hash ko'rinishida; ulash kodi 60 daqiqa amal qiladi.
- AI yordamchi SQL'i: faqat `SELECT`, faqat ruxsat etilgan view'lar, o'qish huquqli alohida rol, vaqt chegarasi.
- Barcha o'zgarishlar audit jurnaliga yoziladi; foydalanuvchi bor-yo'qligi parolni tiklashda oshkor qilinmaydi.
- Avtomatik xavfsizlik yangilanishlari (`unattended-upgrades`) yoqilgan.

## 1-topilma tuzatishi (2026-11-03 da serverga joylandi)

Joylangandan keyin xuddi shu sinov takrorlandi: soxta `X-Forwarded-For` bilan 45 urinishdan 10 tasi o'tdi, 35 tasi `429` (oldin 45/45 o'tgan edi);
oddiy 45 urinishdan 10 tasi o'tdi (oldin 29); bitta pochtaga turli IP'lardan 8 ta xatodan keyin qulf (9-urinishdan `429`).


- `REST_FRAMEWORK["NUM_PROXIES"] = 1`: mijoz manzili — `X-Forwarded-For`ning Nginx qo'shgan oxirgi qiymati.
- `prod.py`: kesh `FileBasedCache` — hamma ishchi uchun umumiy hisob; cheklov haqiqatan 10/daq.
- `LoginView`: bitta pochtaga 8 ta noto'g'ri urinishdan keyin 15 daqiqa qulf (IP'dan qat'i nazar, tarqoq hujumga qarshi);
  muvaffaqiyatli kirish hisobni nolga qaytaradi.
- Testlar: `tests/test_auth.py` (qulf, qayta o'rnatish, hisobga xoslik, soxta sarlavha). `conftest.py` testlar orasida keshni tozalaydi.
- Eslatma: oldindan bor edi, bu ishga aloqasi yo'q — `test_notifications.py::test_morning_plan_for_admin_cashier` bugungi sana (oy boshi) tufayli yiqiladi.

# Instagram/Facebook lidlari — kunlik hisobot (Google Sheets)

Har kuni **19:00** da Bosh menejerga Telegram xabari boradi va Google Sheets faylida shu kun uchun yangi varaq ochiladi
(`Lid_hisoboti_shablon`, varaq nomi sana: `18.11.26`). Varaq «Lid hisoboti» shablonining nusxasi: sana (D2) va 22 ta holat bo'yicha
lid soni (F3:F24) tizim tomonidan yoziladi, jami va guruhlar (Neytral / Sifatli / Sifatsiz) formulalar bilan hisoblanadi.

## Nima sanaladi

- **Shu kuni tushgan** Instagram va Facebook lidlari. **Sayt lidlari kirmaydi.**
- Har bir lid **hisobot paytidagi holati** bo'yicha sanaladi (19:00 da ko'rib chiqilmagani — «Yangi lid»).
- Eski kun hisobotini qayta olish: `python manage.py lead_report --date 2026-11-18` (varaq yangilanadi, Telegram'ga takror ketmaydi).

## Holatlar (qolipdagi 22 ta)

| Guruh | Holatlar |
|---|---|
| **Neytral** | Yangi lid · Ajidaniya · Bog'lanib bo'lmadi |
| **Sifatli** | Maslahat · Kachestvni lead · Kiruvchi qo'ng'iroq · Demoga yozildi · Grafik to'g'ri kelmadi · Markaz o'quvchisi |
| **Sifatsiz** | Boshqa joyda o'qiyabdi · Yosh to'g'ri kelmadi · Online kerak · Savdo boshqa bo'limni so'radi · Qo'shimcha raqam dublikat · Spam · Bog'lanib bo'lmadi (sifatsiz) · Xodimlar o'rtasidagi suhbat · Bizda yo'q kurs · Location to'g'ri kelmadi · To'lov qobiliyati yo'q · Boshqa viloyat · Sifatsiz lead |

## Holat qanday belgilanadi

**Instagram/sayt lidlari** → lid qatorida **«💬 Gaplashdim»** (Administrator+Hisobchi, Bosh menejer; bosh sahifa «Bugungi ish» va Qo'ng'iroqlar ham shu tugmani ishlatadi).
Formada izohdan keyin **keyingi qadam** va **«Lid holati (hisobot uchun)»** majburiy:

- **Qayta aloqa vaqti** → holat: *Ajidaniya*, *Bog'lanib bo'lmadi* yoki *Maslahat*.
- **Yopish** → sabab: *Grafik to'g'ri kelmadi* … *Sifatsiz lead* (15 ta, qolipdagi «Yopilgan Leadlar» bloki).

Qolganlari avtomatik:

| Holat | Qachon |
|---|---|
| **Yangi lid** | hali hech kim ko'rib chiqmagan |
| **Kiruvchi qo'ng'iroq** | lid tushgandan keyin shu raqamdan telefonga o'zi qo'ng'iroq qilgan (qabul telefoni jurnalidan; javobsiz ham hisoblanadi) va holat tanlanmagan |
| **Kachestvni lead** | «Lidga qo'shish» bosilib haqiqiy lid ochilgan |
| **Demoga yozildi** | bog'langan haqiqiy lid 3–5-holatga (sinov darsiga yozilgan / qatnashgan / o'qishni boshlagan) o'tgan |

> Eski (bu o'zgarishdan oldin gaplashilgan) yozuvlarda holat tanlanmagan: «Qayta aloqa» → *Ajidaniya*, «Yopilgan» → *Sifatsiz lead* deb sanaladi.

## Telegram xabari

Jami (Instagram / Facebook), uch guruh va ichidagi nolga teng bo'lmagan holatlar, ko'rib chiqilmagan lidlar soni, Google Sheets havolasi.
Varaqqa yozib bo'lmasa — xabar baribir ketadi va sababi yoziladi. Varaqdagi formulalar bizning hisobdan farq qilsa, xabarda ogohlantirish chiqadi
(qolipdagi formulani kimdir o'zgartirgan bo'lishi mumkin).

## Sozlash (bir marta)

1. Google Sheets fayli **«havola bilan hamma tahrirlaydi»** ochiq bo'lishi kerak (hozir shunday) yoki service account unga Muharrir qilib qo'shiladi (`gsheets_check` pochtasini ko'rsatadi).
2. Serverda `deploy/.env` ga fayl ID'si: `LEAD_REPORT_SHEET_ID=<havoladagi /d/ dan keyingi qism>`, so'ng `docker compose up -d --build web bot`.
3. Shablon varag'i «Lid hisoboti» deb nomlanishi kerak (`LEAD_REPORT_TEMPLATE_TAB`); uni o'chirmang va nomini o'zgartirmang — har kun shundan nusxa olinadi.
4. Alohida cron kerak emas: hisobotni 19:00 dagi `daily_report` o'zi ishga tushiradi.

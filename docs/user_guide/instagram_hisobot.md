# Instagram/Facebook lidlari — kunlik hisobot (Google Sheets)

Har kuni **19:00** da Bosh menejerga Telegram xabari boradi va Google Sheets faylida shu kun uchun yangi varaq ochiladi
(`Lid_hisoboti_shablon`, varaq nomi sana: `18.11.26`). Varaq «Lid hisoboti» shablonining nusxasi: sana (D2) va 22 ta holat bo'yicha
lid soni (F3:F24) tizim tomonidan yoziladi, jami va guruhlar (Neytral / Sifatli / Sifatsiz) formulalar bilan hisoblanadi.

## Nima sanaladi

Hisobotlar **2026-11-18 dan** boshlanadi (eski kunlar uchun varaq yo'q). **Sayt lidlari kirmaydi.**

- **Shu kuni ishlangan** lidlar sanaladi: yangi tushgani («Yangi lid») ham, **eski lid** shu kuni gaplashilgan/yopilgan/lidga qo'shilgan bo'lsa u ham.
- Kun ichida lid necha marta ishlansa ham, **oxirgi holati bilan bir marta** sanaladi. Ertasi kuni holati o'zgarsa, u ertangi varaqda yangi holati bilan chiqadi; kechagi varaq o'zgarmaydi.
- **Hisobot kuni 19:00 da yopiladi**: `18.11.26` varag'i = 17.11 19:00 dan 18.11 19:00 gacha. 19:00 dan keyingi ish keyingi kun varag'iga tushadi (hech narsa yo'qolmaydi).
- **Eski lidlar izohi:** katakka sichqoncha olib borilsa izoh chiqadi: «2 tasi 14.11.26 dan, 5 tasi 15.11.26 dan» — ya'ni shu holatdagi eski lidlar qaysi kunlarda tushgan. Eski lid bo'lmagan katakda izoh yo'q.
- Qo'lda qayta olish: `python manage.py lead_report --date 2026-11-18` (shu kun varag'i yangilanadi, Telegram'ga takror ketmaydi).

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
| **Yangi lid** | lid tushgan (yoki «Qayta ochish» bosilgan) kunda |
| **Kiruvchi qo'ng'iroq** | ochiq lid (yangi yoki qayta aloqada) tushgandan keyin shu raqamdan telefonga o'zi qo'ng'iroq qilgan (qabul telefoni jurnalidan; javobsiz ham); kuniga bir marta |
| **Kachestvni lead** | «Lidga qo'shish» bosilib haqiqiy lid ochilgan kunda |
| **Demoga yozildi** | bog'langan haqiqiy lid 3–5-holatga (sinov darsiga yozilgan / qatnashgan / o'qishni boshlagan) o'tgani hisobot paytida aniqlangan kunda |

## Telegram xabari

Ishlangan lidlar soni (Instagram / Facebook, shundan eski lidlar), uch guruh va ichidagi nolga teng bo'lmagan holatlar, Google Sheets havolasi.
Varaqqa yozib bo'lmasa — xabar baribir ketadi va sababi yoziladi. Varaqdagi formulalar bizning hisobdan farq qilsa, xabarda ogohlantirish chiqadi
(qolipdagi formulani kimdir o'zgartirgan bo'lishi mumkin).

## Sozlash (bir marta)

1. Google Sheets fayli **«havola bilan hamma tahrirlaydi»** ochiq bo'lishi kerak (hozir shunday) yoki service account unga Muharrir qilib qo'shiladi (`gsheets_check` pochtasini ko'rsatadi).
2. Serverda `deploy/.env` ga fayl ID'si: `LEAD_REPORT_SHEET_ID=<havoladagi /d/ dan keyingi qism>`, so'ng `docker compose up -d --build web bot`.
3. Shablon varag'i «Lid hisoboti» deb nomlanishi kerak (`LEAD_REPORT_TEMPLATE_TAB`); uni o'chirmang va nomini o'zgartirmang — har kun shundan nusxa olinadi.
4. Alohida cron kerak emas: hisobotni 19:00 dagi `daily_report` o'zi ishga tushiradi.

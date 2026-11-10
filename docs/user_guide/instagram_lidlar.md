# Instagram/sayt lidlari (kiruvchi lidlar navbati)

Instagram/Facebook reklamasidan (Google Sheets orqali) va saytdan kelgan lidlar **haqiqiy lid emas** — avval shu navbatga tushadi.
Ular oylik statistika, voronka va marketolog KPI'siga **kirmaydi**. Maqsad: lid yo'qolmasin, lekin sifatsiz murojaat ko'rsatkichni buzmasin.

Kim ko'radi: **Bosh menejer, Admin, Administrator+Hisobchi** (menyu «Instagram/sayt lidlari»; bosh sahifadagi «Bugungi ish» ichida ham).

## Jarayon
1. Lid jadvalga/saytga tushadi → Telegram guruhga xabar (avvalgidek) **va** ERP navbatiga «Yangi» bo'lib tushadi.
2. Administrator qo'ng'iroq qiladi va natijani belgilaydi:
   - **💬 Gaplashdim** — izoh majburiy, so'ng yo **qayta aloqa sana-vaqti** (shu vaqtda bosh sahifada yana chiqadi va botdan Administrator+Hisobchiga eslatma boradi), yo **Yopish** (qiziqmadi / noto'g'ri raqam).
   - **＋ Lidga qo'shish** — lid formasi ism, telefon, kurs va manba bilan oldindan to'ldirilib ochiladi (2-telefon va familiyani kiriting). Saqlangach navbatdagi yozuv shu lidga bog'lanadi va faqat shundan keyin statistikaga kiradi.
   - Raqam bazada bor bo'lsa «⚠️ Bazada bor» chiqadi va yangi lid ochilmaydi — mavjud lidga bog'lanadi.
   - Yopilganini «↩️ Qayta ochish» mumkin.
3. Tablar: Yangi · Qayta aloqa · Lidga qo'shilgan · Yopilgan.

## Qo'ng'iroqlar bilan bog'lanish
- Qabul telefonidagi qo'ng'iroq raqami navbatdagi lidniki bo'lsa, **Qo'ng'iroqlar** jurnalida «Noma'lum» o'rniga «Instagram lidi» belgisi, ism va kurs chiqadi; shu qatorning o'zidan «💬 Gaplashdim» va «＋ Lidga qo'shish» bosiladi (raqam bazada bo'lmasa).
- Navbat sahifasida va bosh sahifadagi kartochkada «Qo'ng'iroqlar» ustuni: lid tushgandan keyingi oxirgi qo'ng'iroq (yo'nalish, vaqt, suhbat), jami soni. Gaplashilgan qo'ng'iroq bo'lib, undan keyin izoh yozilmagan bo'lsa — «📞 gaplashilgan — izoh yozing».
- Lid tushishidan oldingi qo'ng'iroqlar hisobga olinmaydi.

## Qaysi lidlar tushadi
- Instagram/Facebook: Google Sheets jadvalidan (`ig_leads.py`, har 5 daqiqada) — **faqat yangi tushganlar** (eski qatorlar ko'chirilmaydi).
- Sayt: saytning forma serveri `POST /api/v1/inbox/site/` ga yuboradi, sarlavha `X-Inbox-Key: <INBOX_SITE_KEY>`, tana JSON: `name`, `phone`, `course`, `message`.
  Kalit serverda `deploy/.env` ga `INBOX_SITE_KEY=<uzun tasodifiy qator>` deb yoziladi. Bir raqam va manbadan 6 soat ichida takror yozuv qo'shilmaydi.
  Brauzerdan to'g'ridan-to'g'ri chaqirmang (kalit ochiladi) — sayt serveri (masalan Vercel funksiyasi) orqali yuboring.

Texnik: `apps/crm/inbox.py` (servis), `inbox_views.py` (API: `/inbox-leads/`, `summary`, `due`, `{id}/talk|link|reopen`), `reminders.inbox_callbacks`, front-end `pages-inbox.js`.

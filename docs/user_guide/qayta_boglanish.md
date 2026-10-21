# Lid: qayta bog'lanish vaqti va bot eslatmasi

**Kim ishlatadi:** lidlarni o'zgartira oladigan xodimlar (Administrator, Administrator+Hisobchi…). Botdagi eslatmani **hamma Administrator+Hisobchi** oladi.

## Vaqtni belgilash
1. Lidni oching → **Statusni o'zgartirish** → **1. Qayta bog'lanishga** yoki **8. Keyinroq o'qiydi**.
2. Chiqqan oynada **sana va vaqtni** tanlang (standart — ertaga 10:00) → **Saqlash**. Vaqt majburiy va kelajakda bo'lishi kerak.
3. Lidni **Tahrirlash** orqali ham holat va vaqtni o'zgartirsa bo'ladi. Kartochkadagi **✎ O'zgartirish** faqat vaqtni suradi.
4. Boshqa holatga (3, 4, 5, 6, 7) o'tganda vaqt o'zi o'chadi.

Belgilangan vaqt kartochkada, voronkadagi lid kartochkasida (⏰) va «Ro'yxat» jadvalida ko'rinadi; muddati o'tgani **qizil**.
Eski lidlarda (1-status, vaqti belgilanmagan) «vaqti belgilanmagan» yozuvi va **＋ Belgilash** tugmasi bor.

## Botdagi eslatma
Belgilangan vaqt kelganda (bot har daqiqada tekshiradi) Administrator+Hisobchilarga xabar keladi:

> ⏰ **Qayta bog'lanish vaqti keldi** · 15:00
> Ism Familiya · +998… · Kurs · holat · oxirgi izoh

Tugmalar:
- **✅ Qo'ng'iroq qilindi** — vaqt tozalanadi, lid izohiga «📞 Qo'ng'iroq qilindi (Telegram): kim» yoziladi. Keyingi bog'lanish uchun saytda yangi vaqt belgilang yoki holatni o'zgartiring.
- **⏰ +1 soat** — eslatma 1 soatdan keyin yana keladi.
- **📅 Ertaga** — ertaga shu vaqtda.

Huquq va muddat saytdagi bilan bir xil. Eslatma har vaqt uchun **bir marta** yuboriladi. Xabarni «Telegram» oynasida «Lid: qayta bog'lanish vaqti keldi» deb o'chirib/yoqib bo'ladi.

## Ertalabki reja (8:30)
- **⏰ Muddati o'tgan qayta bog'lanishlar** — vaqti o'tgan, qo'ng'iroq qilinmagan lidlar (kun va vaqti bilan);
- **🔁 Bugun qayta bog'lanish rejalashtirilgan** — bugungi vaqtlar;
- **🔁 Qayta bog'lanish kerak lidlar** — 1-statusda, vaqti belgilanmaganlar.

Bot to'xtab qolgan bo'lsa ham 12 soatgacha o'tgan vaqt eslatiladi; undan eskisi ertalabki rejaga tushadi.

Kod: `apps/crm/services.py` (`validate_callback`, `callback_action`), `apps/notifications/reminders.py` (`lead_callbacks`, `plan_text`), `services.lead_callback_from_telegram`, front-end `pages-crm.js` (`A.callbackForm`).

# Topshiriqlar (2026-10-16)

Menyu → **Topshiriqlar**. Har bir xodim boshqa xodimga yoki o'ziga topshiriq beradi, bot esa muddatni eslatib turadi.

## Topshiriq berish

**«Yangi topshiriq»** tugmasini bosib, quyidagilarni to'ldirasiz:

- **Mavzu** va **izoh**.
- **Bajaruvchi** — o'z filialingizdagi istalgan faol xodim. Admin va Bosh menejer hammaga bera oladi.
- **Qilinish muddati** — sana va soat.
- **Telegram orqali kimga eslatilsin** — bajaruvchiga, o'zingizga (beruvchiga) yoki ikkalasiga.
- **Eslatish qachon boshlansin** — muddat vaqtida, yoki muddatdan 15 daqiqa, 1 soat, 3 soat, 1 kun, 2 kun oldin.
- **Qanchalik tez-tez takrorlansin** — bir marta, har 30 daqiqa, har soat, har 3 soat yoki har kuni.

Muddat o'tib ketsa ham, topshiriq bajarilmaguncha eslatmalar davom etadi.

Topshiriq berilishi bilan bajaruvchiga Telegram'da «📌 Yangi topshiriq» xabari keladi.

## Bajarish

- Bajaruvchi **«✅ Bajarildi»** tugmasini bosadi. Natija haqida izoh yozish ixtiyoriy.
- Bu tugma sahifada ham, Telegram xabarining ostida ham bor.
- Bajarilgandan keyin eslatmalar to'xtaydi va beruvchiga «✅ Bajarildi» xabari boradi.

## Beruvchi nima qila oladi

Faqat ochiq topshiriq bo'yicha:

- **Muddatni uzaytirish**: +3 soat, +1 kun, +3 kun, +1 hafta yoki boshqa sana. Eslatmalar yangi muddat bo'yicha qaytadan boshlanadi, bajaruvchiga xabar boradi.
- **Tahrirlash**: mavzu, izoh, bajaruvchi va eslatma sozlamalari.
- **Bekor qilish** (sababi bilan): eslatmalar to'xtaydi, bajaruvchiga xabar boradi.

## Kim nimani ko'radi

- Har bir xodim **«Menga berilgan»** va **«Men bergan»** topshiriqlarni ko'radi.
- Admin va Bosh menejer **«Barchasi»** bo'limini ham ko'radi.
- Bosh sahifada ochiq va muddati o'tgan topshiriqlar haqida ogohlantirish chiqadi.
- Menyudagi raqam — sizga berilgan ochiq topshiriqlar soni.

Barcha o'zgarishlar audit tarixiga yoziladi.

## Texnik

- Kod: `apps/tasks/`, API: `/api/v1/tasks/`.
  - Amallar: `done`, `cancel`, `summary`, `people`.
  - So'rov parametrlari: `?box=in|out|all`, `?status=`.
- Ruxsat bo'limi `staffTasks`: hamma rollarga qo'shish va tahrirlash, Admin, BM va FM ga o'chirish ham.
- Eslatmalarni bot jarayoni har daqiqada tekshiradi (`tasks.services.due_reminders`).
- «✅ Bajarildi» tugmasi — Telegram `callback_query` (`td:<id>`).
- «Topshiriqni ochish» tugmasi — Mini App (`?tg=tasks&id=…`).

# Codial ERP — interaktiv prototip

Bu Django tizimi emas, balki **kelajakdagi tizim qanday ishlashini ko'rsatadigan prototip**: dizayn, menyu, formalar, rollar va hisob-kitob qoidalari ([CLAUDE.md](../CLAUDE.md) bo'yicha). Server ham, internet ham deyarli kerak emas — internet faqat shrift va diagrammalar (Chart.js) uchun ishlatiladi.

## Qanday ishga tushiriladi

**1-usul (tavsiya etiladi):** loyiha papkasida terminal ochib:

```bash
python -m http.server 5510 --directory prototype
```

so'ng brauzerda oching: http://localhost:5510

**2-usul:** `prototype/index.html` faylini ikki marta bosib, to'g'ridan-to'g'ri brauzerda ochish.

Telefonda ko'rish uchun kompyuter va telefon bitta Wi-Fi'da bo'lsa, 1-usul bilan ishga tushirib, telefonda `http://<kompyuter-IP>:5510` ni oching.

## Nimalarni sinab ko'rish mumkin

| Nima | Qayerda |
|---|---|
| Rollar o'rtasidagi farq (menyu, ruxsat, ma'lumot doirasi) | O'ng yuqoridagi ism → boshqa foydalanuvchini tanlash |
| Davomat olish (telefonda, katta tugmalar) | Aziz Qodirov yoki Jasur Aliyev (ustoz) → Davomatlar |
| Lid → talaba ma'lumotlari → «Shartnoma tuzish» | Lidlar → yangi lid, status «5. O'qishni boshladi» |
| To'lov + chegirma limiti + chek | Shartnoma → «To'lov qilish» |
| Naqdsiz to'lov / chegirma / o'tkazmani tasdiqlash | Tasdiqlashlar (Admin yoki Bosh menejer) |
| Oydagi dars sonini tasdiqlash → qarz va KPI qayta hisoblanadi | Bosh sahifadagi ogohlantirish yoki Sozlamalar → Oydagi dars soni |
| Qoldirilgan darsni yetkazish so'rovi | Ustoz → Davomatlar → Kelmaganlar → «Darsni yetkazdim» |
| G'azna balansi (yagona jurnal) | G'aznalar → g'aznani bosing |
| Oylik: KPI, jarima, oldingi oylardan qoldiq | Oyliklar |
| Rollar va ruxsatlar matritsasi (o'zgartirsa bo'ladi) | Sozlamalar → Rollar va ruxsatlar |
| Tahrirlash muddatlari | Administrator bilan kirib, eski to'lovni tahrirlashga urinib ko'ring |
| AI yordamchi (namunaviy savollar) | Faqat Bosh menejer → AI yordamchi |
| Audit tarixi | Admin / Bosh menejer → Audit tarixi |

## Muhim

- Sinov ma'lumotlari: Emirat filiali, 5 kurs, 7 guruh, ~60 shartnoma, ~70 lid, sentabr–oktabr davomatlari. Tizim 01.09.2026 da AppSheet'dan import qilingan deb olingan.
- Hamma o'zgarishlar **faqat shu brauzerda** (localStorage) saqlanadi. Boshlang'ich holatga qaytarish: yuqoridagi sana tugmasi → «Qayta tiklash».
- Sana tugmasi orqali «bugun»ni o'zgartirish mumkin (masalan, davomat uchun dars bor kunni tanlash).
- AI javoblari prototipda oldindan yozilgan qoidalar bilan hisoblanadi. Haqiqiy tizimda LLM SQL yozadi.
- Ochiq savollar (CLAUDE.md, 15-bo'lim) tegishli sahifalarda sariq/ko'k ogohlantirish bilan belgilangan.

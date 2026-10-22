# SMS — to'lov eslatmasi (qabul telefoni orqali)

2026-10-22 dan. SMS qabul telefonining (Redmi, «Codial qo'ng'iroqlar» ilovasi) **o'z SIM kartasidan** yuboriladi, shuning uchun SIM tarifidagi SMS paketi sarflanadi. Avtomatik yuborish yo'q: SMS faqat administrator «Yuborish»ni bosganda ketadi.

## Yuborish

1. **Qarzdorlar → «To'lovga tavsiya»**. Kerak bo'lsa kurs, holat yoki daraxt (kurs → guruh) bo'yicha filtrlang.
2. Yuborish ikki xil:
   - **«SMS yuborish»** (yuqorida) — ro'yxatda ko'rinib turgan hamma talabaga;
   - qatordagi **✉** — bitta talabaga.
3. Oynada qolipni tanlang. Matnni shu yerning o'zida tuzatish mumkin, namuna birinchi talaba bilan ko'rsatiladi. **«Davom etish»** bosilgach, tizim hisobni ko'rsatadi: nechta talaba, nechta raqam, nechta SMS. Keyin **«Yuborish»** bosiladi.
4. SMS talabaning **hamma raqamiga** ketadi: 1-telefon, 2-telefon va vasiyning telefoni (bir xil raqam bir marta).
5. Telefon navbatni ish vaqtida (8:00–21:00) 30 soniyada bir, tunda 10 daqiqada bir oladi va har SMS orasida 4 soniya kutadi (operator spam deb to'xtatmasligi uchun).

Qo'shimcha qoidalar:
- To'lov qilgan yoki «✓ To'lov qilgan» bilan olib tashlangan talabaga SMS ketmaydi.
- **Shu oy SMS olgan raqamga qayta yuborilmaydi**. Qayta yuborish kerak bo'lsa, oynada «Shu oy SMS olgan raqamlarga qayta yuborilmasin» belgisini olib tashlang.
- Ro'yxatdagi «SMS» ustunida holat ko'rinadi: ✓ yuborildi, ⏳ navbatda, ✕ xato.

## Qoliplar

**Qo'ng'iroqlar va SMS → SMS → «Qolip qo'shish»**. Matnni administratorlarning o'zi yozadi. Matnga o'rinbosarlar qo'yiladi, ular har talaba uchun almashtiriladi:

| O'rinbosar | Nima qo'yiladi |
|---|---|
| `{talaba}` | ism-familiya |
| `{ism}` | ism |
| `{kurs}`, `{guruh}` | kurs, guruh |
| `{oy}` | oy nomi (noyabr) |
| `{summa}` | to'lov summasi (1 300 000) |
| `{muddat}` | to'lov muddati (10.11) |

Namuna: `Assalomu alaykum! {talaba}ning {oy} oyi uchun to'lovi {summa} so'm. To'lov muddati: {muddat}. Codial o'quv markazi`

- **Lotin harflarida yozing.** Bitta SMS 160 belgigacha. Kirill harfi yoki maxsus belgi bo'lsa, bitta SMS 70 belgigacha qisqaradi va narx 2–3 barobar oshadi. Belgilar soni va SMS soni oynada ko'rinadi.
- `ʻ` va `’` kabi apostroflar o'zi oddiy `'` ga almashtiriladi.

## Talaba kartochkasida

Lid va shartnoma kartochkasida qo'ng'iroqlar yonida **SMS** bloki bor: talabaga va uning raqamlariga yuborilgan SMS'lar (holati, matni, kim yubordi).

## Statistika

**Qo'ng'iroqlar va SMS → «SMS statistikasi»** (davr bo'yicha):
- yuborilgan SMS va bo'laklar soni (tarif shunga qarab hisoblanadi);
- nechta talabaga ketgani;
- **SMS'dan keyin to'lov qilganlar** — birinchi SMS kunidan keyin to'lov tushgan talabalar soni, foizi va summasi;
- navbatda turgan va xato bo'lganlar;
- kunlar bo'yicha diagramma, kimga (talaba / 2-telefon / vasiy) va kim yubordi.

## Jurnal

**Qo'ng'iroqlar va SMS → SMS**:
- har bir SMS: kimga, matn, holat (Navbatda / Yuborilmoqda / Yuborildi / Xato / Bekor qilindi), xato sababi;
- **«Qayta yuborish»** — xato yoki bekor qilingan SMS uchun;
- **«Bekor qilish»** / **«Navbatni bekor qilish»** — telefon hali olmagan SMS'lar uchun (masalan, matn xato bo'lsa);
- telefon 5 daqiqadan ko'p aloqaga chiqmagan bo'lsa, sariq ogohlantirish chiqadi.

Telefon olgan, lekin 30 daqiqa ichida natija qaytarmagan SMS «Xato: Telefondan javob kelmadi» bo'ladi. U o'zi qayta yuborilmaydi, chunki takror ketmasligi kerak. Kerak bo'lsa, «Qayta yuborish»ni bosing.

## Telefonda bir martalik sozlash

1. «Codial qo'ng'iroqlar» ilovasini **1.1 versiyaga** yangilang (APK ustidan o'rnatiladi, ulanish saqlanadi).
2. Ilovada **«Ruxsatlarni berish»** → SMS yuborishga ruxsat bering. Ekranda «✅ SMS yuborishga ruxsat bor» chiqishi kerak.
3. Xiaomi'da: Sozlamalar → Ilovalar → Codial qo'ng'iroqlar → Ruxsatlar → **SMS yuborish — «Ruxsat berish»** (so'rash emas).
4. Ko'p SMS yuborilganda Android «Ilova ko'p SMS yuboryapti» deb so'rashi mumkin. **«Doim ruxsat berish»** ni belgilab, «Yuborish»ni bosing.
5. SIM kartada SMS paketi yoki balans bo'lsin. Ikki SIM bo'lsa, SMS «standart SMS SIM» dan ketadi.

## Ruxsatlar (bo'lim «SMS»)

| Rol | Ruxsat |
|---|---|
| Admin, Bosh menejer, Filial menejeri | hammasi |
| Administrator, Administrator+Hisobchi | yuborish, qolip qo'shish va tahrirlash |
| Hisobchi | faqat ko'rish |

«To'lovga tavsiya» ro'yxati faqat Qarzdorlar bo'limini ko'radiganlarga chiqadi. Bosh menejer ruxsatni «Rollar va ruxsatlar»da o'zgartiradi.

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

## Avtomatik SMS

**Qo'ng'iroqlar va SMS → SMS → «Avtomatik SMS»** bo'limida beshta qoida bor. Ular o'zi ketadi, administrator bosishi shart emas. **Boshida hammasi o'chiq.**

| Qoida | Qachon va kimga |
|---|---|
| 🆕 Yangi lid | Lid yaratilganda, lidning hamma raqamiga (har yangi lidga) |
| 📝 Shartnoma | Shartnoma tuzilganda (faol yoki rejadagi), talaba va vasiyning hamma raqamiga |
| 📅 Oy boshi | Oyning 1-sanasi 10:00. Shu oy narxini to'lamagan, faol, Grant bo'lmagan shartnomalarga |
| 🎁 Oldindan to'lov bonusi | Oyning 25-sanasi 10:00. Kelasi oy uchun hali to'lamaganlarga. Bonus «Avvaldan to'lov» chegirmasidan olinadi |
| 📵 Sababsiz kelmagan | Har kuni 08:00. Oxirgi 3 kunda «Besabab» bo'lgan, «Gaplashildi» belgilanmagan talabalarga (bir talabaga 3 kunda bittadan) |

Yoqish tartibi: **✎** bilan matnni tekshiring (kerak bo'lsa o'zgartiring), **«Ko'rish»** bilan kimlarga nechta SMS ketishini ko'ring, keyin **«Yoqish»**. Yoqishdan oldingi lid, shartnoma va davomatlarga SMS ketmaydi. Jadvalli qoidani vaqti o'tgandan keyin yoqsangiz, bugungi SMS'lar darrov navbatga qo'yiladi.

- Matnda o'rinbosarlar: `{ism}`, `{talaba}`, `{kurs}`, `{guruh}` («Kompyuter savodxonligi 192»), qoidaga qarab `{oy}`, `{summa}`, `{muddat_kun}`, `{bonus}`, `{kun}` (oy tugashiga qolgan kun), `{keyingi_oy}`, `{kecha}` («Kecha» yoki «21.10 kuni»).
- Bitta voqea bitta raqamga ikki marta ketmaydi. Oy boshi SMS'i «To'lovga tavsiya»dan SMS olgan raqamga ketmaydi.
- **Matn 160 belgidan oshmasin**, aks holda har SMS ikki bo'lak bo'lib, SMS paketidan ko'p sarflanadi (matn ostida belgi soni ko'rinadi). Lotin harflarida yozing.
- Jurnalda har SMS'ning turi ko'rinadi (Yangi lid, Shartnoma, Oy boshi, Oldindan to'lov, Kelmadi).
- **SMS bormay qolsa Bosh menejerga botdan xabar keladi:** navbatda 15 daqiqadan ortiq turgan SMS (telefon aloqasiz yoki ilova to'xtagan), xato yoki operator «yetkazilmadi» degan SMS, telefon ulanmagan filial. Har SMS haqida bir marta.

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

## Mijozlardan kelgan SMS (ilova 1.2)

- Qabul telefoniga **oddiy raqamdan** kelgan SMS bir necha soniyada ERP'ga tushadi. Bank kodlari, Click/Payme, operator va boshqa nomli yoki qisqa raqamli SMS'lar **telefondan chiqmaydi**.
- Raqam talaba, vasiy yoki lidga bog'lanadi. Bazada yo'q raqamdan kelgani ham saqlanadi: jurnalda «Noma'lum» va **«＋ Lid yaratish»** tugmasi chiqadi.
- Telefon o'chiq yoki internetsiz paytda kelgan SMS'lar keyin yuboriladi. Sutkada bir marta oxirgi 24 soat qayta tekshiriladi.
- Telefonda «Ruxsatlarni berish» → **SMS o'qish** ruxsati kerak. Ilovada «✅ Kelgan SMS'larni o'qishga ruxsat bor» chiqishi kerak.

## Talaba kartochkasida

Lid va shartnoma kartochkasida qo'ng'iroqlar yonida **SMS** bloki bor. U yozishma ko'rinishida: ↗ biz yuborganlar (holati va kim yubordi), ↙ talaba yoki vasiydan kelganlar.

## Statistika

**Qo'ng'iroqlar va SMS → «SMS statistikasi»** (davr bo'yicha):
- yuborilgan SMS va bo'laklar soni (tarif shunga qarab hisoblanadi);
- nechta talabaga ketgani;
- **SMS'dan keyin to'lov qilganlar** — birinchi SMS kunidan keyin to'lov tushgan talabalar soni, foizi va summasi;
- navbatda turgan va xato bo'lganlar;
- **kelgan SMS**: jami, nechta raqamdan, noma'lum raqamlardan;
- **eslatmaga javob yozdi** — to'lov eslatmasi olgandan keyin SMS yozgan talabalar;
- kunlar bo'yicha diagramma, kimga (talaba / 2-telefon / vasiy) va kim yubordi.

## Yetkazildimi? (ilova 1.3)

«Yuborildi» SMS telefondan chiqib operator markaziga qabul qilinganini bildiradi. Qabul qiluvchiga yetganini operator alohida xabar qiladi:
- **✓✓ Yetkazildi** — qabul qiluvchi telefoniga yetdi;
- **✕ Yetkazilmadi** — operator yetkaza olmadi, sababi (operator holat kodi) ko'rsatiladi;
- **yetkazilishi noma'lum** — operator xabar bermadi (hamma operator yubormaydi); SMS yetgan bo'lishi ham mumkin.

Har SMS tagida qaysi SIM va operator orqali ketgani yoziladi. Filtr: «Barcha yetkazilishlar». Statistikada «Yetkazildi» va «Yetkazilmadi» kartochkalari bor.

## Jurnal

**Qo'ng'iroqlar va SMS → SMS**:
- filtrlar: «Kelgan / Yuborilgan», «Noma'lum raqamlardan», holat, davr, qidiruv (ism, raqam yoki matn);
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

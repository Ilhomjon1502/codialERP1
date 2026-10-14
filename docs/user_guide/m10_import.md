# AppSheet'dan ko'chirish (M10)

Buyurtmachi qarori (2026-10-14): **faqat faol shartnomalar** ko'chiriladi. Ular bilan birga ularga kerak bo'lgan ma'lumotlar ham keladi. Qolgan hammasi yangi tizimda qo'lda kiritiladi, hisob **2026-yil 1-noyabrdan** boshlanadi.

| Ko'chiriladi (Emirat) | Ko'chirilmaydi |
|---|---|
| Sanada faol shartnomalar (raqami, turi, boshlanish sanasi) | Rejadagi va tugagan shartnomalar |
| Ularning talabalari va ota-onalari | Qarzlar: hammasi 0 dan boshlanadi |
| Ular o'qiyotgan guruhlar | Lidlar, to'lovlar, davomat, xarajatlar |
| Shu guruhlarning kursi, dars kunlari, vaqti, xonasi | G'aznalar, kreditorlar, oyliklar |
| Guruh ustozi va yordamchisi | KPI stavkalari, kurs narxlari, oydagi dars soni, boshqa xodimlar |

## Qanday ishlatiladi

1. Google Sheets'da **Fayl → Yuklab olish → Microsoft Excel (.xlsx)**. Faylni `import_data/` papkasiga qo'ying. Bu papka GitHub'ga yuklanmaydi.
2. Sinov rejimi (bazaga yozilmaydi, faqat hisobot chiqadi):
   ```bash
   python manage.py import_appsheet --file ../import_data/Codial1.1.xlsx --on 2026-11-01
   ```
3. Hisobotni AppSheet bilan solishtiring: faol shartnomalar va faol guruhlar soni. «XATOLAR» bo'limidagi yozuvlar ko'chirilmaydi, sababi yonida yozilgan. Ularni AppSheet'da tuzatib, faylni qayta yuklab oling.
4. Haqiqiy import — o'tish kuni (M11), zaxira nusxa olingandan keyin:
   ```bash
   python manage.py import_appsheet --file ../import_data/Codial1.1.xlsx --on 2026-11-01 --commit
   ```

## Qoidalar

- **Faol shartnoma**: shartnoma boshlangan va tugash sanasi yo'q yoki hali kelmagan. Bu `--on` sanasiga nisbatan tekshiriladi, standart holda bugungi sana olinadi.
- **Takroriy import dublikat yaratmaydi.** Har bir yozuvda AppSheet kaliti (`legacy_id`) saqlanadi. Qayta ishga tushirilsa, guruh, talaba va shartnoma ma'lumotlari Excel'dagidek yangilanadi. Shuning uchun yangi tizimda ish boshlangandan keyin importni qayta ishga tushirmang.
- **Xodimlar:**
  - pochtasi tizimda bor bo'lsa, o'sha akkauntga faqat bog'lanadi; roli va ismi o'zgarmaydi;
  - yangi xodimlar parolsiz yaratiladi, xat yuborilmaydi;
  - parol o'rnatish havolasi o'tish kuni Sozlamalar → Foydalanuvchilar → «Havolani qayta yuborish» orqali yuboriladi;
  - AppSheet'dagi «Qo'shilmagan» holat yangi tizimda «Ishdan ketgan» bo'ladi va hisobotda ogohlantirish chiqadi.
- **Rollar:** «Yordmachi», «Ustoz-Yordamchi», «Filial menejer» kabi eski yozuvlar ham taniladi. «Aloqa operatori» va «Asoschi / Investor» rollari «Boshqa» ga o'tadi.
- **Talaba ma'lumotlari:**
  - telefon 9 raqamga keltiriladi (`998…` boshidagi qism olib tashlanadi);
  - 1-telefoni yaroqsiz talaba ko'chirilmaydi va xatolar ro'yxatiga tushadi;
  - 2-telefon 1-telefonga teng bo'lsa, tashlab ketiladi;
  - sharifdagi nuqta olib tashlanadi.
- **Shartnoma:** tugash sanasi yo'q bo'lsa-yu, to'xtatish sababi yozilgan bo'lsa, sabab ko'chirilmaydi va hisobotda ogohlantirish chiqadi.
- **Dars kunlari:** AppSheet'da yakshanba 0 raqami bilan yozilgan, yangi tizimda u 7 bo'ladi.

## 2026-10-14 dagi sinov natijasi (`Codial1.1.xlsx`, 1-noyabr holatiga)

- Ko'chadi: 73 faol shartnoma (buyurtmachi tasdiqladi), 73 talaba, 21 guruh, 4 kurs, 2 xil dars kunlari, 4 dars vaqti, 4 xona, 7 ustoz va yordamchi.
- Xatolar yo'q.
- Ogohlantirishlar:
  - 2 ta yordamchi («FlutterShogirt», «Beckendshogirt») AppSheet'da «Qo'shilmagan» holatida;
  - 5 ta faol shartnomada sanasiz «Kursni tamomladi» sababi bor.

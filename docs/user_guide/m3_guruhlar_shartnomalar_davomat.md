# Guruhlar, shartnomalar va davomat (M3)

## Guruhlar

Menyu → **Guruhlar**. Tablar: Faol · Rejada · Nofaol. Karta rangi — to'lish holati: qizil (yomon, ≤ 50%), to'q sariq (o'rtacha, ≤ 75%), ko'k (yaxshi, ≤ 85%), yashil (zo'r).

- **Yangi guruh:** kurs → dars kunlari → vaqt → ustoz → yordamchi (ixtiyoriy) → xona → sanalar. Raqam avtomatik (kurs bo'yicha oxirgi raqam + 1), nomi «Frontend / #13».
- Ustoz va yordamchi shu filialda ishlaydigan faol xodimlardan tanlanadi. Xona shu vaqtda band bo'lsa ro'yxatda «band!» deb yoziladi.
- Filial o'zgarmaydi. Kursni faqat Admin, guruhda shartnoma bo'lmasa o'zgartiradi.
- Guruh sahifasida — **oylik davomat jurnali** (1 — keldi, 0 — sababli, X — besabab, – — nofaol, · — olinmagan), har talabaning qarzi va shu oy uchun dars soni.
- **Guruhlar tahlili:** faol guruhlar to'lish holati, ustoz va kurs bo'yicha.

Ustoz va yordamchi faqat o'z guruhlarini ko'radi.

## Shartnomalar

Menyu → **Shartnomalar**. Tablar: Faol · Rejada · Nofaol · Talabalar. Kurs → guruh bo'yicha guruhlangan, qarzdor talaba nomi qizil.

- **Yangi shartnoma:** talaba → kurs → guruh → turi → sanalar. Raqam avtomatik (filial bo'yicha).
- Odatda shartnoma **liddan** tuziladi: lid «5. O'qishni boshladi» statusida, lidga guruh tanlangan va talaba ma'lumotlari (sharif, tug'ilgan sana) to'ldirilgan bo'lsa, lid kartochkasida **Shartnoma tuzish** tugmasi ishlaydi. Boshlanish sanasi — sinov dars kuni.
- Turini (Grant) faqat Admin va Bosh menejer qo'yadi. Turi o'zgarsa, shu shartnomaning davomat qatorlari qayta hisoblanadi.
- Tugash sanasi kiritilsa, to'xtatish sababi majburiy.
- Tahrirlash muddati (administrator — 7 kun, filial menejeri — 15 kun) boshlanish sanasidan hisoblanadi. Muddati o'tgan shartnomada **To'xtatish** tugmasi bor: tugash sanasi (oxirgi 30 kun ichida), sabab va izoh kiritiladi.
- Shartnoma sahifasida: balans (qarz), darslar uchun hisoblangan summa, «Qarz qanday hisoblandi» bloki va davomat tarixi. To'lovlar M4 da qo'shiladi.

**Qarz qanday hisoblanadi:** bir dars narxi = kurs narxi ÷ oydagi dars soni (Sozlamalar → Oydagi dars soni, **tasdiqlangan** bo'lishi kerak). Dars bo'lsa qarz yoziladi — talaba kelmagan bo'lsa ham. «Nofaol» va Grant shartnomada qarz yo'q. Balans = boshlang'ich qoldiq + darslar − to'lovlar − chegirmalar.

## Qarzdorlar

Menyu → **Qarzdorlar**: balansi 0 dan katta shartnomalar, guruh bo'yicha, jami qarz bilan. Excel'ga yuklash mumkin.

## Davomat

Menyu → **Davomatlar**.

### Davomat olish

1. Guruhni tanlang (ustozda faol guruh bitta bo'lsa — o'zi tanlanadi).
2. Sana: **ustoz — faqat bugun**. Menejer va administratorlar o'tgan sanani tuzatadi: administrator oxirgi 7 kun, filial menejeri 15 kun, Admin va Bosh menejer cheklovsiz. Guruhning shu kuni darsi bo'lishi shart («Guruhning bu sanaga darsi yo'q»).
3. O'rindosh: darsni boshqa ustoz o'tgan bo'lsa (Admin, Bosh menejer, administratorlar belgilaydi). KPI darsni amalda o'tgan kishiga yoziladi.
4. Har talaba uchun: **Keldi** · **Sababli** (sababini yozing) · **Besabab** · **–** (Nofaol — faqat menejerlar). **Hammasi keldi** — belgilanmaganlarning hammasini «Keldi» qiladi.

Belgilangan zahoti talaba qarzi va ustoz/yordamchi KPI'si hisoblanadi. Bugungi belgini ustoz shu kunning o'zida o'zgartira oladi.

### Kelmaganlar

Besabab (X) va sababli (0) qatorlar, oy bo'yicha. **Bog'lanish holati** shu yerning o'zida tanlanadi: Bog'lanishga · Gaplashildi (izoh majburiy) · Tushib bo'lmadi · Noto'g'ri raqam.

### Qoldirilgan darslar

1. Ustoz «Kelmaganlar»dagi besabab qatorda **Darsni yetkazdim** ni bosadi, yetkazilgan sana va izohni yozadi.
2. So'rov «Qoldirilgan darslar» tabiga tushadi. Bosh menejer, filial menejeri yoki administrator **Tasdiqlash** yoki **Rad etish** (sabab bilan) qiladi.
3. Tasdiqlansa, davomat «Sababli»ga o'zgaradi va ustozga KPI yoziladi. Hammasi Audit tarixiga tushadi.

### Statistika

Oy bo'yicha guruh va ustozlar kesimida: qatorlar, keldi, sababli, besabab, davomat foizi.

## KPI

KPI = stavka ÷ oydagi dars soni («O'zgarmas» — bir o'quvchi uchun oylik summa) yoki foiz × kurs narxi ÷ dars soni («Foiz»). Faqat «Keldi» va «Sababli» uchun yoziladi; Besabab, Nofaol va Grant — 0. Stavkalarni kiritish ekrani M5 (Oyliklar) bosqichida.

## Hisob qachon qayta bajariladi

Kurs narxi, oydagi dars soni (tasdiqlash, o'zgartirish), shartnoma turi yoki davomat statusi o'zgarsa — tegishli qatorlar avtomatik qayta hisoblanadi. Qo'lda: `python manage.py recalculate --month 2026-10`.

# Qarorlar jurnali

| Sana | Qaror | Sabab |
|---|---|---|
| 2026-10-12 | Backend: Django 5 + Django REST Framework (API). Front-end: ma'qullangan prototip (`prototype/`) asos qilinadi va API'ga ulanadi; biznes hisob-kitoblari faqat serverda | Buyurtmachi tanlovi: ekranlar ma'qullangan, API keyin Telegram bot va AI uchun ham kerak. CLAUDE.md 4-bo'limidagi "Django shablonlari" rejasi o'rniga |
| 2026-10-12 | Test va asosiy muhit bitta Hetzner VPS'da (`test.` subdomen + asosiy domen), Docker Compose | Buyurtmachi tanlovi. Shaxsiy ma'lumotlar qonuni talabini buyurtmachi tekshiradi |
| 2026-10-12 | Yangi xodimga parol berilmaydi: pochtaga bir martalik "parol o'rnatish" havolasi yuboriladi | Buyurtmachi tasdiqladi (CLAUDE.md 7.2) |
| 2026-10-12 | Yangi lidda talabaning 2-telefoni majburiy | Buyurtmachi javobi (CLAUDE.md 18, 13-savol) |
| 2026-10-12 | Sozlamalardagi barcha ma'lumotnomalar bitta «settings» ruxsat bo'limi bilan boshqariladi (prototipdagidek). Filiallar — faqat Admin/BM; g'aznalar — «accounts» bo'limi, mas'ullarni faqat Admin/BM o'zgartiradi | Buyurtmachi ma'qullagan prototip shunday ishlaydi. CLAUDE.md 6.2 dagi har bir jadval uchun alohida ruxsat kerak bo'lsa, keyin bo'limlar ajratiladi |
| 2026-10-12 | Admin rolining ruxsatlari matritsadan o'zgartirilmaydi | Tizimdan qulflanib qolmaslik uchun |
| 2026-10-12 | Lid manbasi va xarajat kategoriyasi nomlari takrorlanmaydi (katta-kichik harf farqsiz) | Dublikat manba statistikani buzadi; prototipda tekshirilmagan edi |
| 2026-10-12 | Login so'rovi ham CSRF bilan himoyalangan; login urinishlari 10/daqiqa, parol so'rovlari 5/daqiqa | «Login CSRF» va parol tanlashga qarshi |
| 2026-10-12 | Serverda ilova va baza Docker'da, Nginx va certbot — serverning o'zida (apt) | Bitta serverda ikki muhit uchun eng sodda va boshqarish oson yo'l |
| 2026-10-12 | Lokal ishlab chiqishda SQLite, serverda PostgreSQL 16. Kod faqat ORM orqali | Lokal kompyuterda Docker yo'q; partial unique constraint ikkalasida ishlaydi |
| 2026-10-12 | Front-end'da hali ulanmagan bo'limlar menyuda xira ko'rinadi va «Mx bosqichida ulanadi» sahifasini ochadi | Xodimlar va buyurtmachi tizim holatini ko'rib turadi |
| 2026-10-12 | Server: Hetzner CAX11 (Arm64, 2 vCPU, 4 GB), Helsinki, $7.59/oy + zaxira | Cost-Optimized x86 (CX23) Yevropada mavjud emas edi; Regular CPX22 ~3 baravar qimmat. Tizim Arm64'da to'liq ishlaydi |
| 2026-10-12 | Test muhiti domen tayyor bo'lguncha `test.77-42-9-23.sslip.io` da (haqiqiy SSL bilan) | Domen hali yo'q; prod sozlama HTTPS talab qiladi (xavfsiz cookie) |
| 2026-10-12 | Test muhitida pochta konsolga (server jurnaliga) yoziladi, SMTP berilgach almashtiriladi | SMTP ma'lumotlari hali yo'q |
| 2026-10-13 | `erp.codialinfo.uz` hozirgi (sinov ma'lumotli) muhitga ulandi; haqiqiy ishga tushishda (M10–M11) ma'lumotlar tozalanib import qilinadi, manzil o'zgarmaydi | Buyurtmachi tanlovi |
| 2026-10-13 | Talabalar va ota-onalar API'si «leads» ruxsat bo'limiga bog'langan (6.2 da ular lidlar bilan bir qatorda) | Alohida bo'lim kerak bo'lsa keyin ajratiladi |
| 2026-10-13 | Lidda guruh, sinov dars kuni va «Shartnoma tuzish» M3 da (Group va Contract modellari bilan) ulanadi; M2 da forma 3–5 statuslarda shu haqda eslatma ko'rsatadi | Bosqichlar tartibi: guruhlar M3 da |
| 2026-10-13 | Voronka va statistika serverda hisoblanadi; voronka har ustunda oxirgi 40 ta lidni beradi, qolgani «Ro'yxat» tabida 50 tadan | AppSheet'dagi «hammasini yuklash» sekinligini takrorlamaslik uchun |
| 2026-10-13 | Servis xatolari ham `{"maydon": ["xato"]}` shaklida qaytadi (umumiy exception handler) | Front-end xatoni tegishli maydon ostida ko'rsatishi uchun |
| 2026-10-13 | Parol siyosati yumshatildi: faqat kamida 4 belgi (o'xshashlik, oddiy parol va faqat raqam cheklovlari olib tashlandi). Login urinishlari limiti qoladi | Buyurtmachi talabi: xodim istalgan, oson parolni ham qo'ya olsin. Xavf buyurtmachiga tushuntirildi |
| 2026-10-13 | M3: KPI stavkasi modeli (`payroll.KPIRate`) M3 da yaratildi — davomat qatoridagi KPI unga tayanadi. Stavkalarni kiritish ekrani M5 da; hozircha sinov stavkalari `seed_demo` va Django admin orqali | KPI hisobini M3 da yozib, M5 ni kutmaslik uchun |
| 2026-10-13 | Bo'lish natijasi (dars narxi, KPI) so'mgacha `ROUND_HALF_UP` bilan yaxlitlanadi; har davomat qatorida alohida | CLAUDE.md 5-bo'lim |
| 2026-10-13 | Oy uchun dars soni tasdiqlanmagan bo'lsa qarz va KPI `null` («hisoblanmagan») saqlanadi, 0 emas; qatorda sababi (`calc_note`) yoziladi. Stavka topilmasa KPI = 0 va «KPI stavkasi belgilanmagan» | CLAUDE.md 8.1, 8.3 |
| 2026-10-13 | Shartnoma va guruh statusi bazada saqlanmaydi — har so'rovda sanadan hisoblanadi (18-bo'lim 1-savol taxmini: tugagan → Nofaol, boshlanmagan → Rejada, aks holda Faol) | Statusni kunlik yangilash kerak bo'lmaydi |
| 2026-10-13 | Shartnoma balansi indeksli subquery aggregatsiyasi bilan olinadi: boshlang'ich qoldiq + Σ dars narxi − Σ to'lov − Σ chegirma (to'lovlar M4 da qo'shiladi) | AppSheet'dagi har ochilishda qayta hisoblashning o'rniga |
| 2026-10-13 | O'tgan sanaga davomat **olish** ham, **o'zgartirish** ham rol muddati bo'yicha (6.4): administrator 7 kun, filial menejeri 15 kun, Admin va Bosh menejer cheklovsiz, ustoz faqat bugun | 6.4 jadvali; «tuzatish uchun ≤ bugun» qoidasi muddat ichida |
| 2026-10-13 | Kelmaganlardagi bog'lanish holati va izoh muddat bilan cheklanmaydi (davomat ruxsati «qo'shish» yoki «tahrirlash» bo'lsa bas); davomat statusi esa muddat bilan | Administrator ota-onaga bir necha kundan keyin ham qo'ng'iroq qiladi |
| 2026-10-13 | «Sababli» belgilanganda izoh majburiy (serverda ham) | Prototipdagi forma; CLAUDE.md 7.4 «Sababli (izoh bilan)» |
| 2026-10-13 | Guruh kursini Admin faqat guruhda shartnoma bo'lmasa o'zgartiradi | Shartnoma va davomat qatorlaridagi kurs guruh kursi bilan bir xil bo'lishi kerak |
| 2026-10-13 | Shartnoma raqami filial bo'yicha o'chirilganlarni ham hisobga olib max+1 (raqam qayta ishlatilmaydi) | Qog'ozdagi shartnoma raqami bilan chalkashmaslik uchun |
| 2026-10-13 | Lid orqali «Shartnoma tuzish»: 5-status, lidda guruh tanlangan va talabaning tug'ilgan sanasi kiritilgan bo'lishi shart; boshlanish = sinov dars kuni (bo'lmasa bugun), turi Pullik | CLAUDE.md 7.3, prototip |
| 2026-10-13 | Shartnomani tahrirlash muddati boshlanish sanasi bo'yicha (prototipdagidek). **Istisno — to'xtatish:** tugash sanasi, sabab va izohni shartnoma ruxsati «tahrirlash» bo'lgan xodim muddatdan qat'i nazar o'zgartiradi, lekin tugash sanasi oxirgi 30 kun ichida bo'lsin (`services.check_contract_edit`). Front-end'da muddati o'tgan shartnomada «Tahrirlash» o'rniga «To'xtatish» | Buyurtmachi javobi: «administrator bir oy oldinga ham belgilay olsin» |
| 2026-10-13 | Guruhlar bootstrap'ga qo'shildi (doira bo'yicha, to'lish va oxirgi davomat sanasi bilan); shartnoma, davomat — sahifa ochilganda | Guruhlar kichik jadval, nomi ko'p joyda kerak |

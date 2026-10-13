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

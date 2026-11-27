# Suhbat yozuvlari (2026-11-18)

Qabul telefonidagi suhbatlar audio yozuv sifatida ERP'ga tushadi va **Qo'ng'iroqlar** ro'yxatida mos qo'ng'iroq qatorida «▶ Yozuv» tugmasi bilan eshitiladi.

## Yangi birlashgan ilova (2026-11-20)

Telefonda endi **Shizuku** va **Codial qo'ng'iroqlar** (yozuvchi shu ilovaning ichida, «Yozuvchi sozlamalari» tugmasi) ishlaydi; alohida ShizuCallRecorder kerak emas. Sozlash va yangilash tartibi, MIUI ruxsatlari: `tools/shizucallrecorder/README.md`. Muhim: yangilagandan keyin MIUI «Fonda avtomatik ishga tushirish» ruxsatini o'chirib qo'yadi — qayta yoqing; ekran qulfi parolsiz (swipe) bo'lsin; audio manba «Qo'ng'iroq ovozi». «Yozuvlar» ro'yxatida bitta yozuv bir qator ko'rinadi (telefon uni yozuv davomida bir necha marta yuklasa ham).

## Qanday ishlaydi

1. **Yozish** — telefondagi alohida yozuvchi ilova (tavsiya: ShizuCallRecorder, F-Droid) qiladi. «Codial qo'ng'iroqlar» ilovasi (1.4) o'zi yozmaydi.
2. Yozuvchi ilova fayllarni alohida papkaga saqlaydi.
3. «Codial qo'ng'iroqlar» ilovasi shu papkani kuzatadi: yangi audio fayl paydo bo'lsa, ERP'ga yuklaydi.
4. Server faylni qo'ng'iroqqa **vaqt bo'yicha** biriktiradi (fayl tugash vaqti + davomiylik ≈ qo'ng'iroq jurnalidagi tugash). Qo'ng'iroq hali jurnaldan kelmagan bo'lsa, ilova 3 kungacha qayta urinadi.

## Sozlash (bir marta)

1. Telefonda yozuvchi ilovani o'rnating va unda yozuvlar papkasini ko'rsating (masalan «Yozuvlar»).
2. «Codial qo'ng'iroqlar» ilovasini 1.4 ga yangilang → **4. Suhbat yozuvlari → «Yozuvlar papkasini tanlash»** → shu papkani tanlang. Tanlangan paytdan keyingi fayllargina yuklanadi (eski fayllar to'kilmaydi).
3. Sinov: bitta qo'ng'iroq qiling, tugagach 1–2 daqiqa kuting yoki «Yozuvlarni hozir yuklash»ni bosing. ERP'da qatorda «▶ Yozuv» chiqadi.

Android 11 da Shizuku usuli **cheklangan**: yozish paytida ekran qulfsiz bo'lishi kerak, Shizuku telefon o'chib yonganda qo'lda qayta ishga tushiriladi (Wi-Fi va «Simsiz tuzatish» orqali). Ish telefonida ekran qulfini o'chirib qo'yish tavsiya etiladi.

## Ruxsat

Yozuvni eshitish alohida bo'lim — **«Suhbat yozuvlarini eshitish»** (`call_audio`). Standart: Admin, Bosh menejer, asoschi. Boshqa rolga Bosh menejer Sozlamalar → Rollar va ruxsatlar'da «ko'rish» beradi. Qo'ng'iroqlar ro'yxatini ko'ra oladigan, lekin bu ruxsati yo'q xodim «▶ Yozuv» tugmasini ko'rmaydi (server ham fayl so'rovini rad etadi).

## Hajm va saqlash

- Fayl ko'pi bilan 80 MB. Nginx `client_max_body_size 80m`. Haqiqiy `erp.codialinfo.uz` ni **`/etc/nginx/sites-enabled/codial-erp`** xizmat qiladi (`codial-test` — zaxira domen, repodagi `deploy/nginx/codial-test.conf` shunga namuna). O'zgartirgach `nginx -t && nginx -s reload`. 2026-11-18 da ikkalasi 80m qilingan.
- Fayllar `media` Docker hajmida (`call_audio/YYYY/MM/`), bazadan alohida; zaxira nusxaga kirishini tekshiring.
- Eski fayllarni tozalash: `python manage.py purge_call_audio --days 180` (qo'ng'iroq yozuvi qoladi, faqat audio o'chadi). Tavsiya cron: har oy 1-kuni 04:00.

## Yozuvlar ro'yxati (Qo'ng'iroqlar → «Yozuvlar»)

Telefon yuborgan **har bir** yozuv serverda saqlanadi va shu yerda ko'rinadi — qo'ng'iroqqa biriktirilgan ham, biriktirilmagan ham. Biriktirilmagan yozuv (mos qo'ng'iroq jurnalga hali kelmagan yoki vaqti mos kelmagan) yo'qolmaydi: telefon yangi qo'ng'iroqlarni yuborganda server o'zi qayta moslaydi, «↻ Qayta moslash» tugmasi ham bor. Ro'yxatda: yozuv boshlangan vaqt, raqam, yo'nalish, kim, davomiyligi, holat (Biriktirilgan / Biriktirilmagan), ▶ Eshitish. Filtr: sana, raqam, biriktirilgan/biriktirilmagan. Bitta qo'ng'iroqqa ikki fayl tushsa, asosiysi uzuni, qisqasi «qisqaroq nusxa» bo'lib qoladi. Ko'rish ruxsati — «Suhbat yozuvlarini eshitish» (`call_audio`).

Moslash fayl nomidagi **yozuv boshlangan vaqt** bo'yicha (yozuvchi ilova uni yozadi): raqam ma'lum bo'lsa shu raqamning eng yaqin qo'ng'irog'iga; raqam yo'q (yashirin) kiruvchida javob berilgan kiruvchi qo'ng'iroqqa. Davomiylikka tayanilmaydi: jurnaldagi «suhbat» javobdan keyin hisoblanadi, yozuv esa jiringlashni ham o'z ichiga oladi.

## Instagram/Facebook lidlari audiosi — Telegram guruhiga

Instagram yoki Facebook lidi (Instagram/sayt lidlari navbatidagi) bilan **gaplashilgan** qo'ng'iroq yozuvi ERP'ga tushgach, bot uni **«Mardon aka ustoz Codialda»** guruhiga yuboradi (ovozli xabar sifatida, shu yerning o'zida tinglanadi). Audio tagidagi izohda:

- 👤 **Kim** — lidning ismi va telefoni;
- 📚 **Kurs**;
- 🔁 **Bog'lanish** — lid tushgandan beri shu raqam bilan nechanchi bog'lanish (javobsiz urinishlar ham sanaladi);
- 🆕 **Lid tushgan** sana va vaqt;
- 📞 **Qo'ng'iroq** vaqti, yo'nalishi va suhbat davomiyligi.

Qoidalar: faqat suhbat davomiyligi 0 dan katta qo'ng'iroqlar; lid qo'ng'irodan oldin tushgan bo'lishi kerak; har yozuv bir marta; yozuv yuklangach ~1 daqiqada yuboriladi. Sayt lidlari (Instagram/Facebook emas) va bazadagi oddiy lidlar guruhga bormaydi. Guruh manzili — `IG_CALLS_CHAT_ID` (`deploy/.env`; `0` — o'chiq). Kod: `apps/calls/ig_audio.py`, bot har daqiqada tekshiradi.

## Yozuv uzilsa — avtomatik ogohlantirish (2026-11-20)

Shizuku o'chib qolsa, yozuv suhbat o'rtasida uziladi yoki fayl bo'sh chiqadi. Gaplashilgan (15 soniyadan uzun) qo'ng'iroq tugaganidan 5 daqiqa o'tgach yozuv yo'q bo'lsa yoki suhbatdan sezilarli qisqa bo'lsa (15% yoki kamida 8 soniya), Administrator, Administrator+Hisobchi va Bosh menejerga Telegram xabari keladi: qaysi qo'ng'iroq, suhbat va yozuv davomiyligi, Shizuku'ni qayta yoqish ko'rsatmasi. Har qo'ng'iroq haqida bir marta; ketma-ket xatolar 10 daqiqada bitta xabarga jamlanadi. Xodim bu xabarni Telegram oynasida o'chira oladi («Suhbat yozuvi to'liq emas»). Kod: `apps/calls/rec_watch.py`.

## Yozuvchi o'chsa — darhol ogohlantirish (2026-11-26, ilova 4.1)

Telefon Shizuku o'chganini o'zi sezadi: ekranda ovoz bilan «Yozuv o'chgan!» bildirishnomasi chiqadi (bosilsa Shizuku ochiladi), 2 daqiqadan keyin Telegram'ga «🔴 Yozuvchi o'chgan» xabari boradi va ish vaqtida har 30 daqiqada takrorlanadi. Qo'ng'iroqlar → «Ro'yxat» tepasida ham ogohlantirish chiqadi. Shizuku ishga tushgach bildirishnoma o'zi o'chadi.

## Telefon ilovasi 5.0 (2026-11-27)

- **So'nggilar:** raqam o'rnida ERP'dagi ism, «Javobsiz» filtri. Qatorni bosing — raqam sahifasi (kim, holat, izoh, barcha qo'ng'iroqlar), «Qo'ng'iroq», «SMS».
- **Qidiruv:** yuqoridagi maydonga ism yoki raqam (ERP'dan qidirish uchun kamida 3 belgi).
- **Klaviatura:** yozayotganda mos raqamlar chiqadi; bo'sh maydonda yashil tugma oxirgi terilgan raqamni yozadi.

## Eslatma

Suhbatni yozish haqida mijozga xabar berish yoki roziligini olish masalasi markaz zimmasida (masalan, qabul telefoniga javobda «suhbat sifat nazorati uchun yozib olinadi» deyish).

## Muammolar

| Belgi | Sabab |
|---|---|
| Ilova: «Papkaga ruxsat yo'q» | Papkani qayta tanlang (ruxsat Android'da bekor bo'lgan) |
| «Mos qo'ng'iroq topilmadi» | Fayl vaqti va jurnal mos kelmadi (soat noto'g'ri yoki fayl nusxalangan). Qo'ng'iroq yozuvi ERP'da bor-yo'qligini tekshiring |
| Yozuv bor, lekin jim | Yozuvchi ilovaning o'zi tovushni ololmagan (Android 11 da ekran qulfli bo'lsa shunday bo'ladi) |
| Qo'ng'iroqda «▶ Yozuv» yo'q | Sizda «Suhbat yozuvlarini eshitish» ruxsati yo'q yoki yozuv hali yuklanmagan |

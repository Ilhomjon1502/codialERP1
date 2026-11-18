# Suhbat yozuvlari (2026-11-18)

Qabul telefonidagi suhbatlar audio yozuv sifatida ERP'ga tushadi va **Qo'ng'iroqlar** ro'yxatida mos qo'ng'iroq qatorida «▶ Yozuv» tugmasi bilan eshitiladi.

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

- Fayl ko'pi bilan 80 MB. Nginx `client_max_body_size 80m` (serverda `/etc/nginx/sites-available/codial-test` ni yangilab, `nginx -s reload`).
- Fayllar `media` Docker hajmida (`call_audio/YYYY/MM/`), bazadan alohida; zaxira nusxaga kirishini tekshiring.
- Eski fayllarni tozalash: `python manage.py purge_call_audio --days 180` (qo'ng'iroq yozuvi qoladi, faqat audio o'chadi). Tavsiya cron: har oy 1-kuni 04:00.

## Eslatma

Suhbatni yozish haqida mijozga xabar berish yoki roziligini olish masalasi markaz zimmasida (masalan, qabul telefoniga javobda «suhbat sifat nazorati uchun yozib olinadi» deyish).

## Muammolar

| Belgi | Sabab |
|---|---|
| Ilova: «Papkaga ruxsat yo'q» | Papkani qayta tanlang (ruxsat Android'da bekor bo'lgan) |
| «Mos qo'ng'iroq topilmadi» | Fayl vaqti va jurnal mos kelmadi (soat noto'g'ri yoki fayl nusxalangan). Qo'ng'iroq yozuvi ERP'da bor-yo'qligini tekshiring |
| Yozuv bor, lekin jim | Yozuvchi ilovaning o'zi tovushni ololmagan (Android 11 da ekran qulfli bo'lsa shunday bo'ladi) |
| Qo'ng'iroqda «▶ Yozuv» yo'q | Sizda «Suhbat yozuvlarini eshitish» ruxsati yo'q yoki yozuv hali yuklanmagan |

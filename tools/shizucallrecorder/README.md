# Codial qo'ng'iroqlar 3.x — birlashgan Android ilova (2026-11-20)

Bitta ilova (`uz.codial.calls`): **Codial ERP qo'ng'iroqlar/SMS** (eski `android/` ilovasi, Java) + **suhbat yozuvchi** ([ShizuCallRecorder](https://github.com/kitsumed/ShizuCallRecorder) v2.0.0, GPLv3, Kotlin) + to'liq o'zbekcha interfeys.
Telefonda faqat ikkita ilova qoladi: bu ilova va **Shizuku** (`moe.shizuku.privileged.api`). Asos — ShizuCallRecorder loyihasi, unga Codial kodi qo'shilgan; `applicationId = uz.codial.calls` (eski Codial ilovaning ustiga yangilanadi, ERP bilan ulanish saqlanadi).

## Fayllar
- `codial.patch` — ShizuCallRecorder v2.0.0 ustiga bizning o'zgarishlar (Codial Java kodi `app/src/main/java/uz/codial/calls/`, manifest, versiya, tuzatishlar).
- `strings-uz.xml` — o'zbekcha `app/src/main/res/values/strings.xml`; boshqa `values-*` papkalar o'chiriladi (ilova faqat o'zbekcha).

## Tuzatishlar (nima uchun kerak bo'lgan)
1. **Karnay/quloq almashganda yozuv uzilishi** (`ShellRecordingEngine.recoverCapture`): Android AudioRecord'ni uzadi va o'zi qayta ocholmaydi (`createRecord ... getInputForAttr -1`); oqim(lar) noldan qayta ochiladi. Ikkala oqim ham qayta ochiladi (Android tiklagani jim qaytaradi).
2. **Ekran qulfi (swipe) yopiq turganda yozuv boshlanmasligi**: Android 11 da yozuv shell'ning «ko'rinadigan oynasi»ga tayanadi, qulf ustida u ko'rinmaydi (`recording not allowed for uid 2000`). `CallReceiver` jiringlash/javobda ekranni yoqadi va `UnlockActivity` bilan qulfni yechadi (+ to'liq ekranli bildirishnoma zaxirasi). `AudioRecordCapture`: urinish 25 × 200 ms.
3. **Doimiy xizmat** (`CallService`) jarayonni tirik saqlaydi — MIUI uni qo'ng'iroq jiringlayotganda o'ldirmaydi, kiruvchi qo'ng'iroqda yozuv javobdan ~4 s keyin boshlanadi.

## Yig'ish (Windows, foydalanuvchi Terminalida)
```
git clone --branch v2.0.0 https://github.com/kitsumed/ShizuCallRecorder.git src
cd src && git apply ../codial.patch && cp ../strings-uz.xml app/src/main/res/values/strings.xml
rm -rf app/src/main/res/values-[a-z]*   # values/ dan tashqari hammasi
# local.properties: sdk.dir=...; Gradle 9.8.2 (services.gradle.org), JDK 17+ (Android Studio jbr), compileSdk 37 (Gradle o'zi o'rnatadi)
gradle assembleDebug   # app/build/outputs/apk/debug/app-debug.apk (~66 MB)
```
Debug kalit (`~/.android/debug.keystore`) bilan imzolanadi — eski Codial ilova ham shu kompyuterda shu kalit bilan edi, shuning uchun yangilanadi. Boshqa kompyuterda yig'ilsa — eskisini o'chirib qayta ulash kerak. `versionCode`/`versionName`ni har yig'ishda oshiring.

## Telefon sozlamalari (MIUI, Redmi Note 8 / Android 11) — HAR o'rnatish/yangilashdan keyin tekshiring
1. **Xavfsizlik → Ruxsatlar → Fonda avtomatik ishga tushirish → Codial qo'ng'iroqlar: yoqiq** (MIUI o'rnatganda o'chiradi; usiz qo'ng'iroqda ilova uyg'onmaydi: `process is not permitted to auto start`).
2. Ilova → «Yozuvchi sozlamalari»: **Kiruvchi** va **Chiquvchi qo'ng'iroqlarni avtomatik yozish** — yoqiq; audio manba — **«Qo'ng'iroq ovozi»** (ikkala tomon; «Uplink+Downlink» narigi tomonni yozmagan); yozuv papkasi — «Yozuvlar».
3. Shizuku ishlayotgan bo'lsin («Shizuku is running»); ilovaga Shizuku ruxsati berilgan. USB ulash/uzish yoki telefonni qayta yoqish Shizuku'ni o'chiradi — «Simsiz nosozlikni tuzatish» orqali qayta yoqing.
4. Batareya tejash: «Cheklovlarsiz»; «So'nggi ilovalar»da ilovani qulflang (🔒).
5. Ekran qulfi parolsiz (swipe) bo'lsin — parol/barmoq izi bo'lsa qulfni yechib bo'lmaydi.

Nosozlik bo'lsa: serverdagi `rec_watch` 15 s+ suhbat yozuvi 5 daqiqada kelmasa/qisqa bo'lsa Telegram'ga ogohlantirish yuboradi (Administrator, Administrator+Hisobchi, Bosh menejer).

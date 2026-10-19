# Qo'ng'iroqlar

Qabul telefonidagi barcha qo'ng'iroqlar (kiruvchi, chiquvchi, javobsiz) qo'ng'iroq tugashi bilan ERP'dagi **Qo'ng'iroqlar** bo'limiga tushadi.
Raqam bazada bo'lsa, talaba yoki vasiy ismi, lid statusi, manba va kurs ham ko'rsatiladi. Suhbat yozib olinmaydi.

## Telefonni ulash (bir marta)

1. ERP → **Qo'ng'iroqlar → Qurilmalar** → «Qurilma qo'shish» (Admin yoki Bosh menejer). Jadvalda 8 belgili **ulash kodi** chiqadi (1 soat amal qiladi).
2. Telefonga `app-debug.apk` ni o'rnating: faylni Telegram orqali telefonga yuboring → oching → «Noma'lum manbalardan o'rnatishga ruxsat» → O'rnatish.
3. «Codial qo'ng'iroqlar» ilovasini oching:
   - **Ruxsatlarni berish** → «Qo'ng'iroqlar jurnali» va «Telefon» — Ruxsat berish;
   - **Batareya tejashni o'chirish** → Ruxsat berish;
   - **MIUI: Avtozapusk** → ilovani yoqing;
   - Sozlamalar → Ilovalar → Codial qo'ng'iroqlar → Batareya tejash → **Cheklovlarsiz**;
   - oxirgi ilovalar ro'yxatida ilovani pastga torting va qulflang (🔒).
4. Ilovada «Ulash kodi»ni kiriting → **Ulash**. Shu kungi qo'ng'iroqlar darhol yuboriladi.
5. Tekshirish: telefonga qo'ng'iroq qiling → 5–10 soniyadan keyin ERP'da ko'rinadi.

Bildirishnomalar panelida «Qo'ng'iroqlar ERP tizimiga yuborilmoqda» yozuvi doim turadi — bu ilova ishlayotganini bildiradi.

## Ro'yxat

- **Filtrlar:** sana oralig'i, yo'nalish («Javobsiz — qayta qo'ng'iroq qilinmagan» — eng muhimi), bazada bor yoki noma'lum raqamlar, «Faqat birinchi marta».
- Javob berilmagan qo'ng'iroq qizil qatorda. Shu raqamga telefondan qayta qo'ng'iroq qilinsa, u **avtomatik** «Qayta bog'lanildi» bo'ladi; boshqa telefondan qilingan bo'lsa, «✓ Qo'ng'iroq qilindi» tugmasini bosing.
- **＋ Lid yaratish** — noma'lum raqamdan: lid formasi telefon va izoh bilan ochiladi.
- ✎ — qo'ng'iroqqa izoh («Frontend narxini so'radi» va h.k.).
- Telefon 6 soatdan ko'p aloqaga chiqmasa, ro'yxat tepasida ogohlantirish chiqadi.

## Statistika

Jami, kiruvchi, chiquvchi, javobsiz (qancha javobsiz qolgan), javobsizga o'rtacha qayta javob vaqti, yangi raqamlar; soatlar va kunlar bo'yicha diagramma; lid manbasi va lid statusi bo'yicha.

## Ruxsatlar

| Rol | Imkoniyat |
|---|---|
| Admin, Bosh menejer | hammasi, qurilmalarni qo'shish/kod olish |
| Filial menejeri, Administrator, Administrator+Hisobchi | ko'rish, izoh, «qo'ng'iroq qilindi» belgisi |
| Marketolog | ko'rish va statistika |

## Muammolar

| Belgi | Nima qilish kerak |
|---|---|
| Ilovada «Ulanish bekor qilingan» | ERP'dan «Yangi kod» olib qayta ulang |
| Qo'ng'iroqlar kechikib tushadi | Batareya tejash va Avtozapusk sozlamalarini tekshiring; internet bormi |
| Ilova yangilandi | APK'ni ustidan o'rnating — ulanish saqlanadi (bir xil kompyuterda yig'ilgan bo'lsa) |

Dasturchi uchun: ilova kodi `android/`, yig'ish — `android/build.ps1` (Android Studio o'rnatilgan kompyuter), API — `/api/v1/calls/pair|ingest|ping/`.

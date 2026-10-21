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

Jami, kiruvchi, chiquvchi, javobsiz (qancha javobsiz qolgan), javobsizga o'rtacha qayta javob vaqti, yangi raqamlar; suhbat vaqti: umumiy (kiruvchi/chiquvchi alohida), o'rtacha, eng uzun, davomiylik bo'yicha taqsimot (1–30 s … 10 daq+); soatlar va kunlar bo'yicha diagramma; lid manbasi va lid statusi bo'yicha.

## Ertalabki reja (08:30)

Administrator+Hisobchi'ga boradigan «Bugungi ish rejasi»ning boshida: kecha 18:30 dan bugun 8:30 gacha **javobsiz qolgan va hali qayta terilmagan** raqamlar (ism, raqam, vaqt; bir raqam bir necha marta qo'ng'iroq qilgan bo'lsa ×soni). Birinchi bo'lib shularga qo'ng'iroq qiling.

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

## Baza bilan integratsiya (2026-10-21)

**1. Kartochkada qo'ng'iroqlar tarixi.** Lid kartochkasi va shartnoma kartochkasida «Qo'ng'iroqlar (N) · oxirgi aloqa: 3 soat oldin» bloki chiqadi: talabaning 1-, 2-telefoni va vasiyning raqamidagi oxirgi qo'ng'iroqlar (yo'nalish, davomiylik, javobsiz bo'lsa belgisi). «Barcha qo'ng'iroqlar →» bosilsa Qo'ng'iroqlar bo'limi shu raqam bo'yicha ochiladi. Blok faqat «Qo'ng'iroqlar» bo'limini ko'ra oladigan xodimlarga chiqadi.
Qo'ng'iroqlar ro'yxatida talaba nomi bosilsa lid (yoki lidi bo'lmasa shartnoma) kartochkasi ochiladi.

**2. Suhbatdan keyingi izoh.** Qayta bog'lanishdagi (1- yoki 8-status) lidning raqamiga **gaplashilgan** qo'ng'iroq (chiquvchi yoki javob berilgan kiruvchi) bo'lsa:
- eslatma **to'xtamaydi** va qayta bog'lanish vaqti avtomatik yopilmaydi;
- lid kartochkasida «📞 … da gaplashilgan — izoh hali yozilmagan [📝 Izoh yozish]» belgisi, Qo'ng'iroqlar ro'yxatida «📝 Izoh yozish» tugmasi chiqadi;
- Administrator+Hisobchilarga botdan «📞 Suhbat bo'ldi — izoh yozing» xabari keladi (tugmalar: 📝 Izoh yozish — saytdagi kartochkani ochadi; 📅 Ertaga; 📅 3 kundan keyin). Agar qayta bog'lanish vaqti hali kelmagan bo'lsa, xabar o'sha vaqtda «allaqachon gaplashilgan — izoh yozing» ko'rinishida keladi;
- «Izoh yozish» oynasida: suhbat izohi (majburiy), holat va — lid 1/8-statusda qolsa — **keyingi qayta bog'lanish sana-vaqti** (vaqti o'tgan yoki yo'q bo'lsa majburiy);
- izoh yozilgach (yoki lidga oddiy izoh qo'shilsa) belgi o'chadi. Izoh yozilmaganlar 8:30 rejada «📝 Gaplashilgan, izoh yozilmagan lidlar» bo'limida chiqadi.

**3. Kelmagan talaba bilan bog'lanish.** Talabaning raqamiga gaplashilgan qo'ng'iroq bo'lsa va uning bog'lanish kutayotgan kelmagan darsi (oxirgi 14 kun, «Bog'lanishga» holati) bo'lsa, ro'yxatda «📌 Kelmagan (N): Gaplashildi» tugmasi chiqadi. Izoh yozilsa (majburiy) o'sha darslar «Gaplashildi» bo'ladi va — belgi qo'yilsa — «Ota-onalar bilan aloqa» jurnaliga ham yoziladi.

**4. Statistika.** «Qo'ng'iroq → lid → shartnoma» voronkasi (manba bo'yicha): qo'ng'iroq qilgan raqamlar, lidi borlar, o'qishni boshlaganlar, shartnoma tuzganlar, lidsiz raqamlar. AI yordamchi uchun `analytics_calls` (raqamsiz).

Kod: `apps/calls/services.py` (`history`, `_note_prompt`, `absence_contact`, `_funnel`), `apps/crm/services.py` (`save_call_note`), `reminders.lead_call_note`, front-end `pages-crm.js` (`A.callNoteForm`, `A.fillCalls`), `pages-calls.js`.

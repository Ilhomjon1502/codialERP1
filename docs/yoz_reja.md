# «Codial Yoz» — klaviatura mashqi sayti (yoz.codialinfo.uz)

> Holat: reja tasdiqlandi (2026-11-02). **Y1 bajarildi** (2026-11-02, kod `yoz/`, lokalda; serverga
> joylanmagan): yozish mexanikasi, mashq ekrani, klaviatura va qo'llar, natija oynasi (grafik bilan), lokal
> profillar, darslar xaritasi va yulduzlar, «Natijalarim» (14 kun, harflar xaritasi, tarix, faylga saqlash/yuklash).
> Darslar: 0–4 bo'limlar (tayyorgarlik, asosiy, yuqori, pastki qatorlar — barcha lotin harflari), 55 dars.
> **Y3 bajarildi** (2026-11-02): serverda `/srv/codial-yoz`, Nginx HTTP ishlayapti; DNS (`yoz` A → 77.42.9.23) va SSL (Let's Encrypt) ulandi — **https://yoz.codialinfo.uz ishlayapti** (2026-11-02).
> Savollarga javob kelmagani uchun tavsiyalar qo'llandi: xatoda to'xtaydi, kunlik maqsad 15 daqiqa, nom «Codial Yoz».
>
> Buyurtmachi qarori (2026-11-02): hozircha **faqat mustaqil sayt** — login/parol yo'q, ERP, bot va
> boshqa hech narsaga ulanmaydi. O'quvchiga manzil beriladi, xolos. Natija darsda sinalgandan keyin
> integratsiya alohida reja bilan qilinadi.

## 1. Maqsad

Kompyuter savodxonligi darsida o'quvchilar **o'n barmoq bilan, klaviaturaga qaramasdan** tez va to'g'ri
yozishni o'rganadigan, bolalarga qiziq, o'zbek tiliga moslangan sayt. Hamma narsa o'zbekcha.

## 2. O'xshash dasturlar — nimani o'rganamiz

| Dastur | Kuchli tomoni | Bizga oladigan g'oya |
|---|---|---|
| **TypingClub / EdClub** | yulduzli darslar xaritasi, ekranda klaviatura va qo'llar, xatoda to'xtaydi, qiziq dizayn | bosqichli yo'l, 0–3 yulduz, keyingi tugma va barmoq ko'rsatiladi |
| **Typing.com** | boshlang'ich / o'rta / yuqori kurslar, nishonlar, o'yinlar, sertifikat | bo'limlar darajasi, nishonlar, sertifikat |
| **keybr.com** | **moslashuvchan**: harflar bittalab qo'shiladi, faqat o'rganilgan harflardan so'z yasaydi, eng zaif harfni ko'proq beradi, har harf tezligi | «Zaif harflar» mashqi va har bir harf statistikasi |
| **Monkeytype** | toza ekran, vaqtli test (15/30/60 s), natijada tezlik grafigi, «raw» tezlik, barqarorlik (consistency) | tezlik testi va batafsil natija oynasi |
| **10FastFingers** | 1 daqiqada eng ko'p ishlatiladigan 200 so'z | o'zbekcha «200 so'z» testi |
| **Ratatype** | qadam-baqadam kurs, sertifikat | chop etiladigan sertifikat |
| **Nitro Type, Klavogonki** | poyga o'yini — kuchli motivatsiya | o'z rekordiga (sharpa) yoki «robot»ga qarshi poyga |
| **«Solo na klaviature» (Stamina)** | aniqlikka qattiq talab: xato ko'p bo'lsa keyingi mashq ochilmaydi | o'tish sharti — aniqlik (tezlik emas) |

Xulosa: **TypingClub tuzilmasi** (darslar xaritasi + yulduzlar + klaviatura/qo'llar) + **keybr aqli**
(zaif harflar, o'rganilgan harflardan so'zlar) + **Monkeytype testi** + **o'yinlar**.
Darslar matni, dizayn, rasm va nomlar o'zimizniki — hech qaysi dasturdan ko'chirilmaydi.

## 3. Kirish va natijalar (loginsiz)

- Saytga kirilganda: **«Ismingizni yozing»** — profil shu kompyuter brauzerida saqlanadi (`localStorage`).
- Bitta kompyuterda bir necha profil bo'ladi (darsda bir kompyuterda bir necha o'quvchi) — ism va
  avatar tanlab kiriladi. Parol yo'q.
- **Natija kartasi** — o'quvchi ustozga ko'rsatadi: ism, jami vaqt, eng yaxshi tezlik, aniqlik,
  yulduzlar, o'tilgan bo'lim, seriya kunlari.
- **«Shu kompyuterdagi o'quvchilar»** jadvali — ustoz darsda bir qarashda hamma profilni ko'radi.
- **Saqlash fayli**: «Natijamni yuklab olish» → fayl; uydagi kompyuterda «Faylni yuklash» → davom etadi.
- Cheklov (ma'lum): brauzer tozalansa natija yo'qoladi (fayl bo'lsa tiklanadi); markaziy reyting yo'q —
  bu keyingi, integratsiya bosqichida.

## 4. Kurs tuzilmasi

### 4.1 Darslar xaritasi
12 ga yaqin bo'lim, jami **~100 dars**. Har dars — 30 soniyadan 2 daqiqagacha. Dars o'tilmaguncha
keyingisi qulflangan (o'qituvchi rejimida hammasi ochiq).

| # | Bo'lim | Nima o'rganiladi |
|---|---|---|
| 0 | Tayyorgarlik | to'g'ri o'tirish, F va J dagi bo'rtiqlar, barmoqlar joyi (rasm + qisqa interaktiv) |
| 1 | Asosiy qator | F J → D K → S L → A ; → G H, bo'sh joy |
| 2 | Yuqori qator 1 | E I → R U → T Y |
| 3 | Yuqori qator 2 | W O → Q P |
| 4 | Pastki qator | V M → B N → C , → X . → Z |
| 5 | O'zbek harflari | o' g' (apostrof), sh, ch, ng |
| 6 | Bosh harflar | chap/o'ng Shift qoidasi |
| 7 | Tinish belgilari | ? ! : " - |
| 8 | Raqamlar | yuqori qator raqamlari |
| 9 | So'zlar | eng ko'p ishlatiladigan o'zbekcha so'zlar |
| 10 | Gaplar va matnlar | maqollar, qisqa hikoyalar, IT haqida matnlar |
| 11 | Inglizcha | so'zlar va gaplar (kompyuter atamalari) |

Harflar tartibi yakuniy kontentda o'zbek tilidagi harflar chastotasiga qarab aniqlanadi
(a, i, o, n, r, l, e … erta kelsin, so'z yasash oson bo'lsin).

### 4.2 Har yangi harf uchun darslar to'plami
1. **Tanishuv** — klaviaturada tugma va barmoq yonadi, «qaysi barmoq» rasmi, 10–20 marta bosish.
2. **Mashq** — harf birikmalari (`fj jf fff jjj`).
3. **So'zlar** — faqat o'rganilgan harflardan tuzilgan **haqiqiy o'zbekcha so'zlar** (keybr g'oyasi).
4. **Takrorlash** — bo'lim oxirida aralash.
5. **Bo'lim sinovi** — shartdan o'tmasa keyingi bo'lim ochilmaydi.

### 4.3 Yulduzlar va o'tish sharti
- O'tish: **aniqlik ≥ 90%** (tezlik emas — avval to'g'ri, keyin tez).
- ★ — o'tdi; ★★ — aniqlik ≥ 95%; ★★★ — aniqlik ≥ 97% **va** shu darsning maqsad tezligi.
- Maqsad tezlik bo'limdan bo'limga asta oshadi (masalan 8 → 25 so'z/daqiqa).

## 5. Mashq ekrani (eng muhim qism)

- Katta shriftli matn; joriy harf belgilangan, to'g'ri — yashil, xato — qizil.
- **Ekrandagi klaviatura**: keyingi tugma yonadi, tugmalar barmoq ranglarida; Shift kerak bo'lsa —
  qaysi Shift.
- **Qo'llar rasmi**: qaysi barmoq bosishi ko'rsatiladi (yuqori bo'limlarda o'chirib qo'yish mumkin —
  qaramasdan yozishga o'rgansin).
- Xato bo'lsa: **darslarda to'g'ri tugma bosilmaguncha oldinga o'tmaydi** (TypingClub kabi), testlarda —
  davom etadi, Backspace bilan tuzatiladi.
- Nusxa qo'yish (paste) ishlamaydi.
- Tepada jonli: tezlik, aniqlik, vaqt. Pauza (10 s dan ko'p to'xtash) vaqtga kirmaydi.
- Ovoz (bosish, xato, tugatish) — yoqish/o'chirish.
- Apostrof: `'` `` ` `` `ʻ` `ʼ` `‘` `’` — bir xil qabul qilinadi (o' va g' uchun).

## 6. Natija va statistika

- **Natija oynasi**: tezlik (sof WPM), «raw» tezlik, aniqlik, vaqt, yulduzlar, **barqarorlik**,
  dars davomida tezlik grafigi, xato qilingan harflar.
- **Profil**: jami ishlagan vaqt, kunlar bo'yicha grafik, tezlik o'sishi, ketma-ket kunlar (🔥),
  nishonlar, **har bir harf xaritasi** (klaviatura rasmi: yashil — yaxshi, qizil — sekin/ko'p xato).
- Formulalar:
  - Tezlik (WPM) = to'g'ri belgilar ÷ 5 ÷ daqiqa;
  - Raw = hamma bosilgan belgilar ÷ 5 ÷ daqiqa;
  - Aniqlik = to'g'ri bosishlar ÷ jami bosishlar × 100;
  - Barqarorlik = 100 − tezlik o'zgaruvchanligi (har soniyadagi tezlikdan).

## 7. Qo'shimcha rejimlar

- **Tezlik testi**: 30 s / 1 daq / 3 daq; o'zbekcha «200 so'z», inglizcha, yoki matn. Rekordlar jadvali (profil bo'yicha).
- **Zaif harflar**: eng sekin va ko'p xato harflardan avtomatik mashq (keybr g'oyasi).
- **O'yinlar** (2–3 ta, oddiy):
  - «Poyga» — o'z eng yaxshi natijangga (sharpa) yoki tanlangan tezlikdagi robotga qarshi;
  - «Yog'ilayotgan so'zlar» — so'z yerga tushmasdan yozib ulgur;
  - «Shar» — harf yozilgan sharlarni yozib yorish (eng kichiklar uchun).
- **Nishonlar**: birinchi dars, 7 kun ketma-ket, 1 soat, 20/30/40 WPM, xatosiz dars va h.k.
- **Kunlik maqsad**: masalan 15 daqiqa — halqa to'lib boradi.
- **Sertifikat** (chop etiladi): bo'lim/kurs tugaganda — ism, tezlik, aniqlik, sana, Codial logotipi.
- **O'qituvchi rejimi** (oddiy parol bilan, faqat shu brauzerda): hamma darslar ochiq, shu kompyuterdagi
  profillar jadvali, profilni o'chirish.

## 8. Texnik yechim

- **Faqat statik sayt**: HTML + CSS + JavaScript (ERP front-end kabi — framework va build yo'q).
  Server tomoni, baza, login yo'q.
- Repo'da alohida papka `yoz/`; ERP koduga tegilmaydi.
  - `index.html`, `assets/css/`, `assets/img/` (qo'llar, klaviatura — SVG)
  - `js/engine.js` — yozish mexanikasi va hisob (WPM, aniqlik, barqarorlik)
  - `js/keyboard.js` — ekrandagi klaviatura va qo'llar
  - `js/lessons.js`, `js/words_uz.js`, `js/words_en.js` — darslar va so'z ro'yxatlari
  - `js/store.js` — profillar (`localStorage`), saqlash fayli
  - `js/pages/*.js` — xarita, mashq, natija, profil, test, o'yinlar
- **Internet sekin bo'lsa ham ishlaydi** (PWA: bir marta ochilgach, oflayn ishlaydi).
- Engine uchun avtomatik testlar (Node), sintaksis tekshiruvi.
- **Joylash**: o'sha Hetzner serverida Nginx statik papka `yoz.codialinfo.uz`, Let's Encrypt SSL.
  DNS: ahost.uz'da `yoz` A-yozuvi → `77.42.9.23` (buyurtmachi qo'shadi). ERP va asosiy saytga tegilmaydi.
- Kompyuterda ishlash uchun. Telefonda sayt ochiladi, lekin «kompyuterda mashq qiling» degan yozuv chiqadi.

## 9. Bosqichlar

| # | Nima | Natija |
|---|---|---|
| **Y1** | Yozish mexanikasi, mashq ekrani, klaviatura va qo'llar, natija oynasi, profillar; 0–1 bo'limlar | Lokalda sinab ko'rsa bo'ladi |
| **Y2** | Darslar xaritasi, yulduzlar va o'tish sharti, 2–8 bo'limlar kontenti | To'liq boshlang'ich kurs |
| **Y3** | yoz.codialinfo.uz ga joylash (+ oflayn) — **darsda sinab ko'rish shu yerdan boshlanadi** | Bolalarga manzil beriladi |
| **Y4** | Tezlik testi, zaif harflar, profil statistikasi, harf xaritasi, natija kartasi, saqlash fayli, o'qituvchi rejimi | Ustoz natijani ko'radi |
| **Y5** | 9–11 bo'limlar (so'z, matn, inglizcha), o'yinlar, nishonlar, kunlik maqsad, sertifikat | To'liq versiya |

Y1–Y3 dan keyin buyurtmachi darsda sinaydi, fikrlariga qarab Y4–Y5 tartibi o'zgarishi mumkin.

## 10. Buyurtmachiga savollar

1. Xato qilganda **to'g'ri tugmani bosmaguncha to'xtasinmi** (TypingClub kabi, tavsiya) yoki davom etsinmi?
2. **Inglizcha bo'lim** kerakmi? Ruscha (kirill klaviatura) — keyinroqmi yoki umuman kerak emasmi?
3. O'quvchilar **yoshi** asosan qancha (9–12, 13–17, kattalar)? Dizayn ohangi va o'yinlar shunga qarab.
4. **Kunlik maqsad** 15 daqiqa ma'qulmi?
5. Kurs oxirida kutilgan natija (masalan **25–30 so'z/daqiqa, 95%**) — yulduz chegaralari shunga qo'yiladi.
6. Sayt nomi **«Codial Yoz»** bo'lsinmi?

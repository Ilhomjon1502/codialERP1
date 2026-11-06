# Mijozlar boti: Kompyuter savodxonligi testi — reja

> 2026-11-06, buyurtmachi so'rovi: «stiendtlar uchun bot qilgandik, shunga kompyuter savodxonligidan test oladigan qilish kerak.
> Testlar https://ilhomjon1502.github.io/Ks-darsi/ o'quv rejasidan tuziladi, 20 dona.»
> Holat: **bajarildi (kod, testlar)**, serverga joylanmagan. Tavsiyalar qo‘llandi (2026-11-06, «Ha, boshla»).

## 1. Nima bo'ladi (qisqacha)

- «Kompyuter savodxonligi» kursidagi o'quvchi mijozlar botida (@codialstudentbot) **20 savollik test** topshiradi.
- Har savolda **4 ta variant** bor, javob tugma bilan tanlanadi. Savollar va variantlar har safar aralashtiriladi.
- Oxirida ball chiqadi (masalan, 16/20 — 80%). Xato javoblar ro'yxati to'g'ri javob va «qaysi darsda o'tilgan» belgisi bilan beriladi.
- Natijalar ERP'da ko'rinadi: Qo'ng'iroqlar va SMS → Telegram bot → **«Test»** tabi (o'quvchi, guruh, ustoz, ball, sana, xatolar).
- Savollarni Bosh menejer o'sha tabda tahrirlaydi (so'rovnoma savollari kabi). Boshlang'ich 20 savol migratsiya bilan qo'shiladi (3-bo'lim).

## 2. Ishlar (bosqichlar)

| # | Ish | Fayllar |
|---|---|---|
| T1 | **Modellar:** `QuizQuestion` (kurs, dars raqami 1–12, savol, 4 variant, to'g'ri javob, tartib, holat), `QuizAttempt` (talaba, shartnoma, guruh, akkaunt, boshlangan/tugagan vaqt, savollar tartibi, javoblar, ball). Migratsiya + 20 savol (data migration) | `apps/clientbot/models.py`, `migrations/0008_…` |
| T2 | **Servis** `apps/clientbot/quiz.py`: kim topshira oladi (faol yoki tugagan KS shartnomasi, «Talaba» roli), testni boshlash, savolni yuborish, javobni qabul qilish (`qz:` callback), yakunlash va ball, xatolar tahlili, qayta topshirish qoidasi, 30 daqiqada tugamasa eskiradi | `quiz.py`, `services.py` (menyu, `handle_callback`), `cabinet.py` (`📝 Test` tugmasi) |
| T3 | **Testni ochish:** 4-bo'limdagi qarorga ko'ra — menyu tugmasi yoki ERP'dan guruhga «Testni yuborish» (bot har o'quvchiga taklif yuboradi, `ClientOutbox` orqali) | `quiz.py`, `views.py` |
| T4 | **API:** `/clientbot/quiz-questions/` (CRUD, BM), `/clientbot/quiz-attempts/` (ro'yxat, filtr: guruh, sana, ball; `stats`), kerak bo'lsa `/groups/{id}/send-quiz/` | `views.py`, `config/api.py` |
| T5 | **ERP ekrani:** Telegram bot → «Test» tabi: natijalar jadvali, guruh bo'yicha o'rtacha ball, eng ko'p xato qilingan savollar (qaysi darsni qayta tushuntirish kerakligini ko'rsatadi), savollar ro'yxati va tahrirlash formasi; Excel'ga yuklash | `frontend/assets/js/pages-clientbot.js`, `index.html` (`?v=`) |
| T6 | **Xabarlar (ixtiyoriy):** test tugaganda ustozga xodimlar botida qisqa xabar («Ali Valiyev — 16/20») | `notifications` |
| T7 | **Testlar:** savol tanlash va aralashtirish, ball, qayta topshirish, faqat KS o'quvchisi, vasiy topshira olmaydi, eskirish, ruxsatlar, so'rovlar soni | `backend/tests/test_clientbot_quiz.py` |
| T8 | **Hujjat:** `docs/user_guide/mijozlar_boti.md` ga «Test» bo'limi, CLAUDE.md 0-bo'lim jadvaliga qator | |
| T9 | **Joylash:** buyurtmachi aytganda — GitHub va server (`web`, `clientbot` qayta quriladi) | |

Taxminiy hajm: T1–T5 va T7 — bitta sessiya.

## 3. 20 ta savol (qoralama — buyurtmachi ko'rib chiqsin)

Manba: o'quv rejaning 1–11-darslari. 12-dars (yakuniy loyiha va himoya) amaliy, testga kirmaydi.
Sayt ichidagi 11 ta «tekshiruv» savoli olindi (✱ belgisi), qolgan 9 tasi dars matnidan tuzildi. To'g'ri javob — **qalin**.

| № | Dars | Savol | Variantlar |
|---|---|---|---|
| 1 ✱ | 1. Kompyuter va Windows | Kompyuterni o'chirsak, qaysi xotiradagi narsa yo'qoladi? | Disk · **Operativ xotira (RAM)** · Fleshka · Google Drive |
| 2 ✱ | 1. Kompyuter va Windows | Ochiq oynalar orasida tez almashish uchun qaysi tugmalar? | **Alt + Tab** · Ctrl + C · Win + L · Win + D |
| 3 ✱ | 2. Fayl va papkalar | Qaysi fayl nomi eng to'g'ri? | yangi document (2).docx · referat/oxirgi?.docx · **2026-10-20_Ali_Referat.docx** · oxirgi_oxirgi2.docx |
| 4 ✱ | 2. Fayl va papkalar | Shift + Delete nima qiladi? | Faylni Savatga tashlaydi · **Faylni butunlay o'chiradi** · Faylning nusxasini oladi · Faylni qayta nomlaydi |
| 5 ✱ | 3. Tezkor tugmalar, fleshka | Fleshkani sug'urishdan oldin nima qilish kerak? | Kompyuterni o'chirish · Hech narsa · **«Xavfsiz chiqarish»ni bosish** · Ctrl + S ni bosish |
| 6 | 3. Tezkor tugmalar, fleshka | Ekranning bir qismini rasmga olish (skrinshot) uchun qaysi tugmalar? | **Win + Shift + S** · Ctrl + Shift + N · Win + E · Ctrl + P |
| 7 ✱ | 4. Internet va qidiruv | Google'da faqat PDF fayllarni topish uchun nima qo'shamiz? | **filetype:pdf** · site:pdf · "pdf" · -pdf |
| 8 | 4. Internet va qidiruv | Internetdagi ma'lumot to'g'riligini qanday tekshiramiz? | Birinchi chiqqan saytga ishonamiz · **Kamida 2 ta ishonchli manbada tekshiramiz** · Rasmi chiroyli saytga ishonamiz · Tekshirish shart emas |
| 9 | 5. Prompt va AI | R-V-K-F formulasidagi «K» nimani bildiradi? | Kompyuter · Kod · **Kontekst** · Kitob |
| 10 | 5. Prompt va AI | Qaysi ma'lumotni AI ga hech qachon yozmaymiz? | Dars mavzusi · **Bank karta raqami va SMS kod** · Umumiy savol · O'zingiz yozgan matn |
| 11 ✱ | 6. Word | Mundarija avtomatik chiqishi uchun sarlavhaga nima qilish kerak? | Qalin qilish · **«Sarlavha 1» stilini berish** · Shriftni kattalashtirish · Markazga tekislash |
| 12 | 6. Word | Hujjat hamma kompyuter va telefonda bir xil ko'rinishi uchun qaysi formatda yuboramiz? | .docx · **.pdf** · .txt · .zip |
| 13 ✱ | 7. Word + AI | AI bergan manbalar ro'yxati bilan nima qilamiz? | Shundayligicha ko'chirib qo'yamiz · O'chirib tashlaymiz · **Har birini topib tekshiramiz** · AI dan yana so'raymiz |
| 14 ✱ | 8. Excel | =AVERAGE(B2:B5) nima hisoblaydi? | Yig'indini · **O'rtachani** · Eng kattasini · Nechta son borligini |
| 15 | 8. Excel | Excelda formula qaysi belgi bilan boshlanadi? | **=** · # · $ · * |
| 16 ✱ | 9. Excel + AI | Formulani pastga tortganda F1 katak o'zgarmasligi uchun nima yozamiz? | **$F$1** · F1 · "F1" · #F1 |
| 17 | 9. Excel + AI | C2 katakda 60 turibdi. =IF(C2>=60; "O'tdi"; "Yiqildi") nima chiqaradi? | **O'tdi** · Yiqildi · #VALUE! · 60 |
| 18 ✱ | 10. Taqdimot | Qaysi slayd yaxshiroq? | **Katta sarlavha, rasm va 3 qator** · 15 qator mayda matn · Har so'zda animatsiya · Referat matni to'liq |
| 19 ✱ | 11. Bulut va xavfsizlik | SMS: «Kartangiz bloklandi, kodni shu raqamga yuboring». Nima qilasiz? | Kodni yuboraman · Havolani ochib ko'raman · **Bankning rasmiy raqamiga o'zim qo'ng'iroq qilaman** · Javob yozib so'rayman |
| 20 | 11. Bulut va xavfsizlik | Qaysi parol eng kuchli? | 123456 · ali2012 · qwerty · **Olma-Daryo-Kitob-47** |

Saytdagi «tekshiruv» savollarida 3 tadan variant bor edi. Botda hamma savolda 4 tadan bo'lsin deb 4-variant qo'shildi.

## 4. Buyurtmachidan so'raladigan savollar (javob bo'lmasa — tavsiya qo'llanadi)

| # | Savol | Tavsiya |
|---|---|---|
| 1 | **Test qachon ochiladi?** a) menyuda doim turadi; b) ustoz yoki administrator ERP'da guruhga «Testni yuborish»ni bosadi (kurs oxirida); c) shartnoma «Kursni tamomladi» bilan yopilganda o'zi yuboriladi | **b** — o'quvchi o'tilmagan mavzudan test topshirib qo'ymasin |
| 2 | **Necha marta topshiradi?** | **1 marta**. Ustoz yoki administrator ERP'dan qayta ruxsat bera oladi; oxirgi natija ham, oldingilari ham saqlanadi |
| 3 | **To'g'ri javob qachon ko'rsatiladi?** Har savoldan keyin yoki test oxirida | **Oxirida**: ball va xato javoblar ro'yxati |
| 4 | **O'tish bali bormi?** Sertifikat yoki baholashga ta'sir qiladimi? | **12/20 (60%)**, hozircha faqat ma'lumot uchun |
| 5 | **Kim topshiradi?** Vasiy akkauntidan ham bo'ladimi? | **Faqat o'quvchining o'zi** («Talaba» roli bilan ulangan). Vasiy natijani ko'radi |
| 6 | **Natija kimga boradi?** | ERP «Test» tabi + ustozga xodimlar botida qisqa xabar |
| 7 | **Vaqt chegarasi?** | Butun test uchun 30 daqiqa, keyin eskiradi |
| 8 | **Savollar banki:** faqat 20 ta (hammaga bir xil, tartibi aralash) yoki kattaroq bank (masalan 40 ta) va undan har gal 20 tasi | Hozircha **20 ta**, keyin BM ERP'da qo'shib boradi. Bank 20 tadan ko'p bo'lsa, har darsdan teng tanlab olinadi |

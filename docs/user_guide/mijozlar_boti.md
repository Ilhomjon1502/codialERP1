# Mijozlar boti (o'quvchi va vasiylar) — 1–5-bosqichlar

O'quvchilar va ota-onalar uchun **alohida Telegram bot**. Xodimlar botidan (`@bildirishnomaERP1bot`) farqli — alohida token.
Bu bosqichda: ulanish (SMS'dagi kod), «Codialni qayerdan topdingiz?» so'rovi, tavsiya qiluvchi (tanish) ismi, Bosh menejer uchun «Telegram bot» bo'limi.
Hamma bosqichlar tayyor.

## Ishga tushirish (bir marta)

1. Telegram'da **@BotFather** → `/newbot` → bot yarating (masalan `@CodialBot`). Tokenni chatga yozmang.
2. Serverda: `bash /srv/codial-test/deploy/set-clientbot.sh` — token so'raladi (ekranda qolmaydi) va `clientbot` xizmati ishga tushadi.
3. Qo'ng'iroqlar va SMS → **SMS** → «Avtomatik SMS»da **«Yangi lid»** va **«Shartnoma tuzilganda»** qoidalari yoqilgan bo'lishi kerak: bot havolasi shu SMS'lar oxiriga qo'shiladi.

## Qanday ishlaydi

- Lid yaratilganda (yoki shartnoma tuzilganda) har telefon raqamiga SMS ketadi, oxirida: `Telegram bot: t.me/CodialBot?start=K7M4Q9XD`.
  Kod har raqam uchun alohida (8 belgi). Havola ochilmasa, kodni botga yozib yuborish ham yetadi.
- Raqam vasiyniki bo'lsa — **vasiy**, talabaning 1-telefoni bo'lsa — **o'quvchi**; 2-telefon va noaniq hollarda bot bir tugma bilan so'raydi («O'quvchining o'zi / Ota-ona yoki vasiy»).
- Bitta kod bilan ko'pi bilan 3 ta Telegram akkaunt ulanishi mumkin (o'quvchi, ota, ona). Bitta vasiy bir necha farzandga ulanadi.
- Noto'g'ri kod 8 martadan keyin bir soatga to'xtatiladi. `/stop` — ulanishni uzadi.
- Raqam allaqachon ulangan bo'lsa, SMS'ga havola qo'shilmaydi.

## Bot so'rovlari

1. **Manba.** Lid ulangach: «Codial haqida qayerdan eshitdingiz?» — tugmalar Sozlamalardagi faol lid manbalaridan. Javob **alohida** saqlanadi, administrator kiritgan manba o'zgarmaydi.
2. **Tavsiya.** Manba nomida «tanish» yoki «tavsiya» so'zi bo'lsa (masalan «Tanishlardan eshitdim»), bot tavsiya qilgan odamning ism-familiyasini so'raydi va shartnomasi bor (faol yoki tugagan) talabalar orasidan 5 tagacha nomzod tugmasini ko'rsatadi. Topilmasa — «Bu ro'yxatda yo'q», ism «Aniqlanmagan» tavsiya sifatida saqlanadi.
   Lidning o'zi tavsiya qiluvchi bo'la olmaydi.

## Bosh menejer va administratorlar uchun

**Qo'ng'iroqlar va SMS → Telegram bot** (ruxsat bo'limi `clientbot`: Admin/Bosh menejer — hammasi; Filial menejeri, Administrator, Adm+Hisobchi — ko'rish va tahrirlash; Marketolog — ko'rish):

| Tab | Nima |
|---|---|
| Umumiy | ulangan talabalar (o'quvchi/vasiy), yuborilgan va ulanmagan kodlar, manba javoblari, tavsiyalar, xabarlar navbati |
| Ulanganlar | kim, qaysi raqam, Telegram nomi, vaqti |
| Ulanmaganlar | SMS bilan kod yuborilgan, lekin hali ulanmagan raqamlar |
| Manba javoblari | mijoz aytgan manba va administrator kiritgani yonma-yon (farqlari belgilanadi) |
| Tavsiyalar | kim kimni tavsiya qilgan; «Aniqlanmagan» ismni talabaga bog'lash, rad etish |
| Sozlamalar | filial bo'yicha: SMS'ga havola qo'shilsinmi, **tavsiya bonusi (standart 75 000 so'm)**, bonus uchun birinchi to'lov (oy narxining %), start eslatmasi oralig'i va soni (B2 da ishlaydi) |

## Texnik

`apps/clientbot` — `BotConfig`, `BotInvite` (talaba + raqam → kod), `BotAccount`, `BotLink`, `LeadSurvey`, `Referral`, `ClientOutbox`.
API: `/api/v1/bot-links/` (+`summary/`), `bot-invites/`, `bot-surveys/`, `bot-referrals/`, `bot-config/`. Jarayon: `python manage.py run_clientbot` (Docker `clientbot` xizmati).
SMS'ga havola: `calls/auto_sms._bot_suffix` (faqat lid va shartnoma qoidalari).

## 2-bosqich: SMS o'rniga bot, sinov darsi xabari, ulanish eslatmasi

**Bot yoki SMS.** Talaba + raqam botga ulangan bo'lsa, xabar **SMS o'rniga botga** boradi (bepul, yetkazilishi aniq). Ulanmagan raqamga SMS ketadi, oxirida bot havolasi bo'ladi.
Bu hamma avtomatik SMS'larga (lid, shartnoma, sinov darsi, oy boshi, oldindan to'lov, kelmagan) va «To'lovga tavsiya» → «SMS yuborish»ga tegishli.
- Qabul telefoni aloqasiz bo'lsa ham, ulangan raqamlarga xabar boraveradi.
- Bir voqea ikki marta ketmaydi: bot orqali ketgan xabar, ulanish uzilsa ham, SMS bo'lib qayta ketmaydi. «Shu oy eslatma olgan» tekshiruvi botga ketganini ham hisoblaydi.
- Akkaunt botni bloklagan bo'lsa, xabar SMS bo'lib ketadi.
- «To'lovga tavsiya»da SMS yuborishdan oldingi tasdiq oynasida: «N ta raqamga SMS va M ta raqamga Telegram bot orqali».

**Yangi avtomatik qoidalar** (Qo'ng'iroqlar va SMS → SMS → «Avtomatik SMS», boshida **o'chiq**; yoqishdan oldin «Ko'rish» bilan tekshiring):
| Qoida | Qachon | Matn (standart) |
|---|---|---|
| 🎓 Sinov darsga qatnashdi | lid shu holatga o'tganda, har lidga bir marta, talabaning hamma raqamiga | «Assalomu alaykum! Sinov darsimizga qatnashganingiz uchun rahmat. Savollaringiz bo'lsa, 998204432 ga murojaat qiling.» |
| 🤖 Botga ulanish eslatmasi | har kuni 10:00: faol shartnomasi yoki ochiq lidi (1–4) bor, lekin ulanmagan raqamlarga | «Codial o'quv markazi xabarlari Telegram botda ham keladi, ulanib qo'ying.» + havola |

Eslatma har `reminder_days` kunda (standart 7) bir martadan, bir taklifga jami `reminder_max` marta (standart 3) ketadi; havola bilan oxirgi SMS ketgan vaqtdan sanaladi. Ikkalasi Telegram bot → Sozlamalarda o'zgaradi.
Telefon raqami matnda yozilgan (sinov darsi qoidasi) — kerak bo'lsa ✎ bilan o'zgartiring.

**Telegram bot → Xabarlar** tabi: botga ketgan hamma xabarlar (vaqt, kim, turi, matn, holat) va «Umumiy»da soni turlar bo'yicha. API: `/api/v1/bot-messages/`.

## 3-bosqich: o'quvchi va vasiy kabineti

Ulangan o'quvchi yoki vasiy botdagi pastki tugmalar orqali (yoki `/menu`) **faqat o'qish** rejimida ko'radi. Vasiy ham, o'quvchining o'zi ham bir xil ma'lumotni ko'radi.

| Tugma | Nima ko'rinadi |
|---|---|
| 💳 To'lovlar | oxirgi 10 ta to'lov (sana, summa, shakli, chegirma; tasdiqlanmagan naqdsiz to'lov «⏳ tasdiqlanmoqda»), jami to'langan va har kurs bo'yicha qarz yoki oldindan to'langan summa |
| 📋 Davomat | shu oy: keldi/sababli/sababsiz soni; oxirgi 12 ta dars holati |
| 📅 Dars jadvali | faol va boshlanmagan shartnomalar: guruh, dars kunlari va vaqti, xona, ustoz, keyingi dars sanasi |
| 💰 To'lov muddati | shu oy uchun to'lash kerak summa va muddat (kechiksa — necha kun), eski qarz; to'lov qilingan bo'lsa «✅»; Grant — to'lov talab qilinmaydi |

- Hisob saytdagi bilan bir xil servislardan olinadi (`with_balance`, `month_dues`): bu «To'lovga tavsiya» va qarzdorlar ro'yxati bilan mos keladi. «✓ To'lov qilgan» deb olib tashlangan o'quvchiga «to'lash kerak» chiqmaydi.
- Bir vasiy bir necha farzandga ulangan bo'lsa, tugma bosilganda bot qaysi farzand uchun ekanini so'raydi. Akkaunt faqat o'ziga ulangan talabani ko'ra oladi; `/stop` dan keyin kabinet yopiladi.
- KPI, ustoz izohlari, ichki hisoblar va o'zgartirish imkoniyati yo'q.

## Shartnoma raqami bilan ulanish (SMS kelmasa)

SMS yetib bormagan yoki kod yo'qolgan bo'lsa, administrator talabaga aytadi: **botga shartnoma raqamingizni yuboring** (ERP'da shartnoma sahifasidagi «№»; «1234», «№1234» yoki «shartnoma 1234» ko'rinishida).
Keyin bot shartnomadagi telefonlardan birining (o'quvchi, 2-telefon yoki ota-ona) **oxirgi 4 raqamini** so'raydi — to'g'ri bo'lsa ulaydi (bu raqamga qarab o'quvchi yoki vasiy aniqlanadi; 2-telefon bo'lsa bot kimligini so'raydi).

Xavfsizlik: shartnoma raqami ketma-ket va sir emas, shuning uchun u o'zi yetmaydi — raqamlarni sinab birovning ma'lumotini ko'rib bo'lmasin.
- Tekshiruvdan oldin bot talaba ismini aytmaydi.
- Bir talaba uchun noto'g'ri telefon urinishi sutkada 5 tadan oshsa, o'sha talaba bir sutkaga bloklanadi (to'g'ri raqam ham o'tmaydi; SMS'dagi kod baribir ishlaydi).
- Bir akkaunt soatiga 8 ta noto'g'ri urinishdan keyin to'xtatiladi; bir raqamga ko'pi bilan 3 akkaunt ulanadi.

## Hozirgi talabalarni botga ulash

Bot ishga tushganda faol talabalar hali ulanmagan bo'ladi. Ulash yo'llari (birga ishlatiladi):
1. **Ommaviy taklif** — Qo'ng'iroqlar va SMS → Telegram bot → **Talabalar** → «Mavjud talabalarni taklif qilish». Faol (yoki boshlanmagan) shartnomali talabalarning **ulanmagan** raqamlariga (1-, 2-telefon, vasiy) SMS ketadi, oxirida shu raqamga xos bot havolasi va kodi bo'ladi. Avval hisob ko'rsatiladi (nechta talaba, nechta raqam, jami SMS), siz tasdiqlaysiz. Ulangan raqamga va avval taklif olganga qayta ketmaydi. Matnni o'zgartirish mumkin (`{ism}`, `{talaba}`). Bu taklifning birinchi eslatmasi hisoblanadi.
2. **Eslatmalar** — «Botga ulanish eslatmasi» qoidasi (SMS → Avtomatik SMS) yoqilsa, ulanmaganlarga har 7 kunda, jami 3 marta eslatadi.
3. **Shartnoma raqami** — kimgadir SMS yetmagan bo'lsa, botga shartnoma raqamini yuborishni ayting (telefon oxirgi 4 raqami so'raladi).
4. **E'lon** — ichki guruhga/ota-onalar guruhiga bot manzilini tashlab, shartnoma raqami bilan ulanishni tushuntiring.

«Talabalar» tabida har talaba uchun holat ko'rinadi: ulangan (o'quvchi/vasiy), taklif yuborilgan, yuborilmagan; filtr — ulanmaganlar. «Umumiy»da «Faol talabalar ulangan» ko'rsatkichi (necha foiz).

## 4-bosqich: tamomlash/to'xtatish so'rovnomasi

Shartnomaga tugash sanasi kiritilgach, **ertasi kuni 10:00 dan 20:00 gacha** botga ulangan o'quvchi va vasiylarga bot so'rovnoma yuboradi (shartnoma tugaganiga 14 kundan oshmagan bo'lsa; talaba keyin ulansa ham shu oynada yuboriladi). Har shartnomaga bitta so'rovnoma; javobni birinchi javob bergan akkaunt tugatadi.

- **Oqim:** shartnomadagi sabab «Kursni tamomladi» bo'lsa — *tamomlaganlarga*, boshqa sabab bo'lsa — *to'xtatganlarga* savollari. Standart savollar:
  - to'xtatganlarga: nima uchun to'xtatdingiz (variantlar + «Boshqa (yozaman)»), ustozni baholash (1–5), qaytasizmi, fikr-taklif;
  - tamomlaganlarga: kursni baholash, ustozni baholash, do'stlarga tavsiya qilasizmi, boshqa kursni davom ettirasizmi, fikr-taklif.
- Har savolni o'tkazib yuborish mumkin. Tanlov savolida tugma bosiladi yoki o'zi yozadi, matnli savolda yozib yuboradi.
- **Bosh menejer savollarni o'zgartiradi:** Telegram bot → **Savollar** (qo'shish, tahrirlash, tartib, o'chirish, nofaol qilish; turi — tanlov/baho/matn; kimga — hammaga/tamomlaganlarga/to'xtatganlarga). O'zgarish faqat keyingi so'rovnomalarga ta'sir qiladi. Filial menejeri, administrator tahrirlay oladi, yangi savolni faqat Admin/Bosh menejer qo'shadi.
- **Javoblar:** Telegram bot → **Ketish so'rovnomasi** — yuborilgan/javob bergan soni, talaba aytgan sabab va shartnomada kiritilgan sabab yonma-yon, baholar o'rtachasi, har talaba javoblari. Javob kelganda Bosh menejerga Telegram xabar boradi («Telegram» oynasida o'chirib qo'yish mumkin).
- Hali botga ulanmagan talabaga so'rovnoma yuborilmaydi.

## 5-bosqich: tavsiya bonusi

Lid botda «Do'stlar (o'qiydi)» (yoki «tanish», «tavsiya») manbasini tanlab do'stining ismini yozgan bo'lsa, u **Telegram bot → Tavsiyalar** da ko'rinadi. Tavsiya qiluvchi aniqlangan bo'lsa («Kutilmoqda»), lid o'qishni boshlab to'lov qilganda bonus **avtomatik** beriladi.

**Shart** (Telegram bot → Sozlamalar, filial bo'yicha):
- lidning haqiqiy to'lovlari (naqd yoki tasdiqlangan naqdsiz) **yig'indisi** kurs oylik narxining kamida **50%** i (o'zgartiriladi). Naqdsiz to'lov tasdiqlanmaguncha hisobga olinmaydi, tasdiqlansa — shu zahoti tekshiriladi;
- tavsiya qiluvchining **faol (Pullik) shartnomasi** bor.

**Bonus:** standart **75 000 so'm** (sozlanadi; 0 — bonus o'chiq). Tavsiya qiluvchining shartnomasiga «Tavsiya bonusi» chegirmasi yoziladi (to'lov summasi 0, chegirma = bonus; tasdiqlangan holda). Natijada uning shartnoma balansi va «To'lovga tavsiya» hisobi shuncha kamayadi, ya'ni keyingi to'lovda shuncha kam to'laydi. G'azna harakati yo'q. Bu yozuv To'lovlar ro'yxatida ham, o'quvchi/vasiy botida ham («🎁 chegirma») ko'rinadi.
- Har tavsiyaga bir marta (holat «Berildi»).
- Tavsiya qiluvchi botga ulangan bo'lsa, unga «🎁 Tabriklaymiz!» xabari boradi (do'sti ismi va summa). Bosh menejerga ham Telegram xabar boradi.
- Tavsiya qiluvchining faol shartnomasi bo'lmasa — holat «Rad etildi», izohda sababi, Bosh menejerga xabar (qo'lda hal qilinadi).
- «Aniqlanmagan» tavsiyani talabaga bog'lasangiz va lid allaqachon yetarli to'lagan bo'lsa, bonus darrov beriladi. «Rad etish» bonusni to'xtatadi.
- Bir odam nechta do'stni tavsiya qilsa ham, har biri uchun bonus beriladi (cheklov yo'q).

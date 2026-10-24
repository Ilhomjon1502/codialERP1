# Mijozlar boti (o'quvchi va vasiylar) — 1- va 2-bosqich

O'quvchilar va ota-onalar uchun **alohida Telegram bot**. Xodimlar botidan (`@bildirishnomaERP1bot`) farqli — alohida token.
Bu bosqichda: ulanish (SMS'dagi kod), «Codialni qayerdan topdingiz?» so'rovi, tavsiya qiluvchi (tanish) ismi, Bosh menejer uchun «Telegram bot» bo'limi.
Keyingi bosqichlar: to'lov va davomat kabineti (B3), tamomlash so'rovnomasi (B4), tavsiya bonusi (B5).

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

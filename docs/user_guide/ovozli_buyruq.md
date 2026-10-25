# Telegram botda ovozli buyruqlar (Bosh menejer)

Bosh menejer xodimlar botiga (Codial ERP boti) **ovozli** yoki **yozma** xabar yuboradi. Bot xabarni tushunib, ikki xil ishlaydi:

| Nima deysiz | Bot nima qiladi |
|---|---|
| **Savol** — «Bu oy qancha xarajat bo'ldi?», «Bosh g'aznada qancha pul bor?», «Qarzdorlar ro'yxati» | Darhol javob beradi (saytdagi AI yordamchi orqali). Tasdiq so'ramaydi, chunki hech narsa o'zgarmaydi |
| **Amal yoki topshiriq** | **Yozma tasdiq kartasi** chiqaradi. «✅ Tasdiqlash» bosilmaguncha hech narsa yozilmaydi |

Bitta xabarda bir nechta narsa aytsangiz bo'ladi, masalan: «Internetga 300 ming, ijaraga 2 million to'ladim, Ilhomjon 500 ming olib ketdi».

## Qanday amallar ishlaydi

| Amal | Misol |
|---|---|
| Xarajat | «Bugun internetga 300 ming to'ladim, naqd» · «Sentyabr uchun kommunal 450 ming, kartadan» |
| Tashqi pul oqimi (kreditorlar) | «MNSH Ilhomjon 2 million olib ketdi» (g'aznadan chiqdi) · «Ilhomjon 5 million qo'ydi» (g'aznaga kirdi) |
| Ichki o'tkazmalarni tasdiqlash | «O'tkazmalarni tasdiqla» · «Emiratdan kelgan 500 minglik o'tkazmani tasdiqla» |
| Naqdsiz to'lov va chegirmani tasdiqlash | «Karta to'lovlarini tasdiqla» · «Ali Valiyevning chegirmasini tasdiqla» |
| To'lovni o'zgartirish | «Ali Valiyevning bugungi to'lovini 350 ming qil» · «… to'lov turini karta qil» |
| Oylik berish | «Akbarxo'jaga sentyabr oyligidan 1 million berdim, naqd» |
| Oylik belgilash: bonus, jarima, oylik | «Akbarxo'jaga 100 ming bonus» (qo'shiladi) · «Bonusi 300 ming bo'lsin» (aniq qiymat) · «50 ming jarima yoz» |
| Topshiriq | «Akbarxo'jaga ertaga soat 12 gacha xonani tozalashni topshir» |
| Topshiriqni yopish, bekor qilish, muddatini o'zgartirish | «Akbarxo'janing xona tozalash topshirig'i bajarildi» · «… muddatini juma kuniga surib qo'y» |
| Yangi to'lov | «Ali Valiyev 400 ming naqd to'ladi» · «… 50 ming rag'batlantiruvchi chegirma bilan» |
| Ichki o'tkazma | «Emiratdan Bosh g'aznaga 2 million o'tkaz» |
| Pul ayirboshlash | «Bosh g'aznada kartadagi 1 millionni naqdga yechdim, 990 ming chiqdi» |
| **O'chirish** (xarajat, to'lov, kreditor amali, oylik berish, o'tkazma, ayirboshlash) | «Xo'jalik xarajatlariga yozilgan 192 000 karta xarajatini o'chir» · «Oxirgi kiritgan xarajatimni o'chir» |
| **O'zgartirish** (xarajat, to'lov, kreditor amali, oylik berish, o'tkazma) | «Internet 300 ming emas 350 ming» · «Kecha MNSH olgan 2 millionni 2,5 million qil» · «Konstanta xarajatini kantselyariyaga o'tkaz» |

Mavjud yozuvni bot sana, summa, kategoriya, nom, g'azna, kreditor, xodim yoki o'quvchi bo'yicha qidiradi (oxirgi 90 kun, sana aytilsa — shu kun). Bir nechta yozuv mos kelsa, kartada tanlash tugmalari chiqadi. Kreditor amali saytdagidek o'zgartiriladi: eskisi o'chiriladi va yangisi kiritiladi. O'chirilgan yozuv bazada arxivda qoladi, g'azna qoldig'i esa qaytadi.

### Lidlar, shartnomalar, davomat

| Amal | Misol |
|---|---|
| Yangi lid | «Yangi lid: Jasur Toshev, 90 777 66 55 va 91 123 45 67, Instagramdan, Frontendga» (2 ta telefon majburiy — saytdagi qoida) |
| Lid holati, qayta bog'lanish, guruh, sinov darsi | «Jasur Toshevni qayta bog'lanishga, ertaga soat 10 da» · «… Frontend 3 ga sinov darsiga yozildi, 28-oktabr» |
| Lidga izoh | «Jasurga izoh: kechqurun qulay ekan» |
| Lidni o'chirish | «907776655 raqamli lidni o'chir» |
| Shartnoma tuzish | «Sardor Karimovga Frontend 3 guruhiga shartnoma tuz» — lid bo'lsa, holati «5. O'qishni boshladi» ga o'tadi |
| Shartnomani to'xtatish | «Sardorning shartnomasini to'xtat, moliyaviy qiyinchilik» (sabab aytilmasa — tugma bilan so'raydi) |
| Boshqa guruhga o'tkazish, qayta faollashtirish | «Alini Frontend 4 ga o'tkaz» · «Alining shartnomasini qayta faollashtir» |
| Davomat | «Frontend 3 da bugun hamma keldi, faqat Vali Aliyev kelmadi» · «… Ali sababli, kasal» (sababli bo'lsa sabab majburiy) |
| Kelmagan bilan bog'lanish | «Vali bilan gaplashdim, kasal ekan» |

O'quvchi, lid va shartnoma ism yoki telefon raqami bo'yicha topiladi. Ism aynan mos kelsa, o'xshash ismlardan ustun turadi. Guruh «Kurs raqam» ko'rinishida aytiladi, masalan «Frontend 3».

Hali qila olmaydiganlari: talaba ma'lumotlarini (sharif, tug'ilgan sana, vasiy) to'ldirish, guruh ochish, sozlamalar. Bular uchun saytdan foydalaning. Bunday buyruq bersangiz, bot qila oladigan ishlar ro'yxatini ko'rsatadi.

## Tasdiq kartasi

```
🎙 «Bugun internetga 300 ming to'ladim, naqd»

1) 💸 Xarajat
   Kategoriya: Internet
   Nomi: Internet
   Summa: 300 000 so'm
   G'azna: Emirat g'azna (naqd)
   Sana: 25.10.2026

Tasdiqlaysizmi?
[✅ Tasdiqlash] [✏️ Tuzatish] [❌ Bekor]
```

- **✅ Tasdiqlash** — amal bajariladi. Kartada natija chiqadi: «✅ Xarajat saqlandi» yoki xato sababi (masalan «G'aznada X so'm pul bor»).
- **✏️ Tuzatish** — bot «Nimani o'zgartirish kerak?» deydi. Keyin ovoz yoki matn bilan yozing, masalan «summasi 350 ming» yoki «kartadan». Yangi karta chiqadi, eskisi yopiladi. Kartaga Telegram'da **javob (reply)** qilib yozsangiz ham tuzatish bo'ladi.
- **❌ Bekor** — hech narsa yozilmaydi.
- Nom noaniq bo'lsa (masalan ikkita o'xshash g'azna yoki xodim, yoki o'quvchining bir nechta to'lovi), kartada **tanlash tugmalari** chiqadi. Tanlaganingizdan keyin «✅ Tasdiqlash» paydo bo'ladi.
- Kartani **30 daqiqa** ichida tasdiqlang, keyin u eskiradi.
- Tugmani ikki marta bossangiz, amal ikki marta yozilmaydi.

## Standart qiymatlar

- **Sana** aytilmasa — xabar yozilgan kun. Telegram'dagi saqlangan xabarlardan eski ovozni **forward** qilsangiz, ovoz yozilgan kun olinadi. «Kecha», «dushanba kuni» kabi so'zlar ham shu kunga nisbatan tushuniladi. Sana bugun bo'lmasa, kartada ⚠️ belgisi chiqadi.
- **Pul turi** aytilmasa — naqd.
- **G'azna** aytilmasa: naqd pul — filialning standart g'aznasi (Emirat g'azna), karta va bank — naqdsiz to'lovlar g'aznasi (Bosh g'azna).
- **Topshiriq muddati** aytilmasa — bugun soat 18:00 (kech bo'lsa ertaga 18:00). Kartada «(standart)» deb yoziladi.
- **Kreditor**: «olib ketdi», «qaytardik» — pul g'aznadan chiqdi (+). «Qo'ydi», «qarz oldik» — pul g'aznaga kirdi (−). Kartada qaysi tomon ekani va kreditor haqqi «oldin → keyin» ko'rinishida chiqadi. Tomoni aniq aytilmasa, bot tugma bilan so'raydi.

## Qoidalar va xavfsizlik

- Faqat **Bosh menejer** roli ishlatadi (buyurtmachi qarori, 2026-10-25). Boshqa xodim ovoz yuborsa, bot «faqat Bosh menejer uchun» deb javob beradi va tugmalarni ham bosa olmaydi.
- Hamma tekshiruvlar saytdagidek ishlaydi: ruxsatlar, g'azna qoldig'i, chegirma limiti, o'tkazmani kim tasdiqlashi.
- **Audit tarixida** shu amal yonida «🎙 Telegram ovozli buyruq: «…»» belgisi va ovoz matni saqlanadi.
- Ovoz va ma'lumotnoma nomlari (kategoriyalar, g'aznalar, kreditorlar, xodimlar) Gemini'ga boradi. Ovozda o'quvchi ismi aytilsa, u ham boradi (buyurtmachi ruxsati). Savollarga javob saytdagi AI yordamchi orqali olinadi: natija qatorlari Gemini'ga yuborilmaydi, faqat sizning Telegram chatingizga keladi.
- Kunlik limit — 150 ta buyruq. Ovozli xabar 10 daqiqagacha bo'lishi kerak. Savollar saytdagi AI yordamchining kunlik limitiga ham kiradi.
- `/start` va `/stop` buyruqlari avvalgidek ishlaydi.

## Dasturchi uchun

- Kod `backend/apps/voice/`:
  - `parser.py` — Gemini so'rovi: ovoz `inline_data` sifatida, javob JSON bandlar;
  - `actions.py` — har bir band turi uchun moslash (`r_*`) va bajarish (`x_*`); bajarish mavjud servislar orqali;
  - `match.py` — nomlarni moslash;
  - `services.py` — bot oqimi va tugmalar `vc:ok|no|ed|pk`;
  - `models.VoiceCommand` — buyruqlar jurnali.
- Bot `run_bot` shaxsiy chatdagi xabarni avval `voice.handle_update` ga beradi.
- Yangi amal turini qo'shish:
  1. `actions.HANDLERS` ga `(resolve, execute)` juftini qo'shing;
  2. `parser.SCHEMA` ga band tavsifini yozing;
  3. `tests/test_voice.py` ga test qo'shing.

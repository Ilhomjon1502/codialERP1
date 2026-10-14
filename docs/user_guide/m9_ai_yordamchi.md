# AI yordamchi (M9)

Faqat **Bosh menejer** uchun. Menyu → **AI yordamchi**.

## Sozlash (bir marta, administrator)

1. https://aistudio.google.com/apikey → Google akkaunt bilan kiring → **Create API key** → kalitni nusxalang.
2. Serverda: `bash /srv/codial-test/deploy/set-ai.sh` → kalitni qo'ying (ekranda ko'rinmaydi). Skript kalitni Google'da tekshiradi, mos Gemini modelini tanlaydi va saytni qayta ishga tushiradi.
   Kalitni chatga yoki boshqa joyga yozmang. Kalit oshkor bo'lib qolsa — AI Studio'da o'chirib, yangisini yarating va skriptni qayta ishga tushiring.

## Qanday ishlaydi

1. Savolni o'zbekcha yozasiz. Masalan: «O'tgan oyda Instagram'dan kelgan lidlar konversiyasi qancha?», «Qaysi guruhda qarzdorlik eng ko'p?», «Oxirgi 6 oyda foyda oyma-oy».
2. Gemini'ga **faqat savolingiz** va jadvallar **tuzilmasi** (ustun nomlari va tavsiflari) boradi. U SQL so'rovini yozadi.
3. Server SQL'ni tekshiradi:
   - faqat o'qish;
   - faqat hisobot ko'rinishlari (`analytics_*`);
   - ko'pi bilan 500 qator;
   - 5 soniya vaqt chegarasi.

   Shundan keyin so'rovni bajaradi.
4. Natija — jadval va diagramma — **faqat sizning ekraningizda** ko'rinadi. Unda talaba ismlari va telefonlar ham bo'lishi mumkin. Bu ma'lumotlar Gemini'ga yuborilmaydi.
5. **Tahlil** tugmasi Gemini'dan qisqa xulosa so'raydi:
   - natijada shaxsiy ma'lumot (ism, telefon, tug'ilgan sana) bo'lmasa, natija jadvali (40 qatorgacha) yuboriladi;
   - aks holda faqat yig'ma raqamlar (qatorlar soni, yig'indi, o'rtacha) yuboriladi.

Diqqat: savolga talaba ismini yozsangiz, savol matni Gemini'ga boradi.

## Qulayliklar

- **Oxirgi savollar** (chapda): bosilsa, saqlangan SQL Gemini'siz qayta bajariladi. Limitga kirmaydi, ma'lumot yangilanadi.
- Davomiy savol: «endi o'tgan oy uchun» — bugungi oxirgi 3 ta savol kontekst sifatida hisobga olinadi. Ularning faqat matni va SQL'i yuboriladi, natijalari yuborilmaydi.
- **CSV yuklash** — natijani Excel'da ochish uchun.
- «SQL» bo'limini ochib, so'rov qanday yozilganini ko'rish mumkin.

## Cheklovlar

- Kuniga 50 ta Gemini so'rovi (`AI_DAILY_LIMIT`). Savol ham, tahlil ham hisoblanadi.
- Gemini bepul tarifida Google'ning o'z limitlari bor. «Limit tugadi (429)» chiqsa — biroz kuting.
- AI xato SQL yozsa, server xato matnini Gemini'ga qaytarib, bir marta qayta so'raydi.
- Natija noto'g'ri tuyulsa, «SQL» bo'limida shartni tekshiring yoki savolni aniqroq yozing. Masalan, yil va oyni ayting, «faol talabalar» deb yozing.

## Texnik

- Kod: `backend/apps/ai_assistant/`.
  - `analytics.py` — view'lar va ularning tavsifi;
  - `guard.py` — SQL tekshiruvi va xavfsiz bajarish;
  - `providers.py` — Gemini, Anthropic, OpenAI;
  - `services.py` — oqim va prompt.
- View'lar har `migrate` da qayta yaratiladi. Qo'lda: `python manage.py ai_views`.
- PostgreSQL'da so'rov `codial_ai` roli bilan bajariladi: u faqat `analytics_*` view'larni o'qiy oladi, tranzaksiya READ ONLY.
- Provayderni almashtirish: `.env` da `AI_PROVIDER=anthropic|openai`, `AI_API_KEY`, ixtiyoriy `AI_MODEL`.
- Jurnal: Django admin → «AI so'rovlari». Unda savol, SQL, natija hajmi va vaqt yoziladi; natija qatorlari saqlanmaydi.

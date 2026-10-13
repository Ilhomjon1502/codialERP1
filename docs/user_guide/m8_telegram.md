# Telegram bot (M8)

## Sozlash (bir marta, administrator)

1. Telegram'da **@BotFather** → `/newbot` → nom (masalan «Codial ERP») va username (`..._bot` bilan tugaydi) → bot **token** beradi.
2. Serverda: `bash /srv/codial-test/deploy/set-telegram.sh` → tokenni qo'ying (ekranda qolmaydi). Skript tokenni tekshiradi va botni ishga tushiradi.
   Tokenni chatga yoki boshqa joyga yozmang.

## Xodim akkauntini bog'lash

Tizimda o'ng yuqoridagi ismingiz → **✈️ Telegram** → «bog'lash havolasi»ni bosing (yoki botga oynadagi kodni yuboring). Bot «✅ Bog'landi» deydi.
Kod bir martalik. Uzish — shu oynada «Bog'lanishni uzish» yoki botga `/stop`.

## Qaysi xabarlar keladi

| Xabar | Kimga |
|---|---|
| Yangi lid | Filial administratorlari (Administrator, Administrator+Hisobchi) |
| Tasdiq kutayotgan chegirma yoki naqdsiz to'lov | Bosh menejer, Filial menejeri |
| Tasdiq kutayotgan o'tkazma | Qabul qiluvchi g'azna mas'ullari |
| Qoldirilgan dars so'rovi («Darsni yetkazdim») | Bosh menejer, Filial menejeri, administratorlar |
| Dars boshlanganiga 30 daqiqa bo'ldi, davomat olinmagan | Guruh ustozi va administratorlar (guruhga kuniga bir marta) |
| Kunlik hisobot (har kuni 20:00): to'lovlar, yangi lidlar, yangi shartnomalar, kelmaganlar, g'azna qoldiqlari | Bosh menejer |

«✈️ Telegram» oynasida har bir xabar turini o'chirib qo'yish mumkin.

## Texnik

Xabar avval bazadagi navbatga yoziladi, `bot` jarayoni har ~20 soniyada yuboradi (Telegram ishlamasa 5 marta qayta urinadi).
Davomat eslatmasi — cron har 10 daqiqada (`notify_attendance`), kechikish `.env` dagi `TELEGRAM_ATTENDANCE_DELAY_MIN` (standart 30).
Kunlik hisobot — cron 20:00 (`daily_report`). Bot xotirasi 200 MB bilan cheklangan.

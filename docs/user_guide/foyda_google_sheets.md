# Foyda → «Hisobot olish» (Google Sheets)

**Kim ko'radi:** faqat Admin va Bosh menejer (Foyda (oyma-oy) sahifasi, o'ng yuqorida).

## Qanday ishlaydi
1. **Foyda (oyma-oy)** → **Hisobot olish** → oyni tanlang (standart — joriy oy) → **Hisobot olish**.
2. Tizim Google Sheets'dagi **bitta doimiy faylga** shu oy uchun varaq (`oktabr 2026`) yaratadi, tayyor bo'lgach havola chiqadi. Har oy yangi varaq qo'shiladi, eskilari saqlanadi.
3. Joriy oy tugamagan bo'lsa, varaq sarlavhasida «hozirgacha (sana holatiga, oy tugamagan)» yoziladi. Tugma qayta bosilsa varaq yangilanadi.

## Varaq tuzilishi (namuna «Codial moliyaviy hisobot.xlsx» dagidek)
| Qism | Qayerdan |
|---|---|
| **Tushum** | oy ichidagi to'lovlar (sana bo'yicha) — Foyda sahifasi bilan bir xil |
| **Oyliklar → Ustozlar / Xodimlar** | oylik belgilashdagi hisoblangan «Jami» (jarima ayirilgan). Ustoz, Ustoz+Yordamchi va Yordamchi rollari — Ustozlar, qolganlari — Xodimlar |
| **Xarajatlar** | «Xarajat» turidagi kategoriyalar (hisob davri bo'yicha); qator tartibi: Ijara, Internet, Komunal, Marketing… Har bir summa katagida **izoh (note)** bor: sana, nomi, soni × narxi va xarajat izohi |
| **Foyda** | Tushum − ustozlar − xodimlar − xarajatlar |
| **Foyda taqsimoti** | MNSH 75%, Ilhomjon 25% |
| **Olingan pullar** | Kreditorlar bo'limidagi MNSH va Ilhomjon amallari: olingan (−) minus qaytarilgan (+) |
| **Avvalgi oyda** (P ustuni) | oldingi oy varag'idagi foizlar (oldingi oy varag'i bo'lmasa — bo'sh) |

Yig'indilar va foizlar Sheets **formulasi** bo'lib qoladi: raqamni qo'lda o'zgartirsangiz, jami o'zi hisoblanadi.

## Qo'lda yoziladigan joylar (tizim tegmaydi)
- **«avvalgi oydan»** katagi (O16, O17) — o'zingiz yozasiz; «Oy yakunida» formulasi shuni hisobga oladi.
- Chap/o'ng chekkadagi ustunlarga (A, B, Q va undan keyingi) yozgan izohlaringiz.

Qayta bosilganda C:P oralig'idagi raqamlar tizim ma'lumoti bilan **qayta yoziladi** (qo'lda o'zgartirgan raqam o'chadi).

## Sozlash (bir marta)
Google Cloud'da service account va bo'sh Sheets fayl tayyorlanadi, fayl service account pochtasiga «Editor» qilib ulashiladi. Keyin kalit serverga yuboriladi:

```bash
scp -i ~/.ssh/codial_hetzner "C:\Users\...\Downloads\codialerp1-XXXX.json" root@77.42.9.23:/root/google.json
ssh -i ~/.ssh/codial_hetzner root@77.42.9.23
bash /srv/codial-test/deploy/set-google.sh
```

Skript JSON yo'lini va fayl havolasini so'raydi, kalitni `deploy/.env` ga yozadi, ulanishni tekshiradi (`python manage.py gsheets_check`) va serverdagi JSON nusxani o'chiradi. Kalit chatga yoki git'ga tushmaydi.

## Xatolar
| Xabar | Sabab |
|---|---|
| «Google Sheets hali ulanmagan» | `set-google.sh` ishga tushirilmagan |
| «Google faylga ruxsat yo'q: … pochtasiga Editor qilib ulashing» | fayl service account bilan ulashilmagan |
| «Google Sheets API yoqilmagan» | Google Cloud'da API yoqilmagan (APIs & Services → Library) |
| «fayl topilmadi» | fayl ID'si noto'g'ri — `set-google.sh` ni qayta ishga tushiring |

Kod: `backend/apps/reports/sheet_report.py` (varaq tuzilishi), `gsheets.py` (Google API), `views.sheet` (`/api/v1/reports/sheet/`). Foyda taqsimoti nisbati — `settings.PROFIT_SHARE_HOLDERS`.

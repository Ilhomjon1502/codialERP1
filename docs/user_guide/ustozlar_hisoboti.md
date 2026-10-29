# Ustozlar ish sifati hisoboti (PDF)

Har oy **1-kuni 09:00** da Bosh menejerga xodimlar botida PDF keladi: o'tgan oyda **Ustoz** va **Ustoz+Yordamchi** rolidagi ustozlar qanday ishlagani. Hisobotga o'sha oyda guruhi bo'lgan ustozlar kiradi.

## Ichida nima bor

- Har ustozga 100 ballik baho: **A'lo** (80+), **Yaxshi** (55–79), **Qoniqarsiz** (55 dan past).
- 6 mezon:

  | Mezon | Ball | Nima hisoblanadi |
  |---|---|---|
  | Davomat intizomi | 25 | darslarning qanchasida hamma o'quvchi belgilangan (15) va davomat dars kuni kiritilganmi (10) |
  | O'quvchilar qatnashi | 20 | «Keldi» ulushi: 60% va past — 0, 90% va yuqori — to'liq |
  | O'quvchilarni saqlab qolish | 25 | kursni tamomlamay to'xtatganlar: 15% va ko'p — 0 |
  | Sinov darsidan shartnomaga | 15 | sinov darsiga kelgan lidlardan o'qishni boshlaganlar (60% — to'liq); sinov darsi bo'lmasa — 7,5 |
  | Guruhlar to'lishi | 10 | faol guruhlardagi o'quvchilar / xona sig'imi (85% — to'liq) |
  | Topshiriqlar | 5 | muddatida bajarilganlar |

- Davomat to'liq olinmagan bo'lsa, qatnash va saqlab qolish ballari davomat olingan darslar ulushiga ko'paytiriladi. Aks holda davomat olmagan ustoz ma'lumot yo'qligi uchun yuqori ball olib qolardi.
- Har ustozning yaxshi tomonlari, kamchiliklari (davomat olinmagan darslar ro'yxati bilan), tavsiyalar va guruhlari jadvali.

Ma'lumot faqat ERP'dan olinadi: dars sifatini (tushuntirish, metodika) ERP o'lchay olmaydi — uni darsni kuzatish va o'quvchi bahosi bilan to'ldirish kerak. Hisobotda talaba ismi va telefoni yo'q.

## Qo'lda olish

Serverda:

```bash
cd /srv/codial-test/deploy
docker compose --env-file .env exec -T web python manage.py teacher_report --month 2026-10 --send
```

- `--month YYYY-MM` — shu oy (standart — o'tgan oy);
- `--from` / `--to` — boshqa davr;
- `--send` — botga ulangan Bosh menejerga yuboradi;
- `--out fayl.pdf` — faylga saqlaydi.

Kod: `backend/apps/reports/teacher_report.py` (mezonlar va chegaralar — fayl boshida `CRITERIA` va `grade()`).

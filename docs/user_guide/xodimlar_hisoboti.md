# Xodimlar ish sifati hisoboti (PDF)

Har **dushanba 09:00** da Bosh menejerga xodimlar botida PDF keladi: o'tgan hafta (dushanba–yakshanba) **Administrator+Hisobchi** rolidagi xodimlar qanday ishlagani.

## Ichida nima bor

- Har xodimga 100 ballik baho: **A'lo** (80+), **Yaxshi** (55–79), **Qoniqarsiz** (55 dan past).
- 6 mezon:

  | Mezon | Ball | Nima hisoblanadi |
  |---|---|---|
  | Faollik | 10 | kuniga kamida 5 ta amal bo'lgan ish kunlari |
  | Sotuv | 25 | lidlar + 2 × shartnomalar |
  | To'lov va undirish | 20 | qabul qilingan to'lovlar, «To'lovga tavsiya»da belgilanganlar, eslatma SMS |
  | Topshiriqlar | 15 | muddatida bajarilganlar |
  | Ma'lumot sifati | 15 | lid izohlari, talabaning vasiysi, sinov darsi natijasi, lid holatini orqaga qaytarmaslik |
  | Kelmaganlar va qayta bog'lanish | 15 | kelmaganlar natijasi, «Qayta bog'lanish» lidlariga izoh va vaqt |

  Sotuv, to'lov va kuzatish ballari xodimlarning o'rtacha natijasiga nisbatan hisoblanadi.
- Kunlik faollik diagrammasi.
- Har xodimning yaxshi tomonlari, kamchiliklari va tavsiyalar.
- Jamoa ko'rsatkichlari: javobsiz qo'ng'iroqlar, kelmaganlar, «Qayta bog'lanish» lidlari. Qo'ng'iroqlar umumiy telefondan bo'lgani uchun ular xodimlarga bo'linmaydi.

Ma'lumot faqat ERP'dagi amallardan olinadi: ERP'ga yozilmagan ish (telefondagi yoki yuzma-yuz suhbat) hisobotda ko'rinmaydi. Hisobotda talaba ismi va telefoni yo'q.

## Qo'lda olish

Serverda:

```bash
cd /srv/codial-test/deploy
docker compose --env-file .env exec -T web python manage.py staff_report --from 2026-10-19 --to 2026-10-27 --send
```

- `--send` — botga ulangan Bosh menejerga yuboradi;
- `--out fayl.pdf` — faylga saqlaydi;
- sanalarsiz — kechagacha oxirgi 7 kun.

Kod: `backend/apps/reports/staff_report.py` (mezonlar va chegaralar — fayl boshida `CRITERIA`, `GRADES`).

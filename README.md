# Codial ERP

Codial IT o'quv markazi (Farg'ona) uchun boshqaruv tizimi. Hozirgi AppSheet ilovasi ("Codial 1.0") o'rniga tez va qulay veb-tizim qurilmoqda.

## Holat

| Bosqich | Holat |
|---|---|
| AppSheet tahlili, prototip va uning o'zgarishlari | ✅ tayyor, ma'qullangan |
| **M1 — asos**: server (Django + API), kirish va parol, rollar va ruxsatlar, Sozlamalar, Audit tarixi | ✅ https://erp.codialinfo.uz |
| **M2 — CRM**: lidlar (voronka, ro'yxat, statistika, kartochka, izohlar), talabalar va ota-onalar | ✅ |
| **M3 — O'quv jarayoni**: guruhlar, shartnomalar, qarzdorlar, davomat (olish, kelmaganlar, statistika, qoldirilgan darslar), qarz va KPI hisobi | ✅ |
| **M4 — Moliya**: to'lovlar (chegirma limiti, tasdiqlar, PDF chek), g'aznalar va pul harakatlari jurnali, o'tkazmalar, ayirboshlash, xarajatlar, kreditorlar, Tasdiqlashlar | ✅ |
| **M5 — Oyliklar**: KPI stavkalari, oylik belgilash, hisoblangan KPI (daraxt), oylik berish, xodim balansi | ✅ |
| **M6 — Qo'shimcha**: ustozni baholash, ota-onalar bilan aloqa, Excel (.xlsx) eksport. «Talaba vazifalari», «Baholash bo'limi» va «50% chegirmalar» — olib tashlangan | ✅ |
| **M7 — Hisobotlar**: bosh sahifa, foyda (oyma-oy), oylik statistika, sotuv voronkasi, birinchi to'lovchilar | ✅ |
| **M8 — Telegram bot**: akkaunt bog'lash, yangi lid, tasdiqlar, o'tkazma, qoldirilgan dars, davomat eslatmasi, kunlik hisobot | ✅ |
| **M9 — AI yordamchi** (Bosh menejer): savol → Gemini SQL yozadi → server tekshirib bajaradi → jadval va diagramma; ma'lumot Gemini'ga bormaydi | ✅ |
| **M10 — AppSheet'dan ko'chirish**: faol shartnomalar, talabalar, guruhlar, ustozlar (`import_appsheet`, avval sinov rejimi) | ✅ |
| M11: haqiqiy ishga tushirish (2026-11-01) — demo tozalash, o'tish kuni importi, xodimlarga taklif, monitoring | ⏳ kod tayyor |

Reja: [docs/architecture.md](docs/architecture.md). Texnik topshiriq: [CLAUDE.md](CLAUDE.md).

## Prototip (dizayn namunasi)

**https://ilhomjon1502.github.io/codialERP1/** — soxta ma'lumotlar, brauzerda ishlaydi. Haqiqiy tizim ekranlari shunday bo'ladi.

## Tuzilma

```
backend/    Django 5.2 + Django REST Framework (API: /api/v1/), testlar (pytest)
frontend/   Ma'qullangan prototip ekranlari, API'ga ulangan (HTML/CSS/JS, build yo'q)
deploy/     Docker Compose (PostgreSQL + Gunicorn), Nginx sozlamasi, zaxira skriptlari
docs/       Reja, qarorlar, serverga o'rnatish, foydalanuvchi qo'llanmasi
prototype/  GitHub Pages'dagi prototip (o'zgarmaydi)
```

## Kompyuterda ishga tushirish (dasturchi)

Talab: Python 3.12. Lokalda baza — SQLite (serverda PostgreSQL).

```bash
cd backend
py -3.12 -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_demo --password "Sinov-parol-123"
.venv/Scripts/python manage.py runserver 8000
```

http://localhost:8000 — kirish: demo xodim pochtasi (masalan `dilshod@codial.test` — Bosh menejer) va yuqoridagi parol. Xatlar (parol o'rnatish havolasi) lokalda server konsoliga chiqadi.

Qarz va KPI ni qo'lda qayta hisoblash: `.venv/Scripts/python manage.py recalculate --month 2026-10`.

Testlar va kod sifati:

```bash
cd backend
.venv/Scripts/python -m pytest
.venv/Scripts/ruff check .
```

Linux/macOS'da `.venv/Scripts/` o'rniga `.venv/bin/`.

## Serverga joylash

[docs/deploy_hetzner.md](docs/deploy_hetzner.md) — Hetzner VPS, test (`test.` subdomen) va asosiy muhit, SSL, zaxira, yangilash.

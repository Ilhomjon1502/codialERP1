# Codial ERP

Codial IT o'quv markazi (Farg'ona) uchun boshqaruv tizimi. Hozirgi AppSheet ilovasi ("Codial 1.0") o'rniga tez va qulay veb-tizim qurilmoqda.

## Holat

| Bosqich | Holat |
|---|---|
| AppSheet tahlili, prototip va uning o'zgarishlari | ✅ tayyor, ma'qullangan |
| **M1 — asos**: server (Django + API), kirish va parol, rollar va ruxsatlar, Sozlamalar, Audit tarixi | ✅ kod tayyor, serverga joylash kutilmoqda |
| M2–M7: CRM, o'quv jarayoni, moliya, oyliklar, qo'shimcha modullar, hisobotlar | ⏳ navbatda |
| M10–M11: AppSheet'dan ko'chirish va ishga tushirish | ⏳ |

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

Testlar va kod sifati:

```bash
cd backend
.venv/Scripts/python -m pytest
.venv/Scripts/ruff check .
```

Linux/macOS'da `.venv/Scripts/` o'rniga `.venv/bin/`.

## Serverga joylash

[docs/deploy_hetzner.md](docs/deploy_hetzner.md) — Hetzner VPS, test (`test.` subdomen) va asosiy muhit, SSL, zaxira, yangilash.

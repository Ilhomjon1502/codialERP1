# Codial ERP

Codial IT o'quv markazi (Farg'ona) uchun boshqaruv tizimi. Hozirgi AppSheet ilovasi ("Codial 1.0") o'rniga tez va qulay veb-tizim qurilmoqda.

## 👉 Prototipni ko'rish

**https://ilhomjon1502.github.io/codialERP1/**

Kirish sahifasida xodimni tanlang (parol kerak emas). O'ng yuqoridagi ismni bosib, boshqa rollar bilan ham kirib ko'ring: Bosh menejer, Administrator, Ustoz va boshqalar. Telefonda ham ochiladi.

> Bu — **prototip**: tizim qanday ko'rinishi va ishlashini ko'rsatadi. Ichidagi talabalar, to'lovlar va xodimlar **soxta (sinov) ma'lumotlar**. Siz kiritgan narsalar faqat sizning brauzeringizda saqlanadi.

## Loyiha holati

| Bosqich | Holat |
|---|---|
| AppSheet tizimini tahlil qilish | ✅ tayyor |
| Bosiladigan prototip (dizayn va jarayonlar) | ✅ tayyor, ma'qullangan |
| Prototipdagi kichik o'zgarishlar | ⏳ jarayonda |
| Haqiqiy tizim (Django + PostgreSQL) | ⏳ keyingi bosqich |

## Dasturchilar uchun

- To'liq texnik topshiriq va joriy holat: [CLAUDE.md](CLAUDE.md) (0-bo'lim va 20-bo'limdan boshlang).
- Prototip kodi: [prototype/](prototype/) — oddiy HTML/CSS/JS. Kompyuterda ochish:

```bash
python -m http.server 5510 --directory prototype
```

- AppSheet'ning texnik tavsifi: `codial_appdoc.json`.

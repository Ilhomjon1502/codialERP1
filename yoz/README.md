# Codial Yoz — klaviatura mashqi sayti

Mustaqil statik sayt (HTML/CSS/JS, framework va build yo'q). ERP'ga, botga va serverga ulanmaydi:
login yo'q, natijalar o'quvchi brauzerida (`localStorage`, kalit `codial-yoz-v1`). Reja: `docs/yoz_reja.md`.

## Ishga tushirish

```bash
python -m http.server 5520 --directory yoz
```

http://localhost:5520 (Claude Code'da: `.claude/launch.json` → `yoz`).

## Testlar

```bash
node --test yoz/tests/engine.test.js
```

Yozish mexanikasi (tezlik, aniqlik, pauza, yulduzlar), tugmalar xaritasi, har dars matni faqat ruxsat etilgan
harflardan iboratligi va hamma JS fayllar sintaksisi tekshiriladi.

## Fayllar

| Fayl | Nima |
|---|---|
| `assets/js/keys.js` | klaviatura qatorlari, barmoqlar va ranglari, belgi → tugma (+ qaysi Shift), apostrof turlari |
| `assets/js/engine.js` | `Y.Session` — bitta mashq: bosishlar, faol vaqt (10 s dan uzun pauza kirmaydi), natija; `Y.calc` — WPM, aniqlik, barqarorlik, yulduzlar |
| `assets/js/words_uz.js` | o'zbekcha so'zlar (lotin, `o'` `g'` oddiy apostrof bilan) |
| `assets/js/lessons.js` | bo'limlar va darslar (`Y.UNITS`, `Y.LESSONS`), `Y.makeText` — har urinishda yangi matn |
| `assets/js/store.js` | profillar, natijalar, seriya, faylga saqlash/yuklash |
| `assets/js/ui.js` | ekrandagi klaviatura, qo'llar (SVG), ovoz, grafiklar |
| `assets/js/app.js` | sahifalar: `#/` profil tanlash, `#/map` darslar, `#/l/<id>` dars, `#/me` natijalarim |

## Yangi dars yoki bo'lim qo'shish

`lessons.js` dagi `units` ro'yxatiga yozing. Yangi harflar uchun `trio('xy', <hamma ruxsat etilgan harflar>, [maqsad tezliklar])`
— tanishuv, mashq va (so'z yetarli bo'lsa) so'zlar darsini o'zi yasaydi. So'zlar `words_uz.js` dan avtomatik olinadi:
faqat o'rganilgan harflardan iborat so'zlar. O'zgarishdan keyin testlarni ishga tushiring va `index.html` dagi `?v=` ni oshiring.

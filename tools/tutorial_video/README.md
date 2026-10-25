# Yo'riqnoma videolari (Administrator+Hisobchi)

Tizimni o'rgatuvchi 14 ta video avtomatik yoziladi: brauzer (Playwright) haqiqiy bazaning **lokal nusxasida**
ishlaydi, kerakli joy to'q sariq bilan yoritiladi, pastda o'zbekcha yozuv, orqada o'zbekcha ovoz
(edge-tts, `uz-UZ-MadinaNeural`). Natija: `docs/video/NN_nom.mp4` + `.srt` (git'ga kirmaydi).

Tizim o'zgarsa — tegishli darsni qayta yozib oling (bir buyruq).

## Tuzilishi

| Fayl | Nima |
|---|---|
| `engine.py` | Dvigatel: brauzer, 30 kadr/s yozish (CDP screencast → ffmpeg), ovoz, yig'ish, `.srt` |
| `overlay.js` | Sahifa ustidagi qatlam: kursor, yoritish, yozuv, kartochkalar, soxta ro'yxat, telefon raqamini yashirish |
| `common.py` | Darslar ro'yxati, `lesson`, `outro`, selektor yordamchilari |
| `l01.py` … `l14.py` | Har bir dars ssenariysi (`L.say(matn, *amallar)`) |
| `make.py`, `run.sh` | Ishga tushirish |
| `setup_copy.py`, `make_link.py` | Nusxa bazada «Namuna Administrator» xodimi va parol havolasi |
| `sheet.sh` | Tekshiruv uchun kadrlar varag'i |

## Qayta yozib olish

1. **Nusxa baza** (haqiqiy tizimga tegilmaydi): serverdan `dumpdata` → alohida SQLite
   (`TV_COPY_DIR/copy.sqlite3`), `migrate` + `flush` + `loaddata`, keyin `setup_copy.py`
   (namuna xodim, parol `video_login.json` ga) va `pristine.sqlite3` nusxasi, so'ng `make_link.py`.
   Har bir dars boshida baza `pristine` holatiga qaytariladi.
2. **Lokal server**: `.claude/launch.json` dagi `video-copy` (8010-port; `DATABASE_URL` nusxaga,
   Telegram tokeni soxta — xabar yuborilmaydi). Video `http://erp.localhost:8010` dan yoziladi
   (`localhost` bo'lsa sarlavhada «test» yozuvi chiqadi).
3. Avval tezkor sinov: `bash run.sh check 05` — dars ovozsiz va kutishsiz o'tadi (1–2 daqiqa), barcha tugma va
   maydonlar topilishi tekshiriladi, oxirgi holat `out/check/05_fast_end.png` ga saqlanadi.
   Yozib olish: `bash run.sh rec 05` yoki `bash run.sh rec all`. Avval ovozlar tayyorlanadi
   (internet kerak), keyin dars real vaqtda yoziladi.
4. Tekshirish: `bash sheet.sh 05` → `out/check/05_sheet_*.jpg`; aniq qadamlar: `python moments.py 05 "matn bo'lagi"`.
5. To'liq darslik (bitta video): `TV_COPY_DIR=x .venv/Scripts/python combine.py` → `docs/video/Codial_ERP_toliq_darslik.mp4`
   (boblar bilan), `.srt` va `_boblar.txt` (YouTube tavsifi uchun vaqtlar). Biror dars qayta yozilsa — buni ham qayta ishga tushiring.

O'rnatish: `python -m venv .venv && .venv/Scripts/pip install edge-tts playwright imageio-ffmpeg pillow pypdfium2`
va `.venv/Scripts/python -m playwright install chromium`.

## Eslatmalar

- Ovozdagi talaffuz: `engine.SPEAK` (faqat ovozga ta'sir qiladi), apostrof `ʻ` ga o'giriladi.
- Telefon raqamlari videoda `90 123 •• ••` ko'rinishida yashiriladi (`overlay.js`, `PHONE`).
- PDF chek yangi oynada ochilmaydi — rasmga aylantirilib ko'rsatiladi (`L.show_pdf`).
- Nusxa bazada haqiqiy shaxsiy ma'lumot bor: ish tugagach nusxani o'chiring, videolarni faqat xodimlarga bering.

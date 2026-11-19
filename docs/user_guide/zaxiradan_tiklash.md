# Telegram zaxirasi va yangi serverda tiklash

Har kuni **00:00** da Bosh menejerning Telegramiga shifrlangan zaxira keladi. Server buzilsa, hujum bo'lsa yoki boshqa serverga
o'tish kerak bo'lsa, shu fayllardan tizim **kechagi holatida** qayta ko'tariladi.

## Nima keladi

| Fayl | Qachon | Ichida | Hajmi |
|---|---|---|---|
| `codial-zaxira-YYYYMMDD-HHMM.zip` | har kuni 00:00 | baza (`db.sql.gz`), sirlar (`env.backup` = `deploy/.env`), nginx sozlamalari, cron ro'yxati, `VERSION.txt` (qatorlar soni va kod versiyasi), `RESTORE.txt` | ~2 MB |
| `codial-media-YYYYMMDD-HHMM.zip` (kerak bo'lsa `.zip.001`, `.002` …) | yakshanba 00:05 | yuklangan fayllar: qo'ng'iroq yozuvlari, darslik fayllari | ~35 MB (45 MB dan oshsa bo'laklarga bo'linadi) |

- Zip'lar **AES-256 parol** bilan shifrlangan. Ochish: **7-Zip** (Windows'ning o'zi AES-zip'ni ochmaydi), `.001` bo'laklarni bir papkaga saqlab, birinchisini oching.
- Zaxira eng ko'pi bilan **24 soatlik** ma'lumotni yo'qotadi (00:00 dan keyin kiritilganini).
- Xato bo'lsa (baza dump bo'lmasa, Telegram'ga yuborilmasa) o'sha chatga «⚠️ zaxira YUBORILMADI» xabari keladi. **Xabar kelmasa ham signal:** server o'chgan bo'lishi mumkin — Telegramda kechagi zaxira borligini tekshirib turing.
- Haftada bir marta oxirgi zip'ni kompyuteringizga ham saqlab qo'ying (bot o'z xabarini 48 soat ichida o'chira oladi).

## Birinchi marta sozlash (bir marta, serverda)

```bash
bash /srv/codial-test/deploy/set-backup.sh
```

Skript: zip parolini so'raydi (Enter — tasodifiy kuchli parol yaratadi va **bir marta** ko'rsatadi), Bosh menejerning chat raqamini
o'zi topadi, sinov xabarini yuboradi, parolni `deploy/.env` ga (600 ruxsat) yozadi, cron qatorlarini qo'shadi va birinchi zaxirani yuborishni taklif qiladi.
**Parolni parol menejeriga saqlang — yo'qolsa zaxira hech kim tomonidan ochilmaydi.**

Parolni almashtirish: skriptni qayta ishga tushiring (eski zip'lar eski parol bilan ochiladi).

## Serverdagi hozirgi zaxira (o'zgarmagan)

`deploy/backup.sh` har kuni 03:15 da bazani `/srv/backups/codial-test/` ga yozadi (30 kun). U **shu serverning o'zida**: tez qayta tiklash uchun qulay,
lekin server yo'qolsa u ham yo'qoladi. Telegram nusxasi shuning uchun.

## Yangi serverda tiklash (taxminan 1–2 soat)

1. **Server tayyorlash:** Ubuntu 24.04, Docker va Compose, `git`, `nginx`, `certbot`, `p7zip-full` (`apt install`). Hetzner'da yangi server oching (Arm64 bo'lsa ham mos).
2. **Kodni olish:**
   ```bash
   git clone https://github.com/Ilhomjon1502/codialERP1.git /srv/codial-test
   ```
3. **Zaxirani ochish** (Telegramdan yuklab, serverga ko'chiring — `scp` yoki Telegram Desktop → fayl):
   ```bash
   7z x codial-zaxira-YYYYMMDD-0000.zip -o/srv/restore          # parol so'raydi
   7z x codial-media-YYYYMMDD-0005.zip.001 -o/srv/restore-media # ixtiyoriy, oxirgi haftalikni oling
   ```
4. **Tiklash:**
   ```bash
   bash /srv/codial-test/deploy/restore_full.sh /srv/restore /srv/restore-media
   ```
   Skript `.env` ni qo'yadi, bazani tiklaydi, yuklangan fayllarni joylaydi, `web`, `bot`, `clientbot` ni ishga tushiradi, sayt javobini
   kutadi va oxirida **qatorlar sonini** zaxiradagi `VERSION.txt` bilan yonma-yon chiqaradi — ular mos bo'lishi kerak.
5. **nginx, DNS, SSL:** skript oxirida chiqqan buyruqlar: `nginx/codial-erp` ni joyiga qo'yish, ahost.uz'da `erp` A yozuvini yangi IP'ga yo'naltirish, `certbot --nginx -d erp.codialinfo.uz`.
6. **Cron:** `/srv/restore/crontab.txt` dagi qatorlarni `crontab -e` ga qo'shing (monitoring, kunlik hisobot, zaxira). Telegram zaxirasi uchun `set-backup.sh` ni qayta ishga tushiring (yoki `.env` allaqachon parol bilan tiklangan, shunda faqat cron kerak).
7. **Tekshiruv:** https://erp.codialinfo.uz — kirish, bosh sahifa, bugungi davomat; Telegram botlar javob beradimi; Qo'ng'iroqlar → Qurilmalar (telefon o'zi qayta ulanadi: token bazada).

## Hujumdan keyin — majburiy

Eski server buzilgan bo'lsa, zaxiradagi **`.env` ham xavfsiz emas** deb hisoblang. Tiklagach darhol almashtiring:
Telegram tokenlari (@BotFather → /revoke), Gmail App password, Gemini kaliti, Google service account kaliti (`GOOGLE_*`), `SECRET_KEY` (hamma sessiyalar tugaydi — bu normal), `INBOX_SITE_KEY`; barcha xodimlar uchun parol o'rnatish havolalarini qayta yuboring.
Eski serverni o'chiring: ikkita server bir token bilan bot ishlatsa, xabarlar ikki barobar ketadi.

## Sinash

Zaxiraning ishonchliligi faqat tiklab ko'rilganda ma'lum. Loyiha ichida tiklash serverning o'zida **alohida vaqtinchalik nusxada** sinalgan (haqiqiy tizimga va botlarga tegmasdan) — sana va natija `docs/decisions.md` da.
Xohlagan payt takrorlash mumkin: `ENV_FILE=/yo'l/sinov.env RESTORE_SERVICES="web" bash deploy/restore_full.sh <papka>` (sinov `.env` da `ENV_NAME` va `WEB_PORT` boshqa bo'lsin; botlarni ishga tushirmang).

## Texnik

`deploy/backup_telegram.sh daily|media` (`BACKUP_DRY_RUN=1` — Telegram'ga yubormay sinash), `deploy/set-backup.sh`, `deploy/restore_full.sh`.
`.env` kalitlari: `BACKUP_ZIP_PASSWORD`, `BACKUP_TELEGRAM_CHAT`. Jurnal: `/var/log/codial-backup-telegram.log`.

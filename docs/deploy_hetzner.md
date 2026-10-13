# Hetzner serverga o'rnatish (test va asosiy muhit)

Bitta serverda ikkita muhit ishlaydi:

| Muhit | Manzil (namuna) | Papka | Port | Ma'lumot |
|---|---|---|---|---|
| Test | `test.codial.uz` | `/srv/codial-test` | 8001 | sinov (`seed_demo`) |
| Asosiy | `erp.codial.uz` | `/srv/codial-prod` | 8002 | haqiqiy (M10 importidan keyin) |

Har bir muhit: Docker'da **PostgreSQL + Django (Gunicorn)**. Serverning o'zida: **Nginx** (front-end fayllarini beradi va `/api/` ni Docker'ga yo'naltiradi) va **certbot** (bepul SSL).

> Akkaunt ochish, to'lov va DNS — buyurtmachi tomonidan qilinadi. Qolgan buyruqlarni dasturchi bajaradi.

## 0. Joriy holat (2026-10-12)

| | |
|---|---|
| Server | Hetzner Cloud **CAX11** (Arm64, 2 vCPU, 4 GB RAM, 40 GB), nomi `codial-1`, Helsinki, IP `77.42.9.23`, Ubuntu 24.04 |
| Kirish | `ssh -i ~/.ssh/codial_hetzner root@77.42.9.23` (faqat kalit; parol bilan kirish o'chirilgan) |
| Joriy muhit | **https://erp.codialinfo.uz** (2026-10-13 dan; DNS A `erp` → `77.42.9.23`, ahost.uz), Nginx sayti `/etc/nginx/sites-available/codial-erp`, Let's Encrypt SSL (certbot.timer yangilaydi). Papka `/srv/codial-test`, `ENV_NAME=test`, hozircha sinov ma'lumotlari. Zaxira manzil: https://test.77-42-9-23.sslip.io (sayt `codial-test`) |
| Pochta | SMTP hali sozlanmagan: test muhitida xatlar `docker compose logs web` ga chiqadi (`EMAIL_BACKEND=console`) |
| Cron | test bazasi zaxirasi har kuni 03:15 (`/srv/backups/codial-test`), oydagi dars soni takliflari har oy 1-kuni 06:00 |
| Asosiy muhit | hali o'rnatilmagan (M11) |

Cost-Optimized x86 (CX23) o'rnatish paytida Yevropaning hech bir joyida bo'lmagani uchun Arm64 (CAX11) tanlandi. Docker obrazlari (python, postgres) Arm64'da ishlaydi.

Ubuntu 24.04 da SSH socket orqali ishga tushadi: `/etc/ssh/sshd_config.d/` dagi o'zgarish keyingi ulanishdan kuchga kiradi, `systemctl reload ssh` kerak emas.

## 1. Server va domen (buyurtmachi)

1. https://console.hetzner.cloud → yangi loyiha → **Add Server**:
   - Location: Falkenstein yoki Helsinki; Image: **Ubuntu 24.04**; Type: **CX22** (2 vCPU, 4 GB) yoki CX32;
   - SSH key: dasturchi bergan ochiq kalitni (`.pub`) qo'shing; Backups: yoqish tavsiya etiladi (+20%).
2. Server IP manzilini dasturchiga yuboring.
3. Domen boshqaruvida **A yozuvlar**: `test` → server IP, `erp` → server IP.

## 2. Serverni tayyorlash (bir marta)

```bash
ssh root@SERVER_IP
apt update && apt -y upgrade
apt -y install nginx certbot python3-certbot-nginx git ufw
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 'Nginx Full' && ufw --force enable
mkdir -p /srv/backups
```

## 3. Test muhitini o'rnatish

```bash
git clone https://github.com/Ilhomjon1502/codialERP1.git /srv/codial-test
cd /srv/codial-test/deploy
cp .env.example .env && nano .env        # SECRET_KEY, domen, POSTGRES_PASSWORD, pochta
docker compose --env-file .env up -d --build
docker compose --env-file .env exec web python manage.py seed_demo --password "SINOV_PAROLI"   # faqat test uchun
docker compose --env-file .env exec web python manage.py createsuperuser                       # Admin
```

Kalit yaratish: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.

Nginx va SSL:

```bash
cp /srv/codial-test/deploy/nginx/codial-test.conf /etc/nginx/sites-available/codial-test
ln -s /etc/nginx/sites-available/codial-test /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d test.codial.uz --redirect -m ADMIN_POCHTASI --agree-tos
```

Tekshirish: `https://test.codial.uz` ochiladi, kirish sahifasi chiqadi; `https://test.codial.uz/api/v1/auth/csrf/` → `{"ok": true}`.

## 4. Asosiy muhit (M11 da)

Xuddi shu qadamlar: papka `/srv/codial-prod`, `.env` da `ENV_NAME=prod`, `WEB_PORT=8002`, domen `erp.codial.uz`, Nginx faylida papka/port/domenni almashtiring. **`seed_demo` ishga tushirilmaydi** — ma'lumotlar M10 importi bilan kiritiladi.

## 5. Avtomatik vazifalar (cron)

`crontab -e`:

```
# Har kuni 03:15 — asosiy bazaning zaxirasi (30 kun saqlanadi)
15 3 * * *  /srv/codial-prod/deploy/backup.sh prod >> /var/log/codial-backup.log 2>&1
# Har oy 1-kuni 06:00 — oydagi dars soni bo'yicha takliflar
0 6 1 * *   cd /srv/codial-prod/deploy && docker compose --env-file .env exec -T web python manage.py propose_lesson_frequencies
0 6 1 * *   cd /srv/codial-test/deploy && docker compose --env-file .env exec -T web python manage.py propose_lesson_frequencies
```

Tashqi nusxa (tavsiya): Hetzner Storage Box yoki boshqa joyga `/srv/backups` ni kuniga bir marta ko'chirish.

## 6. Yangilash

```bash
cd /srv/codial-test && git pull
cd deploy && docker compose --env-file .env up -d --build    # migratsiyalar o'zi qo'llanadi
```

Front-end fayllari `git pull` bilan darhol yangilanadi (Nginx ularni papkadan beradi). Brauzer eski faylni ko'rsatmasligi uchun `frontend/index.html` dagi `?v=` raqami oshiriladi.

## 7. Zaxiradan tiklash

```bash
/srv/codial-prod/deploy/restore.sh prod /srv/backups/codial-prod/codial-prod-YYYYMMDD-HHMM.sql.gz
```

Tiklashni ishga tushirishdan oldin **bir marta test muhitida sinab ko'ring**.

## 8. Muammolar

| Belgi | Tekshirish |
|---|---|
| Sayt ochilmaydi | `systemctl status nginx`, `nginx -t`, DNS: `dig test.codial.uz` |
| 502 Bad Gateway | `docker compose --env-file .env ps` va `docker compose --env-file .env logs web --tail 100` |
| Kirishda "CSRF" xatosi | `.env` da `CSRF_TRUSTED_ORIGINS=https://domen` va `ALLOWED_HOSTS=domen` |
| SSL'dan oldin cheksiz yo'naltirish | avval certbot'ni ishga tushiring (prod sozlama HTTPS'ga yo'naltiradi) |
| Xat kelmaydi | `.env` dagi `EMAIL_*`; Gmail uchun "App password"; `logs web` da xato |

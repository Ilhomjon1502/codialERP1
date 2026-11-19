#!/bin/bash
# Codial ERP: Telegram zaxirasidan YANGI serverda to'liq tiklash (2026-11-19).
#
# Tayyorgarlik: serverda Docker o'rnatilgan, repo olingan (git clone … /srv/codial-test), Telegramdan kelgan zaxira zip'i
# parol bilan ochilgan (7z x codial-zaxira-….zip -o/srv/restore), yuklangan fayllar zip'i ham ochilgan bo'lsa (codial-media-….zip.001).
#
#   bash /srv/codial-test/deploy/restore_full.sh /srv/restore [/srv/restore-media]
#
#   1-argument — kunlik zaxira ochilgan papka (ichida db.sql.gz, env.backup, nginx/ …)
#   2-argument — ixtiyoriy: yuklangan fayllar ochilgan papka (media)
#
# Sinov uchun (haqiqiy tizimga tegmaslik): ENV_FILE=/yo'l/boshqa.env  va  RESTORE_SERVICES="web"  bering — ENV_NAME va WEB_PORT boshqa bo'lsin.
# DIQQAT: botlar bir xil token bilan ikki joyda bir vaqtda ishlamasligi kerak — eski server o'chiq ekaniga ishonch hosil qiling.
set -euo pipefail
SRC="${1:?Ishlatish: restore_full.sh <zaxira-papkasi> [media-papkasi]}"
MEDIA="${2:-}"
cd "$(dirname "$0")"
SERVICES="${RESTORE_SERVICES:-web bot clientbot}"

[ -f "$SRC/db.sql.gz" ] || { echo "Xato: $SRC/db.sql.gz topilmadi"; exit 1; }
[ -f "$SRC/env.backup" ] || { echo "Xato: $SRC/env.backup topilmadi"; exit 1; }
command -v docker > /dev/null || { echo "Docker o'rnatilmagan"; exit 1; }
gzip -t "$SRC/db.sql.gz" || { echo "Xato: baza fayli buzuq"; exit 1; }

# 1) Sirlar
if [ -n "${ENV_FILE:-}" ]; then
  ENVF="$ENV_FILE"
else
  ENVF=".env"
  if [ -f "$ENVF" ]; then
    read -r -p "deploy/.env allaqachon bor — zaxiradagi bilan almashtirilsinmi? [ha/yo'q] " ok
    [ "$ok" = "ha" ] || { echo "To'xtatildi."; exit 1; }
  fi
  cp "$SRC/env.backup" "$ENVF"
  chmod 600 "$ENVF"
fi
DC="docker compose --env-file $ENVF"
val() { grep -E "^$1=" "$ENVF" | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//;s/^"//;s/"$//'; }
PORT=$(val WEB_PORT); PORT=${PORT:-8001}
HOST=$(val ALLOWED_HOSTS | cut -d, -f1 | tr -d ' ')

# 2) Baza
echo "Baza ko'tarilmoqda…"
$DC up -d db > /dev/null < /dev/null
for i in $(seq 1 60); do
  $DC exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /dev/null > /dev/null 2>&1 && break
  sleep 2
  [ "$i" = 60 ] && { echo "Baza ishga tushmadi"; exit 1; }
done
# AI yordamchining o'qish roli bazaning ichida emas (klaster darajasida) — dump unga ruxsat beradi, shuning uchun u oldindan bo'lishi shart
# (yangi serverda bo'lmasa tiklash «role codial_ai does not exist» bilan to'xtaydi; 2026-11-19 sinovda topilgan)
$DC exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres' << 'SQL'
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'codial_ai') THEN CREATE ROLE codial_ai NOLOGIN; END IF; END $$;
SQL
echo "Baza tiklanmoqda…"
$DC exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"' < /dev/null
gunzip -c "$SRC/db.sql.gz" | $DC exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /dev/null

# 3) Yuklangan fayllar
if [ -n "$MEDIA" ]; then
  echo "Yuklangan fayllar joylanmoqda…"
  $DC create web > /dev/null < /dev/null
  $DC cp "$MEDIA/." web:/app/media/ < /dev/null
  $DC run --rm --no-deps -u root --entrypoint sh web -c 'chown -R app /app/media' > /dev/null < /dev/null
fi

# 4) Xizmatlar
echo "Xizmatlar ishga tushirilmoqda ($SERVICES)…"
$DC up -d --build $SERVICES < /dev/null

echo -n "Sayt javobini kutyapman"
OK=0
for i in $(seq 1 60); do
  if curl -fsS -m 5 -H "Host: $HOST" -H "X-Forwarded-Proto: https" "http://127.0.0.1:$PORT/api/v1/health/" > /dev/null 2>&1; then OK=1; break; fi
  echo -n "."; sleep 3
done
echo
[ "$OK" = 1 ] && echo "Sayt ishlayapti (127.0.0.1:$PORT)." || { echo "Sayt javob bermadi: $DC logs web --tail 80"; exit 1; }

# 5) Tekshiruv: qatorlar soni zaxiradagi VERSION.txt bilan bir xil bo'lishi kerak
echo
echo "--- Zaxira yaratilgan paytdagi qatorlar (VERSION.txt):"
sed -n '/qatorlar soni/,$p' "$SRC/VERSION.txt" 2> /dev/null | tail -n +2
echo "--- Hozir tiklangan bazada:"
$DC exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F " "' << 'SQL'
select 'foydalanuvchi', count(*) from accounts_user union all select 'talaba', count(*) from crm_student union all select 'lid', count(*) from crm_lead union all select 'shartnoma', count(*) from education_contract union all select 'davomat', count(*) from education_attendance union all select 'tolov', count(*) from finance_payment;
SQL

cat << EOF

Tayyor. Endi qo'lda:
  1. nginx:   cp $SRC/nginx/codial-erp /etc/nginx/sites-available/ && ln -s /etc/nginx/sites-available/codial-erp /etc/nginx/sites-enabled/ && nginx -t && nginx -s reload
  2. DNS:     erp.codialinfo.uz (A yozuvi) ni shu serverning IP manziliga yo'naltiring (ahost.uz)
  3. SSL:     certbot --nginx -d erp.codialinfo.uz
  4. cron:    $SRC/crontab.txt ichidagi qatorlarni ko'rib chiqing (crontab -e) — kunlik zaxira, hisobotlar, monitoring
  5. Xavfsizlik: eski server buzilgan bo'lsa — Telegram tokenlari (@BotFather), pochta App password, Gemini kaliti, SECRET_KEY va barcha xodim parollarini almashtiring
  6. Android qo'ng'iroq ilovasi domen o'zgarmasa o'zi ulanadi (token bazada); domen o'zgarsa qurilmani qayta ulang
EOF

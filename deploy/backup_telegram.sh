#!/bin/bash
# Codial ERP: shifrlangan zaxirani Telegram orqali Bosh menejerga yuborish (2026-11-19, buyurtmachi so'rovi).
#
#   daily — baza + .env + nginx sozlamalari + tiklash yo'riqnomasi (har kuni 00:00, ~2 MB)
#   media — yuklangan fayllar (qo'ng'iroq yozuvlari, darslik fayllari): yakshanba 00:05; 45 MB dan oshsa bo'laklarga bo'linadi
#
# crontab (server vaqti — Asia/Tashkent):
#   0 0 * * *  bash /srv/codial-test/deploy/backup_telegram.sh daily >> /var/log/codial-backup-telegram.log 2>&1
#   5 0 * * 0  bash /srv/codial-test/deploy/backup_telegram.sh media >> /var/log/codial-backup-telegram.log 2>&1
#
# Sozlash (bir marta, buyurtmachi o'zi): bash /srv/codial-test/deploy/set-backup.sh — zip paroli va chat raqamini .env ga yozadi.
# Tiklash: docs/user_guide/zaxiradan_tiklash.md va deploy/restore_full.sh.
# BACKUP_DRY_RUN=1 — Telegram'ga yubormaydi, natijani BACKUP_OUT papkasiga qo'yadi (sinov uchun; parol BACKUP_ZIP_PASSWORD dan olinadi).
set -uo pipefail
MODE="${1:-daily}"
cd "$(dirname "$0")" || exit 1
ROOT="$(dirname "$(pwd)")"
val() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//;s/^"//;s/"$//'; }
TOKEN=$(val TELEGRAM_BOT_TOKEN)
CHAT="${BACKUP_TELEGRAM_CHAT:-$(val BACKUP_TELEGRAM_CHAT)}"
PW="${BACKUP_ZIP_PASSWORD:-$(val BACKUP_ZIP_PASSWORD)}"
DRY="${BACKUP_DRY_RUN:-0}"
LIMIT=$((45 * 1024 * 1024))   # Telegram bot fayl chegarasi 50 MB; zaxira bilan
NOW=$(date '+%Y%m%d-%H%M')
HUMAN=$(date '+%d.%m.%Y %H:%M')

log() { echo "$(date '+%F %T') [$MODE] $*"; }
tg_msg() { [ -n "$TOKEN" ] && [ -n "$CHAT" ] || return 0; curl -s -m 20 "https://api.telegram.org/bot$TOKEN/sendMessage" -d chat_id="$CHAT" --data-urlencode text="$1" > /dev/null; }
fail() { log "XATO: $1"; [ "$DRY" = 1 ] || tg_msg "⚠️ Codial zaxirasi ($MODE, $HUMAN) YUBORILMADI: $1"; exit 1; }
size_h() { du -h "$1" | cut -f1; }

mkdir -p /srv/backups && chmod 700 /srv/backups
exec 9> /srv/backups/.telegram.lock
flock -n 9 || { log "oldingi zaxira hali tugamagan, o'tkazib yuborildi"; exit 0; }

[ "$MODE" = daily ] || [ "$MODE" = media ] || { echo "Ishlatish: $0 daily|media"; exit 2; }
command -v 7z > /dev/null || fail "7z o'rnatilmagan (apt-get install p7zip-full)"
[ "${#PW}" -ge 12 ] || fail "zip paroli sozlanmagan (bash deploy/set-backup.sh)"
if [ "$DRY" != 1 ]; then
  [ -n "$TOKEN" ] || fail "TELEGRAM_BOT_TOKEN yo'q"
  [ -n "$CHAT" ] || fail "BACKUP_TELEGRAM_CHAT sozlanmagan (bash deploy/set-backup.sh)"
fi

WORK=$(mktemp -d /srv/backups/.tg.XXXXXX) || fail "vaqtinchalik papka ochilmadi"
chmod 700 "$WORK"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/src" "$WORK/out"

# Zip (AES-256, parolli). Chegaradan katta bo'lsa — 44 MB li bo'laklar (.zip.001, .002 …; 7-Zip birinchisini ochsa, qolganlari o'zi ulanadi)
make_zip() {  # $1 — nom, $2 — papka, $3 — siqish darajasi
  local name="$1" dir="$2" lvl="${3:-3}"
  rm -f "$WORK/out/$name".zip*
  (cd "$dir" && 7z a -tzip -mem=AES256 "-mx=$lvl" "-p$PW" "$WORK/out/$name.zip" . > /dev/null) || return 1
  if [ "$(stat -c %s "$WORK/out/$name.zip")" -gt "$LIMIT" ]; then
    rm -f "$WORK/out/$name".zip*
    (cd "$dir" && 7z a -tzip -mem=AES256 "-mx=$lvl" -v44m "-p$PW" "$WORK/out/$name.zip" . > /dev/null) || return 1
  fi
  local first; first=$(ls "$WORK/out/$name".zip* | sort | head -1)
  7z t "-p$PW" "$first" > /dev/null || return 1   # butunligini tekshirish (parol ham to'g'ri ekanini tasdiqlaydi)
}

send_file() {  # $1 — fayl, $2 — izoh
  local r try
  for try in 1 2 3; do
    r=$(curl -s -m 600 -F chat_id="$CHAT" -F document=@"$1" -F caption="$2" "https://api.telegram.org/bot$TOKEN/sendDocument")
    echo "$r" | grep -q '"ok":true' && return 0
    log "Telegram javobi ($try/3): $(echo "$r" | cut -c1-200)"
    sleep 30
  done
  return 1
}

if [ "$MODE" = daily ]; then
  NAME="codial-zaxira-$NOW"
  S="$WORK/src"
  # 1) Baza. pg_dump tugaganini oxirgi qatordagi belgi bilan tekshiramiz (yarim fayl yuborilmasin)
  docker compose --env-file .env exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < /dev/null | gzip > "$S/db.sql.gz" \
    || fail "pg_dump ishlamadi"
  gzip -t "$S/db.sql.gz" || fail "baza fayli buzuq"
  [ "$(stat -c %s "$S/db.sql.gz")" -gt 50000 ] || fail "baza fayli juda kichik"
  END_TXT=$(zcat "$S/db.sql.gz" | tail -5)
  case "$END_TXT" in *"PostgreSQL database dump complete"*) ;; *) fail "pg_dump oxiriga yetmagan" ;; esac
  # 2) Sirlar va sozlamalar (Telegram'ga faqat shifrlangan zip ichida chiqadi)
  cp .env "$S/env.backup"
  mkdir -p "$S/nginx"
  cp -L /etc/nginx/sites-enabled/* "$S/nginx/" 2> /dev/null || true
  crontab -l > "$S/crontab.txt" 2> /dev/null || true
  # 3) Tekshiruv uchun qatorlar soni va versiya
  SQL="select 'foydalanuvchi', count(*) from accounts_user union all select 'talaba', count(*) from crm_student union all select 'lid', count(*) from crm_lead union all select 'shartnoma', count(*) from education_contract union all select 'davomat', count(*) from education_attendance union all select 'tolov', count(*) from finance_payment;"
  COUNTS=$(docker compose --env-file .env exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F " "' <<< "$SQL" 2> /dev/null || true)
  COMMIT=$(git -C "$ROOT" rev-parse HEAD 2> /dev/null || echo "?")
  {
    echo "Codial ERP zaxirasi"
    echo "Sana: $HUMAN (Asia/Tashkent)"
    echo "Server: $(hostname)"
    echo "Kod versiyasi (git): $COMMIT"
    echo "Repo: https://github.com/Ilhomjon1502/codialERP1"
    echo
    echo "Bazadagi qatorlar soni (tiklagandan keyin shular bilan solishtiring):"
    echo "$COUNTS"
  } > "$S/VERSION.txt"
  cat > "$S/RESTORE.txt" << 'EOF'
TIKLASH (qisqacha) — to'liq yo'riqnoma: repodagi docs/user_guide/zaxiradan_tiklash.md

1. Yangi Ubuntu serverda: Docker o'rnating, reponi oling:
     git clone https://github.com/Ilhomjon1502/codialERP1.git /srv/codial-test
2. Bu zipni parol bilan oching (7-Zip), papkani serverga ko'chiring, so'ng:
     bash /srv/codial-test/deploy/restore_full.sh /yo/l/ochilgan-papka [/yo/l/media-papkasi]
   (skript .env ni qo'yadi, bazani tiklaydi, xizmatlarni ishga tushiradi)
3. nginx/ papkasidagi sozlamani /etc/nginx/sites-available ga qo'ying, DNS'da erp.codialinfo.uz ni yangi IP'ga
   yo'naltiring, certbot bilan SSL oling.
4. Tiklagandan keyin xavfsizlik uchun kalitlarni (Telegram tokenlari, pochta paroli, Gemini kaliti, SECRET_KEY) almashtiring.
EOF
  make_zip "$NAME" "$S" 5 || fail "zip yaratilmadi"
  CAPTION="🗄 Codial zaxirasi · $HUMAN
Baza: $(size_h "$S/db.sql.gz") · kod: ${COMMIT:0:7}
Ochish: 7-Zip + zaxira paroli"
else
  NAME="codial-media-$NOW"
  S="$WORK/src"
  docker compose --env-file .env cp web:/app/media/. "$S/" > /dev/null 2>&1 || fail "media papkasi nusxalanmadi"
  FILES=$(find "$S" -type f | wc -l)
  [ "$FILES" -gt 0 ] || fail "media papkasi bo'sh"
  make_zip "$NAME" "$S" 1 || fail "media zip yaratilmadi"
  CAPTION="📎 Codial yuklangan fayllari · $HUMAN
$FILES ta fayl, asl hajmi $(du -sh "$S" | cut -f1)
Ochish: 7-Zip + zaxira paroli"
fi

mapfile -t PARTS < <(ls "$WORK/out/$NAME".zip* | sort)
TOTAL=$(du -ch "${PARTS[@]}" | tail -1 | cut -f1)
if [ "$DRY" = 1 ]; then
  OUTDIR="${BACKUP_OUT:-/srv/backups/dry-run}"
  mkdir -p "$OUTDIR" && cp "${PARTS[@]}" "$OUTDIR/"
  log "SINOV (Telegram'ga yuborilmadi): $OUTDIR ga qo'yildi — ${#PARTS[@]} fayl, $TOTAL"
  exit 0
fi
i=0
for f in "${PARTS[@]}"; do
  i=$((i + 1))
  cap="$CAPTION"
  [ "${#PARTS[@]}" -gt 1 ] && cap="$CAPTION
Qism $i/${#PARTS[@]} — hamma qismni bir papkaga saqlab, .001 ni oching"
  send_file "$f" "$cap" || fail "Telegram'ga yuborib bo'lmadi ($(basename "$f"))"
done
log "yuborildi: ${#PARTS[@]} fayl, $TOTAL"

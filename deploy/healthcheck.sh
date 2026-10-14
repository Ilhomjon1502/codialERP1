#!/bin/bash
# Codial ERP: monitoring (M11). Cron: */5 * * * *  bash /srv/codial-test/deploy/healthcheck.sh
# Sayt javob bermasa — web qayta ishga tushiriladi; disk 90% dan to'lsa yoki sayt tiklanmasa — Telegram'ga xabar
# (.env: TELEGRAM_BOT_TOKEN va ALERT_TELEGRAM_CHAT — Bosh menejerning chat raqami). Bir xil xabar soatiga bir martadan ko'p ketmaydi.
cd "$(dirname "$0")"
val() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed 's/[[:space:]]*#.*$//;s/^"//;s/"$//'; }
TELEGRAM_BOT_TOKEN=$(val TELEGRAM_BOT_TOKEN); ALERT_TELEGRAM_CHAT=$(val ALERT_TELEGRAM_CHAT)
PORT=$(val WEB_PORT); PORT=${PORT:-8001}
HOST=$(val ALLOWED_HOSTS | cut -d, -f1 | tr -d ' ')  # Django ALLOWED_HOSTS va HTTPS yo'naltirishidan o'tish uchun
STATE=/tmp/codial-health-$PORT
alert() {
  [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$ALERT_TELEGRAM_CHAT" ] || return 0
  key=$(echo "$1" | md5sum | cut -c1-8)
  if [ -f "$STATE.$key" ] && [ $(( $(date +%s) - $(stat -c %Y "$STATE.$key") )) -lt 3600 ]; then return 0; fi
  touch "$STATE.$key"
  curl -s -m 15 "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" -d chat_id="$ALERT_TELEGRAM_CHAT" --data-urlencode text="⚠️ Codial ERP: $1" > /dev/null
}
ok() { curl -fsS -m 10 -H "Host: $HOST" -H "X-Forwarded-Proto: https" "http://127.0.0.1:$PORT/api/v1/health/" > /dev/null 2>&1; }
if ! ok; then
  sleep 20
  if ! ok; then
    echo "$(date '+%F %T') sayt javob bermadi — web qayta ishga tushirilmoqda"
    docker compose --env-file .env up -d > /dev/null 2>&1
    docker compose --env-file .env restart web > /dev/null 2>&1
    sleep 40
    if ok; then
      alert "sayt javob bermay qoldi va avtomatik qayta ishga tushirildi ($(date '+%d.%m %H:%M')). Hozir ishlayapti."
    else
      alert "sayt ishlamayapti va qayta ishga tushirish yordam bermadi ($(date '+%d.%m %H:%M')). Dasturchiga xabar bering."
    fi
  fi
fi
USE=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "${USE:-0}" -ge 90 ] && alert "server diski ${USE}% to'lgan. Eski zaxiralarni tozalash kerak."
exit 0

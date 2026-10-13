#!/bin/bash
# Codial ERP: Telegram bot tokenini sozlash (M8).
# Ishga tushirish (serverda):  bash /srv/codial-test/deploy/set-telegram.sh
# Token @BotFather'dan olinadi; ekranda qoldirilmaydi va faqat deploy/.env ga yoziladi.
set -e
cd "$(dirname "$0")"
for try in 1 2 3; do
  read -r -p "Bot token (@BotFather bergan, qo'ying va Enter): " T
  printf '\033[1A\033[2K'
  T=$(echo "$T" | tr -d ' ')
  if echo "$T" | grep -Eq '^[0-9]{6,}:[A-Za-z0-9_-]{30,}$'; then break; fi
  echo "Token ko'rinishi noto'g'ri (masalan 123456789:AA...). Qaytadan qo'ying."
  T=""
done
[ -n "$T" ] || { echo "To'xtatildi."; exit 1; }
NAME=$(curl -s "https://api.telegram.org/bot$T/getMe" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
[ -n "$NAME" ] || { echo "Xato: Telegram tokenni qabul qilmadi. Tokenni tekshirib, qayta ishga tushiring"; exit 1; }
sed -i '/^TELEGRAM_BOT_TOKEN=/d;/^TELEGRAM_BOT_USERNAME=/d' .env
{ echo "TELEGRAM_BOT_TOKEN=$T"; echo "TELEGRAM_BOT_USERNAME=$NAME"; } >> .env
grep -q '^TELEGRAM_ATTENDANCE_DELAY_MIN=' .env || echo "TELEGRAM_ATTENDANCE_DELAY_MIN=30" >> .env
chmod 600 .env
docker compose --env-file .env up -d web bot > /dev/null 2>&1
echo "Tayyor: bot @$NAME ulandi. Xodimlar tizimda o'ng yuqoridagi ism → «Telegram» orqali akkauntini bog'laydi."

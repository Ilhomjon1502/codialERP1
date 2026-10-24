#!/bin/bash
# Codial ERP: mijozlar (o'quvchi va vasiylar) Telegram botining tokenini sozlash.
# Ishga tushirish (serverda):  bash /srv/codial-test/deploy/set-clientbot.sh
# Token @BotFather'dan olinadi (xodimlar botidan ALOHIDA bot); ekranda qoldirilmaydi va faqat deploy/.env ga yoziladi.
set -e
cd "$(dirname "$0")"
for try in 1 2 3; do
  read -r -p "Mijozlar boti tokeni (@BotFather bergan, qo'ying va Enter): " T
  printf '\033[1A\033[2K'
  T=$(echo "$T" | tr -d ' ')
  if echo "$T" | grep -Eq '^[0-9]{6,}:[A-Za-z0-9_-]{30,}$'; then break; fi
  echo "Token ko'rinishi noto'g'ri (masalan 123456789:AA...). Qaytadan qo'ying."
  T=""
done
[ -n "$T" ] || { echo "To'xtatildi."; exit 1; }
NAME=$(curl -s "https://api.telegram.org/bot$T/getMe" | sed -n 's/.*"username":"\([^"]*\)".*/\1/p')
[ -n "$NAME" ] || { echo "Xato: Telegram tokenni qabul qilmadi. Tokenni tekshirib, qayta ishga tushiring"; exit 1; }
sed -i '/^CLIENT_BOT_TOKEN=/d;/^CLIENT_BOT_USERNAME=/d' .env
{ echo "CLIENT_BOT_TOKEN=$T"; echo "CLIENT_BOT_USERNAME=$NAME"; } >> .env
chmod 600 .env
docker compose --env-file .env up -d web clientbot > /dev/null 2>&1
echo "Tayyor: mijozlar boti @$NAME ulandi. Lid va shartnoma SMS'lariga bot havolasi qo'shiladi (Qo'ng'iroqlar va SMS -> Telegram bot -> Sozlamalar)."

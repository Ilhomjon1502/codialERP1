#!/bin/bash
# Codial ERP: AI yordamchi (Gemini) API kalitini sozlash (M9).
# Ishga tushirish (serverda):  bash /srv/codial-test/deploy/set-ai.sh
# Kalit https://aistudio.google.com/apikey dan olinadi; ekranda ko'rinmaydi va faqat deploy/.env ga yoziladi.
set -e
cd "$(dirname "$0")"
for try in 1 2 3; do
  read -r -s -p "Gemini API kaliti (qo'ying va Enter, ekranda ko'rinmaydi): " K
  echo
  K=$(echo "$K" | tr -d ' ')
  if echo "$K" | grep -Eq '^[A-Za-z0-9_-]{30,}$'; then break; fi
  echo "Kalit ko'rinishi noto'g'ri (odatda AIza... bilan boshlanadi). Qaytadan qo'ying."
  K=""
done
[ -n "$K" ] || { echo "To'xtatildi."; exit 1; }
# Kalit buyruq qatoriga tushmasin — sarlavha fayldan o'qiladi
LIST=$(curl -s -H @<(printf 'x-goog-api-key: %s\n' "$K") "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200")
if ! echo "$LIST" | grep -q '"models/'; then
  echo "Xato: Google kalitni qabul qilmadi. Kalitni tekshirib, qayta ishga tushiring."; exit 1
fi
MODEL=gemini-2.5-flash
if ! echo "$LIST" | grep -q "\"models/$MODEL\""; then
  MODEL=$(echo "$LIST" | grep -o '"models/gemini-[0-9.]*-flash"' | sed 's/"models\///;s/"//' | sort -V | tail -1)
fi
[ -n "$MODEL" ] || { echo "Xato: mos Gemini modeli topilmadi."; exit 1; }
sed -i '/^AI_PROVIDER=/d;/^AI_API_KEY=/d;/^AI_MODEL=/d' .env
{ echo "AI_PROVIDER=gemini"; echo "AI_API_KEY=$K"; echo "AI_MODEL=$MODEL"; } >> .env
grep -q '^AI_DAILY_LIMIT=' .env || echo "AI_DAILY_LIMIT=50" >> .env
chmod 600 .env
docker compose --env-file .env up -d web > /dev/null 2>&1
echo "Tayyor: AI yordamchi ulandi (model $MODEL). Bosh menejer menyuda «AI yordamchi» bo'limidan foydalanadi."

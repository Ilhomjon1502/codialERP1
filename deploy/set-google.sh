#!/bin/bash
# Codial ERP: Google Sheets hisobot (Foyda → «Hisobot olish») sozlamasi.
# Avval kompyuteringizdan service account JSON kalitini serverga yuboring (bir marta):
#   scp -i ~/.ssh/codial_hetzner "C:\Users\...\Downloads\codialerp1-XXXX.json" root@77.42.9.23:/root/google.json
# Keyin serverda:  bash /srv/codial-test/deploy/set-google.sh
# Kalit deploy/.env ga yoziladi (chatga yoki git'ga tushmaydi); JSON fayl serverdan o'chiriladi.
set -e
cd "$(dirname "$0")"
read -r -p "JSON kalit fayli yo'li [/root/google.json]: " F
F=${F:-/root/google.json}
[ -f "$F" ] || { echo "Fayl topilmadi: $F"; exit 1; }
EMAIL=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['type']=='service_account' and 'BEGIN PRIVATE KEY' in d['private_key']; print(d['client_email'])" "$F") \
  || { echo "Bu service account kalit fayli emas. Google Cloud → Service Accounts → Keys → JSON faylini yuboring."; exit 1; }
echo "Service account: $EMAIL"
read -r -p "Google Sheets fayl havolasi yoki ID'si: " S
ID=$(echo "$S" | sed -E 's#.*/d/([A-Za-z0-9_-]+).*#\1#' | tr -d ' ')
echo "$ID" | grep -Eq '^[A-Za-z0-9_-]{25,}$' || { echo "Fayl ID'si noto'g'ri. Manzil docs.google.com/spreadsheets/d/<ID>/edit ko'rinishida bo'ladi."; exit 1; }
B64=$(base64 -w0 "$F")
sed -i '/^GOOGLE_SERVICE_ACCOUNT_B64=/d;/^GOOGLE_SHEET_ID=/d' .env
{ echo "GOOGLE_SERVICE_ACCOUNT_B64=$B64"; echo "GOOGLE_SHEET_ID=$ID"; } >> .env
chmod 600 .env
docker compose --env-file .env up -d web > /dev/null 2>&1
sleep 8
if docker compose --env-file .env exec -T web python manage.py gsheets_check; then
  shred -u "$F" 2>/dev/null || rm -f "$F"
  echo "Tayyor: Google Sheets ulandi. Kalit fayli serverdan o'chirildi (kompyuteringizdagi nusxani ham o'chiring)."
else
  echo "Ulanmadi: yuqoridagi xabarni o'qing (odatda faylni $EMAIL pochtasiga Editor qilib ulashish kerak) va qayta ishga tushiring. JSON fayl o'chirilmadi."
  exit 1
fi

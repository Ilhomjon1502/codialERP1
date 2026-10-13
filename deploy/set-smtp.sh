#!/bin/bash
# Codial ERP: Gmail SMTP sozlash (xodimlarga parol o'rnatish xatlari uchun).
# Ishga tushirish (serverda):  bash /srv/codial-test/deploy/set-smtp.sh
# Gmail manzili va App password so'raladi; parol ekranda ko'rinmaydi va faqat deploy/.env ga yoziladi.
set -e
cd "$(dirname "$0")"
read -r -p "Gmail manzil: " U
for try in 1 2 3; do
  # Ko'rinadigan maydon (ba'zi terminallarda yashirin maydonga qo'yish ishlamaydi); Enter'dan keyin qator ekrandan o'chiriladi
  read -r -p "App password (16 belgi, qo'ying va Enter): " P
  printf '[1A[2K'
  P=$(echo "$P" | tr -d ' ')
  if [ ${#P} -eq 16 ]; then break; fi
  echo "App password 16 harfdan iborat bo'lishi kerak (siz ${#P} ta kiritdingiz). Qaytadan qo'ying."
  P=""
done
[ -n "$P" ] || { echo "To'xtatildi."; exit 1; }
sed -i '/^EMAIL_/d;/^DEFAULT_FROM_EMAIL=/d' .env
{
  echo "EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend"
  echo "EMAIL_HOST=smtp.gmail.com"
  echo "EMAIL_PORT=587"
  echo "EMAIL_USE_TLS=true"
  echo "EMAIL_HOST_USER=$U"
  echo "EMAIL_HOST_PASSWORD=$P"
  echo "DEFAULT_FROM_EMAIL=\"Codial ERP <$U>\""
} >> .env
chmod 600 .env
docker compose --env-file .env up -d web > /dev/null 2>&1
sleep 8
if docker compose --env-file .env exec -T web python manage.py shell -c "from django.core.mail import get_connection; c = get_connection(); c.open(); c.close()" > /dev/null 2>&1; then
  echo "Tayyor: pochta sozlandi, Gmail'ga ulanish ishladi"
else
  echo "Xato: Gmail'ga ulanib bo'lmadi. Manzil yoki App password'ni tekshirib, qayta ishga tushiring"
fi

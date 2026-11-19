#!/bin/bash
# Codial ERP: Telegram orqali shifrlangan zaxirani sozlash (bir marta).
# Ishga tushirish (serverda, buyurtmachi o'zi):  bash /srv/codial-test/deploy/set-backup.sh
# Zip paroli faqat deploy/.env ga yoziladi (chmod 600). Chatga yoki git'ga tushmaydi.
# MUHIM: parol yo'qolsa zaxirani hech kim ocha olmaydi — uni parol menejeriga (yoki boshqa xavfsiz joyga) saqlang.
set -e
cd "$(dirname "$0")"

command -v 7z > /dev/null || { echo "7z o'rnatilmoqda (p7zip-full)..."; apt-get install -y -qq p7zip-full > /dev/null; }

echo "Zip paroli: kamida 12 belgi (harf, raqam va . _ @ % + = : , ! - belgilari; probel va # bo'lmasin)."
read -r -s -p "Parolni yozing yoki shunchaki Enter bosing — tasodifiy kuchli parol yaratiladi: " P
echo
GEN=0
if [ -z "$P" ]; then
  P=$(tr -dc 'A-HJ-NP-Za-km-z2-9' < /dev/urandom | head -c 24)
  GEN=1
else
  read -r -s -p "Parolni takrorlang: " P2
  echo
  [ "$P" = "$P2" ] || { echo "Parollar mos kelmadi. To'xtatildi."; exit 1; }
fi
echo "$P" | grep -Eq '^[A-Za-z0-9._@%+=:,!-]{12,64}$' || { echo "Parol talabga mos emas (12–64 belgi; ruxsat etilgan: harf, raqam va . _ @ % + = : , ! -). To'xtatildi."; exit 1; }

if [ "$GEN" = 1 ]; then
  echo
  echo "================================================================"
  echo "  ZAXIRA PAROLI (faqat shu yerda bir marta ko'rsatiladi):"
  echo
  echo "      $P"
  echo
  echo "  Uni HOZIR parol menejeriga saqlang. Yo'qolsa zaxira ochilmaydi."
  echo "================================================================"
  read -r -p "Saqlab bo'ldingizmi? Davom etish uchun «ha» deb yozing: " OK
  [ "$OK" = "ha" ] || { echo "To'xtatildi (hech narsa yozilmadi)."; exit 1; }
  printf '\033[2J\033[H'
fi

# Bosh menejerning Telegram chat raqami (botga bog'langan akkaunt)
LIST=$(docker compose --env-file .env exec -T web python manage.py shell -c "
from apps.notifications.models import TelegramLink
for l in TelegramLink.objects.filter(user__role__code='BOSH_MENEJER', chat_id__isnull=False).exclude(user__employment_status='Ishdan ketgan'):
    print('CHAT|%s|%s' % (l.chat_id, l.user.full_name))
" < /dev/null | grep '^CHAT|' || true)
N=$(echo -n "$LIST" | grep -c '^CHAT|' || true)
if [ "$N" = 1 ]; then
  CHAT=$(echo "$LIST" | cut -d'|' -f2); WHO=$(echo "$LIST" | cut -d'|' -f3)
elif [ "$N" -gt 1 ]; then
  echo "Botga bog'langan bir nechta Bosh menejer bor:"
  echo "$LIST" | nl -w2 -s') ' | sed 's/CHAT|[0-9-]*|//'
  read -r -p "Qaysi biriga yuborilsin (raqami): " K
  LINE=$(echo "$LIST" | sed -n "${K}p"); CHAT=$(echo "$LINE" | cut -d'|' -f2); WHO=$(echo "$LINE" | cut -d'|' -f3)
else
  read -r -p "Botga bog'langan Bosh menejer topilmadi. Telegram chat raqamini yozing: " CHAT; WHO="(qo'lda)"
fi
echo "$CHAT" | grep -Eq '^-?[0-9]{5,}$' || { echo "Chat raqami noto'g'ri. To'xtatildi."; exit 1; }

TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' .env | tail -1 | cut -d= -f2- | tr -d '"')
R=$(curl -s -m 20 "https://api.telegram.org/bot$TOKEN/sendMessage" -d chat_id="$CHAT" --data-urlencode text="🗄 Codial zaxirasi sozlandi: bundan buyon har kuni 00:00 da shu yerga shifrlangan zaxira keladi.")
echo "$R" | grep -q '"ok":true' || { echo "Telegram'ga xabar yuborib bo'lmadi ($WHO). Botga /start yozilganini tekshiring. To'xtatildi."; exit 1; }

sed -i '/^BACKUP_ZIP_PASSWORD=/d;/^BACKUP_TELEGRAM_CHAT=/d' .env
{ echo "BACKUP_ZIP_PASSWORD=$P"; echo "BACKUP_TELEGRAM_CHAT=$CHAT"; } >> .env
chmod 600 .env
echo "Sozlandi: zaxira $WHO ga yuboriladi."

# Cron: kunlik 00:00 va yakshanba 00:05 (media). Qayta ishga tushirsangiz takrorlanmaydi.
if ! crontab -l 2> /dev/null | grep -q backup_telegram.sh; then
  ( crontab -l 2> /dev/null
    echo "0 0 * * *  bash $(pwd)/backup_telegram.sh daily >> /var/log/codial-backup-telegram.log 2>&1"
    echo "5 0 * * 0  bash $(pwd)/backup_telegram.sh media >> /var/log/codial-backup-telegram.log 2>&1" ) | crontab -
  echo "Cron qo'shildi (har kuni 00:00; yakshanba 00:05 — yuklangan fayllar)."
fi

read -r -p "Birinchi zaxirani hozir yuborib ko'raymi? [ha/yo'q]: " GO
if [ "$GO" = "ha" ]; then
  bash ./backup_telegram.sh daily && echo "Yuborildi — Telegramni tekshiring, zip'ni parol bilan oching." || echo "Xato bo'ldi: Telegramdagi ogohlantirishni va /var/log/codial-backup-telegram.log ni ko'ring."
fi

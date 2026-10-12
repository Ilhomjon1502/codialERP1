#!/bin/sh
# Kunlik zaxira: PostgreSQL bazasi siqilgan holda, 30 kun saqlanadi.
# crontab:  15 3 * * *  /srv/codial-prod/deploy/backup.sh prod >> /var/log/codial-backup.log 2>&1
set -eu
ENV_NAME="${1:-prod}"
DIR="/srv/codial-$ENV_NAME/deploy"
OUT="/srv/backups/codial-$ENV_NAME"
mkdir -p "$OUT"
cd "$DIR"
FILE="$OUT/codial-$ENV_NAME-$(date +%Y%m%d-%H%M).sql.gz"
# Baza nomi va foydalanuvchi konteynerning o'z muhitidan olinadi
docker compose --env-file .env exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$FILE"
find "$OUT" -name "*.sql.gz" -mtime +30 -delete
echo "$(date '+%F %T') zaxira: $FILE ($(du -h "$FILE" | cut -f1))"

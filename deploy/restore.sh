#!/bin/sh
# Zaxiradan tiklash (DIQQAT: joriy baza o'chiriladi!):
#   ./restore.sh prod /srv/backups/codial-prod/codial-prod-20261012-0315.sql.gz
set -eu
ENV_NAME="$1"; FILE="$2"
cd "/srv/codial-$ENV_NAME/deploy"
printf "codial-%s bazasi %s dan tiklanadi, joriy ma'lumotlar o'chadi. Davom etilsinmi? [ha/yo'q] " "$ENV_NAME" "$FILE"
read -r ok; [ "$ok" = "ha" ] || exit 1
docker compose --env-file .env stop web
docker compose --env-file .env exec -T db sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
gunzip -c "$FILE" | docker compose --env-file .env exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose --env-file .env start web
echo "Tiklandi."

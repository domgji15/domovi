#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Nedostaje .venv/bin/python. Aktiviraj virtualno okruzenje."
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" && -z "${POSTGRES_DB:-}" ]]; then
  echo "Postavi DATABASE_URL ili POSTGRES_* varijable prije pokretanja skripte."
  exit 1
fi

EXPORT_FILE="db/sqlite_export.json"

echo "1) Export podataka iz SQLite baze..."
DB_BACKUP_URL="${DATABASE_URL:-}"
PG_DB_BACKUP="${POSTGRES_DB:-}"
PG_USER_BACKUP="${POSTGRES_USER:-}"
PG_PASSWORD_BACKUP="${POSTGRES_PASSWORD:-}"
PG_HOST_BACKUP="${POSTGRES_HOST:-}"
PG_PORT_BACKUP="${POSTGRES_PORT:-}"
unset DATABASE_URL POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT
.venv/bin/python manage.py dumpdata \
  --natural-foreign \
  --natural-primary \
  --exclude auth.permission \
  --exclude contenttypes \
  > "$EXPORT_FILE"

echo "2) Pokretanje migracija na PostgreSQL..."
if [[ -n "$DB_BACKUP_URL" ]]; then
  export DATABASE_URL="$DB_BACKUP_URL"
else
  export POSTGRES_DB="$PG_DB_BACKUP"
  export POSTGRES_USER="$PG_USER_BACKUP"
  export POSTGRES_PASSWORD="$PG_PASSWORD_BACKUP"
  export POSTGRES_HOST="$PG_HOST_BACKUP"
  export POSTGRES_PORT="$PG_PORT_BACKUP"
fi
.venv/bin/python manage.py migrate

echo "3) Import podataka u PostgreSQL..."
.venv/bin/python manage.py loaddata "$EXPORT_FILE"

echo "Migracija zavrsena. Export datoteka: $EXPORT_FILE"

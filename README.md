# Domovi - setup, sigurnost i deployment

Ovaj projekt podrzava SQLite (default fallback) i PostgreSQL (preporuceno za produkciju).

## 1. Instalacija

```bash
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Aplikacija automatski ucitava `.env` iz roota projekta.

## 2. PostgreSQL lokalno (opcionalno preko Dockera)

```bash
docker compose -f deploy/docker-compose.postgres.yml --env-file .env up -d
```

## 3. Konfiguracija baze

Opcija A (`DATABASE_URL`, preporuceno):

`DATABASE_URL=postgresql://domovi:domovi@127.0.0.1:5432/domovi`

Opcija B (`POSTGRES_*`):

`POSTGRES_DB=domovi`  
`POSTGRES_USER=domovi`  
`POSTGRES_PASSWORD=domovi`  
`POSTGRES_HOST=127.0.0.1`  
`POSTGRES_PORT=5432`

Migracije:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
```

## 4. Migracija podataka SQLite -> PostgreSQL

Ako imas podatke u SQLite backupu:

```bash
./scripts/migrate_sqlite_to_postgres.sh
```

Skripta:
- izvozi podatke u `db/sqlite_export.json`
- pokrece migracije na PostgreSQL
- importa podatke u PostgreSQL

## 5. Pokretanje aplikacije

Lokalno:

```bash
.venv/bin/python manage.py runserver
```

Produkcija (Gunicorn):

```bash
.venv/bin/python manage.py collectstatic --noinput
gunicorn config.wsgi:application -c deploy/gunicorn.conf.py
```

`Procfile` je spreman za PaaS deployment.

## 6. Sigurnosne postavke za produkciju

Minimalno postaviti:

- `APP_ENV=production`
- `DEBUG=False`
- jak `SECRET_KEY`
- `ALLOWED_HOSTS=app.example.com,www.app.example.com`
- `CSRF_TRUSTED_ORIGINS=https://app.example.com,https://www.app.example.com`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `USE_X_FORWARDED_PROTO=True` (ako si iza reverse proxyja)

Napomena: `AUTO_LOGIN_ENABLED` je samo za razvoj i ignorira se kad `DEBUG=False`.

## 7. Testovi i produkcijska provjera

Pokreni testove:

```bash
DATABASE_URL='' POSTGRES_DB='' .venv/bin/python manage.py test
```

Pokreni Django deployment check:

```bash
APP_ENV=production DEBUG=False .venv/bin/python manage.py check --deploy
```

## 8. Struktura projekta

```text
domovi/
  config/                  # Django project config (settings, urls, wsgi, asgi)
  dashboard/               # Glavna aplikacija (models, views, forms, tests)
  templates/               # HTML templateovi
  static/                  # Source static assets
  staticfiles/             # collectstatic output (runtime)
  scripts/                 # Utility skripte (npr. migracija baze)
  deploy/                  # Deployment konfiguracija (docker compose, gunicorn)
  docs/                    # Tehnicka dokumentacija i SQL schema
  db/                      # Runtime/export artefakti i backupi
  manage.py
```

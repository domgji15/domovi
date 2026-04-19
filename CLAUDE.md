# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Domovi is a Django 6.0.2 property management system for residential care facilities in Croatia. It handles resident management, employee scheduling, and financial tracking with multi-property support and role-based access control. All UI text is in Croatian.

## Commands

```bash
# Run development server
.venv/bin/python manage.py runserver

# Run all tests
.venv/bin/python manage.py test dashboard

# Run a single test module
.venv/bin/python manage.py test dashboard.tests.test_views

# Run a specific test class or method
.venv/bin/python manage.py test dashboard.tests.test_views.SwitchDomTests.test_open_redirect_blocked

# Run migrations
.venv/bin/python manage.py migrate

# Create migrations after model changes
.venv/bin/python manage.py makemigrations dashboard

# Collect static files (production)
.venv/bin/python manage.py collectstatic --noinput

# Django deployment checks
.venv/bin/python manage.py check --deploy
```

## Architecture

### Single-app Django project
- `config/` — Django project settings, root URL conf, WSGI
- `dashboard/` — The sole app containing all models, views, forms, admin, tests

### Multi-tenancy model
Every data model has a ForeignKey to `Dom` (facility). Users see only data for their selected dom. Dom access is controlled by role via `Profil`:
- **admin** — access to all domovi
- **upravitelj** (manager) — access to `upravljani_domovi` (M2M on Profil)
- **zaposlenik** (employee) — access only to their assigned dom, restricted from financial/management views

Dom selection is session-based. The helper `resolve_selected_dom_id()` in `dashboard/dom_access.py` resolves which dom the user is viewing and stores it in `request.session["selected_dom_id"]`.

### Key data flow
- `dashboard/context_processors.py` injects `domovi`, `selected_dom`, `profil`, `show_dom_dropdown` into every template
- All views call `_get_profil(request)` and `resolve_selected_dom_id()` to scope queries
- Employee role is blocked from financial views, CRUD on korisnici/investicije/troškovi/režije via explicit checks in views

### Models (dashboard/models.py)
`Klijent` → has many `Dom` → each Dom has: `Korisnik` (residents), `Zaposlenik` (employees), `Investicija`, `Trosak` (expenses), `Rezija` (utilities). `KorisnikUplata` tracks monthly payments per resident. `Smjena` tracks daily shifts per employee. `Profil` links Django User to a Dom with a role.

### Financial amounts
All monetary fields use `DecimalField(max_digits=12, decimal_places=2)`. The template filter `numfmt` in `dashboard/templatetags/number_format.py` formats them for display.

### Forms (dashboard/forms.py)
All forms exclude `dom` — it's set from the session in the view. Notable validations: OIB must be 11 digits, TrosakForm requires `trgovina`+`meso` when `kategorija=="kuhinja"`, RezijaForm validates date range.

## Database

- **Development**: SQLite (default fallback when no DATABASE_URL or POSTGRES_* vars set)
- **Production**: PostgreSQL on Railway, configured via `DATABASE_URL` env var
- Connection to Railway Postgres (public): `DATABASE_PUBLIC_URL` variable on the Postgres service
- Internal Railway URL (`postgres.railway.internal`) only works within Railway's network

## Deployment

Deployed on **Railway** (project: `romantic-renewal`). Railway CLI is installed and linked.

```bash
# Check service status
railway service status --all

# View logs
railway service logs --service web

# Get environment variables
railway variables --service web
railway variables --service Postgres
```

Start command runs: `migrate` → `collectstatic` → `gunicorn` (see `railway.toml`).
Gunicorn config in `deploy/gunicorn.conf.py` (2 gthread workers, 60s timeout).
Static files served via WhiteNoise in production.

## Environment Variables

See `.env.example`. Key variables:
- `APP_ENV` — `development` or `production`
- `DATABASE_URL` — PostgreSQL connection string (preferred over separate POSTGRES_* vars)
- `AUTO_LOGIN_ENABLED` / `AUTO_LOGIN_USERNAME` — dev-only auto-login middleware

## Testing

Three test modules in `dashboard/tests/`:
- `test_dom_access.py` — role-based dom access logic
- `test_forms.py` — form validation (OIB, expense categories, date ranges)
- `test_views.py` — login requirements, employee restrictions, redirect safety

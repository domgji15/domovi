web: python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi:application -c deploy/gunicorn.conf.py

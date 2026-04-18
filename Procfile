release: python manage.py migrate --noinput && python manage.py ensure_superuser
web: gunicorn config.wsgi:application -c deploy/gunicorn.conf.py

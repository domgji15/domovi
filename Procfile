web: python manage.py migrate --noinput && python deploy/create_superuser.py && gunicorn config.wsgi:application -c deploy/gunicorn.conf.py

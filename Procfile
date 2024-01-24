postdeploy: python manage.py migrate
web: gunicorn aidants_connect.wsgi:application -w "${GUNICORN_WORKERS:-1}" --log-file -
worker: celery --app aidants_connect worker --beat --loglevel INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

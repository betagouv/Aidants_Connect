# This configuration file is taken from the official Celery documentation:
# http://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
# Please refer to it for additional information.

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aidants_connect.settings")

app = Celery("aidants_connect")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from django.db import models
from django.utils import timezone
from datetime import timedelta


def default_expiration_date():
    now = timezone.now()
    return now + timedelta(minutes=30)


class Connection(models.Model):
    state = models.CharField(max_length=30)
    redirectUrl = models.CharField(max_length=100)
    expiresOn = models.DateTimeField(default=default_expiration_date)

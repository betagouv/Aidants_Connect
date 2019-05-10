from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser


def default_expiration_date():
    now = timezone.now()
    return now + timedelta(minutes=30)


class Connection(models.Model):
    state = models.TextField()
    code = models.TextField()
    nonce = models.TextField(default="No Nonce Provided")
    expiresOn = models.DateTimeField(default=default_expiration_date)


class User(AbstractUser):
    pass

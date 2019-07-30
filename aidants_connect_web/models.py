from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField

CONNECTION_EXPIRATION_TIME = 10


def default_expiration_date():
    now = timezone.now()
    return now + timedelta(minutes=CONNECTION_EXPIRATION_TIME)


class User(AbstractUser):
    profession = models.TextField(blank=False)
    organisme = models.TextField(blank=False)
    ville = models.TextField(blank=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Usager(models.Model):
    given_name = models.TextField(blank=False)
    family_name = models.TextField(blank=False)
    preferred_username = models.TextField(blank=True)
    birthdate = models.DateField(blank=False)
    GENDER = (("female", "Femme"), ("male", "Homme"))
    gender = models.CharField(max_length=6, choices=GENDER, default="F", blank=False)
    birthplace = models.PositiveIntegerField(
        validators=[MinValueValidator(9999), MaxValueValidator(100000)], blank=False
    )
    birthcountry = models.IntegerField(
        validators=[MinValueValidator(99100), MaxValueValidator(99500)],
        default=99100,
        blank=False,
    )
    sub = models.TextField(blank=False, unique=True)

    email = models.EmailField(
        blank=False, default="noemailprovided@aidantconnect.beta.gouv.fr"
    )

    def __str__(self):
        return f"{self.given_name} {self.family_name}"


class Connection(models.Model):
    state = models.TextField()
    code = models.TextField()
    nonce = models.TextField(default="No Nonce Provided")
    expiresOn = models.DateTimeField(default=default_expiration_date)
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, blank=True, null=True)
    access_token = models.TextField(default="No token Provided")
    CONNECTION_TYPE = (("FS", "FC as FS"), ("FI", "FC as FI"))
    connection_type = models.CharField(
        max_length=2, choices=CONNECTION_TYPE, default="FI", blank=False
    )
    demarche = models.TextField(default="No demarche provided")
    complete = models.BooleanField(default=False)


class Mandat(models.Model):
    aidant = models.ForeignKey(User, on_delete=models.CASCADE, default=0)
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, default=0)
    perimeter = ArrayField(models.CharField(blank=False, max_length=100))
    creation_date = models.DateTimeField(default=timezone.now)
    duration = models.IntegerField(default=3)

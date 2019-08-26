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


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    organisme = models.TextField(blank=False)
    ville = models.TextField(blank=False)

    class Meta:
        verbose_name = "aidant"

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

    creation_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
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
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE, blank=True, null=True)
    complete = models.BooleanField(default=False)


class Mandat(models.Model):
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE, default=0)
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, default=0)
    perimeter = ArrayField(models.CharField(blank=False, max_length=100))
    creation_date = models.DateTimeField(default=timezone.now)
    duration = models.IntegerField(default=3)


class JournalManager(models.Manager):
    def connection(self, aidant: Aidant):
        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        journal_entry = self.create(initiator=initiator, action="connect_aidant")
        return journal_entry

    def mandat_creation(
        self, aidant: Aidant, usager: Usager, demarches: list, duree: int, fc_token: str
    ):

        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        usager = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=initiator,
            usager=usager,
            action="create_mandat",
            demarches=demarches,
            duree=duree,
            access_token=fc_token,
        )
        return journal_entry

    def mandat_use(
        self, aidant: Aidant, usager: Usager, demarche: str, access_token: str
    ):

        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        usager = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=initiator,
            usager=usager,
            action="use_mandat",
            demarches=[demarche],
            access_token=access_token,
        )
        return journal_entry


class Journal(models.Model):
    ACTIONS = (
        ("connect_aidant", "Connexion d'un aidant"),
        ("create_mandat", "Création d'un mandat"),
        ("use_mandat", "Utilisation d'un mandat"),
    )
    # mandatory
    action = models.CharField(max_length=30, choices=ACTIONS, blank=False)
    initiator = models.TextField(blank=False)
    # automatic
    creation_date = models.DateTimeField(auto_now_add=True)
    # action dependant
    demarches = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    usager = models.TextField(blank=True, null=True)
    duree = models.IntegerField(blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)

    objects = JournalManager()

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        else:
            super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

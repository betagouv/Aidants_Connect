from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField, JSONField
from django.conf import settings

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

    preferred_contact_method = models.CharField(max_length=8, blank=True)
    contact_address = JSONField(blank=True, null=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=12, blank=True)

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
        return f"{self.given_name} {self.family_name}"


class Mandat(models.Model):
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE, default=0)
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, default=0)
    demarche = models.CharField(blank=False, max_length=100)
    creation_date = models.DateTimeField(default=timezone.now)
    duree = models.IntegerField(default=3)
    modified_by_access_token = models.TextField(
        blank=False, default="No token provided"
    )

    class Meta:
        unique_together = ["aidant", "demarche", "usager"]


class Connection(models.Model):
    state = models.TextField()  # FS
    nonce = models.TextField(default="No Nonce Provided")  # FS
    CONNECTION_TYPE = (("FS", "FC as FS"), ("FI", "FC as FI"))  # FS
    connection_type = models.CharField(
        max_length=2, choices=CONNECTION_TYPE, default="FI", blank=False
    )
    demarches = ArrayField(models.TextField(default="No démarche"), null=True)  # FS
    duree = models.IntegerField(blank=False, null=True)  # FS
    usager = models.ForeignKey(
        Usager, on_delete=models.CASCADE, blank=True, null=True
    )  # FS
    expiresOn = models.DateTimeField(default=default_expiration_date)  # FS
    access_token = models.TextField(default="No token Provided")  # FS

    code = models.TextField()
    demarche = models.TextField(default="No demarche provided")
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE, blank=True, null=True)
    complete = models.BooleanField(default=False)
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE, blank=True, null=True)


class JournalManager(models.Manager):
    def connection(self, aidant: Aidant):
        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        journal_entry = self.create(initiator=initiator, action="connect_aidant")
        return journal_entry

    def mandat_creation(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=initiator,
            usager=usager_info,
            action="create_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree,
            access_token=mandat.modified_by_access_token,
            mandat=mandat.id,
        )
        return journal_entry

    def mandat_update(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=initiator,
            usager=usager_info,
            action="update_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree,
            access_token=mandat.modified_by_access_token,
            mandat=mandat.id,
        )
        return journal_entry

    def mandat_use(
        self,
        aidant: Aidant,
        usager: Usager,
        demarche: str,
        access_token: str,
        mandat: Mandat,
    ):

        initiator = f"{aidant.get_full_name()} - {aidant.organisme} - {aidant.email}"
        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=initiator,
            usager=usager_info,
            action="use_mandat",
            demarche=demarche,
            access_token=access_token,
            mandat=mandat.id,
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
    demarche = models.CharField(max_length=100, blank=True, null=True)
    usager = models.TextField(blank=True, null=True)
    duree = models.IntegerField(blank=True, null=True)  # En jours
    access_token = models.TextField(blank=True, null=True)
    mandat = models.IntegerField(blank=True, null=True)

    objects = JournalManager()

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        else:
            super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

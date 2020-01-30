import io
import base64
import qrcode
import qrcode.image.svg
from datetime import date, timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField, JSONField

CONNECTION_EXPIRATION_TIME = 10


def default_expiration_date():
    now = timezone.now()
    return now + timedelta(minutes=CONNECTION_EXPIRATION_TIME)


def generate_qrcode_base64(string: str, image_type: str = "png"):
    stream = io.BytesIO()
    if image_type == "png":
        img = qrcode.make(string)
        img.save(stream, "PNG")
    elif image_type == "svg":
        img = qrcode.make(string, image_factory=qrcode.image.svg.SvgImage)
        img.save(stream, "SVG")
    journal_print_mandat_qrcode = base64.b64encode(stream.getvalue())
    return journal_print_mandat_qrcode.decode("utf-8")


class Organisation(models.Model):
    name = models.TextField(default="No name provided")
    siret = models.PositiveIntegerField(default=1)
    address = models.TextField(default="No address provided")

    def __str__(self):
        return f"{self.name}"


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    organisation = models.ForeignKey(Organisation, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_string_identifier(self):
        return f"{self.get_full_name()} - {self.organisation.name} - {self.email}"

    def get_usagers(self):
        """
        :return: a queryset of usagers who have a mandat (both active & expired)
        with the aidant
        """
        mandats_for_aidant = Mandat.objects.filter(aidant=self)
        usagers = (
            Usager.objects.filter(mandat__in=mandats_for_aidant)
            .distinct()
            .order_by("family_name")
        )
        return usagers

    def get_usagers_with_active_mandat(self):
        """
        :alternate name: get_active_usagers()
        :return: a queryset of usagers who have a active mandat with the aidant
        """
        active_mandats_for_aidant = Mandat.objects.active().filter(aidant=self)
        usagers = (
            Usager.objects.filter(mandat__in=active_mandats_for_aidant)
            .distinct()
            .order_by("family_name")
        )
        return usagers

    def get_active_mandats_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the active mandats with the usagers
        """
        active_mandats = (
            Mandat.objects.active()
            .filter(usager=usager, aidant=self)
            .order_by("creation_date")
        )
        return active_mandats

    def get_expired_mandats_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the expired mandats with the usagers
        """
        expired_mandats = (
            Mandat.objects.expired()
            .filter(usager=usager, aidant=self)
            .order_by("creation_date")
        )
        return expired_mandats

    def get_active_demarches_for_usager(self, usager):
        """
        :param usager:
        :return: list of demarche the usager and the aidant have a active mandat for
        """
        active_mandats = Mandat.objects.active().filter(usager=usager, aidant=self)
        return active_mandats.values_list("demarche", flat=True)

    def get_last_action_timestamp(self):
        a = (
            Journal.objects.filter(initiator=self.full_string_identifier)
            .last()
            .creation_date
        )
        return a


class UsagerManager(models.Manager):
    def active(self):
        return self.filter(mandat__expiration_date__gt=timezone.now()).distinct()

    def get_journal_of_last_print_mandat(self):
        """
        :return: the last 'print_mandat' Journal entry initiated by the aidant
        """
        journal_print_mandat = Journal.objects.filter(
            action="print_mandat", hash_data__aidant_id=self.id
        ).last()
        return journal_print_mandat


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

    objects = UsagerManager()

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
        return f"{self.given_name} {self.family_name}"


class MandatManager(models.Manager):
    def active(self):
        return self.exclude(expiration_date__lt=timezone.now())

    def expired(self):
        return self.exclude(expiration_date__gt=timezone.now())

    def demarche(self, demarche):
        return self.filter(demarche=demarche)


class Mandat(models.Model):
    # Mandat information
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE, default=0)
    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, default=0)
    demarche = models.CharField(blank=False, max_length=100)
    # Mandat expiration date management
    creation_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField(default=timezone.now)
    last_mandat_renewal_date = models.DateTimeField(default=timezone.now)
    # Journal entry creation information
    last_mandat_renewal_token = models.TextField(
        blank=False, default="No token provided"
    )

    objects = MandatManager()

    class Meta:
        unique_together = ["aidant", "demarche", "usager"]

    @property
    def is_expired(self):
        return timezone.now() > self.expiration_date

    @property
    def duree_in_days(self):
        duree_for_computer = self.expiration_date - self.last_mandat_renewal_date
        # we add one day so that duration is human friendly
        # i.e. for a human, there is one day between now and tomorrow at the same time,
        # and 0 for a computer
        return duree_for_computer.days + 1


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

    @property
    def is_expired(self):
        return timezone.now() > self.expiresOn


class JournalManager(models.Manager):
    def connection(self, aidant: Aidant):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier, action="connect_aidant"
        )
        return journal_entry

    def mandat_papier(
        self, aidant: Aidant, usager: Usager, demarches: list, expiration_date
    ):
        demarches.sort()
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            action="print_mandat",
            hash_data={
                "aidant_id": aidant.id,
                "creation_date": date.today().isoformat(),
                "demarches_list": ",".join(demarches),
                "expiration_date": expiration_date.date().isoformat(),
                "organisation_id": aidant.organisation.id,
                "template_version": settings.MANDAT_TEMPLATE_VERSION,
                "usager_sub": usager.sub,
            },
        )
        return journal_entry

    def activity_check(self, aidant: Aidant):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier, action="activity_check_aidant"
        )
        return journal_entry

    def mandat_creation(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager_info,
            action="create_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree_in_days,
            access_token=mandat.last_mandat_renewal_date,
            mandat=mandat.id,
        )
        return journal_entry

    def mandat_update(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager_info,
            action="update_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree_in_days,
            access_token=mandat.last_mandat_renewal_date,
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

        usager_info = f"{usager.get_full_name()} - {usager.id} - {usager.email}"

        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
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
        ("activity_check_aidant", "Reprise de connexion d'un aidant"),
        ("create_mandat", "Création d'un mandat"),
        ("use_mandat", "Utilisation d'un mandat"),
        ("update_mandat", "Renouvellement d'un mandat"),
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
    hash_data = JSONField(blank=True, null=True)

    objects = JournalManager()

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        else:
            super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

    def generate_qrcode(self, image_type: str):
        sorted_hash_data = dict(sorted(self.hash_data.items()))
        hash_data_string = ",".join(str(x) for x in list(sorted_hash_data.values()))
        return generate_qrcode_base64(hash_data_string, image_type=image_type)

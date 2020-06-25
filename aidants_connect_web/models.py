from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Organisation(models.Model):
    name = models.TextField(default="No name provided")
    siret = models.PositiveIntegerField(default=1)
    address = models.TextField(default="No address provided")

    def __str__(self):
        return f"{self.name}"


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    organisation = models.ForeignKey(
        Organisation, null=True, on_delete=models.CASCADE, related_name="aidants"
    )

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_string_identifier(self):
        return f"{self.get_full_name()} - {self.organisation.name} - {self.email}"

    def get_valid_autorisation(self, demarche, usager):
        """
        :param demarche:
        :param usager:
        :return: Autorisation object if this aidant may perform the specified `demarche`
        for the specified `usager`, `None` otherwise.`
        """
        try:
            return (
                Autorisation.objects.active()
                .for_demarche(demarche)
                .for_usager(usager)
                .visible_by(self)
                .get()
            )
        except Autorisation.DoesNotExist:
            return None

    def get_usagers(self):
        """
        :return: a queryset of usagers who have at least one autorisation
        (active or expired) with the aidant's organisation.
        """
        return Usager.objects.visible_by(self).distinct()

    def get_usager(self, usager_id):
        """
        :return: an usager or `None` if the aidant isn't allowed
        by an autorisation to access this usager.
        """
        try:
            return self.get_usagers().get(pk=usager_id)
        except Usager.DoesNotExist:
            return None

    def get_usagers_with_active_autorisation(self):
        """
        :return: a queryset of usagers who have an active autorisation
        with the aidant's organisation.
        """
        return self.get_usagers().active()

    def get_autorisations(self):
        """
        :return: a queryset of autorisations visible by this aidant.
        """
        return Autorisation.objects.visible_by(self).distinct()

    def get_autorisation(self, autorisation_id):
        """
        :return: an autorisation or `None` if this autorisation is not
        visible by this aidant.
        """
        try:
            return self.get_autorisations().get(pk=autorisation_id)
        except Autorisation.DoesNotExist:
            return None

    def get_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's autorisations.
        """
        return self.get_autorisations().for_usager(usager)

    def get_active_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's active autorisations
        that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).active()

    def get_inactive_autorisations_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's inactive (expired or revoked)
        autorisations that are visible by this aidant.
        """
        return self.get_autorisations_for_usager(usager).inactive()

    def get_active_demarches_for_usager(self, usager):
        """
        :param usager:
        :return: a list of demarches the usager has active autorisations for
        in this aidant's organisation.
        """
        return self.get_active_autorisations_for_usager(usager).values_list(
            "demarche", flat=True
        )

    def get_last_action_timestamp(self):
        """
        :return: the timestamp of this aidant's last logged action or `None`.
        """
        try:
            return (
                Journal.objects.filter(initiator=self.full_string_identifier)
                .last()
                .creation_date
            )
        except AttributeError:
            return None

    def get_journal_create_attestation(self, access_token):
        """
        :return: the corresponding 'create_attestation' Journal entry initiated
        by the aidant
        """
        journal_create_attestation = Journal.objects.filter(
            initiator=self.full_string_identifier,
            action="create_attestation",
            access_token=access_token,
        ).last()
        return journal_create_attestation


class UsagerQuerySet(models.QuerySet):
    def active(self):
        return self.filter(mandats__expiration_date__gt=timezone.now()).distinct()

    def visible_by(self, aidant):
        """
        :param aidant:
        :return: a new QuerySet instance only filtering in the usagers who have
        an autorisation with this aidant's organisation.
        """
        return self.filter(mandats__organisation=aidant.organisation).distinct()


class Usager(models.Model):

    GENDER_FEMALE = "female"
    GENDER_MALE = "male"
    GENDER_CHOICES = (
        (GENDER_FEMALE, "Femme"),
        (GENDER_MALE, "Homme"),
    )
    BIRTHCOUNTRY_FRANCE = "99100"
    EMAIL_NOT_PROVIDED = "noemailprovided@aidantconnect.beta.gouv.fr"

    given_name = models.TextField(blank=False)
    family_name = models.TextField(blank=False)
    preferred_username = models.TextField(blank=True)
    birthdate = models.DateField(blank=False)
    gender = models.CharField(
        max_length=6, choices=GENDER_CHOICES, default=GENDER_FEMALE,
    )
    birthplace = models.CharField(max_length=5, blank=True, null=True)
    birthcountry = models.CharField(max_length=5, default=BIRTHCOUNTRY_FRANCE,)
    sub = models.TextField(blank=False, unique=True)
    email = models.EmailField(blank=False, default=EMAIL_NOT_PROVIDED)
    creation_date = models.DateTimeField(default=timezone.now)

    objects = UsagerQuerySet.as_manager()

    class Meta:
        ordering = ["family_name", "given_name"]

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    @property
    def full_string_identifier(self):
        return f"{self.get_full_name()} - {self.id} - {self.email}"

    def get_full_name(self):
        return str(self)

    def get_mandat(self, mandat_id):
        try:
            return self.mandats.get(pk=mandat_id)
        except Mandat.DoesNotExist:
            return None

    def get_autorisation(self, mandat_id, autorisation_id):
        try:
            return self.get_mandat(mandat_id).autorisations.get(pk=autorisation_id)
        except (AttributeError, Autorisation.DoesNotExist):
            return None

    def normalize_birthplace(self):
        if not self.birthplace:
            return None

        normalized_birthplace = self.birthplace.zfill(5)
        if normalized_birthplace != self.birthplace:
            self.birthplace = normalized_birthplace
            self.save(update_fields=["birthplace"])

        return self.birthplace


class AutorisationDureeKeywords(models.TextChoices):
    SHORT = (
        "SHORT",
        "pour une durée de 1 jour",
    )
    LONG = (
        "LONG",
        "pour une durée de 1 an",
    )
    EUS_03_20 = (
        "EUS_03_20",
        "jusqu’à la fin de l’état d’urgence sanitaire ",
    )


def get_staff_organisation_name_id() -> int:
    try:
        return Organisation.objects.get(name=settings.STAFF_ORGANISATION_NAME).pk
    except Organisation.DoesNotExist:
        return 1


class MandatQuerySet(models.QuerySet):
    def active(self):
        return (
            self.exclude(expiration_date__lt=timezone.now())
            .filter(autorisations__revocation_date__isnull=True)
            .distinct()
        )


class Mandat(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="mandats",
        default=get_staff_organisation_name_id,
    )
    usager = models.ForeignKey(Usager, on_delete=models.PROTECT, related_name="mandats")
    creation_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField(default=timezone.now)
    duree_keyword = models.CharField(
        max_length=16, choices=AutorisationDureeKeywords.choices, null=True
    )
    is_remote = models.BooleanField(default=False)

    objects = MandatQuerySet.as_manager()

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expiration_date


class AutorisationQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(mandat__expiration_date__lt=timezone.now()).filter(
            revocation_date__isnull=True
        )

    def inactive(self):
        return self.filter(
            Q(mandat__expiration_date__lt=timezone.now())
            | (
                Q(mandat__expiration_date__gt=timezone.now())
                & Q(revocation_date__isnull=False)
            )
        )

    def expired(self):
        return self.filter(mandat__expiration_date__lt=timezone.now())

    def revoked(self):
        return self.filter(
            Q(mandat__expiration_date__gt=timezone.now())
            & Q(revocation_date__isnull=False)
        )

    def for_usager(self, usager):
        return self.filter(mandat__usager=usager)

    def for_demarche(self, demarche):
        return self.filter(demarche=demarche)

    def visible_by(self, aidant):
        return self.filter(mandat__organisation=aidant.organisation)


class Autorisation(models.Model):

    # Autorisation information
    aidant = models.ForeignKey(
        Aidant, on_delete=models.CASCADE, default=0, related_name="autorisations"
    )
    usager = models.ForeignKey(
        Usager, on_delete=models.CASCADE, default=0, related_name="autorisations",
    )
    demarche = models.CharField(blank=False, max_length=100)
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE, null=True, related_name="autorisations"
    )

    # Autorisation expiration date management
    creation_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField(default=timezone.now)
    revocation_date = models.DateTimeField(blank=True, null=True)

    # Journal entry creation information
    last_renewal_token = models.TextField(blank=False, default="No token provided")
    is_remote = models.BooleanField(default=False)

    objects = AutorisationQuerySet.as_manager()

    def __str__(self):
        return (
            f"Autorisation #{self.id} : "
            f"{self.usager} <-> {self.aidant} ({self.demarche})"
        )

    @property
    def is_revoked(self) -> bool:
        return True if self.revocation_date else False

    @property
    def is_expired(self) -> bool:
        return self.mandat.is_expired

    @property
    def duree_in_days(self):
        duree_for_computer = self.mandat.expiration_date - self.creation_date
        # we add one day so that duration is human friendly
        # i.e. for a human, there is one day between now and tomorrow at the same time,
        # and 0 for a computer
        return duree_for_computer.days + 1


class ConnectionQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expires_on__lt=timezone.now())


def default_connection_expiration_date():
    now = timezone.now()
    return now + timedelta(seconds=settings.FC_CONNECTION_AGE)


class Connection(models.Model):
    state = models.TextField()  # FS
    nonce = models.TextField(default="No Nonce Provided")  # FS
    CONNECTION_TYPE = (("FS", "FC as FS"), ("FI", "FC as FI"))  # FS
    connection_type = models.CharField(
        max_length=2, choices=CONNECTION_TYPE, default="FI", blank=False
    )
    demarches = ArrayField(models.TextField(default="No démarche"), null=True)  # FS
    duree_keyword = models.CharField(
        max_length=16, choices=AutorisationDureeKeywords.choices, null=True
    )
    mandat_is_remote = models.BooleanField(default=False)
    usager = models.ForeignKey(
        Usager,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )  # FS
    expires_on = models.DateTimeField(default=default_connection_expiration_date)  # FS
    access_token = models.TextField(default="No token provided")  # FS

    code = models.TextField()
    demarche = models.TextField(default="No demarche provided")
    aidant = models.ForeignKey(
        Aidant,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    complete = models.BooleanField(default=False)
    autorisation = models.ForeignKey(
        Autorisation,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )

    objects = ConnectionQuerySet.as_manager()

    class Meta:
        verbose_name = "connexion"

    def __str__(self):
        return f"Connexion #{self.id} - {self.usager}"

    @property
    def is_expired(self):
        return self.expires_on < timezone.now()


class JournalManager(models.Manager):
    def connection(self, aidant: Aidant):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier, action="connect_aidant"
        )
        return journal_entry

    def activity_check(self, aidant: Aidant):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier, action="activity_check_aidant"
        )
        return journal_entry

    def franceconnection_usager(self, aidant: Aidant, usager: Usager):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="franceconnect_usager",
        )
        return journal_entry

    def update_email_usager(self, aidant: Aidant, usager: Usager):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="update_email_usager",
        )
        return journal_entry

    def attestation(
        self,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        is_remote_mandat: bool,
        access_token: str,
        attestation_hash: str,
    ):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="create_attestation",
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            attestation_hash=attestation_hash,
            # COVID-19
            is_remote_mandat=is_remote_mandat,
            additional_information="Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
        )
        return journal_entry

    def autorisation_creation(self, autorisation: Autorisation, aidant: Aidant):
        usager = autorisation.mandat.usager

        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="create_autorisation",
            demarche=autorisation.demarche,
            duree=autorisation.duree_in_days,
            autorisation=autorisation.id,
            # COVID-19
            is_remote_mandat=True,
            additional_information="Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
        )
        return journal_entry

    def autorisation_use(
        self,
        aidant: Aidant,
        usager: Usager,
        demarche: str,
        access_token: str,
        autorisation: Autorisation,
    ):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="use_autorisation",
            demarche=demarche,
            access_token=access_token,
            autorisation=autorisation.id,
        )
        return journal_entry

    def autorisation_cancel(self, autorisation: Autorisation, aidant: Aidant):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=autorisation.mandat.usager.full_string_identifier,
            action="cancel_autorisation",
            demarche=autorisation.demarche,
            duree=autorisation.duree_in_days,
            autorisation=autorisation.id,
        )
        return journal_entry


class JournalQuerySet(models.QuerySet):
    def not_staff(self):
        return self.exclude(initiator__icontains=settings.STAFF_ORGANISATION_NAME)


class Journal(models.Model):
    ACTIONS = (
        ("connect_aidant", "Connexion d'un aidant"),
        ("activity_check_aidant", "Reprise de connexion d'un aidant"),
        ("franceconnect_usager", "FranceConnexion d'un usager"),
        ("update_email_usager", "L'email de l'usager a été modifié"),
        ("create_attestation", "Création d'une attestation"),
        ("create_autorisation", "Création d'une autorisation"),
        ("use_autorisation", "Utilisation d'une autorisation"),
        ("cancel_autorisation", "Révocation d'une autorisation"),
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
    autorisation = models.IntegerField(blank=True, null=True)
    attestation_hash = models.CharField(max_length=100, blank=True, null=True)
    additional_information = models.TextField(blank=True, null=True)
    is_remote_mandat = models.BooleanField(default=False)

    objects = JournalManager()
    stats_objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée de journal"
        verbose_name_plural = "entrées de journal"

    def __str__(self):
        return f"Entrée #{self.id} : {self.action} - {self.initiator}"

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        else:
            # COVID-19
            if self.is_remote_mandat:
                self.additional_information = (
                    "Mandat conclu à distance pendant "
                    "l'état d'urgence sanitaire (23 mars 2020)"
                )
            super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

    @property
    def usager_id(self):
        try:
            return int(self.usager.split(" - ")[1])
        except (IndexError, ValueError):
            return None

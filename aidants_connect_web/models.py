from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property


class Organisation(models.Model):
    name = models.TextField("Nom", default="No name provided")
    siret = models.BigIntegerField("N° SIRET", default=1)
    address = models.TextField("Adresse", default="No address provided")
    zipcode = models.CharField("Code Postal", max_length=10, default="0")

    def __str__(self):
        return f"{self.name}"

    @cached_property
    def num_active_aidants(self):
        return self.aidants.active().count()

    def admin_num_active_aidants(self):
        return self.num_active_aidants

    admin_num_active_aidants.short_description = "Nombre d'aidants actifs"

    @cached_property
    def num_mandats(self):
        return self.mandats.count()

    def admin_num_mandats(self):
        return self.num_mandats

    admin_num_mandats.short_description = "Nombre de mandats"


class AidantManager(UserManager):
    def active(self):
        return self.filter(is_active=True)


class Aidant(AbstractUser):
    profession = models.TextField(blank=False)
    organisation = models.ForeignKey(
        Organisation, null=True, on_delete=models.CASCADE, related_name="aidants"
    )

    objects = AidantManager()

    class Meta:
        verbose_name = "aidant"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return str(self)

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
        active_mandats = Mandat.objects.filter(organisation=self.organisation).active()
        user_list = active_mandats.values_list("usager", flat=True)
        return Usager.objects.filter(pk__in=user_list)

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
            return Journal.objects.filter(aidant=self).last().creation_date
        except AttributeError:
            return None

    def get_journal_create_attestation(self, access_token):
        """
        :return: the corresponding 'create_attestation' Journal entry initiated
        by the aidant
        """
        journal_create_attestation = Journal.objects.filter(
            aidant=self,
            action="create_attestation",
            access_token=access_token,
        ).last()
        return journal_create_attestation


class UsagerQuerySet(models.QuerySet):
    def active(self):
        return (
            self.filter(mandats__expiration_date__gt=timezone.now())
            .filter(mandats__autorisations__revocation_date__isnull=True)
            .distinct()
        )

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

    given_name = models.CharField("Prénom", max_length=255, blank=False)
    family_name = models.CharField("Nom", max_length=255, blank=False)
    preferred_username = models.CharField(max_length=255, blank=True)

    gender = models.CharField(
        "Genre",
        max_length=6,
        choices=GENDER_CHOICES,
        default=GENDER_FEMALE,
    )

    birthdate = models.DateField("Date de naissance", blank=False)
    birthplace = models.CharField(
        "Lieu de naissance", max_length=5, blank=True, null=True
    )
    birthcountry = models.CharField(
        "Pays de naissance",
        max_length=5,
        default=BIRTHCOUNTRY_FRANCE,
    )

    sub = models.TextField(blank=False, unique=True)
    email = models.EmailField(blank=False, default=EMAIL_NOT_PROVIDED)
    creation_date = models.DateTimeField("Date de création", default=timezone.now)

    objects = UsagerQuerySet.as_manager()

    class Meta:
        ordering = ["family_name", "given_name"]

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
        return str(self)

    def get_mandat(self, mandat_id):
        try:
            return self.mandats.get(pk=mandat_id)
        except Mandat.DoesNotExist:
            return None

    def get_autorisation(self, autorisation_id):
        """
        This method returns the Authorisation object with the id _autorisation_id_
        only if the Usager of the autorization is the current usager.
        Otherwise, returns None
        :param autorisation_id:
        :return: Autorisation object or None
        """
        try:
            autorisation = Autorisation.objects.get(pk=autorisation_id)
        except Autorisation.DoesNotExist:
            return None
        if autorisation.mandat.usager == self:
            return autorisation

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

    def inactive(self):
        return self.filter(
            Q(expiration_date__lt=timezone.now())
            | ~Q(autorisations__revocation_date__isnull=True)
        ).distinct()


class Mandat(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="mandats",
        default=get_staff_organisation_name_id,
    )
    usager = models.ForeignKey(Usager, on_delete=models.PROTECT, related_name="mandats")
    creation_date = models.DateTimeField("Date de création", default=timezone.now)
    expiration_date = models.DateTimeField("Date d'expiration", default=timezone.now)
    duree_keyword = models.CharField(
        "Durée", max_length=16, choices=AutorisationDureeKeywords.choices, null=True
    )
    is_remote = models.BooleanField("Signé à distance ?", default=False)

    objects = MandatQuerySet.as_manager()

    def __str__(self):
        return f"#{self.id}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expiration_date

    @property
    def is_active(self):
        # A `mandat` is considered `active` if it contains
        # at least one active `autorisation`.
        return self.autorisations.active().exists()

    def admin_is_active(self):
        return self.is_active

    admin_is_active.boolean = True
    admin_is_active.short_description = "is active"


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

    DEMARCHE_CHOICES = [
        (name, attributes["titre"]) for name, attributes in settings.DEMARCHES.items()
    ]

    # Autorisation information
    mandat = models.ForeignKey(
        Mandat, null=True, on_delete=models.CASCADE, related_name="autorisations"
    )
    demarche = models.CharField(max_length=16, choices=DEMARCHE_CHOICES)

    # Autorisation expiration date management
    revocation_date = models.DateTimeField("Date de révocation", blank=True, null=True)

    # Journal entry creation information
    last_renewal_token = models.TextField(blank=False, default="No token provided")

    objects = AutorisationQuerySet.as_manager()

    def __str__(self):
        return f"#{self.id} {self.mandat} {self.mandat.usager} {self.demarche}"

    @cached_property
    def creation_date(self):
        return self.mandat.creation_date

    @cached_property
    def expiration_date(self):
        return self.mandat.expiration_date

    @cached_property
    def is_expired(self) -> bool:
        return self.mandat.is_expired

    @property
    def is_revoked(self) -> bool:
        return True if self.revocation_date else False

    @property
    def duration_for_humans(self) -> int:
        duration_for_computer = self.expiration_date - self.creation_date

        # We add one day so that duration is human-friendly.
        # i.e. for a human, there is one day between now and tomorrow at the same time,
        # and 0 for a computer.
        return duration_for_computer.days + 1

    def revoke(self, aidant: Aidant, revocation_date=None):
        """
        revoke an autorisation and create the corresponding journal entry
        """
        if revocation_date is None:
            revocation_date = timezone.now()
        self.revocation_date = revocation_date
        self.save(update_fields=["revocation_date"])
        Journal.log_autorisation_cancel(self, aidant)


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


class JournalQuerySet(models.QuerySet):
    def excluding_staff(self):
        return self.exclude(aidant__organisation__name=settings.STAFF_ORGANISATION_NAME)


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
        ("import_totp_cards", "Importation de cartes TOTP"),
    )

    INFO_REMOTE_MANDAT = "Mandat conclu à distance pendant l'état d'urgence sanitaire (23 mars 2020)"  # noqa

    # mandatory
    action = models.CharField(max_length=30, choices=ACTIONS, blank=False)
    aidant = models.ForeignKey(
        Aidant, on_delete=models.PROTECT, related_name="journal_entries"
    )

    # automatic
    creation_date = models.DateTimeField(auto_now_add=True)

    # action dependant
    demarche = models.CharField(max_length=100, blank=True, null=True)
    usager = models.ForeignKey(
        Usager, null=True, on_delete=models.PROTECT, related_name="journal_entries"
    )
    duree = models.IntegerField(blank=True, null=True)  # En jours
    access_token = models.TextField(blank=True, null=True)
    autorisation = models.IntegerField(blank=True, null=True)
    attestation_hash = models.CharField(max_length=100, blank=True, null=True)
    additional_information = models.TextField(blank=True, null=True)
    is_remote_mandat = models.BooleanField(default=False)
    mandat = models.ForeignKey(
        Mandat, null=True, on_delete=models.PROTECT, related_name="journal_entries"
    )
    objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée de journal"
        verbose_name_plural = "entrées de journal"

    def __str__(self):
        return f"Entrée #{self.id} : {self.action} - {self.aidant}"

    def save(self, *args, **kwargs):
        if self.id:
            raise NotImplementedError("Editing is not allowed on journal entries")
        super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

    @classmethod
    def log_connection(cls, aidant: Aidant):
        return cls.objects.create(aidant=aidant, action="connect_aidant")

    @classmethod
    def log_activity_check(cls, aidant: Aidant):
        return cls.objects.create(aidant=aidant, action="activity_check_aidant")

    @classmethod
    def log_franceconnection_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            usager=usager,
            action="franceconnect_usager",
        )

    @classmethod
    def log_update_email_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            usager=usager,
            action="update_email_usager",
        )

    @classmethod
    def log_attestation_creation(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        is_remote_mandat: bool,
        access_token: str,
        attestation_hash: str,
    ):
        return cls.objects.create(
            aidant=aidant,
            usager=usager,
            action="create_attestation",
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            attestation_hash=attestation_hash,
            is_remote_mandat=is_remote_mandat,
        )

    @classmethod
    def log_autorisation_creation(cls, autorisation: Autorisation, aidant: Aidant):
        mandat = autorisation.mandat
        usager = mandat.usager

        return cls.objects.create(
            aidant=aidant,
            usager=usager,
            action="create_autorisation",
            demarche=autorisation.demarche,
            duree=autorisation.duration_for_humans,
            autorisation=autorisation.id,
            is_remote_mandat=mandat.is_remote,
        )

    @classmethod
    def log_autorisation_use(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarche: str,
        access_token: str,
        autorisation: Autorisation,
    ):
        return cls.objects.create(
            aidant=aidant,
            usager=usager,
            action="use_autorisation",
            demarche=demarche,
            access_token=access_token,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_autorisation_cancel(cls, autorisation: Autorisation, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            usager=autorisation.mandat.usager,
            action="cancel_autorisation",
            demarche=autorisation.demarche,
            duree=autorisation.duration_for_humans,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_mandat_cancel(cls, mandat: Mandat, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            usager=mandat.usager,
            action="cancel_mandat",
            mandat=mandat,
        )

    @classmethod
    def log_toitp_card_import(cls, aidant: Aidant, added: int, updated: int):
        message = f"{added} ajouts - {updated} modifications"
        return cls.objects.create(
            aidant=aidant, action="import_totp_cards", additional_information=message
        )

class CarteTOTP(models.Model):
    serial_number = models.CharField(max_length=100)
    seed = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "carte TOTP"
        verbose_name_plural = "cartes TOTP"

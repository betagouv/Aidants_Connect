from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


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

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_string_identifier(self):
        return f"{self.get_full_name()} - {self.organisation.name} - {self.email}"

    def may_perform(self, demarche, usager):
        """
        :param demarche:
        :param for_usager:
        :return: `True` if this aidant may perform the specified `demarche`
        for the specified `usager`, `False` otherwise.`
        """
        return Autorisation.objects.filter(
            demarche=demarche,
            expiration_date__gt=timezone.now(),
            mandat__organisation=self.organisation,
            mandat__usager=usager,
        ).exists()

    def get_usagers(self):
        """
        :return: a queryset of usagers who have a mandat (both active & expired)
        with the aidant's organisation.
        """
        return Usager.objects.visible_by(self).distinct()

    def get_usager(self, usager_id):
        """
        :return: an usager or `None` if the aidant isn't allowed
        by a mandat to access this usager.
        """
        try:
            return self.get_usagers().get(pk=usager_id)
        except Usager.DoesNotExist:
            return None

    def get_usagers_with_active_mandat(self):
        """
        :return: a queryset of usagers who have an active mandat
        with the aidant's organisation.
        """
        return self.get_usagers().active()

    def get_mandats(self):
        """
        :return: a queryset of mandats visible by this aidant.
        """
        return Mandat.objects.visible_by(self).distinct()

    def get_mandat(self, mandat_id):
        """
        :return: a mandat or `None` if this mandat is not
        visible by this aidant.
        """
        try:
            return self.get_mandats().get(pk=mandat_id)
        except Mandat.DoesNotExist:
            return None

    def get_mandats_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's mandats.
        """
        return self.get_mandats().for_usager(usager)

    def get_active_mandats_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's active mandats
        that are visible by this aidant.
        """
        return self.get_mandats_for_usager(usager).active()

    def get_expired_mandats_for_usager(self, usager):
        """
        :param usager:
        :return: a queryset of the specified usager's expired mandats
        that are visible by this aidant.
        """
        return self.get_mandats_for_usager(usager).expired()

    def get_active_demarches_for_usager(self, usager):
        """
        :param usager:
        :return: a list of demarches the usager has active mandats for
        in this aidant's organisation.
        """
        return self.get_active_mandats_for_usager(usager).values_list(
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

    def get_journal_create_mandat_print(self, access_token):
        """
        :return: the corresponding 'create_mandat_print' Journal entry initiated
        by the aidant
        """
        journal_create_mandat_print = Journal.objects.filter(
            initiator=self.full_string_identifier,
            action="create_mandat_print",
            access_token=access_token,
        ).last()
        return journal_create_mandat_print


class UsagerQuerySet(models.QuerySet):

    def active(self):
        return self.filter(mandats__expiration_date__gt=timezone.now()).distinct()

    def visible_by(self, aidant):
        """
        :param aidant:
        :return: a new QuerySet instance only filtering in the usagers who have
        a mandat with this aidant's organisation.
        """
        return self.filter(mandats__aidant__organisation=aidant.organisation).distinct()


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

    def normalize_birthplace(self):
        if not self.birthplace:
            return None

        normalized_birthplace = self.birthplace.zfill(5)
        if normalized_birthplace != self.birthplace:
            self.birthplace = normalized_birthplace
            self.save(update_fields=["birthplace"])

        return self.birthplace


class MandatQuerySet(models.QuerySet):

    def for_usager(self, usager):
        return self.filter(usager=usager)

    def visible_by(self, aidant):
        return self.filter(organisation=aidant.organisation)


class Mandat(models.Model):
    usager = models.ForeignKey(
        Usager, on_delete=models.CASCADE, related_name="mandats"
    )
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="mandats"
    )

    creation_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField()

    is_remote_mandat = models.BooleanField(default=False)

    objects = MandatQuerySet.as_manager()

    def __str__(self):
        return f"{self.usager} <-> {self.demarche} (#{self.id})"

    @cached_property
    def is_active(self):
        # A `mandat` is considered `active` if it contains
        # at least one active `autorisation`.
        return self.autorisations.active().exists()

    def admin_is_active(self):
        return self.is_active
    admin_is_active.boolean = True
    admin_is_active.short_description = "active"


class AutorisationQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            mandat__expiration_date__gt=timezone.now(),
            revocation_date__isnull=True,
        )

    def expired(self):
        return self.exclude(
            mandat__expiration_date__gt=timezone.now()
        )

    def revoked(self):
        return self.exclude(
            revocation_date__isnull=True
        )


class Autorisation(models.Model):

    DEMARCHE_CHOICES = [
        (name, attributes["titre"]) for name, attributes in settings.DEMARCHES.items()
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE, related_name="autorisations"
    )
    demarche = models.CharField(max_length=16, choices=DEMARCHE_CHOICES)

    last_usage_date = models.DateTimeField(blank=True, null=True)
    revocation_date = models.DateTimeField(blank=True, null=True)

    objects = AutorisationQuerySet.as_manager()

    def __str__(self):
        return f"{self.usager} <-> {self.demarche} (#{self.id})"

    @property
    def usager(self):
        return self.mandat.usager

    @cached_property
    def creation_date(self):
        # The creation date of an `autorisation` is the creation date
        # of the `mandat` in which it was declared.
        return self.mandat.creation_date

    @cached_property
    def expiration_date(self):
        # The expiration date of an `autorisation` is the expiration date
        # of the `mandat` in which it which it was declared.
        return self.mandat.expiration_date

    @property
    def is_expired(self):
        return timezone.now() > self.expiration_date

    @property
    def is_revoked(self):
        return self.revocation_date is not None

    @property
    def is_active(self):
        return not(self.is_expired or self.is_revoked)

    @property
    def duration_for_humans(self):
        duration_for_computers = self.expiration_date - self.creation_date
        # We add one day so that duration is human-friendly.
        # i.e. for a human, there is one day between now and tomorrow at the same time,
        # and 0 for a computer
        return duration_for_computers.days + 1

    def use(self):
        self.last_usage_date = timezone.now()
        self.save()

    def revoke(self):
        self.revocation_date = timezone.now()
        self.save()


class Attestation(models.Model):

    TYPE_CREATION = "creation"
    TYPE_REVOCATION = "revocation"
    TYPE_CHOICES = (
        (TYPE_CREATION, "Création"),
        (TYPE_REVOCATION, "Révocation"),
    )

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE, related_name="attestations"
    )

    creation_date = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_CREATION)
    data = JSONField(blank=True, null=True)
    document = models.FileField(blank=True, null=True)

    def __str__(self):
        return "#%d" % self.id


class ConnectionQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expires_on__lt=timezone.now())


def default_connection_expiration_date():
    now = timezone.now()
    return now + timedelta(seconds=settings.FC_CONNECTION_AGE)


class MandatDureeKeywords(models.TextChoices):
    SHORT = (
        "SHORT",
        "pour une durée de 1 jour",
    )
    LONG = (
        "LONG",
        "pour une durée de 1 an",
    )
    EUS_COVID_19 = (
        "EUS_COVID_19",
        "jusqu’à la fin de l’état d’urgence sanitaire ",
    )


class Connection(models.Model):
    state = models.TextField()  # FS
    nonce = models.TextField(default="No nonce provided")  # FS
    CONNECTION_TYPE = (("FS", "FC as FS"), ("FI", "FC as FI"))  # FS
    connection_type = models.CharField(
        max_length=2, choices=CONNECTION_TYPE, default="FI", blank=False
    )
    demarches = ArrayField(models.TextField(default="No démarche"), null=True)  # FS
    duree_keyword = models.CharField(
        max_length=16, choices=MandatDureeKeywords.choices, null=True
    )
    usager = models.ForeignKey(
        Usager, on_delete=models.CASCADE, blank=True, null=True, related_name="usagers"
    )  # FS
    expires_on = models.DateTimeField(default=default_connection_expiration_date)  # FS
    access_token = models.TextField(default="No token provided")  # FS

    code = models.TextField()
    demarche = models.TextField(default="No demarche provided")
    aidant = models.ForeignKey(
        Aidant, on_delete=models.CASCADE, blank=True, null=True, related_name="usagers"
    )
    complete = models.BooleanField(default=False)
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE, blank=True, null=True, related_name="usagers"
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

    def mandat_print(
        self,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        access_token: str,
        mandat_print_hash: str,
    ):
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="create_mandat_print",
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            mandat_print_hash=mandat_print_hash,
            # COVID-19
            is_remote_mandat=True,
            additional_information="Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
        )
        return journal_entry

    def mandat_creation(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="create_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree_in_days,
            access_token=mandat.last_mandat_renewal_date,
            mandat=mandat.id,
            # COVID-19
            is_remote_mandat=True,
            additional_information="Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
        )

        return journal_entry

    def mandat_update(self, mandat: Mandat):
        aidant = mandat.aidant
        usager = mandat.usager

        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="update_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree_in_days,
            access_token=mandat.last_mandat_renewal_date,
            mandat=mandat.id,
            # COVID-19
            is_remote_mandat=True,
            additional_information="Mandat conclu à distance "
            "pendant l'état d'urgence sanitaire (23 mars 2020)",
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
        journal_entry = self.create(
            initiator=aidant.full_string_identifier,
            usager=usager.full_string_identifier,
            action="use_mandat",
            demarche=demarche,
            access_token=access_token,
            mandat=mandat.id,
        )
        return journal_entry

    def mandat_cancel(self, mandat: Mandat):
        journal_entry = self.create(
            initiator=mandat.aidant.full_string_identifier,
            usager=mandat.usager.full_string_identifier,
            action="cancel_mandat",
            demarche=mandat.demarche,
            duree=mandat.duree_in_days,
            access_token=mandat.last_mandat_renewal_date,
            mandat=mandat.id,
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
        ("create_mandat_print", "Création d'un mandat papier"),
        ("create_mandat", "Création d'un mandat"),
        ("use_mandat", "Utilisation d'un mandat"),
        ("update_mandat", "Renouvellement d'un mandat"),
        ("cancel_mandat", "Révocation d'un mandat"),
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
    mandat_print_hash = models.CharField(max_length=100, blank=True, null=True)
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
            super(Journal, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Deleting is not allowed on journal entries")

    @property
    def usager_id(self):
        try:
            return int(self.usager.split(" - ")[1])
        except (IndexError, ValueError):
            return None

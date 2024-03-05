from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timedelta
from os import walk as os_walk
from os.path import dirname
from os.path import join as path_join
from re import sub as regex_sub
from typing import TYPE_CHECKING, Collection, Optional, Union

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import IntegrityError, models, transaction
from django.db.models import SET_NULL, Q, QuerySet
from django.template import defaultfilters, loader
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from django_otp.plugins.otp_totp.models import TOTPDevice
from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import PhoneNumber, PhoneNumberFormat, format_number, is_valid_number
from phonenumbers import parse as parse_number
from phonenumbers import region_code_for_country_code

from aidants_connect_common.constants import (
    AuthorizationDurationChoices,
    AuthorizationDurations,
)
from aidants_connect_web.constants import RemoteConsentMethodChoices
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    mandate_template_path,
)

from .journal import Journal
from .organisation import Organisation, get_staff_organisation_name_id
from .usager import Usager

if TYPE_CHECKING:
    from .aidant import Aidant

logger = logging.getLogger()


class MandatQuerySet(models.QuerySet):
    def exclude_outdated(self):
        return self.exclude(
            Q(expiration_date__lt=timezone.now() - timedelta(365))
            | Q(autorisations__revocation_date__lt=timezone.now() - timedelta(365))
        )

    def active(self):
        return (
            self.exclude(expiration_date__lt=timezone.now())
            .filter(autorisations__revocation_date__isnull=True)
            .distinct()
        )

    def inactive(self):
        return (
            self.exclude_outdated()
            .filter(
                Q(expiration_date__lt=timezone.now())
                | ~Q(autorisations__revocation_date__isnull=True)
            )
            .distinct()
        )

    def for_usager(self, usager):
        return self.filter(usager=usager)

    def renewable(self):
        return self.exclude_outdated().filter(
            ~Q(expiration_date__gt=timezone.now())
            | Q(autorisations__revocation_date__isnull=True)
        )


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
        "Durée", max_length=16, choices=AuthorizationDurationChoices.choices, null=True
    )

    is_remote = models.BooleanField("Signé à distance ?", default=False)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )

    template_path = models.TextField(
        "Template utilisé",
        null=True,
        blank=False,
        default=mandate_template_path,
        editable=False,
    )

    objects = MandatQuerySet.as_manager()

    def __str__(self):
        return f"#{self.id}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expiration_date

    @property
    def is_active(self):
        if self.is_expired:
            return False
        # A `mandat` is considered `active` if it contains
        # at least one active `autorisation`.
        return self.autorisations.active().exists()

    @property
    def can_renew(self):
        return (
            not self.is_expired or self.objects.renewable().filter(mandat=self).exists()
        )

    @cached_property
    def revocation_date(self) -> Optional[datetime]:
        """
        Returns the date of the most recently revoked authorization if all them
        were revoked, ``None``, otherwise.
        """
        return (
            self.autorisations.order_by("-revocation_date").first().revocation_date
            if self.was_explicitly_revoked and self.autorisations.exists()
            else None
        )

    @cached_property
    def template_repr(self):
        """Defines a stadard way to represent a Mandat in templates"""
        creation_date_repr = (
            f" le {defaultfilters.date(self.creation_date)}"
            if self.creation_date
            else ""
        )
        duree_keyword_repr = (
            f" pour une durée de {self.get_duree_keyword_display()}"
            if self.duree_keyword
            else ""
        )
        return f"signé avec {self.usager}{creation_date_repr}{duree_keyword_repr}"

    @cached_property
    def was_explicitly_revoked(self) -> bool:
        """
        Returns whether the mandate was explicitely revoked, independently of it's
        expiration date.
        """
        return not self.autorisations.exclude(revocation_date__isnull=False)

    def get_absolute_url(self):
        path = reverse("mandat_visualisation", kwargs={"mandat_id": self.pk})
        url = regex_sub(r"/+", "/", f"{settings.HOST}{path}")
        return f"https://{url}"

    def get_mandate_template_path(self) -> str | None:
        """Returns the template file path of the consent document that was presented
        to the user when the mandate was issued.

        :return: the template file relative path as can be used on Django's
        template engine (without `templates` prepended), otherwise `None`
        """
        return (
            self.template_path
            if self.template_path is not None
            else self._get_mandate_template_path_from_journal_hash()
        )

    def _get_mandate_template_path_from_journal_hash(self) -> Union[None, str]:
        """Legacy mode for `models.Mandat.text()`

        This will search which template file was used using the hash login in
        `models.Journal` entries and parse the template using it.

        :return: None when:
            - no log record could be found on this mandate
            - the original template file could not be found
        the template file relative path as can be used on Django's template engine
        (without `templates` prepended`) otherwise
        """

        journal_entries = Journal.find_attestation_creation_entries(self)

        if journal_entries.count() == 0:
            return None

        template_dir = dirname(
            loader.get_template(settings.MANDAT_TEMPLATE_PATH).origin.name
        )

        demarches = [it.demarche for it in self.autorisations.all()]

        for journal_entry in journal_entries:
            for _, _, filenames in os_walk(template_dir):
                for filename in filenames:
                    file_hash = generate_attestation_hash(
                        journal_entry.aidant,
                        self.usager,
                        demarches,
                        self.expiration_date,
                        journal_entry.creation_date.date().isoformat(),
                        path_join(settings.MANDAT_TEMPLATE_DIR, filename),
                    )

                    if file_hash == journal_entry.attestation_hash:
                        return path_join(settings.MANDAT_TEMPLATE_DIR, filename)

        return None

    def admin_is_active(self):
        return self.is_active

    admin_is_active.boolean = True
    admin_is_active.short_description = "is active"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if (
            self.remote_constent_method == RemoteConsentMethodChoices.SMS
            and not self.usager.phone
        ):
            raise IntegrityError("User phone must be set when remote consent is SMS")
        super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_attestation_or_none(cls, mandate_id):
        try:
            mandate = Mandat.objects.get(mandate_id)
            journal = Journal.find_attestation_creation_entries(mandate)
            # If the journal count is 1, let's use this, otherwise, we don't consider
            # the results to be sufficiently specific to display a hash
            if journal.count() == 1:
                return journal.first()
        except Exception:
            return None

    @classmethod
    def get_attestation_hash_or_none(cls, mandate_id) -> None | str:
        result = cls.get_attestation_or_none(mandate_id)
        return result.attestation_hash if result is not None else result

    @classmethod
    def find_soon_expired(cls, nb_days_before: int) -> QuerySet["Mandat"]:
        """Finds mandates that will be expired in less than `nb_days_before` days"""

        start = timezone.now()
        end = start + timedelta(days=nb_days_before)

        return cls.objects.filter(
            duree_keyword__in=(
                AuthorizationDurations.LONG,
                AuthorizationDurations.SEMESTER,
            ),
            expiration_date__range=(start, end),
        ).order_by("organisation", "expiration_date")

    @classmethod
    def transfer_to_organisation(cls, organisation: Organisation, ids: Collection[str]):
        failed_updates = []

        for mandate_id in ids:
            try:
                mandate = Mandat.objects.get(pk=mandate_id)
                journal = Mandat.get_attestation_or_none(mandate_id)

                with transaction.atomic():
                    mandate.organisation = organisation
                    mandate.save()

                    Journal.log_transfert_mandat(
                        mandate,
                        mandate.organisation,
                        getattr(journal, "attestation_hash", None),
                    )
                    if journal is not None:
                        journal.attestation_hash = generate_attestation_hash(
                            aidant=journal.aidant,
                            usager=mandate.usager,
                            demarches=journal.demarche,
                            expiration_date=mandate.expiration_date,
                            creation_date=mandate.expiration_date.date().isoformat(),
                            mandat_template_path=mandate.get_mandate_template_path(),
                            organisation_id=organisation.id,
                        )
                        journal.save()
            except Exception:
                failed_updates.append(mandate_id)
                logger.exception(
                    "An error happened while trying to transfer mandates to "
                    "another organisation"
                )

        return len(failed_updates) != 0, failed_updates

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(is_remote=False)
                    | (Q(is_remote=True) & ~Q(remote_constent_method=""))
                ),
                name="mandat_remote_mandate_method_set",
            ),
            # fmt: off
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                    | (
                        Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                        & ~Q(consent_request_id="")
                    )
                ),
                name="mandat_consent_request_id_set",
            ),
            # fmt: on
        ]


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

    @cached_property
    def was_separately_revoked(self) -> bool:
        """
        :return: `True` if the authorization's revocation date is considered
            different from the mandate's computed revocation date, `False` otherwise.
            **Notes:** The mandate's computed revocation date is the date of the most
            recently revoked authorization. The authorization's revocation date will be
            recently revoked authorization. The authorization's revocation date will be
            considered different if it was revoked outside a time window of 30 seconds
            around the mandate's computed reocation date. I.E., if it was revoked at
            least 15 seconds before or after the mandate.
        """
        if not self.is_revoked:
            return False

        if self.mandat.revocation_date is None:
            return True

        return abs(self.revocation_date - self.mandat.revocation_date) > timedelta(
            seconds=15
        )

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
        "Durée", max_length=16, choices=AuthorizationDurationChoices.choices, null=True
    )
    mandat_is_remote = models.BooleanField(default=False)
    user_phone = PhoneNumberField(blank=True)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )

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
        "aidants_connect_web.Aidant",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    organisation = models.ForeignKey(
        Organisation,
        blank=True,
        null=True,
        default=None,
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

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if (user_phone := self.user_phone) and isinstance(user_phone, PhoneNumber):
            # Test phone number is valid for provided region
            if not is_valid_number(user_phone):
                for region in set(settings.FRENCH_REGION_CODES) - {
                    region_code_for_country_code(self.user_phone.country_code)
                }:
                    parsed = parse_number(str(self.user_phone), region)
                    if is_valid_number(parsed):
                        user_phone = parsed
                        break
                else:
                    raise IntegrityError(
                        f"Phone number {user_phone} is not valid in any of the "
                        f"french region among {settings.FRENCH_REGION_CODES}"
                    )

            # Normalize phone number to international format
            self.user_phone = format_number(user_phone, PhoneNumberFormat.E164)
            if update_fields is not None:
                update_fields = {"user_phone"}.union(update_fields)

        super().save(force_insert, force_update, using, update_fields)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(aidant__isnull=True) & Q(organisation__isnull=True))
                    | (Q(aidant__isnull=False) & Q(organisation__isnull=False))
                ),
                name="aidant_and_organisation_set_together",
            ),
            models.CheckConstraint(
                check=(
                    Q(mandat_is_remote=False)
                    | (Q(mandat_is_remote=True) & ~Q(remote_constent_method=""))
                ),
                name="connection_remote_mandate_method_set",
            ),
            # fmt: off
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)
                    | (
                        Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)  # noqa: E501
                        & ~Q(user_phone="")
                    )
                ),
                name="connection_user_phone_set",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                    | (
                        Q(remote_constent_method__in=RemoteConsentMethodChoices.blocked_methods())  # noqa: E501
                        & ~Q(consent_request_id="")
                    )
                ),
                name="connection_consent_request_id_set",
            ),
        ]
        verbose_name = "connexion"

    def __str__(self):
        return f"Connexion #{self.id} - {self.usager}"

    @property
    def is_expired(self):
        return self.expires_on < timezone.now()


class CarteTOTP(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    seed = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    aidant = models.OneToOneField(
        "aidants_connect_web.Aidant",
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="carte_totp",
    )
    is_functional = models.BooleanField("Fonctionne correctement", default=True)
    totp_device = models.ForeignKey(
        TOTPDevice,
        on_delete=SET_NULL,
        related_name="totp_card",
        null=True,
        blank=True,
        default=None,
    )

    class Meta:
        verbose_name = "carte TOTP"
        verbose_name_plural = "cartes TOTP"

    def __str__(self):
        return self.serial_number

    def unlink_aidant(self):
        # AttributeError is thrown if totp_device is null
        with contextlib.suppress(AttributeError):
            self.totp_device.delete()
        self.aidant = None
        self.totp_device = None
        self.save(update_fields={"aidant", "totp_device"})

    @transaction.atomic
    def get_or_create_totp_device(self, confirmed=False):
        if self.totp_device:
            return self.totp_device

        device = TOTPDevice(
            key=self.seed,
            user=self.aidant,
            step=60,  # todo: some devices may have a different step!
            confirmed=confirmed,
            name=f"Carte n° {self.serial_number}",
        )
        device.save()
        self.totp_device = device
        self.save()
        return device

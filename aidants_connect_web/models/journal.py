from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Collection, Iterable, Optional

from django.conf import settings
from django.db import IntegrityError, models
from django.db.models import Q, QuerySet

from phonenumber_field.modelfields import PhoneNumberField
from phonenumbers import PhoneNumber, PhoneNumberFormat, format_number

from aidants_connect_common.utils.constants import (
    JOURNAL_ACTIONS,
    AuthorizationDurations,
    JournalActionKeywords,
)
from aidants_connect_web.constants import RemoteConsentMethodChoices

if TYPE_CHECKING:
    from .aidant import Aidant
    from .mandat import Autorisation, Mandat
    from .organisation import Organisation
    from .usager import Usager

logger = logging.getLogger()


class JournalQuerySet(models.QuerySet):
    def excluding_staff(self):
        return self.exclude(aidant__organisation__name=settings.STAFF_ORGANISATION_NAME)

    def has_user_explicitly_consented(
        self,
        user: Usager,
        aidant: Aidant,
        remote_constent_method: RemoteConsentMethodChoices,
        user_phone: str,
        consent_request_id: str,
    ) -> JournalQuerySet:
        return self.filter(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            usager=user,
            aidant=aidant,
            remote_constent_method=remote_constent_method,
            is_remote_mandat=True,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        ).exists()

    def find_sms_consent_requests(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_consent_recap(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_user_consent(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def find_sms_user_consent_or_denial(
        self, user_phone: PhoneNumber, consent_request_id: str | None = None
    ):
        return self._find_consent_actions(
            action=[
                JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
                JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
            ],
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    def _find_consent_actions(
        self,
        action: str | Collection,
        user_phone: PhoneNumber,
        consent_request_id: str | None = None,
    ):
        kwargs = {"user_phone": format_number(user_phone, PhoneNumberFormat.E164)}
        if isinstance(action, str):
            kwargs["action"] = action
        else:
            kwargs["action__in"] = list(action)
        if consent_request_id:
            kwargs["consent_request_id"] = consent_request_id

        return self.filter(**kwargs)

    def find_demarches_for_organisation(self, org: Organisation):
        return self.filter(
            organisation=org,
            action__in=[
                JournalActionKeywords.CREATE_ATTESTATION,
                JournalActionKeywords.USE_AUTORISATION,
                JournalActionKeywords.CANCEL_MANDAT,
                JournalActionKeywords.INIT_RENEW_MANDAT,
                JournalActionKeywords.CANCEL_AUTORISATION,
            ],
        )


class Journal(models.Model):
    INFO_REMOTE_MANDAT = "Mandat conclu à distance pendant l'état d'urgence sanitaire (23 mars 2020)"  # noqa

    # mandatory
    action = models.CharField(max_length=30, choices=JOURNAL_ACTIONS, blank=False)
    aidant = models.ForeignKey(
        "aidants_connect_web.Aidant",
        on_delete=models.PROTECT,
        related_name="journal_entries",
        null=True,
    )

    # automatic
    creation_date = models.DateTimeField(auto_now_add=True)

    # action dependant
    demarche = models.CharField(max_length=100, blank=True, null=True)
    usager = models.ForeignKey(
        "aidants_connect_web.Usager",
        null=True,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )
    duree = models.IntegerField(blank=True, null=True)  # En jours
    access_token = models.TextField(blank=True, null=True)
    autorisation = models.IntegerField(blank=True, null=True)
    attestation_hash = models.CharField(max_length=100, blank=True, null=True)
    additional_information = models.TextField(blank=True, null=True)

    is_remote_mandat = models.BooleanField(default=False)
    user_phone = PhoneNumberField(blank=True)
    consent_request_id = models.CharField(max_length=36, blank=True, default="")
    remote_constent_method = models.CharField(
        "Méthode de consentement à distance",
        choices=RemoteConsentMethodChoices.model_choices,
        blank=True,
        max_length=200,
    )
    mandat = models.ForeignKey(
        "aidants_connect_web.Mandat",
        null=True,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )

    organisation = models.ForeignKey(
        "aidants_connect_web.Organisation",
        null=True,
        on_delete=models.PROTECT,
        related_name="journal_entries",
    )

    objects = JournalQuerySet.as_manager()

    class Meta:
        verbose_name = "entrée de journal"
        verbose_name_plural = "entrées de journal"
        constraints = [
            # All infos are set when creating a journal for remote mandate by SMS
            models.CheckConstraint(
                check=(
                    ~Q(
                        action__in=[
                            JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                            JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
                            JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
                            JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
                        ]
                    )
                    | (
                        Q(aidant__isnull=False)
                        & Q(is_remote_mandat=True)
                        & Q(user_phone__isnull_or_blank=False)
                        & Q(consent_request_id__isnull_or_blank=False)
                        & Q(remote_constent_method=RemoteConsentMethodChoices.SMS.name)
                        & Q(additional_information__isnull_or_blank=False)
                    )
                ),
                name="infos_set_remote_mandate_by_sms",
            )
        ]

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
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.CONNECT_AIDANT,
        )

    @classmethod
    def log_activity_check(cls, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.ACTIVITY_CHECK_AIDANT,
        )

    @classmethod
    def log_card_association(cls, responsable: Aidant, aidant: Aidant, sn: str):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_ASSOCIATION,
            additional_information=more_info,
        )

    @classmethod
    def log_card_validation(cls, responsable: Aidant, aidant: Aidant, sn: str):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_VALIDATION,
            additional_information=more_info,
        )

    @classmethod
    def log_card_dissociation(
        cls, responsable: Aidant, aidant: Aidant, sn: str, reason: str
    ):
        more_info = f"aidant.id = {aidant.id}, sn = {sn}, reason = {reason}"
        return cls.objects.create(
            aidant=responsable,
            organisation=responsable.organisation,
            action=JournalActionKeywords.CARD_DISSOCIATION,
            additional_information=more_info,
        )

    @classmethod
    def log_franceconnection_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.FRANCECONNECT_USAGER,
        )

    @classmethod
    def log_update_email_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.UPDATE_EMAIL_USAGER,
        )

    @classmethod
    def log_update_phone_usager(cls, aidant: Aidant, usager: Usager):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.UPDATE_PHONE_USAGER,
        )

    @classmethod
    def log_init_renew_mandat(
        cls,
        aidant: Aidant,
        usager: Usager,
        demarches: list,
        duree: int,
        is_remote_mandat: bool,
        access_token: str,
        remote_constent_method: str,
        user_phone: str,
        consent_request_id: str,
    ):
        if is_remote_mandat and not remote_constent_method:
            raise IntegrityError(
                "remote_constent_method must be set when mandate is remote"
            )

        if (
            remote_constent_method in RemoteConsentMethodChoices.blocked_methods()
            and not consent_request_id
        ):
            raise IntegrityError(
                "consent_request_id must be set when mandate uses one of the following "
                f"consent methods {RemoteConsentMethodChoices.blocked_methods()}"
            )

        if (
            remote_constent_method == RemoteConsentMethodChoices.SMS.name
            and not user_phone
        ):
            raise IntegrityError(
                "user_phone must be set when " "mandate uses SMS consent method"
            )

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.INIT_RENEW_MANDAT,
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            is_remote_mandat=is_remote_mandat,
            remote_constent_method=remote_constent_method,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
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
        mandat: Mandat,
        remote_constent_method: str,
        user_phone: str,
        consent_request_id: str,
    ):
        if is_remote_mandat and not remote_constent_method:
            raise IntegrityError(
                "remote_constent_method must be set when mandate is remote"
            )

        if (
            remote_constent_method in RemoteConsentMethodChoices.blocked_methods()
            and not consent_request_id
        ):
            raise IntegrityError(
                "consent_request_id must be set when mandate uses one of the following "
                f"consent methods {RemoteConsentMethodChoices.blocked_methods()}"
            )

        if (
            remote_constent_method == RemoteConsentMethodChoices.SMS.name
            and not user_phone
        ):
            raise IntegrityError(
                "user_phone must be set when " "mandate uses SMS consent method"
            )

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.CREATE_ATTESTATION,
            demarche=",".join(demarches),
            duree=duree,
            access_token=access_token,
            attestation_hash=attestation_hash,
            mandat=mandat,
            is_remote_mandat=is_remote_mandat,
            remote_constent_method=remote_constent_method,
            user_phone=user_phone,
            consent_request_id=consent_request_id,
        )

    @classmethod
    def log_autorisation_creation(cls, autorisation: Autorisation, aidant: Aidant):
        mandat = autorisation.mandat
        usager = mandat.usager

        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.CREATE_AUTORISATION,
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
            organisation=aidant.organisation,
            usager=usager,
            action=JournalActionKeywords.USE_AUTORISATION,
            demarche=demarche,
            access_token=access_token,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_autorisation_cancel(cls, autorisation: Autorisation, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=autorisation.mandat.usager,
            action=JournalActionKeywords.CANCEL_AUTORISATION,
            demarche=autorisation.demarche,
            duree=autorisation.duration_for_humans,
            autorisation=autorisation.id,
        )

    @classmethod
    def log_mandat_cancel(cls, mandat: Mandat, aidant: Aidant):
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            usager=mandat.usager,
            action=JournalActionKeywords.CANCEL_MANDAT,
            mandat=mandat,
        )

    @classmethod
    def log_toitp_card_import(cls, aidant: Aidant, added: int, updated: int):
        message = f"{added} ajouts - {updated} modifications"
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.IMPORT_TOTP_CARDS,
            additional_information=message,
        )

    @classmethod
    def log_transfert_mandat(
        cls,
        mandat: Mandat,
        previous_organisation: Organisation,
        previous_hash: Optional[str],
    ):
        return cls.objects.create(
            mandat=mandat,
            organisation=mandat.organisation,
            action=JournalActionKeywords.TRANSFER_MANDAT,
            additional_information=(
                f"previous_organisation = {previous_organisation.pk}, "
                f"previous_hash = {previous_hash}"
            ),
        )

    @classmethod
    def find_attestation_creation_entries(cls, mandat: Mandat) -> QuerySet["Journal"]:
        # Let's first search by mandate
        journal = cls.objects.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION, mandat=mandat
        )
        if journal.count() == 1:
            return journal

        # If the journal entry was created prior to this modification, there's no
        # association between the journal entry and the mandate so we need to search
        # using the naive heuristics
        start = mandat.creation_date - timedelta(hours=24)
        end = mandat.creation_date + timedelta(hours=24)
        return cls.objects.filter(
            action=JournalActionKeywords.CREATE_ATTESTATION,
            usager=mandat.usager,
            aidant__organisation=mandat.organisation,
            creation_date__range=(start, end),
        )

    @classmethod
    def log_switch_organisation(cls, aidant: Aidant, previous: Organisation):
        more_info = (
            f"previous organisation : {previous.name} (#{previous.id}) -"
            f"new organisation : {aidant.organisation.name} (#{aidant.organisation.id})"
        )
        return cls.objects.create(
            aidant=aidant,
            organisation=aidant.organisation,
            action=JournalActionKeywords.SWITCH_ORGANISATION,
            additional_information=more_info,
        )

    @classmethod
    def log_user_consents_sms(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_denies_sms(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_mandate_recap_sms_sent(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def log_user_consent_request_sms_sent(
        cls,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        return cls._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            aidant,
            demarche,
            duree,
            remote_constent_method,
            user_phone,
            consent_request_id,
            message,
        )

    @classmethod
    def _log_sms_event(
        cls,
        action: str,
        aidant: Aidant,
        demarche: str | Iterable,
        duree: int | str,
        remote_constent_method: RemoteConsentMethodChoices | str,
        user_phone: PhoneNumber,
        consent_request_id: str,
        message: str,
    ) -> Journal:
        remote_constent_method = (
            RemoteConsentMethodChoices[remote_constent_method]
            if isinstance(remote_constent_method, str)
            else remote_constent_method
        )
        demarche = demarche if isinstance(demarche, str) else ",".join(demarche)
        duree = (
            AuthorizationDurations.duration(duree) if isinstance(duree, str) else duree
        )

        return cls.objects.create(
            action=action,
            aidant=aidant,
            demarche=demarche,
            duree=duree,
            remote_constent_method=remote_constent_method,
            is_remote_mandat=True,
            user_phone=format_number(user_phone, PhoneNumberFormat.E164),
            consent_request_id=consent_request_id,
            additional_information=f"message={message}",
        )

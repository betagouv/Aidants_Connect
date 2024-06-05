from enum import auto
from typing import Set

from django.conf import settings
from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _

from aidants_connect_common.constants import DictChoices, TextChoicesEnum

OTP_APP_DEVICE_NAME = "OTP App for user %s"


class RemoteConsentMethodChoices(DictChoices):
    LEGACY = {
        "label": _("Par signature sur papier"),
        "description": _(
            "Vous devrez imprimer le mandat et le faire signer à "
            "la personne accompagnée aussi vite que possible. "
            "Ce mandat vous protège légalement."
        ),
        "img_src": "images/icons/Papier.svg",
    }

    SMS = {
        "label": _("Par SMS"),
        "description": _(
            "Un SMS est envoyé à la personne accompagnée pour recueillir "
            "son consentement. L'exécution du mandat est bloqué tant que "
            "la personne n'a pas répondu positivement."
        ),
        "img_src": "images/icons/SMS.svg",
    }

    @staticmethod
    def _human_readable_name(enum_item):
        return enum_item.label["label"]

    @staticmethod
    def blocked_methods() -> Set[str]:
        if settings.FF_ACTIVATE_SMS_CONSENT:
            return {RemoteConsentMethodChoices.SMS.name}
        else:
            return set()


class NotificationType(TextChoicesEnum):
    INFORMATION = "Information"
    NEW_FEATURE = "Nouveauté sur Aidants Connect"
    WARNING = "Alerte"


class ReferentRequestStatuses(TextChoices):
    STATUS_WAITING_LIST_HABILITATION = ("waitling_list", "Liste d'attente")
    STATUS_NEW = ("new", "Nouvelle")
    STATUS_PROCESSING = ("processing", "Éligibilité validée")
    STATUS_PROCESSING_P2P = ("processing_p2p", "Éligibilité validée (pair-à-pair)")
    STATUS_VALIDATED = ("validated", "Validée")
    STATUS_REFUSED = ("refused", "Refusée")
    STATUS_CANCELLED = ("cancelled", "Annulée")
    STATUS_CANCELLED_BY_RESPONSABLE = (
        "status_cancelled_by_responsable",
        "Annulée par le ou la référente",
    )

    @staticmethod
    def formation_registerable():
        return (
            ReferentRequestStatuses.STATUS_PROCESSING,
            ReferentRequestStatuses.STATUS_PROCESSING_P2P,
            ReferentRequestStatuses.STATUS_VALIDATED,
        )

    @staticmethod
    def cancellable_by_responsable():
        return (
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
            ReferentRequestStatuses.STATUS_NEW,
            ReferentRequestStatuses.STATUS_PROCESSING,
            ReferentRequestStatuses.STATUS_PROCESSING_P2P,
            ReferentRequestStatuses.STATUS_VALIDATED,
        )


class HabilitationRequestCourseType(IntegerChoices):
    CLASSIC = (auto(), "Parcours classique")
    P2P = (auto(), "Parcours pair-à-pair")

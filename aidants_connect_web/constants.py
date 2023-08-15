from typing import Set

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from aidants_connect_common.utils.constants import DictChoices, TextChoicesEnum


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
    pass

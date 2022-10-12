from typing import Set

from django.utils.translation import gettext_lazy as _

from aidants_connect_common.utils.constants import DictChoices


class RemoteConsentMethodChoices(DictChoices):
    LEGACY = {
        "label": _("Historique"),
        "description": _(
            "Vous devrez imprimer le mandat et le faire signer à "
            "la personne accompagnée aussi vite que possible. "
            "Ce mandat vous protège légalement."
        ),
    }
    SMS = {
        "label": _("Par SMS"),
        "description": _(
            "Un SMS est envoyé à la personne accompagnée pour receuillir "
            "son consentement. L'exécution du mandat est bloqué tant que "
            "la personne n'a pas répondu positivement."
        ),
    }

    @staticmethod
    def _human_readable_name(enum_item):
        return enum_item.label["label"]

    @staticmethod
    def blocked_methods() -> Set[str]:
        return {RemoteConsentMethodChoices.SMS.name}

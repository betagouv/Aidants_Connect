from enum import auto
from typing import Self

from django.db.models import IntegerChoices
from django.utils.version import PY311

if PY311:
    from enum import property as enum_property
else:
    from types import DynamicClassAttribute as enum_property


class HabilitationFormStep(IntegerChoices):
    ISSUER = auto(), "Informations demandeur"
    SIRET_VERIFICATION = auto(), "Numéro Siret de la structure"
    ORGANISATION = auto(), "Informations structure"
    REFERENT = auto(), "Référent Aidants Connect"
    PERSONNEL = auto(), "Les aidants de ma structure"
    SUMMARY = auto(), "Récapitulatif & validation"

    @enum_property
    def enum(self):
        return self.__class__

    @enum_property
    def next(self) -> Self | None:
        try:
            return list(self.__class__)[self.value]
        except IndexError:
            return None

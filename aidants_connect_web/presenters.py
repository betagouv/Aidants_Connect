from enum import Enum
from typing import Any

from django.template.defaultfilters import yesno
from django.urls import reverse

from aidants_connect.utils import strtobool
from aidants_connect_common.presenters import GenericHabilitationRequestPresenter
from aidants_connect_web.constants import HabilitationRequestCourseType
from aidants_connect_web.models import Aidant, HabilitationRequest


class HabilitationRequestItemPresenter(GenericHabilitationRequestPresenter):
    def __init__(self, form, idx):
        super().__init__()
        self._form = form
        self.idx = idx

    @property
    def pk(self):
        return self.idx

    @property
    def edit_endpoint(self):
        return reverse(
            "api_espace_responsable_aidant_new_edit", kwargs={"idx": self.idx}
        )

    @property
    def full_name(self) -> str:
        return f'{self._form["first_name"].value()} {self._form["last_name"].value()}'

    @property
    def email(self) -> str:
        return str(self._form["email"].value())

    @property
    def details_fields(self) -> list[dict[str, Any]]:
        return [
            # email profession conseiller_numerique organisation
            {"label": "Email", "value": self.email},
            {"label": "Profession", "value": self._form["profession"].value()},
            {
                "label": "Conseiller numérique",
                "value": yesno(
                    strtobool(self._form["conseiller_numerique"].value()), "Oui,Non"
                ),
            },
            {
                "label": "Organisation",
                "value": getattr(
                    getattr(self._form, "cleaned_data", {}).get("organisation"),
                    "name",
                    "",
                ),
            },
        ]

    @property
    def form(self) -> str:
        return self._form.as_hidden()

    @property
    def details_id(self):
        return f"added-form-{self.idx}"


class FormationType(Enum):
    CLASSIC = "classic"
    P2P = "p2p"
    FNE = "fne"


class FormationStatus(Enum):
    FORMATION_ATTENDANCE = "formation_attendance"
    FORMATION_COMPLETED = "formation_completed"


class AidantFormationPresenter:
    def __init__(self, aidant: Aidant):
        habilitation_request = (
            HabilitationRequest.objects.filter(email=aidant.email)
            .order_by("-created_at")
            .last()
        )
        self._habilitation_request = habilitation_request
        self._formation_attendant = None
        if (
            self._habilitation_request
            and self._habilitation_request.formations.exists()
        ):
            self._formation_attendant = self._habilitation_request.formations.first()

    @property
    def info_available(self) -> bool:
        """Decide weither formation info should be displayed."""
        if not self._habilitation_request:
            return False
        if self._habilitation_request.formation_done:
            return True
        # at this point, with two previous guards we know formation_done == False
        if not self._habilitation_request.formations.exists():
            # with no formation_attendant, we do not know if aidant is registered
            return False
        return True

    @property
    def type(self) -> FormationType | None:
        if not self.info_available:
            return None
        if self._habilitation_request.created_by_fne:
            return FormationType.FNE
        elif (
            self._habilitation_request.course_type == HabilitationRequestCourseType.P2P
        ):
            return FormationType.P2P
        else:
            return FormationType.CLASSIC

    @property
    def status(self) -> FormationStatus | None:
        if not self.info_available:
            return None
        if self._habilitation_request.formation_done:
            return FormationStatus.FORMATION_COMPLETED
        if self._formation_attendant:
            return FormationStatus.FORMATION_ATTENDANCE
        # no other cases should happen, caught by formation_info_available guard

    @property
    def date_formation(self) -> str | None:
        if not self.info_available:
            return None
        if self._formation_attendant:
            return self._formation_attendant.formation.start_datetime.strftime(
                "%d/%m/%Y"
            )
        return None

    @property
    def organisation_name(self) -> str | None:
        if not self.info_available:
            return None
        if self._formation_attendant:
            return self._formation_attendant.formation.organisation.name
        return None

    @property
    def organisation_email(self) -> str | None:
        if not self.info_available:
            return None
        if self._formation_attendant:
            contacts = self._formation_attendant.formation.organisation.contacts
            return contacts[0] if contacts else None
        return None

    @property
    def date_test_pix(self) -> str | None:
        if not self.info_available or not self._habilitation_request.date_test_pix:
            return None
        if (
            self._habilitation_request.formation_done
            and self._habilitation_request.date_test_pix
        ):
            return self._habilitation_request.date_test_pix.strftime("%d/%m/%Y")
        return None

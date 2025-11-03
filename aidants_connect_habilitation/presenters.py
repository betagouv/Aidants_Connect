from typing import Any

from django.template.defaultfilters import yesno
from django.urls import reverse

from aidants_connect.utils import strtobool
from aidants_connect_common.constants import RequestStatusConstants
from aidants_connect_common.presenters import GenericHabilitationRequestPresenter
from aidants_connect_habilitation.models import AidantRequest, OrganisationRequest


class ProfileCardAidantRequestPresenter(GenericHabilitationRequestPresenter):
    def __init__(self, org: OrganisationRequest, req: AidantRequest):
        self.org: OrganisationRequest = org
        self.req: AidantRequest = req

    @property
    def pk(self):
        return self.req.pk

    @property
    def edit_endpoint(self):
        if self.org.status not in self.org.Status.aidant_registrable:
            return None

        return reverse(
            "api_habilitation_aidant_edit",
            kwargs={
                "issuer_id": self.req.organisation.issuer.issuer_id,
                "uuid": self.req.organisation.uuid,
                "aidant_id": self.req.pk,
            },
        )

    @property
    def edit_href(self) -> str | None:
        return None

    @property
    def full_name(self) -> str:
        return self.req.get_full_name()

    @property
    def email(self) -> str:
        return self.req.email

    @property
    def details_fields(self) -> list[dict[str, Any]]:
        return [
            # email profession conseiller_numerique organisation
            {"label": "Email", "value": self.req.email},
            {"label": "Profession", "value": self.req.profession},
            {
                "label": "Conseiller numérique",
                "value": yesno(self.req.conseiller_numerique, "Oui,Non"),
            },
            {"label": "Organisation", "value": self.req.organisation},
        ]


class ProfileCardAidantRequestPresenter2(GenericHabilitationRequestPresenter):
    @property
    def pk(self):
        return self.idx

    @property
    def edit_endpoint(self):
        return reverse(
            "api_habilitation_new_aidants_idx",
            kwargs={
                "issuer_id": f"{self.organisation.issuer.issuer_id}",
                "uuid": f"{self.organisation.uuid}",
                "idx": self.idx,
            },
        )

    @property
    def full_name(self):
        return f'{self._form["first_name"].value()} {self._form["last_name"].value()}'

    @property
    def email(self):
        return str(self._form["email"].value())

    @property
    def details_fields(self):
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
            {"label": "Organisation", "value": self.organisation.name},
        ]

    @property
    def form(self) -> str:
        return self._form

    @property
    def details_id(self):
        return f"added-form-{self.idx}"

    def __init__(self, organisation, form, idx):
        super().__init__()
        self.organisation = organisation
        self._form = form
        self.idx = idx


class OrganisationRequestPresenter:
    def __init__(self, organisation: OrganisationRequest):
        self.organisation = organisation

    @property
    def issuer_editable(self) -> bool:
        """Determine if issuer section is editable based on status"""
        return self.organisation.status in [
            RequestStatusConstants.NEW,
            RequestStatusConstants.CHANGES_REQUIRED,
            RequestStatusConstants.VALIDATED,
            # Ajoutez les autres statuts selon vos règles
        ]

    @property
    def organisation_editable(self) -> bool:
        """Determine if organisation section is editable based on status"""
        return self.organisation.status in [
            RequestStatusConstants.NEW,
            RequestStatusConstants.CHANGES_REQUIRED,
            # Pas VALIDATED pour l'organisation selon votre exemple
        ]

    @property
    def manager_editable(self) -> bool:
        """Determine if manager section is editable based on status"""
        return self.organisation.status in [
            RequestStatusConstants.NEW,
            RequestStatusConstants.CHANGES_REQUIRED,
            RequestStatusConstants.VALIDATED,
        ]

    @property
    def personnel_editable(self) -> bool:
        """Determine if aidants section is editable based on status"""
        return self.organisation.status in [
            RequestStatusConstants.NEW,
            RequestStatusConstants.CHANGES_REQUIRED,
            RequestStatusConstants.VALIDATED,
        ]

    @property
    def request_submitable(self) -> bool:
        """Determine if request can be submitted based on status"""
        return self.organisation.status in [
            RequestStatusConstants.NEW,
        ]

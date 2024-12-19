from typing import Any

from django.template.defaultfilters import yesno
from django.urls import reverse

from aidants_connect.utils import strtobool
from aidants_connect_common.presenters import GenericHabilitationRequestPresenter


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

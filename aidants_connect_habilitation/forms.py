from typing import List, Tuple

from django.conf import settings
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.forms import (
    BaseModelFormSet,
    BooleanField,
    CharField,
    ChoiceField,
    FileField,
    modelformset_factory,
)
from django.forms.formsets import MAX_NUM_FORM_COUNT, TOTAL_FORM_COUNT
from django.urls import reverse
from django.utils.html import format_html

from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberInternationalFallbackWidget

from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect.common.forms import (
    PatchedErrorList,
    PatchedErrorListForm,
    PatchedForm,
)
from aidants_connect_habilitation import models
from aidants_connect_habilitation.models import (
    AidantRequest,
    DataPrivacyOfficer,
    Manager,
    OrganisationRequest,
    PersonWithResponsibilities,
)
from aidants_connect_web.models import OrganisationType


class IssuerForm(PatchedErrorListForm):
    phone = PhoneNumberField(
        initial="",
        label="Téléphone",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
        required=False,
    )

    def __init__(self, render_non_editable=False, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(**kwargs)
        self.render_non_editable = render_non_editable
        if self.render_non_editable:
            self.auto_id = False
            for name, field in self.fields.items():
                field.disabled = True
                field.widget.attrs.update(id=f"id_{name}")

    def add_prefix(self, field_name):
        """
        Return empty ``name`` HTML attribute when ``self.render_non_editable is True``
        """
        return "" if self.render_non_editable else super().add_prefix(field_name)

    def add_initial_prefix(self, field_name):
        """
        Return empty ``name`` HTML attribute when ``self.render_non_editable is True``
        """
        return (
            "" if self.render_non_editable else super().add_initial_prefix(field_name)
        )

    class Meta:
        model = models.Issuer
        exclude = ["issuer_id", "email_verified"]


class OrganisationRequestForm(PatchedErrorListForm):
    type = ChoiceField(required=True, choices=RequestOriginConstants.choices)

    name = CharField(
        label="Nom de la structure",
    )

    zipcode = CharField(
        label="Code Postal",
        max_length=10,
        error_messages={
            "required": "Le champ « code postal » est obligatoire.",
        },
    )
    city = CharField(
        label="Ville",
        max_length=255,
        error_messages={
            "required": "Le champ « ville » est obligatoire.",
        },
    )

    is_private_org = BooleanField(
        label=(
            "Cochez cette case si vous faites cette demande pour une structure privée "
            "(hors associations)"
        ),
        required=False,
    )

    partner_administration = CharField(
        label="Renseignez l’administration avec laquelle vous travaillez",
        required=False,
    )

    public_service_delegation_attestation = FileField(
        label="Téléversez ici une attestation de délégation de service public",
        help_text="Taille maximale : 2 Mo. Formats supportés : PDF, JPG, PNG.",
        required=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.widget_attrs(
            "type_other",
            {
                "data-dynamic-form-target": "typeOtherInput",
                "data-displayed-label": "Veuillez préciser le type d’organisation",
            },
        )
        self.widget_attrs(
            "type",
            {
                "data-action": "change->dynamic-form#onTypeChange",
                "data-dynamic-form-target": "typeInput",
                "data-other-value": RequestOriginConstants.OTHER.value,
            },
        )
        self.widget_attrs(
            "is_private_org",
            {
                "data-action": "change->dynamic-form#onIsPrivateOrgChange",
                "data-dynamic-form-target": "privateOrgInput",
            },
        )
        self.widget_attrs(
            "france_services_label",
            {
                "data-action": "change->dynamic-form#onFranceServicesChange",
                "data-dynamic-form-target": "franceServicesInput",
            },
        )

    def clean_type(self):
        return OrganisationType.objects.get(pk=int(self.data["type"]))

    def clean_type_other(self):
        if int(self.data["type"]) != RequestOriginConstants.OTHER.value:
            return ""

        if not self.data["type_other"]:
            label = self.fields["type_other"].label
            raise ValidationError(
                f"Le champ « {label} » doit être rempli si la "
                f"structure est de type {RequestOriginConstants.OTHER.label}."
            )

        return self.data["type_other"]

    class Meta:
        model = models.OrganisationRequest
        fields = [
            "type",
            "type_other",
            "name",
            "siret",
            "address",
            "zipcode",
            "city",
            "is_private_org",
            "partner_administration",
            "public_service_delegation_attestation",
            "france_services_label",
            "france_services_number",
            "web_site",
            "mission_description",
            "avg_nb_demarches",
        ]


class PersonWithResponsibilitiesForm(PatchedErrorListForm):
    phone = PhoneNumberField(
        initial="",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
        required=False,
    )

    class Meta:
        model = PersonWithResponsibilities
        exclude = ["id"]


class ManagerForm(PatchedErrorListForm):
    zipcode = CharField(
        label="Code Postal",
        max_length=10,
        error_messages={
            "required": "Le champ « code postal » est obligatoire.",
        },
    )

    city = CharField(
        label="Ville",
        max_length=255,
        error_messages={
            "required": "Le champ « ville » est obligatoire.",
        },
    )

    class Meta(PersonWithResponsibilitiesForm.Meta):
        model = Manager


class DataPrivacyOfficerForm(PersonWithResponsibilitiesForm):
    class Meta(PersonWithResponsibilitiesForm.Meta):
        model = DataPrivacyOfficer


class AidantRequestForm(PatchedErrorListForm):
    class Meta:
        model = AidantRequest
        exclude = ["organisation"]
        error_messages = {
            NON_FIELD_ERRORS: {
                "unique_together": (
                    "Il y a déjà un aidant avec la même adresse e-mail dans "
                    "cette organisation. Chaque aidant doit avoir son propre "
                    "e-mail nominatif."
                ),
            }
        }


class BaseAidantRequestFormSet(BaseModelFormSet):
    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", AidantRequest.objects.none())
        kwargs.setdefault("error_class", PatchedErrorList)
        super().__init__(**kwargs)

    def management_form_widget_attrs(self, widget_name: str, attrs: dict):
        widget = self.management_form.fields[widget_name].widget
        for attr_name, attr_value in attrs.items():
            widget.attrs[attr_name] = attr_value


AidantRequestFormSet = modelformset_factory(
    AidantRequestForm.Meta.model, AidantRequestForm, formset=BaseAidantRequestFormSet
)


class PersonnelForm:
    MANAGER_FORM_PREFIX = "manager"
    DPO_FORM_PREFIX = "dpo"
    AIDANTS_FORMSET_PREFIX = "aidants"

    @property
    def non_field_errors(self):
        errors = self.manager_form.non_field_errors().copy()

        for error in self.data_privacy_officer_form.non_field_errors():
            errors.append(error)

        for error in self.aidants_formset.non_form_errors():
            errors.append(error)

        return errors

    def __init__(self, **kwargs):
        def merge_kwargs(prefix):
            previous_prefix = kwargs.get("prefix")
            local_kwargs = {}

            form_kwargs_prefixes = {
                self.MANAGER_FORM_PREFIX,
                self.DPO_FORM_PREFIX,
                self.AIDANTS_FORMSET_PREFIX,
            }

            for k, v in kwargs.items():
                """
                Let us dispatch form kwargs to specific forms by using their prefixes.

                For instance, PersonnelForm(dpo_instance=some_instance) will
                disptach to DataPrivacyOfficerForm(instance=some_instance).
                """
                kwarg_prefix = k.split("_")
                if len(kwarg_prefix) > 1 and kwarg_prefix[0] in form_kwargs_prefixes:
                    if kwarg_prefix[0] == prefix:
                        k_prefix_removed = k[len(f"{prefix}_") :]
                        local_kwargs[k_prefix_removed] = v
                else:
                    local_kwargs[k] = v

            return {
                **local_kwargs,
                "prefix": prefix
                if not previous_prefix
                else f"{prefix}_{previous_prefix}",
            }

        self.manager_form = ManagerForm(**merge_kwargs(self.MANAGER_FORM_PREFIX))
        self.data_privacy_officer_form = DataPrivacyOfficerForm(
            **merge_kwargs(self.DPO_FORM_PREFIX)
        )
        self.aidants_formset = AidantRequestFormSet(
            **merge_kwargs(self.AIDANTS_FORMSET_PREFIX)
        )

        self.aidants_formset.management_form_widget_attrs(
            TOTAL_FORM_COUNT, {"data-personnel-form-target": "managmentFormCount"}
        )
        self.aidants_formset.management_form_widget_attrs(
            MAX_NUM_FORM_COUNT, {"data-personnel-form-target": "managmentFormMaxCount"}
        )

    def is_valid(self):
        return (
            self.manager_form.is_valid()
            and self.data_privacy_officer_form.is_valid()
            and self.aidants_formset.is_valid()
        )

    def save(
        self, organisation: OrganisationRequest, commit=True
    ) -> Tuple[Manager, DataPrivacyOfficer, List[AidantRequest]]:
        for form in self.aidants_formset:
            form.instance.organisation = organisation

        manager_instance, dpo_instance, aidants_instances = (
            self.manager_form.save(commit),
            self.data_privacy_officer_form.save(commit),
            self.aidants_formset.save(commit),
        )

        organisation.manager = manager_instance
        organisation.data_privacy_officer = dpo_instance
        organisation.save()

        return manager_instance, dpo_instance, aidants_instances

    save.alters_data = True


class ValidationForm(PatchedForm):
    cgu = BooleanField(
        required=True,
        label='J’ai pris connaissance des <a href="{url}">'
        "conditions générales d’utilisation</a> et je les valide.",
    )
    dpo = BooleanField(
        required=True,
        label="Je confirme que le délégué à la protection des données "
        "de mon organisation est informé de ma demande.",
    )
    professionals_only = BooleanField(
        required=True,
        label="Je confirme que la liste des aidants à habiliter contient "
        "exclusivement des aidants professionnels. Elle ne contient "
        "donc ni service civique, ni bénévole, ni apprenti, ni stagiaire.",
    )
    without_elected = BooleanField(
        required=True,
        label="Je confirme qu’aucun élu n’est impliqué dans l’habilitation "
        "Aidants Connect. Le responsable Aidants Connect ainsi que les aidants "
        "à habiliter ne sont pas des élus.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cgu = self["cgu"]
        cgu.label = format_html(cgu.label, url=reverse("cgu"))

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import (
    BaseFormSet,
    BooleanField,
    CharField,
    ChoiceField,
    FileField,
    formset_factory,
)
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

    partner_administration = CharField(
        label="Renseignez l’administration avec laquelle vous travaillez",
        required=False,
    )

    public_service_delegation_attestation = FileField(
        label="Téléversez ici une attestation de délégation de service public",
        help_text="Taille maximale : 2 Mo. Formats supportés : PDF, JPG, PNG.",
        required=False,
    )

    def clean_type(self):
        try:
            return OrganisationType.objects.get(pk=int(self.data["type"]))
        except OrganisationType.DoesNotExist:
            raise ValidationError("Mauvais type d'organisation soumis")

    def clean_type_other(self):
        if (
            int(self.data["type"]) == RequestOriginConstants.OTHER.value
            and not self.data["type_other"]
        ):
            label = self.fields["type_other"].label
            raise ValidationError(
                f"Le champ « {label} » doit être rempli si la "
                f"structure est de type {RequestOriginConstants.OTHER.label}."
            )

        return self.data["type_other"]

    class Meta:
        model = models.OrganisationRequest
        exclude = ["issuer", "manager", "data_privacy_officer", "status", "draft_id"]


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


class BaseAidantRequestFormSet(BaseFormSet):
    def __init__(self, **kwags):
        kwags.setdefault("error_class", PatchedErrorList)
        super().__init__(**kwags)

    def save(self, organisation: OrganisationRequest, commit=True):
        result = []
        for sub_form in self:
            sub_form.instance.organisation = organisation
            result.append(sub_form.save(commit=commit))

        return result


AidantRequestFormSet = formset_factory(
    AidantRequestForm, formset=BaseAidantRequestFormSet
)


class PersonnelForm:
    def __init__(self, **kwargs):
        def merge_kwargs(prefix):
            previous_prefix = kwargs.get("prefix")
            return {
                **kwargs,
                "prefix": prefix
                if not previous_prefix
                else f"{prefix}_{previous_prefix}",
            }

        self.manager_form = ManagerForm(**merge_kwargs("manager"))
        self.data_privacy_officer_form = DataPrivacyOfficerForm(**merge_kwargs("dpo"))
        self.aidants_formset = AidantRequestFormSet(**merge_kwargs("aidants"))

    def is_valid(self):
        return (
            self.manager_form.is_valid()
            and self.data_privacy_officer_form.is_valid()
            and self.aidants_formset.is_valid()
        )

    def save(self, organisation: OrganisationRequest, commit=True):
        return (
            self.manager_form.save(commit),
            self.data_privacy_officer_form.save(commit),
            self.aidants_formset.save(organisation, commit),
        )


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

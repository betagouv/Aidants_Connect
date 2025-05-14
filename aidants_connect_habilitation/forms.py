from re import sub as re_sub

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    FileField,
    HiddenInput,
    Media,
    ModelForm,
    RadioSelect,
    Textarea,
    TypedChoiceField,
    model_to_dict,
    modelformset_factory,
)
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from dsfr.forms import DsfrBaseForm

from aidants_connect.utils import strtobool
from aidants_connect_common.constants import RequestOriginConstants
from aidants_connect_common.forms import (
    AcPhoneNumberField,
    AsHiddenMixin,
    BaseHabilitationRequestFormSet,
    CleanEmailMixin,
    ConseillerNumerique,
    PatchedForm,
    PatchedModelForm,
)
from aidants_connect_common.widgets import JSModulePath
from aidants_connect_habilitation import models
from aidants_connect_habilitation.models import (
    AidantRequest,
    Manager,
    OrganisationRequest,
)
from aidants_connect_habilitation.presenters import ProfileCardAidantRequestPresenter2
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import HabilitationRequest, OrganisationType


class AddressValidatableForm(DsfrBaseForm):
    template_name = "aidants_connect_habilitation/forms/address-validatable.html"

    address = CharField(
        label="Adresse",
        widget=Textarea(
            attrs={
                "rows": 2,
                "data-address-autocomplete-target": "autcompleteInput",
                "data-action": "focus->address-autocomplete#onAutocompleteFocus",
            }
        ),
    )

    zipcode = CharField(
        label="Code Postal",
        max_length=10,
        error_messages={
            "required": "Le champ « code postal » est obligatoire.",
        },
        widget=CharField.widget(
            attrs={"data-address-autocomplete-target": "zipcodeInput"}
        ),
    )

    city = CharField(
        label="Ville",
        max_length=255,
        error_messages={
            "required": "Le champ « ville » est obligatoire.",
        },
        widget=CharField.widget(
            attrs={"data-address-autocomplete-target": "cityInput"}
        ),
    )

    city_insee_code = CharField(
        widget=HiddenInput(
            attrs={"data-address-autocomplete-target": "cityInseeCodeInput"}
        ),
        required=False,
    )

    department_insee_code = CharField(
        widget=HiddenInput(
            attrs={"data-address-autocomplete-target": "dptInseeCodeInput"}
        ),
        required=False,
    )

    @property
    def media(self):
        return super().media + Media(
            css={"all": (static("css/autocomplete.css"),)},
            js=(JSModulePath("js/address-autocomplete.mjs"),),
        )

    @property
    def address_fieldset_fields(self):
        for field_name in AddressValidatableForm.declared_fields:
            yield self[field_name]

    def clean_zipcode(self):
        data: str = re_sub(r"\s+", "", self.cleaned_data["zipcode"]).strip()
        if not data.isdecimal():
            raise ValidationError("Veuillez entrer un code postal valide")

        return data

    def get_context(self):
        return {
            **super().get_context(),
            "GOUV_ADDRESS_SEARCH_API_DISABLED": (
                settings.GOUV_ADDRESS_SEARCH_API_DISABLED
            ),
            "GOUV_ADDRESS_SEARCH_API_BASE_URL": (
                settings.GOUV_ADDRESS_SEARCH_API_BASE_URL
            ),
        }

    def address_fieldset(self, **kwargs):
        return self.render(
            template_name=AddressValidatableForm.template_name,
            context=self.get_context(),
        )


class IssuerForm(ModelForm, CleanEmailMixin, DsfrBaseForm):
    template_name = "aidants_connect_habilitation/forms/issuer.html"

    phone = AcPhoneNumberField(initial="", label="Téléphone", required=False)

    class Meta:
        model = models.Issuer
        exclude = ["issuer_id", "email_verified"]


class OrganisationRequestForm(ModelForm, AddressValidatableForm):
    template_name = "aidants_connect_habilitation/forms/organisation.html"
    type = ChoiceField(
        required=True, choices=RequestOriginConstants.choices, label="Type de structure"
    )
    type_other = CharField(
        label="Veuillez préciser le type d’organisation", required=False
    )

    france_services_label = BooleanField(
        label="Structure labellisée France Services", required=False
    )
    france_services_number = CharField(
        label="Numéro d’immatriculation France Services", required=False
    )

    name = CharField(label="Nom")

    @property
    def media(self):
        return super().media + Media(js=(JSModulePath("js/organisation-form.mjs"),))

    def clean_type(self):
        return OrganisationType.objects.get(pk=int(self.data["type"]))

    def clean_type_other(self):
        if int(self.data["type"]) != RequestOriginConstants.OTHER.value:
            return ""

        if not self.data["type_other"]:
            raise ValidationError(
                f"Ce champ doit être rempli si la "
                f"structure est de type {RequestOriginConstants.OTHER.label}."
            )

        return self.data["type_other"]

    def clean_france_services_number(self):
        if not self.data.get("france_services_label", False):
            return ""

        if not self.data["france_services_number"]:
            raise ValidationError(
                "Vous avez indiqué que la structure est labellisée France Services : "
                "merci de renseigner son numéro d’immatriculation France Services."
            )

        return self.data["france_services_number"]

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
            "city_insee_code",
            "department_insee_code",
            "france_services_label",
            "france_services_number",
            "web_site",
            "mission_description",
            "avg_nb_demarches",
        ]
        widgets = {"mission_description": Textarea(attrs={"rows": "4"})}


class ReferentForm(
    ModelForm, ConseillerNumerique, CleanEmailMixin, AddressValidatableForm
):
    template_name = "aidants_connect_habilitation/forms/referent.html"

    phone = AcPhoneNumberField(
        initial="",
        label="Numéro de téléphone mobile",
        required=True,
    )

    is_aidant = TypedChoiceField(
        label="C’est aussi un aidant",
        choices=((True, "Oui"), (False, "Non")),
        coerce=lambda value: bool(strtobool(value)),
        widget=RadioSelect,
    )

    address_same_as_org = TypedChoiceField(
        label="S'agit-il de la même adresse que celle de la structure administrative ?",
        choices=((True, "Oui"), (False, "Non")),
        coerce=lambda value: bool(strtobool(value)),
        widget=RadioSelect(
            attrs={
                "data-action": "manager-form#onAddressSameAsOrgChanged",
                "data-manager-form-target": "addressSameAsOrgRadio",
            }
        ),
    )

    address = CharField(
        label="Adresse",
        widget=Textarea(
            attrs={
                "rows": 2,
                "data-manager-form-target": "autcompleteInput",
                "data-address-autocomplete-target": "autcompleteInput",
                "data-action": "focus->address-autocomplete#onAutocompleteFocus",
            }
        ),
    )

    zipcode = CharField(
        label="Code Postal",
        max_length=10,
        error_messages={
            "required": "Le champ « code postal » est obligatoire.",
        },
        widget=CharField.widget(
            attrs={
                "data-address-autocomplete-target": "zipcodeInput",
                "data-manager-form-target": "zipcodeInput",
            }
        ),
    )

    city = CharField(
        label="Ville",
        max_length=255,
        error_messages={
            "required": "Le champ « ville » est obligatoire.",
        },
        widget=CharField.widget(
            attrs={
                "data-address-autocomplete-target": "cityInput",
                "data-manager-form-target": "cityInput",
            }
        ),
    )

    @property
    def media(self):
        return super().media + Media(js=(JSModulePath("js/manager-form.mjs"),))

    def __init__(self, organisation: OrganisationRequest, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            # Otherwise test fail
            self.data = self.data.copy()
            self.data.setdefault("address_same_as_org", False)
        self.organisation = organisation

    def _clean_field(self, name):
        # copy of BaseForm._clean_fields for 1 field
        bf = self[name]
        value = bf.initial if bf.field.disabled else bf.data
        try:
            if isinstance(bf.field, FileField):
                value = bf.field.clean(value, bf.initial)
            else:
                value = bf.field.clean(value)
            self.cleaned_data[name] = value
            if hasattr(self, "clean_%s" % name):
                value = getattr(self, "clean_%s" % name)()
                self.cleaned_data[name] = value
        except ValidationError as e:
            self.add_error(name, e)

    def _clean_fields(self):
        self._clean_field("address_same_as_org")
        address_same_as_org = self.cleaned_data["address_same_as_org"]

        if address_same_as_org:
            object_data = model_to_dict(
                self.organisation, AddressValidatableForm.declared_fields
            )
            self.data = self.data.copy()
            for field in AddressValidatableForm.declared_fields:
                self.data[self.add_prefix(field)] = object_data.get(field, None)

        for name in self.fields:
            if name != "address_same_as_org":
                self._clean_field(name)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data.pop("address_same_as_org", None)
        return cleaned_data

    def get_context(self):
        issuer_data = model_to_dict(
            self.organisation.issuer, exclude=(*IssuerForm.Meta.exclude, "id")
        )
        # Fields of type PhoneNumberField are not natively JSON serializable
        issuer_data["phone"] = str(issuer_data["phone"])

        return {**super().get_context(), "issuer_data": issuer_data}

    def save(self, commit=True):
        result = super().save(commit)
        self.organisation.manager = result
        self.organisation.save(update_fields=("manager",))
        return result

    class Meta:
        model = Manager
        include = ("conseiller_numerique",)
        exclude = (
            "pk",
            "habilitation_request",
        )


class EmailOrganisationValidationError(ValidationError):
    _MESSAGE = _(
        "Il y a déjà un aidant ou une aidante avec l'adresse email '%(email)s' "
        "dans cette organisation. Chaque aidant ou aidante doit avoir "
        "son propre e-mail nominatif."
    )

    def __init__(self, email, message=_MESSAGE):
        super().__init__(
            message,
            code="unique_together",
            params={"email": email},
        )


class ManagerEmailOrganisationValidationError(EmailOrganisationValidationError):
    def __init__(self, email):
        super().__init__(
            email,
            _(
                "Le ou la référente de cette organisation est aussi déclarée"
                "comme aidante avec l'email '%(email)s'. Chaque aidant ou aidante "
                "doit avoir son propre e-mail nominatif."
            ),
        )


class AidantRequestForm(
    ConseillerNumerique, CleanEmailMixin, ModelForm, DsfrBaseForm, AsHiddenMixin
):
    template_name = "aidants_connect_habilitation/forms/aidant.html"

    def __init__(self, organisation: OrganisationRequest, *args, **kwargs):
        self.organisation = organisation
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = super().clean_email()

        query = Q(organisation=self.organisation) & Q(email__iexact=email)
        if getattr(self.instance, "pk"):
            # This user already exists, and we need to verify that
            # we are not trying to modify its email with the email
            # of antoher aidant in the organisation
            query = query & ~Q(pk=self.instance.pk)
        if AidantRequest.objects.filter(query).exists():
            raise EmailOrganisationValidationError(email)

        if (
            self.organisation.manager
            and self.organisation.manager.is_aidant
            and self.organisation.manager.email == email
        ):
            raise ManagerEmailOrganisationValidationError(email)

        return email

    def save(self, commit=True):
        self.instance.organisation = self.organisation
        if self.organisation.organisation:
            hr, _ = HabilitationRequest.objects.get_or_create(
                email=self.instance.email,
                organisation=self.instance.organisation.organisation,
                defaults=dict(
                    origin=HabilitationRequest.ORIGIN_HABILITATION,
                    first_name=self.instance.first_name,
                    last_name=self.instance.last_name,
                    profession=self.instance.profession,
                    conseiller_numerique=self.instance.conseiller_numerique,
                    status=ReferentRequestStatuses.STATUS_PROCESSING,
                ),
            )
            self.instance.habilitation_request = hr
        return super().save(commit)

    class Meta:
        model = AidantRequest
        exclude = ["organisation", "habilitation_request"]


class BaseAidantRequestFormSet(BaseHabilitationRequestFormSet):
    presenter_class = ProfileCardAidantRequestPresenter2
    default_error_messages = {
        "too_few_forms": (
            "Vous devez déclarer au moins 1 aidant si le ou la référente de "
            "l'organisation n'est pas elle-même déclarée comme aidante"
        )
    }

    @property
    def action_url(self):
        return reverse(
            "api_habilitation_new_aidants",
            kwargs={
                "issuer_id": f"{self.organisation.issuer.issuer_id}",
                "uuid": f"{self.organisation.uuid}",
            },
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._validate_min = cls.validate_min
        cls.validate_min = property(cls.validate_min_get)

    def __init__(
        self, organisation: OrganisationRequest, empty_permitted=None, **kwargs
    ):
        self.organisation = organisation
        self.empty_permitted = empty_permitted
        kwargs["queryset"] = self.organisation.aidant_requests.order_by("pk").all()
        super().__init__(**kwargs)

    def validate_min_get(self):
        return (
            not getattr(self.organisation.manager, "is_aidant", False)
            or self._validate_min
        )

    def validate_unique(self):
        emails = {
            existing_email: []
            for existing_email in self.get_queryset().values_list("email", flat=True)
        }
        manager_email = (
            {self.organisation.manager.email}
            if getattr(self.organisation.manager, "is_aidant", False)
            else set()
        )
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            email = form.cleaned_data.get("email")

            # Do not test if email is empty: may be a legitimate empty form
            if not email:
                continue

            emails.setdefault(email, [])
            emails[email].append(form)

            if email in manager_email:
                form.add_error(
                    "email",
                    "Cette personne a le même email que la personne que vous avez "
                    "déclarée comme référente. Chaque aidant doit avoir "
                    "une adresse email unique.",
                )

        for email, grouped_forms in emails.items():
            if len(grouped_forms) > 1:
                for form in grouped_forms:
                    form.add_error(
                        "email",
                        EmailOrganisationValidationError(email),
                    )

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["organisation"] = self.organisation
        if self.empty_permitted is not None:
            kwargs["empty_permitted"] = self.empty_permitted
        return kwargs

    def get_presenter_kwargs(self, idx, form) -> dict:
        return {"organisation": self.organisation, "form": form, "idx": idx}


AidantRequestFormSet = modelformset_factory(
    AidantRequestForm.Meta.model,
    AidantRequestForm,
    formset=BaseAidantRequestFormSet,
)


class ValidationForm(DsfrBaseForm, AsHiddenMixin):
    template_name = "aidants_connect_habilitation/forms/validation.html"  # noqa: E501
    cgu = BooleanField(
        required=True,
        label='J’ai pris connaissance des&nbsp;<a href="{url}" class="fr-link">'
        "conditions générales d’utilisation</a>&nbsp;et je les valide.",
    )
    not_free = BooleanField(
        required=True,
        label="Je confirme avoir compris que la formation est payante "
        'et je me suis renseigné(e) sur les&nbsp;<a href="{simulator_url}" class="fr-link">modalités de financements</a>&nbsp;disponibles.',  # noqa: E501
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
        "Aidants Connect. Le ou la référente Aidants Connect ainsi que les aidants "
        "à habiliter ne sont pas des élus.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cgu = self["cgu"]
        not_free = self["not_free"]
        cgu.label = format_html(cgu.label, url=reverse("cgu"))
        not_free.label = format_html(
            not_free.label, simulator_url="https://tally.so/r/mO0Xkg"
        )

    def save(
        self, organisation: OrganisationRequest, commit=True
    ) -> OrganisationRequest:
        organisation.prepare_request_for_ac_validation(self.cleaned_data)
        return organisation

    save.alters_data = True


class RequestViewForm(PatchedForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(
        self, organisation: OrganisationRequest, commit=True
    ) -> OrganisationRequest:
        organisation.prepare_request_for_ac_validation(self.cleaned_data)
        return organisation

    save.alters_data = True


class RequestMessageForm(PatchedModelForm):
    content = CharField(label="Votre message", widget=Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget_attrs("content", {"data-message-form-target": "textarea"})

    class Meta:
        model = models.RequestMessage
        fields = ["content"]


class AdminAcceptationOrRefusalForm(PatchedForm):
    email_subject = CharField(label="Sujet de l’email", required=True)
    email_body = CharField(label="Contenu de l’email", widget=Textarea, required=True)

    def __init__(self, organisation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisation = organisation

from re import sub as re_sub
from typing import List, Tuple, Union
from urllib.parse import quote, unquote

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import (
    BaseModelFormSet,
    BooleanField,
    CharField,
    ChoiceField,
    Form,
    HiddenInput,
    ModelForm,
    RadioSelect,
    Textarea,
    TextInput,
    TypedChoiceField,
    modelformset_factory,
)
from django.forms.formsets import MAX_NUM_FORM_COUNT, TOTAL_FORM_COUNT
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from dsfr.forms import DsfrBaseForm

from aidants_connect.utils import strtobool
from aidants_connect_common.constants import MessageStakeholders, RequestOriginConstants
from aidants_connect_common.forms import (
    AcPhoneNumberField,
    CleanEmailMixin,
    ConseillerNumerique,
    PatchedErrorList,
    PatchedForm,
    PatchedModelForm,
)
from aidants_connect_common.utils.gouv_address_api import Address, search_adresses
from aidants_connect_habilitation import models
from aidants_connect_habilitation.models import (
    AidantRequest,
    Manager,
    OrganisationRequest,
    PersonWithResponsibilities,
    RequestMessage,
)
from aidants_connect_web.models import OrganisationType


class AddressValidatableMixin(Form):
    DEFAULT_CHOICE = "DEFAULT"

    # Necessary so dynamically setting properties
    # in __init__ does not mess with original classes
    class XChoiceField(ChoiceField):
        def validate(self, value):
            # Disable value validation, only keep value requirement
            if value in self.empty_values and self.required:
                raise ValidationError(self.error_messages["required"], code="required")

    class XRadioSelect(RadioSelect):
        pass

    # This field should not be rendered. It is just used by
    # the JS front to disable backend validation
    skip_address_validation = BooleanField(required=False)

    alternative_address = XChoiceField(
        label="Veuillez sélectionner votre adresse dans les propositions ci-dessous :",
        choices=((DEFAULT_CHOICE, "Laisser l'adresse inchangée"),),
        widget=XRadioSelect(attrs={"class": "choice-field"}),
        required=False,
    )

    @property
    def should_display_addresses_select(self):
        return self.__required

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__required = False

        required = property(lambda _: self.__required)
        setattr(AddressValidatableMixin.XChoiceField, "required", required)
        setattr(AddressValidatableMixin.XRadioSelect, "is_required", required)

    def clean_skip_address_validation(self):
        # For expressiveness, the name transmitted byt the JS front
        # will be ``skip_backend_validation`` whereas the name of the form
        # field is ``skip_address_validation``.
        return self.data.get("skip_backend_validation", False)

    def clean_alternative_address(self):
        if self.cleaned_data["skip_address_validation"]:
            self.__required = False
            return None

        alternative_address = self.cleaned_data.get("alternative_address")

        if alternative_address == self.DEFAULT_CHOICE:
            return self.DEFAULT_CHOICE
        elif alternative_address:
            return Address.parse_raw(unquote(alternative_address))
        else:
            results = search_adresses(self.get_address_for_search())

            # Case not result returned (most likely, HTTP request failed)
            if len(results) == 0:
                return self.DEFAULT_CHOICE

            # There is 1 result and it almost 100% matches
            if (
                len(results) == 1
                and results[0].label == self.get_address_for_search()
                and results[0].score > 0.90
            ):
                return results[0]

            self.__required = True

            for result in results:
                self.fields["alternative_address"].choices = [
                    (quote(result.json()), result.label),
                    *self.fields["alternative_address"].choices,
                ]

            raise ValidationError("Plusieurs choix d'adresse sont possibles")

    def post_clean(self):
        """
        Call this method at the end of your own Form's ``clean`` method to
        prevent.
        """
        alternative_address = self.cleaned_data.pop("alternative_address", None)
        if isinstance(alternative_address, Address):
            self.autocomplete(alternative_address)

    def get_address_for_search(self) -> str:
        """
        Implement this method to provide a string to search on the address
        API. This method may, for instance, concatenate street name, zipcode
        and city fields that may otherwise be seperated.
        """
        raise NotImplementedError()

    def autocomplete(self, address: Address):
        """
        Implement this method to fill your Form with the address when the
        API returns one result that matches with more than 90% probability.
        """
        raise NotImplementedError()


class CleanZipCodeMixin:
    def clean_zipcode(self):
        data: str = re_sub(r"\s+", "", self.cleaned_data["zipcode"]).strip()
        if not data.isdecimal():
            raise ValidationError("Veuillez entrer un code postal valide")

        return data


class IssuerForm(ModelForm, CleanEmailMixin, DsfrBaseForm):
    template_name = "aidants_connect_habilitation/forms/issuer.html"

    phone = AcPhoneNumberField(
        initial="",
        label="Téléphone",
        required=False,
    )

    def __init__(self, *args, render_non_editable=False, **kwargs):
        self.render_non_editable = render_non_editable
        super().__init__(*args, **kwargs)
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


class OrganisationRequestForm(
    PatchedModelForm, AddressValidatableMixin, CleanZipCodeMixin
):
    type = ChoiceField(required=True, choices=RequestOriginConstants.choices)
    type_other = CharField(
        label="Veuillez préciser le type d’organisation", required=False
    )

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

    city_insee_code = CharField(widget=HiddenInput(), required=False)
    department_insee_code = CharField(widget=HiddenInput(), required=False)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget_attrs(
            "type",
            {
                "data-action": "change->dynamic-form#onTypeChange",
                "data-dynamic-form-target": "typeInput",
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
            raise ValidationError(
                f"Ce champ doit être rempli si la "
                f"structure est de type {RequestOriginConstants.OTHER.label}."
            )

        return self.data["type_other"]

    def clean_partner_administration(self):
        if not self.data.get("is_private_org", False):
            return ""

        if not self.data["partner_administration"]:
            raise ValidationError(
                "Vous avez indiqué que la structure est privée : merci de renseigner "
                "votre administration partenaire."
            )

        return self.data["partner_administration"]

    def clean_france_services_number(self):
        if not self.data.get("france_services_label", False):
            return ""

        if not self.data["france_services_number"]:
            raise ValidationError(
                "Vous avez indiqué que la structure est labellisée France Services : "
                "merci de renseigner son numéro d’immatriculation France Services."
            )

        return self.data["france_services_number"]

    def clean(self):
        result = super().clean()
        super().post_clean()
        return result

    def get_address_for_search(self) -> str:
        return " ".join(
            [
                self.data[self.add_prefix("address")],
                self.data[self.add_prefix("zipcode")],
                self.data[self.add_prefix("city")],
            ]
        )

    def autocomplete(self, address: Address):
        self.cleaned_data["address"] = address.name
        self.cleaned_data["zipcode"] = address.postcode
        self.cleaned_data["city"] = address.city
        self.cleaned_data["city_insee_code"] = address.citycode
        self.cleaned_data["department_insee_code"] = address.context.department_number

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
            "is_private_org",
            "partner_administration",
            "france_services_label",
            "france_services_number",
            "web_site",
            "mission_description",
            "avg_nb_demarches",
        ]
        widgets = {"address": TextInput}


class PersonWithResponsibilitiesForm(PatchedModelForm, CleanEmailMixin):
    phone = AcPhoneNumberField(
        initial="",
        required=False,
    )

    class Meta:
        model = PersonWithResponsibilities
        exclude = ["id"]


class ManagerForm(
    ConseillerNumerique,
    PersonWithResponsibilitiesForm,
    AddressValidatableMixin,
    CleanZipCodeMixin,
):
    phone = AcPhoneNumberField(
        initial="",
        required=True,
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

    city_insee_code = CharField(widget=HiddenInput(), required=False)
    department_insee_code = CharField(widget=HiddenInput(), required=False)

    is_aidant = TypedChoiceField(
        label="C’est aussi un aidant",
        label_suffix=" :",
        choices=(("", ""), (True, "Oui"), (False, "Non")),
        coerce=lambda value: bool(strtobool(value)),
    )

    def get_address_for_search(self) -> str:
        return " ".join(
            [
                self.data[self.add_prefix("address")],
                self.data[self.add_prefix("zipcode")],
                self.data[self.add_prefix("city")],
            ]
        )

    def autocomplete(self, address: Address):
        self.cleaned_data["address"] = address.name
        self.cleaned_data["zipcode"] = address.postcode
        self.cleaned_data["city"] = address.city
        self.cleaned_data["city_insee_code"] = address.citycode
        self.cleaned_data["department_insee_code"] = address.context.department_number

    def clean(self):
        result = super().clean()
        super().post_clean()
        return result

    class Meta(PersonWithResponsibilitiesForm.Meta):
        model = Manager
        widgets = {"address": TextInput}
        include = ("conseiller_numerique",)
        exclude = ("habilitation_request",)


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


# TODO: Remove and replace by AidantRequestForm when PersonnelRequestFormView is ported to DSFR  # noqa: E501
class AidantRequestFormLegacy(ConseillerNumerique, PatchedModelForm, CleanEmailMixin):
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
        return super().save(commit)

    class Meta:
        model = AidantRequest
        exclude = ["organisation", "habilitation_request"]


class AidantRequestForm(ModelForm, ConseillerNumerique, CleanEmailMixin, DsfrBaseForm):
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
        return super().save(commit)

    class Meta:
        model = AidantRequest
        exclude = ["organisation", "habilitation_request"]


class BaseAidantRequestFormSet(BaseModelFormSet):
    def __init__(self, organisation: OrganisationRequest, **kwargs):
        self.organisation = organisation
        kwargs.setdefault("error_class", PatchedErrorList)
        kwargs.setdefault("queryset", AidantRequest.objects.none())

        super().__init__(**kwargs)

        self.__management_form_widget_attrs(
            TOTAL_FORM_COUNT, {"data-personnel-form-target": "managmentFormCount"}
        )
        self.__management_form_widget_attrs(
            MAX_NUM_FORM_COUNT, {"data-personnel-form-target": "managmentFormMaxCount"}
        )

    def clean(self):
        emails = {}
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue

            email = form.cleaned_data.get("email")

            # Do not test if email is empty: may be a legitimate empty form
            if email:
                emails.setdefault(email, [])
                emails[email].append(form)

        for email, grouped_forms in emails.items():
            if len(grouped_forms) > 1:
                for form in grouped_forms:
                    form.add_error(
                        "email",
                        EmailOrganisationValidationError(email),
                    )

        super().clean()

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["organisation"] = self.organisation
        return kwargs

    def add_non_form_error(self, error: Union[ValidationError, str]):
        if not isinstance(error, ValidationError):
            error = ValidationError(error)
        self._non_form_errors.append(error)

    def is_empty(self):
        for form in self.forms:
            # If the form is not valid, it has data to correct so it is not empty
            if not form.is_valid() or form.is_valid() and len(form.cleaned_data) != 0:
                return False

        return True

    def __management_form_widget_attrs(self, widget_name: str, attrs: dict):
        widget = self.management_form.fields[widget_name].widget
        for attr_name, attr_value in attrs.items():
            widget.attrs[attr_name] = attr_value


AidantRequestFormSet = modelformset_factory(
    AidantRequestFormLegacy.Meta.model,
    AidantRequestFormLegacy,
    formset=BaseAidantRequestFormSet,
)


# TODO: Replace implementation with BaseMultiForm when PersonnelRequestFormView is ported to DSFR  # noqa: E501
class PersonnelForm:
    MANAGER_FORM_PREFIX = "manager"
    AIDANTS_FORMSET_PREFIX = "aidants"

    @property
    def errors(self):
        if self._errors is None:
            self._clean()
        return self._errors

    def __init__(self, organisation: OrganisationRequest, **kwargs):
        self.organisation = organisation

        def merge_kwargs(prefix):
            previous_prefix = kwargs.get("prefix")
            local_kwargs = {}

            form_kwargs_prefixes = {
                self.MANAGER_FORM_PREFIX,
                self.AIDANTS_FORMSET_PREFIX,
            }

            for k, v in kwargs.items():
                """
                Let us dispatch form kwargs to specific forms by using their prefixes.

                For instance, PersonnelForm(manager_instance=some_instance) will
                disptach to ManagerForm(instance=some_instance).
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
                "prefix": (
                    prefix if not previous_prefix else f"{prefix}_{previous_prefix}"
                ),
            }

        self._errors = None

        self.manager_form = ManagerForm(**merge_kwargs(self.MANAGER_FORM_PREFIX))

        self.aidants_formset = AidantRequestFormSet(
            organisation=self.organisation, **merge_kwargs(self.AIDANTS_FORMSET_PREFIX)
        )

    def _clean(self):
        self._errors = PatchedErrorList()

        if not self.manager_form.is_bound or not self.aidants_formset.is_bound:
            # Stop processing if form does not have data
            return

        self.clean_must_have_one_aidant()
        self.clean_must_have_unique_emails()

    def clean_must_have_unique_emails(self):
        if not self.manager_form.cleaned_data.get("is_aidant"):
            return
        if not (manager_email := self.manager_form.cleaned_data.get("email")):
            # if manager's email is None, we don't need to perform
            # that check since manager's email needs to be set
            return
        bogus_aidants_forms = [
            form
            for form in self.aidants_formset.forms
            if form.cleaned_data.get("email", "") == manager_email
        ]

        if not bogus_aidants_forms:
            return

        self.add_error(
            "Vous avez déclaré plusieurs aidants avec la même addresse email"
        )

        self.manager_form.add_error(
            "email",
            "Vous avez déclaré cette personne comme aidante et déclaré un "
            "autre aidant avec la même adresse email. Chaque aidant doit avoir "
            "une adresse email unique.",
        )

        for aidant_form in bogus_aidants_forms:
            aidant_form.add_error(
                "email",
                "Cette personne a le même email que la personne que vous avez "
                "déclarée comme référente. Chaque aidant doit avoir "
                "une adresse email unique.",
            )

    def clean_must_have_one_aidant(self):
        manager_is_aidant = self.manager_form.cleaned_data.get("is_aidant")
        # If is_aidant is None, there was a ValidationError on this field
        # so we don't bother validating
        if not self.aidants_formset.is_empty() or manager_is_aidant is True:
            return

        self.add_error(
            "Vous devez déclarer au moins 1 aidant si le ou la référente de "
            "l'organisation n'est pas elle-même déclarée comme aidante"
        )
        self.manager_form.add_error(
            "is_aidant",
            "Veuillez cocher cette case ou déclarer au moins un aidant ci-dessous",
        )
        self.aidants_formset.add_non_form_error(
            "Vous devez déclarer au moins 1 aidant si le ou la référente de "
            "l'organisation n'est pas elle-même déclarée comme aidante"
        )

    def add_error(self, error: Union[ValidationError, str]):
        if not isinstance(error, ValidationError):
            error = ValidationError(error)
        self._errors.append(error)

    def is_valid(self) -> bool:
        # Eagerly compute the result of `is_valid` calls
        # to prevent early return of the boolean computation.

        # 'self.errors' must be last called so that subforms are
        # validated before performing a global validation
        is_valid = [
            self.manager_form.is_valid(),
            self.aidants_formset.is_valid(),
            not self.errors,
        ]

        return all(is_valid)

    def save(self, commit=True) -> Tuple[Manager, List[AidantRequest]]:
        for form in self.aidants_formset:
            form.instance.organisation = self.organisation

        manager_instance, aidants_instances = (
            self.manager_form.save(commit),
            self.aidants_formset.save(commit),
        )

        self.organisation.manager = manager_instance
        self.organisation.save()

        return manager_instance, aidants_instances

    save.alters_data = True


class ValidationForm(DsfrBaseForm):
    template_name = "aidants_connect_habilitation/forms/validation.html"  # noqa: E501
    cgu = BooleanField(
        required=True,
        label='J’ai pris connaissance des <a href="{url}" class="fr-link">'
        "conditions générales d’utilisation</a> et je les valide.",
    )
    not_free = BooleanField(
        required=True,
        label="Je confirme avoir compris que la formation est payante "
        "et je me suis renseigné(e) sur les modalités de financements disponibles.",
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
    message_content = CharField(
        label="Votre message", required=False, widget=Textarea(attrs={"rows": 4})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cgu = self["cgu"]
        cgu.label = format_html(cgu.label, url=reverse("cgu"))

    def save(
        self, organisation: OrganisationRequest, commit=True
    ) -> OrganisationRequest:
        organisation.prepare_request_for_ac_validation(self.cleaned_data)
        if self.cleaned_data["message_content"] != "":
            RequestMessage.objects.create(
                organisation=organisation,
                sender=MessageStakeholders.ISSUER.name,
                content=self.cleaned_data["message_content"],
            )
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

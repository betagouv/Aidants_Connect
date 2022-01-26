from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import formset_factory, ChoiceField, CharField, BaseFormSet
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberInternationalFallbackWidget

from aidants_connect.constants import RequestOriginConstants
from aidants_connect.forms import PatchedErrorListForm, PatchedErrorList
from aidants_connect_habilitation import models
from aidants_connect_habilitation.models import AidantRequest
from aidants_connect_web.models import OrganisationType


class IssuerForm(PatchedErrorListForm):
    phone = PhoneNumberField(
        initial="",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
        required=False,
    )

    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=PatchedErrorList,
        label_suffix=None,
        empty_permitted=False,
        instance=None,
        use_required_attribute=None,
        renderer=None,
        render_non_editable=False,
    ):
        super().__init__(
            data,
            files,
            auto_id,
            prefix,
            initial,
            error_class,
            label_suffix,
            empty_permitted,
            instance,
            use_required_attribute,
            renderer,
        )
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
        exclude = ["issuer_id"]


class OrganisationRequestForm(PatchedErrorListForm):
    type = ChoiceField(required=True, choices=RequestOriginConstants.choices)

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

    manager_phone = PhoneNumberField(
        initial="",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
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
        exclude = ["issuer", "status", "draft_id"]


class AidantRequestForm(PatchedErrorListForm):
    phone = PhoneNumberField(
        initial="",
        region=settings.PHONENUMBER_DEFAULT_REGION,
        widget=PhoneNumberInternationalFallbackWidget(
            region=settings.PHONENUMBER_DEFAULT_REGION
        ),
        required=False,
    )

    class Meta:
        model = AidantRequest
        exclude = ["organisation"]


class BaseAidantRequestFormSet(BaseFormSet):
    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=PatchedErrorList,
        form_kwargs=None,
    ):
        super().__init__(
            data, files, auto_id, prefix, initial, error_class, form_kwargs
        )

    def save(self, commit=True):
        return [sub_form.save(commit=commit) for sub_form in self]


AidantRequestFormSet = formset_factory(
    AidantRequestForm, formset=BaseAidantRequestFormSet
)

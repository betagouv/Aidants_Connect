from datetime import timedelta
from inspect import signature

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.forms import Form
from django.forms.utils import ErrorList
from django.utils.datastructures import MultiValueDict

from dsfr.forms import DsfrBaseForm
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.phonenumber import to_python
from phonenumbers.phonenumber import PhoneNumber

from aidants_connect_common.models import Formation


class PatchedErrorList(ErrorList):
    """An ErrorList that will just print itself as a <p> when it has only 1 item"""

    template_name = template_name_ul = "forms/errors/list/ul.html"
    template_name_text = "forms/errors/list/text.txt"

    def __init__(self, initlist=None, error_class=None, renderer=None):
        super().__init__(initlist, error_class, renderer)
        self._error_codes = None

    @property
    def error_codes(self):
        if not self._error_codes:
            self._error_codes = [error.code for error in self.data]
        return self._error_codes

    def get_error_by_code(self, error_code):
        return next((error for error in self.data if error.code == error_code), None)


class WidgetAttrMixin:
    def widget_attrs(self, widget_name: str, attrs: dict):
        for attr_name, attr_value in attrs.items():
            self.fields[widget_name].widget.attrs[attr_name] = attr_value


class PatchedModelForm(forms.ModelForm, WidgetAttrMixin):
    def __init__(self, *args, **kwargs):
        sig = signature(super().__init__).bind_partial(*args, **kwargs)
        sig.arguments.setdefault("label_suffix", "")
        sig.arguments["error_class"] = PatchedErrorList

        super().__init__(*sig.args, **sig.kwargs)


class PatchedForm(Form, WidgetAttrMixin):
    def __init__(self, *args, **kwargs):
        sig = signature(super().__init__).bind_partial(*args, **kwargs)
        sig.arguments.setdefault("label_suffix", "")
        sig.arguments["error_class"] = PatchedErrorList

        super().__init__(*sig.args, **sig.kwargs)


class ErrorCodesManipulationMixin:
    @property
    def errors_codes(self) -> dict[str, MultiValueDict[str, str]]:
        """
        Return a dict associating all the form's error codes with a dict associating the
        field names presenting these errors with a list of the error messages
        Exemple:
        >>> from django import forms
        >>> from aidants_connect_common.forms import ErrorCodesManipulationMixin
        >>> class TestForm(ErrorCodesManipulationMixin, forms.Form):
        ...     is_ok = forms.BooleanField()
        ...     name = forms.CharField()
        >>> form = TestForm()
        >>> form.errors_codes
        {'required': {'is_ok': ['Ce champ est obligatoire.'],'name': ['Ce champ est obligatoire.']}}
        """  # noqa: E501

        if not hasattr(self, "errors"):
            raise AttributeError(
                "ErrorCodesManipulationMixin must be used on Form class"
            )
        if not hasattr(self, "_errors_codes"):
            self._errors_codes: dict[str, MultiValueDict[str, str]] = {}
            for field, errors in self.errors.items():
                for error in errors.as_data():
                    code = error.code or ""
                    self._errors_codes.setdefault(code, MultiValueDict())
                    self._errors_codes[code].setlistdefault(field)
                    self._errors_codes[code].appendlist(field, error.message or "")
        return self._errors_codes


class AcPhoneNumberField(PhoneNumberField):
    """A PhoneNumberField which accepts any number from metropolitan France
    and overseas"""

    regions = settings.FRENCH_REGION_CODES

    def to_python(self, value: PhoneNumber | str):
        for region in self.regions:
            # value can be of type PhoneNumber in which case `to_python`
            # does not convert it again using the new region. We need
            # to force conversion of value to string here to ensure
            # the correct region is used.
            phone_number = to_python(f"{value}", region=region)

            if phone_number in validators.EMPTY_VALUES:
                return self.empty_value

            if phone_number and phone_number.is_valid():
                return phone_number

        raise ValidationError(self.error_messages["invalid"])


class FormationRegistrationForm(DsfrBaseForm):
    formations = forms.ModelMultipleChoiceField(queryset=Formation.objects.none())

    def __init__(self, attendant: Model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["formations"].queryset = Formation.objects.available_for_attendant(
            timedelta(days=21), attendant
        )


class FollowMyHabilitationRequesrForm(DsfrBaseForm):
    email = forms.EmailField(label="Adresse email")

    def clean_email(self):
        email = self.cleaned_data.get("email", None)

        from aidants_connect_habilitation.models import Issuer

        try:
            return Issuer.objects.get(email=email)
        except Issuer.DoesNotExist:
            raise ValidationError(
                "Il nʼexiste pas de demande dʼhabilitation associée à cet email. "
                "Veuillez vérifier votre saisie ou renseigner une autre adresse email."
            )

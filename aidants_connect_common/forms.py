from datetime import timedelta
from inspect import signature

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList

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


class PatchedForm(forms.Form, WidgetAttrMixin):
    def __init__(self, *args, **kwargs):
        sig = signature(super().__init__).bind_partial(*args, **kwargs)
        sig.arguments.setdefault("label_suffix", "")
        sig.arguments["error_class"] = PatchedErrorList

        super().__init__(*sig.args, **sig.kwargs)


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
    formations = forms.ModelMultipleChoiceField(
        queryset=Formation.objects.after(timedelta(days=45)).not_full()
    )

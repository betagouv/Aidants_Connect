from django.core import validators
from django.core.exceptions import ValidationError
from django.forms import Form, ModelForm
from django.forms.utils import ErrorList
from django.utils.html import format_html

from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.phonenumber import to_python


class PatchedErrorList(ErrorList):
    """An ErrorList that will just print itself as a <p> when it has only 1 item"""

    def as_ul(self):
        """Just return a <span> instead of a <ul> if there's only one error"""
        if self.data and len(self) == 1:
            return format_html('<p class="{}">{}</p>', self.error_class, self[0])

        return super().as_ul()


class PatchedErrorListForm(ModelForm):
    def __init__(self, **kwargs):
        kwargs.setdefault("label_suffix", "")
        kwargs.setdefault("error_class", PatchedErrorList)
        super().__init__(**kwargs)

    def widget_attrs(self, widget_name: str, attrs: dict):
        for attr_name, attr_value in attrs.items():
            self.fields[widget_name].widget.attrs[attr_name] = attr_value


class PatchedForm(Form):
    def __init__(self, **kwargs):
        kwargs.setdefault("error_class", PatchedErrorList)
        kwargs.setdefault("label_suffix", "")
        super().__init__(**kwargs)


class AcPhoneNumberField(PhoneNumberField):
    """A PhoneNumberField which accepts any number from metropolitan France
    and overseas"""

    regions = ("FR", "GP", "GF", "MQ", "RE", "KM", "PM")

    def to_python(self, value):
        for region in self.regions:
            phone_number = to_python(value, region=region)

            if phone_number in validators.EMPTY_VALUES:
                return self.empty_value

            if phone_number and phone_number.is_valid():
                return phone_number

        raise ValidationError(self.error_messages["invalid"])

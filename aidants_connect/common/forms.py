from django.forms import Form, ModelForm
from django.forms.utils import ErrorList
from django.utils.html import format_html


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

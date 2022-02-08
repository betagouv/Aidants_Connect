from django.forms import ModelForm
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

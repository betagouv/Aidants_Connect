from django.forms import CharField, Media

from import_export.forms import ImportForm

from aidants_connect_common.forms import PatchedModelForm, WidgetAttrMixin
from aidants_connect_common.models import Formation
from aidants_connect_common.widgets import JSModulePath

from .resources import ZRRResource


class CommuneImportForm(ImportForm, WidgetAttrMixin):
    commune_zrr_classification = CharField(
        label=(
            "Valeur indiquant qu'une commune est classé ZRR dans le fichier des zonages"
        ),
        initial="C - Classée en ZRR",
    )

    def __init__(self, import_formats, *args, **kwargs):
        super().__init__(import_formats, *args, **kwargs)
        self.widget_attrs(
            "resource",
            {"data-action": "commune-import-form#onOptionSelected"},
        )
        pass

    def clean(self):
        cleaned_data = super().clean()
        try:
            idx = next(
                idx
                for idx, name in self.fields["resource"].choices
                if name == ZRRResource.get_display_name()
            )
            if str(cleaned_data["resource"]) != str(idx):
                cleaned_data["commune_zrr_classification"] = None
        except StopIteration:
            cleaned_data["commune_zrr_classification"] = None

        return cleaned_data

    @property
    def media(self):
        return super().media + Media(js=[JSModulePath("js/communes-import-form.mjs")])


class ReportFormationForm(PatchedModelForm):
    class Meta:
        model = Formation
        fields = ("start_datetime", "end_datetime")

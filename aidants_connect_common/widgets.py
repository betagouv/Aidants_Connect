from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.forms import Media, RadioSelect, Select
from django.templatetags.static import static
from django.utils.html import html_safe

from aidants_connect_common.templatetags.form_extras import merge_html_attr_values


@html_safe
class JSModulePath:
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f'<script type="module" src="{static(self.path)}"></script>'


class DetailedRadioSelect(RadioSelect):
    template_name = "widgets/detailed_radio.html"
    option_template_name = "widgets/detailed_radio_option.html"
    input_wrapper_base_class = "detailed-radio-select"
    container_classes = ""
    input_wrapper_classes = ""
    label_classes = ""
    checkbox_select_multiple = False

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        opts_context = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )

        if isinstance(opts_context["label"], dict):
            opts_context.update(**self.choices_label_adapter(opts_context.pop("label")))

        opts_context["input_wrapper_base_class"] = self.input_wrapper_base_class

        input_wrapper_classes = [
            self.input_wrapper_base_class,
            self.input_wrapper_classes,
        ]
        if self.allow_multiple_selected:
            input_wrapper_classes.append(f"{self.input_wrapper_base_class}-multiselect")
        opts_context["input_wrapper_classes"] = merge_html_attr_values(
            input_wrapper_classes
        )

        opts_context["label_classes"] = merge_html_attr_values(
            [self.label_classes, f"{self.input_wrapper_base_class}-label"]
        )

        if "id" in attrs:
            opts_context["attrs"]["id"] = self.id_for_label(
                attrs["id"], str(value).lower() if value else index
            )

        return opts_context

    @staticmethod
    def choices_label_adapter(label: dict) -> dict:
        return label

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["container_classes"] = merge_html_attr_values(
            [self.container_classes, attrs.get("class", "")]
        )
        return context

    def use_required_attribute(self, initial):
        return (
            False
            if self.checkbox_select_multiple
            else super().use_required_attribute(initial)
        )

    def value_omitted_from_data(self, data, files, name):
        return (
            False
            if self.checkbox_select_multiple
            else super().value_omitted_from_data(data, files, name)
        )


class SearchableRadioSelect(Select):
    def build_attrs(self, base_attrs, extra_attrs=None):
        extra_attrs = extra_attrs or {}
        extra_attrs["data-searchable-radio-select"] = True
        return super().build_attrs(base_attrs, extra_attrs)

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        return Media(
            js=(
                "admin/js/vendor/select2/select2.full%s.js" % extra,
                staticfiles_storage.url("js/searchable-radio-select.js"),
            ),
            css={
                "screen": (
                    "admin/css/vendor/select2/select2%s.css" % extra,
                    "admin/css/autocomplete.css",
                ),
            },
        )

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.forms import Media, RadioSelect, Select

from aidants_connect_common.templatetags.form_extras import merge_html_attr_values


class DetailedRadioSelect(RadioSelect):
    template_name = "widgets/detailed_radio.html"
    option_template_name = "widgets/detailed_radio_option.html"
    input_wrapper_base_class = "detailed-radio-select"

    def __init__(self, attrs=None, choices=(), wrap_label=False):
        """Unwrap label by default and set a CSS class"""
        self.wrap_label = wrap_label
        attrs = attrs or {}
        self._input_wrapper_classes = attrs.pop(
            "input_wrapper_classes", self.input_wrapper_base_class
        )
        self._container_class = attrs.pop("input_wrapper_classes", "")

        super().__init__(attrs, choices)

    def input_wrapper_classes(self, *extra_classes):
        return merge_html_attr_values([self.input_wrapper_base_class, *extra_classes])

    def container_classes(self, *extra_classes):
        return merge_html_attr_values(extra_classes)

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        opts_context = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )

        if isinstance(opts_context["label"], dict):
            opts_context.update(**opts_context.pop("label"))

        opts_context["wrap_label"] = self.wrap_label
        opts_context["input_wrapper_base_class"] = self.input_wrapper_base_class
        opts_context["input_wrapper_classes"] = self.input_wrapper_classes(
            self._input_wrapper_classes
        )

        if "id" in attrs:
            opts_context["attrs"]["id"] = self.id_for_label(
                attrs["id"], str(value).lower() if value else index
            )

        return opts_context

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["container_classes"] = self.container_classes(
            self._container_class, attrs.get("class")
        )
        return context


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

from typing import Dict, Tuple

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.forms import BaseForm, Media, RadioSelect, Select
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

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
        self._compagnon_fields: Dict[str, Tuple[BaseForm, str, dict]] = {}

        super().__init__(attrs, choices)

    def add_compagnon_field(
        self,
        choice: str,
        form: BaseForm,
        template: str,
        context: dict = None,
    ):
        """
        ``compagnon_fields`` allows to declare another widget to be rendered along
        with one or several Select subwidget. Let's assume a ``DetailedRadioSelect``
        with options ["OPTION_1", "OPTION_2"] and a form with a member like:
        ``some_field = TextField()``. Then ``some_field`` can be redered directly
        below the ``<input>`` for ``OPTION_1`` by doing:

            class SomeForm(Form)
                some_field = TextField()
                choice_field = forms.ChoiceField(
                    choices=[("OPTION_1", "Some label"), ("OPTION_2", "Other label")],
                    widget=DetailedRadioSelect()
                )

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.fields["remote_constent_method"].widget.add_compagnon_field(
                        self, "some_field", "OPTION_1"
                    )
        """
        self._compagnon_fields[choice] = form, template, context or {}

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

        if value in self._compagnon_fields:
            form, template, context = self._compagnon_fields[value]
            opts_context["compagnon_field"] = mark_safe(
                render_to_string(template, context={**form.get_context(), **context})
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

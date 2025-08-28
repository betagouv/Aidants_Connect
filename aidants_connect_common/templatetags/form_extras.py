from collections.abc import Iterable

from django import template
from django.forms import BoundField
from django.forms.utils import flatatt
from django.utils.html import escape

register = template.Library()


def field_as_something(field: BoundField, **kwargs):
    if not isinstance(field, BoundField):
        return {}
    bf_errors = field.form.error_class(field.errors)
    errors_str = str(bf_errors)
    return {"field": field, "errors": errors_str, **kwargs}


@register.inclusion_tag("fields/fields_as_fieldset.html")
def fields_as_fieldset(field: BoundField, fieldset_classes=None, legend_classes=None):
    fieldset_classes = field.css_classes(fieldset_classes)
    return field_as_something(
        field, fieldset_classes=fieldset_classes, legend_classes=legend_classes
    )


@register.inclusion_tag("fields/fields_as_p.html")
def field_as_p(field: BoundField, p_classes=None):
    p_classes = field.css_classes(p_classes)
    return field_as_something(field, p_classes=p_classes)


@register.inclusion_tag("fields/fields_as_fr_grid_row.html")
def field_as_fr_grid_row(field: BoundField, label_size=None):
    label_size_class = {
        "large": "fr-col-md-7",
        "medium": "fr-col-md-6",
        "small": "fr-col-md-5",
    }.get(str(label_size).lower(), "fr-col-md-5")
    input_size_class = {
        "large": "fr-col-md-5",
        "medium": "fr-col-md-6",
        "small": "fr-col-md-7",
    }.get(str(label_size).lower(), "fr-col-md-7")
    return field_as_something(
        field,
        input_size_class=input_size_class,
        label_size_class=label_size_class,
    )


@register.inclusion_tag("fields/fields_as_narrow_fr_grid_row.html")
def field_as_narrow_fr_grid_row(field: BoundField):
    return field_as_something(field)


@register.inclusion_tag("fields/checkbox_fr_grid_row.html")
def checkbox_fr_grid_row(field: BoundField):
    return field_as_something(field)


@register.simple_tag
def id_attr(attr_value: str | Iterable[str]) -> str:
    return html_attr("id", attr_value)


@register.simple_tag
def class_attr(attr_value: str | Iterable[str]) -> str:
    return html_attr("class", attr_value)


@register.simple_tag
def html_attrs(attrs: dict) -> str:
    return flatatt(attrs)


@register.simple_tag
def html_attr(attr_name: str, attr_value: str | Iterable[str]) -> str:
    if not attr_value:
        return ""

    if not isinstance(attr_value, str):
        attr_value = merge_html_attr_values(attr_value)

    return html_attrs({attr_name: attr_value})


def merge_html_attr_values(attr_value: str | Iterable) -> str:
    if not attr_value or not any(attr_value):
        return ""
    # First pass: itterable may consist of individual values or strings that contain
    # several values separated by a space. Joining to a string flattens it.
    values = (
        " ".join([str(item) for item in attr_value if item])
        if not isinstance(attr_value, str)
        else attr_value
    )
    # Second pass: split the values, strip them, eliminate falsy values and duplicates
    values = set(
        [stripped for item in values.split(" ") if (stripped := escape(item.strip()))]
    )

    return " ".join(list(values))


@register.inclusion_tag("forms/aidantc-dsfr-input-snippet-no-asterisk.html")
def aidantc_dsfr_form_field_no_asterisk(field):
    """Template tag DSFR sans astérisque"""
    return {"field": field}

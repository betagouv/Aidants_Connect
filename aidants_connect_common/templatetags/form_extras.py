from django import template
from django.forms import BoundField

register = template.Library()


def field_as_something(field: BoundField):
    if not isinstance(field, BoundField):
        return {}
    bf_errors = field.form.error_class(field.errors)
    errors_str = str(bf_errors)
    return {"field": field, "errors": errors_str}


@register.inclusion_tag("fields/fields_as_p.html")
def field_as_p(field: BoundField):
    return field_as_something(field)


@register.inclusion_tag("fields/fields_as_fr_grid_row.html")
def field_as_fr_grid_row(field: BoundField):
    return field_as_something(field)


@register.inclusion_tag("fields/fields_as_narrow_fr_grid_row.html")
def field_as_narrow_fr_grid_row(field: BoundField):
    return field_as_something(field)


@register.inclusion_tag("fields/checkbox_fr_grid_row.html")
def checkbox_fr_grid_row(field: BoundField):
    return field_as_something(field)

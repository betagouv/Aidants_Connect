import json

from django import template

register = template.Library()


@register.filter
def json_attribute(value):
    return json.dumps(value)


@register.filter
def get_dict_key(dict, key):
    return dict[key]

from django import template

register = template.Library()


@register.filter
def get_dict_key(dict, key):
    return dict[key]

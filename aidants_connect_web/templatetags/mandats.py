from django import template

register = template.Library()


@register.filter
def contact_method(usager):
    return usager.get_contact_method()


@register.filter
def contact(usager):
    return usager.get_contact()

from urllib.parse import quote, urlencode

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def mailto(link_text: str, recipient: str, subject: str, body: str):
    def quote_via(string, _, encoding, errors):
        """
        Custom quote function for urlencode

        By default, urlencode uses `urllib.parse.quote_plus`
        to replace invalid URL characters. This function  replaces
        blank characters by `+` which are not correctly substitued
        by spaces by mail clients when opening the link.
        We want to replace blank characters by `%20` instead.
        """
        return quote(string, "", encoding, errors)

    urlencoded = urlencode({"subject": subject, "body": body}, quote_via=quote_via)
    return mark_safe(f'<a href="mailto:{recipient}?{urlencoded}">{link_text}</a>')

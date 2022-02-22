from urllib.parse import quote, urlencode

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def mailto(link_text: str, recipient: str, subject: str, body: str):
    urlencoded = urlencode(
        {"subject": subject, "body": body},
        quote_via=lambda x, _, enc, err: quote(x, "", enc, err),
    )
    return mark_safe(f'<a href="mailto:{recipient}?{urlencoded}">{link_text}</a>')

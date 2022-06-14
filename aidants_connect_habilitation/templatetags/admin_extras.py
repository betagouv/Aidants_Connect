from urllib.parse import urlparse

from django import template
from django.http import HttpRequest
from django.template.base import Node, Parser, Token
from django.template.defaulttags import url
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


def query_url(request: HttpRequest, path: str) -> SafeString:
    query = urlparse(request.get_full_path()).query
    full_path = f"{path}?{query}" if len(query) else path
    return mark_safe(full_path)


@register.tag
def qurl(parser: Parser, token: Token):
    """
    Similar to {% url %} but passes any query parameters from
    request down to the generated url
    """
    return QUrlNode(parser, token)


class QUrlNode(Node):
    def __init__(self, parser: Parser, token: Token):
        self.parser = parser
        self.token = token

    def render(self, context):
        path = url(self.parser, self.token).render(context)
        return query_url(context["request"], path)

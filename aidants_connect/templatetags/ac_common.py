import re
from urllib.parse import quote, urlencode

from django import template
from django.conf import settings
from django.template.base import Node, NodeList, Parser, TextNode, Token
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


@register.simple_tag
def stimulusjs():
    return mark_safe(f'<script src="{settings.STIMULUS_JS_URL}"></script>')


@register.tag
def linebreakless(parser: Parser, token: Token):
    library = template.Library()
    library.tag(LinebreaklessNode.KEEP_LINEBREAK_TAG, LinebreaklessNode.keeplinebreak)
    parser.add_library(library)
    nodelist = parser.parse(("endlinebreakless",))
    parser.delete_first_token()
    return LinebreaklessNode(token, nodelist)


class LinebreaklessNode(Node):
    KEEP_LINEBREAK_TAG = "keeplinebreak"
    KEEP_LINEBREAK_MARKUP = f"{{% {KEEP_LINEBREAK_TAG} %}}"

    class KeepLineBreak(Node):
        def __init__(self, token: Token):
            self.token = token

        def render(self, context):
            return LinebreaklessNode.KEEP_LINEBREAK_MARKUP

    @staticmethod
    def keeplinebreak(_, token: Token):
        return LinebreaklessNode.KeepLineBreak(token)

    def __init__(self, token: Token, nodelist: NodeList):
        self.token = token
        self.nodelist = nodelist

    def render(self, context):
        for i, node in enumerate(self.nodelist):
            if isinstance(node, LinebreaklessNode.KeepLineBreak) and (
                len(self.nodelist) <= i + 1
                or not isinstance(self.nodelist[i + 1], TextNode)
                or not self.nodelist[i + 1].s.strip(" \t\r\f\v").startswith("\n")
            ):
                raise ValueError(
                    f"{LinebreaklessNode.KEEP_LINEBREAK_MARKUP} needs to be followed "
                    "by a linebreak.\n"
                    f'  File "{node.origin.name}", line {node.token.lineno}'
                )

        return re.sub(
            "\\s*\n+\\s*",
            "",
            self.nodelist.render(context).strip(),
        ).replace(self.KEEP_LINEBREAK_MARKUP, "\n")

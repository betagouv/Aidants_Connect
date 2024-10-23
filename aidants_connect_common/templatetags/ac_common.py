import re
from collections.abc import Iterable
from urllib.parse import quote, urlencode

from django import template
from django.conf import settings
from django.template import TemplateSyntaxError
from django.template.base import Node, NodeList, Parser, TextNode, Token, token_kwargs
from django.template.defaultfilters import stringfilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from aidants_connect import utils

register = template.Library()


@register.simple_tag
def mailto_href(recipient: str, subject: str = "", body: str = ""):
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

    query = {}

    if subject:
        query["subject"] = subject
    if body:
        query["body"] = body

    urlencoded = (
        urlencode({"subject": subject, "body": body}, quote_via=quote_via)
        if query
        else ""
    )

    return f"mailto:{recipient}{'?' + urlencoded if urlencoded else ''}"


@register.simple_tag
def mailto(
    recipient: str,
    link_text: str = "",
    subject: str = "",
    body: str = "",
    link_class=None,
):
    link_text = link_text or recipient
    href = mailto_href(recipient, subject, body)
    link_class = link_class or "fr-link"
    return mark_safe(f'<a class="{link_class}" href="{href}">{link_text}</a>')


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
    return LinebreaklessNode(parser, token, nodelist)


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

    def __init__(self, parser: Parser, token: Token, nodelist: NodeList):
        self.parser = parser
        self.token = token
        self.nodelist = nodelist

    def render(self, context):
        tag_name, *bits = self.token.contents.split()
        kwargs = {
            k: v.resolve(context) for k, v in token_kwargs(bits, self.parser).items()
        }
        dont_rstrip = kwargs.get("dont_rstrip", False)
        dont_lstrip = kwargs.get("dont_lstrip", False)

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

        # Prevent eliminating spaces respectively after and before the newline
        # May be useful when parsing purely text files
        regex = r"\n+"
        if not dont_rstrip:
            regex = rf"{regex}\s*"
        if not dont_lstrip:
            regex = rf"\s*{regex}"

        return re.sub(
            regex,
            "",
            self.nodelist.render(context).strip(),
        ).replace(self.KEEP_LINEBREAK_MARKUP, "\n")


@register.simple_tag(takes_context=True)
def list_term(context, **kwargs):
    """
    Can be used inside a for loop to produce list terminators

    If there's more items in the loop, the filter will produce a coma character (","),
    if there is not more item in the loop, it will produce a dot (".").

    Use it like this:

        {% for item in items %}
        <li>{{ item }}{% list_term %}</li>
        {% endfor %}

    The terminator when there is more elements can be customized using the `more_term`
    parameter and the one whend the list is finished can be customized using the
    `end_term` parameter:

        {% for item in items %}
        <li>{{ item }}{% list_term more_term=';' end_term='…' %}</li>
        {% endfor %}

    Additionnaly, if you *may* have an additionnal element not included in the loop
    that can be appended to the loop, depending on som condition, you can use
    the `additionnal_cond` parameter. The filter will produce a 'more' (",") terminator
    when this condition is true and the loop is finished instead of the 'end' terminator
    so you can append the additionnal elements:

        {% for item in items %}
        <li>{{ item }}{% list_term additionnal_cond=has_additionnal_items %}</li>
        {% endfor %}

    """
    forloop = context.get("forloop", None)
    if not isinstance(forloop, dict) or forloop.get("last", None) is None:
        raise Exception(
            "This filter may only be used inside a {% for %} tag and must be passed "
            "the 'forloop' object as its first parameter"
        )

    more_term = kwargs.get("more_term", ",")
    end_term = kwargs.get("end_term", ".")
    additionnal_cond = kwargs.get("additionnal_cond", False)

    return end_term if forloop["last"] and not additionnal_cond else more_term


@register.filter
@stringfilter
def strtobool(val: str):
    return utils.strtobool(f"{val}", None)


@register.filter
@stringfilter
def camel(value: str):
    splitted = value.split("_")
    if len(splitted) > 1:
        splitted = [splitted[0], *[item.capitalize() for item in splitted[1:]]]

    splitted = "".join(splitted).split("-")
    if len(splitted) > 1:
        splitted = [splitted[0], *[item.capitalize() for item in splitted[1:]]]

    return "".join(splitted)


@register.filter("startswith")
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False


@register.tag
def withdict(parser, token):
    """
    Add a dictionnary or one or more values to the context (inside of this block).
    Name must be specified with ``as <name>`` syntax.

    For example::

        {% withdict name=person.name key=person.key as dict %}
            {% some_tag_expecting_a_dict dict %}
        {% endwithdict %}

    """
    bits = token.split_contents()
    remaining_bits = bits[1:]
    extra_context = token_kwargs(remaining_bits, parser)
    if not extra_context:
        raise TemplateSyntaxError(
            "%r expected at least one variable assignment" % bits[0]
        )
    if len(remaining_bits) != 2 or remaining_bits[0] != "as":
        raise TemplateSyntaxError(
            "expected variable assignement in the form of `as <variable name>`"
        )

    nodelist = parser.parse(("endwithdict",))
    parser.delete_first_token()
    return WithDictNode(nodelist, remaining_bits[1], extra_context)


class WithDictNode(Node):
    def __init__(self, nodelist, variable_name, extra_context):
        self.nodelist = nodelist
        self.variable_name = variable_name
        self.extra_context = extra_context

    def __repr__(self):
        return "<%s>" % self.__class__.__name__

    def render(self, context):
        values = {key: val.resolve(context) for key, val in self.extra_context.items()}
        with context.push(**{self.variable_name: values}):
            return self.nodelist.render(context)


@register.filter(is_safe=True)
def strfmt(args, format_string):
    """
    Shortcup to `str.format`.

    Usage:

    ```
    {{ ctx_variable|strfmt:"The sum of 1 + 2 is {0}" }}
    ```
    See: https://docs.python.org/3/library/stdtypes.html#str.format
    """
    kwargs = {}
    if isinstance(args, dict):
        kwargs.update(args)
        args = tuple()
    if isinstance(args, Iterable) and not isinstance(args, str):
        args = tuple(args)
    else:
        args = (str(args),)

    return format_html(format_string, *args, **kwargs)

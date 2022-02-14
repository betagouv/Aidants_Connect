import json
from re import sub as re_sub

from django import template
from django.template import Library
from django.template.base import Node, NodeList, Parser, TextNode, Token

register = template.Library()


@register.filter
def json_attribute(value):
    return json.dumps(value)


@register.filter
def get_dict_key(dict, key):
    return dict[key]


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


@register.tag
def linebreakless(parser: Parser, token: Token):
    library = Library()
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

        return re_sub(
            "\\s*\n+\\s*",
            "",
            self.nodelist.render(context).strip(),
        ).replace(self.KEEP_LINEBREAK_MARKUP, "\n")

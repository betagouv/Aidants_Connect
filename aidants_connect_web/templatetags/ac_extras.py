import json

from django import template

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

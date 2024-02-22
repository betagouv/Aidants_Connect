import json

from django import template

from aidants_connect_web.constants import ReferentRequestStatuses

register = template.Library()


@register.filter
def json_attribute(value):
    return json.dumps(value)


@register.filter
def get_dict_key(dict, key):
    return dict[key]


@register.simple_tag
def referent_request_status_badge(status):
    try:
        match ReferentRequestStatuses(status):
            case ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION:
                return "fr-badge--info"
            case ReferentRequestStatuses.STATUS_NEW:
                return "fr-badge--info"
            case ReferentRequestStatuses.STATUS_PROCESSING:
                return "fr-badge--info"
            case ReferentRequestStatuses.STATUS_VALIDATED:
                return "fr-badge--success"
            case ReferentRequestStatuses.STATUS_REFUSED:
                return "fr-badge--error"
            case (
                ReferentRequestStatuses.STATUS_CANCELLED
                | ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE
            ):
                return "fr-badge--warning"
            case _:
                """"""
    except ValueError:
        return ""

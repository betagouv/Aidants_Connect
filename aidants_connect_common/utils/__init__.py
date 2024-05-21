from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta
from logging import getLogger
from textwrap import dedent
from typing import TYPE_CHECKING, Type

from django.conf import settings
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models import F, Field, Model
from django.http import HttpRequest
from django.template import loader
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import escape

import pgtrigger
from markdown import markdown
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.nl2br import Nl2BrExtension
from mjml import mjml2html

if TYPE_CHECKING:
    from aidants_connect_habilitation.models import Issuer

logger = getLogger()


@transaction.atomic
def generate_new_datapass_id() -> int:
    from aidants_connect_common.models import IdGenerator

    id_datapass = IdGenerator.objects.select_for_update().get(
        code=settings.DATAPASS_CODE_FOR_ID_GENERATOR
    )

    id_datapass.last_id = F("last_id") + 1
    id_datapass.save()
    id_datapass.refresh_from_db()
    return id_datapass.last_id


class DateTimeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return (datetime.min + obj).time().isoformat()

        return super(DateTimeJsonEncoder, self).default(obj)


def render_email(
    template_name: str, mjml_context: dict, text_context: dict | None = None
) -> tuple[str, str]:
    template_name = template_name.removesuffix(".mjml")
    text_template = f"{template_name}.txt"
    mjml_template = f"{template_name}.mjml"

    text_context = text_context or mjml_context
    text_email = loader.render_to_string(text_template, text_context)
    html_email = mjml2html(
        loader.render_to_string(mjml_template, mjml_context),
        fonts={"Marianne": build_url(static("css/email.css"))},
    )

    logger.info(f"Rendering email with template {mjml_template}")

    return text_email, html_email


def join_url_parts(base: str, *args):
    if len(args) == 0:
        return base
    rest, tail = args[:-1], args[-1]
    parts = "/".join(
        [
            *[arg.removeprefix("/").removesuffix("/") for arg in rest],
            tail.removeprefix("/"),
        ]
    )
    return f"{base.removesuffix('/')}/{parts}"


def build_url(path: None | str):
    path = path or ""
    return (
        f"http{'s' if settings.SSL else ''}://{settings.HOST.removesuffix('/')}"
        f"/{path.removeprefix('/')}"
    )


def render_markdown(content: str) -> str:
    return markdown(
        escape(content),
        extensions=[
            Nl2BrExtension(),  # New line will be treated as linebreak
            AttrListExtension(),  # Allows to add HTML classes and ID
        ],
    )


class PGTriggerExtendedFunc(pgtrigger.Func):
    """Temporary until https://github.com/Opus10/django-pgtrigger/pull/150/ is merged"""

    def __init__(
        self, func, additionnal_models: dict[str, type[models.Model]] | None = None
    ):
        super().__init__(dedent(re.sub(r"[ \t\r\f\v]+\n", "\n", func)).strip())
        self.additionnal_models = additionnal_models or {}

    def render(self, model: models.Model) -> str:
        fields = pgtrigger.utils.AttrDict(
            {field.name: field for field in model._meta.fields}
        )
        columns = pgtrigger.utils.AttrDict(
            {field.name: field.column for field in model._meta.fields}
        )
        format_parameters = {"meta": model._meta, "fields": fields, "columns": columns}
        for prefix, additionnal_model in self.additionnal_models.items():
            format_parameters.update(
                {
                    f"{prefix}_meta": additionnal_model._meta,
                    f"{prefix}_fields": pgtrigger.utils.AttrDict(
                        {field.name: field for field in additionnal_model._meta.fields}
                    ),
                    f"{prefix}_columns": pgtrigger.utils.AttrDict(
                        {
                            field.name: field.column
                            for field in additionnal_model._meta.fields
                        }
                    ),
                }
            )
        return self.func.format(**format_parameters)


def model_fields(model: Type[Model] | None) -> dict[str, Field]:
    result = {}
    if not hasattr(model, "_meta"):
        return result

    for field in model._meta.fields:
        result[field.name] = field
        result[field.attname] = field
    return result


def issuer_exists_send_reminder_email(request: HttpRequest, issuer: "Issuer"):
    text_message, html_message = render_email(
        "email/issuer_profile_reminder.mjml",
        {
            "url": request.build_absolute_uri(
                reverse(
                    "habilitation_issuer_page",
                    kwargs={"issuer_id": str(issuer.issuer_id)},
                )
            ),
        },
    )

    send_mail(
        from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
        recipient_list=[issuer.email],
        subject=settings.EMAIL_HABILITATION_ISSUER_EMAIL_ALREADY_EXISTS_SUBJECT,
        message=text_message,
        html_message=html_message,
    )

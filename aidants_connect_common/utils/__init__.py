import json
from datetime import date, datetime, time, timedelta
from logging import getLogger

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.template import loader
from django.templatetags.static import static
from django.utils.html import escape

from markdown import markdown
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.nl2br import Nl2BrExtension
from mjml import mjml2html

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

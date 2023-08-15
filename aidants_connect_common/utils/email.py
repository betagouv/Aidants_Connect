from logging import getLogger

from django.template import loader
from django.templatetags.static import static

from mjml import mjml2html

from aidants_connect_common.utils.urls import build_url

logger = getLogger()


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

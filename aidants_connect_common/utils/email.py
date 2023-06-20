import re
from logging import getLogger

from django.template import loader

from mjml import mjml2html

logger = getLogger()


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    template_name = template_name.removesuffix(".mjml")
    text_template = f"{template_name}.txt"
    mjml_template = f"{template_name}.mjml"

    html_email_str = loader.render_to_string(mjml_template, context)
    text_email = loader.render_to_string(text_template, context)
    html_email = mjml2html(html_email_str)

    logger.info(f"Rendering email with template {mjml_template}")

    if re.findall(r"<mj-[^>]+>", html_email, re.M):
        logger.error(
            "MJML was not correctly rendered.\n"
            f"Template email:{html_email_str},\n"
            f"Rendered MJML: {html_email}"
        )

    return text_email, html_email

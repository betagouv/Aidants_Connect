from django.template import loader

from mjml import mjml2html


def render_email(template_name: str, context: dict) -> tuple[str, str]:
    template_name = template_name.removesuffix(".mjml")
    text_template = f"{template_name}.txt"
    mjml_template = f"{template_name}.mjml"

    text_email = loader.render_to_string(text_template, context)
    html_email = mjml2html(loader.render_to_string(mjml_template, context))

    return text_email, html_email

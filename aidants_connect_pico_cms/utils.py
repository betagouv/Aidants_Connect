from django.utils.html import escape

from markdown import markdown
from markdown.extensions.attr_list import AttrListExtension

from aidants_connect import settings


def render_markdown(content: str) -> str:
    return markdown(
        escape(content),
        extensions=[
            AttrListExtension(),  # Allows to add HTML classes and ID
        ],
    )


def is_lang_rtl(lang_code):
    return lang_code in settings.LANGUAGES_BIDI

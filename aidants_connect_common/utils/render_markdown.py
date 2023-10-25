from django.utils.html import escape

from markdown import markdown
from markdown.extensions.attr_list import AttrListExtension
from markdown.extensions.nl2br import Nl2BrExtension


def render_markdown(content: str) -> str:
    return markdown(
        escape(content),
        extensions=[
            Nl2BrExtension(),  # New line will be treated as linebreak
            AttrListExtension(),  # Allows to add HTML classes and ID
        ],
    )

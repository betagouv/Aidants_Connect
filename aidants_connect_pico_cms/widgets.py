from django.conf import settings
from django.forms import Media, Textarea
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import html_safe


@html_safe
class JSModulePath:
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f'<script type="module" src="{static(self.path)}" rel="stylesheet">'


class MarkdownTextarea(Textarea):
    markdown_editor_js_files = [
        JSModulePath("js/widgets/markdown-editor.js"),
        JSModulePath("js/widgets/markdown-editor-init.js"),
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        base_attrs.setdefault(
            "data-markdown-editor-render-endpoint-value", reverse("markdown_render")
        )
        extra_attrs = extra_attrs or {}
        extra_attrs["data-markdown-editor-render-kwarg-value"] = "body"
        extra_attrs["data-markdown-editor-target"] = "textareaContainer"
        return super().build_attrs(base_attrs, extra_attrs)

    @property
    def media(self):
        return Media(
            js=(
                settings.STIMULUS_JS_URL,
                settings.MD_EDITOR_JS_URL,
                *self.markdown_editor_js_files,
            ),
            css={
                "screen": (
                    settings.MD_EDITOR_CSS_URL,
                    "css/fork-awesome.min.css",
                    "css/mardown-editor.css",
                )
            },
        )


class TranslationMarkdownTextarea(MarkdownTextarea):
    markdown_editor_js_files = [
        JSModulePath("js/widgets/translations-markdown-editor.js"),
    ]

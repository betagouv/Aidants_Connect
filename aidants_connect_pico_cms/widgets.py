from django.conf import settings
from django.forms import Media, Textarea
from django.urls import reverse

from aidants_connect_common.widgets import JSModulePath


class MarkdownTextarea(Textarea):
    markdown_editor_js_files = [
        JSModulePath("js/widgets/markdown-editor-init.mjs"),
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
            js=self.markdown_editor_js_files,
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
        JSModulePath("js/widgets/translations-markdown-editor.mjs"),
    ]

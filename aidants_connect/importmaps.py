from django.conf import settings

from importmap import static

importmaps = {
    "Stimulus": settings.STIMULUS_JS_URL,
    "AidantsConnectApplication": static("js/ac-app.mjs"),
    "MarkdownEditor": static("js/widgets/markdown-editor.mjs"),
    "autoComplete": settings.AUTOCOMPLETE_SCRIPT_SRC,
}

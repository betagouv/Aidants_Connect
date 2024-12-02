from django.conf import settings

from importmap import static

importmaps = {
    "Stimulus": settings.STIMULUS_JS_URL.replace("umd.js", "js"),
    "AidantsConnectApplication": static("js/ac-app.mjs"),
    "MarkdownEditor": static("js/widgets/markdown-editor.mjs"),
    "ChartJS": settings.CHARTS_JS_URL,
    "ChartJSDatalabel": settings.CHARTS_JS_DATALABEL_URL,
}

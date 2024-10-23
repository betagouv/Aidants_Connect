from django.conf import settings

from importmap import static

importmaps = {
    "AidantsConnectApplication": static("js/ac-app.mjs"),
    "Stimulus": settings.STIMULUS_JS_URL.replace("umd.js", "js"),
}

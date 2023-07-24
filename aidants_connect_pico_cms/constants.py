from aidants_connect import settings

MANDATE_TRANSLATION_LANGUAGE_AVAILABLE = {
    code: name
    for code, name in settings.LANGUAGES
    if not code == settings.LANGUAGE_CODE
}

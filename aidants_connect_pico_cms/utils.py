from aidants_connect import settings


def is_lang_rtl(lang_code):
    return lang_code in settings.LANGUAGES_BIDI

from re import escape

from django.db.models import IntegerField, Value
from django.db.models.functions import Cast, Replace
from django.utils.text import slugify

from aidants_connect import settings


def is_lang_rtl(lang_code):
    return lang_code in settings.LANGUAGES_BIDI


def compute_correct_slug(cls, name):
    slug = slugify(name)

    if not cls._meta.model.objects.filter(slug=slug).exists():
        return slug

    try:
        last_slug_idx = (
            cls._meta.model.objects.filter(slug__regex=rf"^{escape(slug)}-\d+")
            .annotate(slug_idx=Cast(Replace("slug", Value(f"{slug}-")), IntegerField()))
            .order_by("-slug_idx")
            .values_list("slug_idx", flat=True)[0]
        )

        next_idx = int(last_slug_idx) + 1

        return f"{slug}-{next_idx}"
    except IndexError:
        return f"{slug}-1"

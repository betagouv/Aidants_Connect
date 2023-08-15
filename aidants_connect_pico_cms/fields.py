from django.db import models

from aidants_connect_pico_cms.widgets import MarkdownTextarea


class MarkdownField(models.TextField):
    def formfield(self, **kwargs):
        kwargs.setdefault("widget", MarkdownTextarea)
        # Case where the provided widget is a Django's default and does not come from
        # a user override in form
        if not isinstance(kwargs["widget"], MarkdownTextarea) and not issubclass(
            kwargs["widget"], MarkdownTextarea
        ):
            kwargs["widget"] = MarkdownTextarea
        return super().formfield(**kwargs)

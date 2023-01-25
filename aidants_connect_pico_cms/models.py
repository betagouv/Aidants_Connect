from django.db import models
from django.urls import reverse
from django.utils.html import escape, mark_safe

from markdown import markdown
from markdown.extensions.attr_list import AttrListExtension

from aidants_connect_pico_cms.constants import MANDATE_TRANSLATION_LANGUAGE_AVAILABLE
from aidants_connect_web.models import Aidant


class MarkdownContentMixin(models.Model):
    body = models.TextField("Contenu")

    def to_html(self):
        return mark_safe(
            markdown(
                escape(self.body),
                extensions=[
                    AttrListExtension(),  # Allows to add HTML classes and ID
                ],
            )
        )

    class Meta:
        abstract = True


class CmsContent(MarkdownContentMixin, models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    updated_by = models.ForeignKey(
        Aidant, models.SET_NULL, blank=True, null=True, verbose_name="Modifié par"
    )
    published = models.BooleanField("Publié")
    slug = models.SlugField("Clé d’URL")
    sort_order = models.PositiveSmallIntegerField("Tri", null=True, db_index=True)

    class Meta:
        abstract = True


class Testimony(CmsContent):
    name = models.CharField("Nom de l'aidant·e qui témoigne", max_length=255)
    job = models.CharField("Fonction de l'aidant·e qui témoigne", max_length=255)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("temoignage-detail", kwargs={"slug": self.slug})

    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"


class MandateTranslation(MarkdownContentMixin):
    lang = models.CharField(
        "Langue du mandat traduit",
        primary_key=True,
        max_length=10,
        choices=list(sorted(MANDATE_TRANSLATION_LANGUAGE_AVAILABLE.items())),
    )

    @property
    def lang_name(self):
        return MANDATE_TRANSLATION_LANGUAGE_AVAILABLE.get(self.lang, "")

    class Meta:
        verbose_name = "Traduction de mandat"
        verbose_name_plural = "Traductions de mandat"

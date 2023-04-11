from django.db import models
from django.urls import reverse
from django.utils.html import mark_safe

from aidants_connect_pico_cms.constants import MANDATE_TRANSLATION_LANGUAGE_AVAILABLE
from aidants_connect_pico_cms.fields import MarkdownField
from aidants_connect_pico_cms.utils import is_lang_rtl, render_markdown


class MarkdownContentMixin(models.Model):
    body = MarkdownField("Contenu")

    def to_html(self):
        return mark_safe(render_markdown(self.body))

    class Meta:
        abstract = True


class CmsContent(MarkdownContentMixin, models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    published = models.BooleanField("Publié")
    slug = models.SlugField(
        "Clé d’URL",
        help_text=(
            "Par exemple <code>questions-generales</code> pour "
            "« Questions générales ».<br>"
            "Sera utilisée pour créer des liens vers cet élément de contenu.<br>"
            "50 caractères maximum."
        ),
    )
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

    @property
    def is_rtl(self):
        return is_lang_rtl(self.lang)

    def __str__(self):
        return (
            f"{self.lang_name}{' (écriture de droite à gauche)' if self.is_rtl else ''}"
        )

    class Meta:
        verbose_name = "Traduction de mandat"
        verbose_name_plural = "Traductions de mandat"


class FaqCategory(CmsContent):
    name = models.CharField("Nom", max_length=255)
    body = MarkdownField("Introduction", blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("faq-category-detail", kwargs={"slug": self.slug})

    class Meta:
        verbose_name = "Catégorie FAQ"
        verbose_name_plural = "Catégories FAQ"


class FaqQuestion(CmsContent):
    question = models.TextField("Question")
    category = models.ForeignKey(
        FaqCategory, models.SET_NULL, null=True, verbose_name="Catégorie"
    )
    body = models.TextField("Réponse")

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = "Question FAQ"
        verbose_name_plural = "Questions FAQ"

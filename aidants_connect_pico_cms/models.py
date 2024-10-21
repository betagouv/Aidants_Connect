from typing import Self

from django.db import models
from django.db.models import F
from django.templatetags.static import static
from django.urls import reverse

from aidants_connect_common.models import MarkdownContentMixin
from aidants_connect_pico_cms.constants import MANDATE_TRANSLATION_LANGUAGE_AVAILABLE
from aidants_connect_pico_cms.fields import MarkdownField
from aidants_connect_pico_cms.utils import compute_correct_slug, is_lang_rtl


class CmsContent(MarkdownContentMixin, models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    published = models.BooleanField("Publié")
    sort_order = models.PositiveSmallIntegerField("Tri", null=True, db_index=True)
    slug = models.SlugField("Clé d’URL", unique=True)

    @property
    def slug_derived_field(self):
        raise NotImplementedError()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = compute_correct_slug(self, self.slug_derived_field)

        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class TestimonyQuerySet(models.QuerySet):
    def for_display(self) -> Self:
        return self.filter(published=True).order_by("sort_order", "slug")


class Testimony(CmsContent):
    name = models.CharField("Nom de l'aidant·e qui témoigne", max_length=255)
    job = models.CharField("Fonction de l'aidant·e qui témoigne", max_length=255)
    profile_picture_url = models.URLField(
        "URL vers la photo de profil de la personne qui témoigne",
        null=True,
        default=None,
    )
    quote = models.CharField(
        "Citation à afficher sur la page d'accueil", max_length=255
    )

    objects = TestimonyQuerySet.as_manager()

    def __str__(self):
        return self.name

    @property
    def slug_derived_field(self):
        return self.name

    @property
    def profile_picture(self):
        return self.profile_picture_url or static("images/default-profile-picture.png")

    def get_absolute_url(self):
        return reverse("temoignages_detail", kwargs={"slug": self.slug})

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


class FaqSection(CmsContent):
    name = models.CharField("Nom", max_length=255)
    body = MarkdownField("Introduction", blank=True, default="")

    def __str__(self):
        return self.name

    @property
    def slug_derived_field(self):
        return self.name

    class Meta:
        abstract = True


class FaqCategory(FaqSection):
    def get_questions(self, see_draft=False):
        filter_kwargs = (
            {"published": True, "subcategory__published": True} if not see_draft else {}
        )
        return (
            FaqQuestion.objects.filter(**filter_kwargs, category=self)
            .order_by(F("subcategory__sort_order").asc(nulls_first=True), "sort_order")
            .prefetch_related("subcategory")
        )

    def get_absolute_url(self):
        return reverse("faq_category_detail", kwargs={"slug": self.slug})

    class Meta:
        verbose_name = "Catégorie FAQ"
        verbose_name_plural = "Catégories FAQ"


class FaqSubCategory(FaqSection):
    class Meta:
        verbose_name = "Sous-catégorie FAQ"
        verbose_name_plural = "Sous-catégories FAQ"


class FaqQuestion(CmsContent):
    question = models.TextField("Question")
    body = MarkdownField("Réponse")
    category = models.ForeignKey(
        FaqCategory, models.SET_NULL, null=True, default=None, verbose_name="Catégorie"
    )
    subcategory = models.ForeignKey(
        FaqSubCategory,
        models.SET_NULL,
        null=True,
        default=None,
        verbose_name="Sous-catégorie",
    )

    def __str__(self):
        return self.question

    @property
    def slug_derived_field(self):
        return self.question

    def get_absolute_url(self):
        return f"{self.category.get_absolute_url()}#question-{self.slug}"

    class Meta:
        verbose_name = "Question FAQ"
        verbose_name_plural = "Questions FAQ"

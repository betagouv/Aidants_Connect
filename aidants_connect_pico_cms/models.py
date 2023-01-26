from django.db import models
from django.urls import reverse
from django.utils.html import escape, mark_safe

from markdown import markdown

from aidants_connect_web.models import Aidant


class CmsContent(models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    updated_by = models.ForeignKey(
        Aidant, models.SET_NULL, blank=True, null=True, verbose_name="Modifié par"
    )
    published = models.BooleanField("Publié")
    slug = models.SlugField("Clé d’URL")
    sort_order = models.PositiveSmallIntegerField("Tri", null=True, db_index=True)
    body = models.TextField("Contenu")

    def to_html(self):
        return mark_safe(markdown(escape(self.body)))

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

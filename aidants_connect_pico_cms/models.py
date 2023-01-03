from django.db import models

from aidants_connect_web.models import Aidant


class CmsContent(models.Model):
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    updated_at = models.DateTimeField("Date de modification", auto_now=True)
    updated_by = models.ForeignKey(
        Aidant, models.SET_NULL, blank=True, null=True, verbose_name="Modifié par"
    )
    published = models.BooleanField("Publié")

    class Meta:
        abstract = True


class Testimony(CmsContent):
    name = models.CharField("Nom de l'aidant·e qui témoigne", max_length=255)
    job = models.CharField("Fonction de l'aidant·e qui témoigne", max_length=255)
    body = models.TextField("Contenu")
    # picture : @todo

    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"

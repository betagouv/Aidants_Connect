from django.db import models

from aidants_connect_web.models import Aidant


class EmailStatistics(models.Model):
    nb_emails_sent = models.IntegerField("Nombre d'emails envoyés", default=0)
    last_sent_at = models.DateTimeField("Date du dernier envoi", null=True, blank=True)
    code_email = models.CharField("Code email", max_length=50)

    class Meta:
        verbose_name = "Statistiques d'envoi d'email"
        verbose_name_plural = "Statistiques d'envois d'email"

    def __str__(self):
        return f"Statistiques d'envoi d'email pour {self.code_email}"


class AidantEmailStats(models.Model):
    aidant = models.ForeignKey(Aidant, on_delete=models.CASCADE)
    code_email = models.CharField("Code email", max_length=50)
    email_type = models.ForeignKey(
        EmailStatistics, verbose_name="Type d'email", on_delete=models.CASCADE
    )
    sending_date = models.DateTimeField("Date d'envoi", null=True, blank=True)
    infos = models.TextField("Informations supplémentaire", blank=True, null=True)

    class Meta:
        verbose_name = "Envoi d'email pour un aidant"
        verbose_name_plural = "Envois d'email pour un aidant"

    def __str__(self):
        return f"Envoi d'email pour {self.aidant.email} pour le type {self.email_type.code_email}"  # noqa: E501

    def get_sending_date_display(self):
        if self.sending_date:
            return self.sending_date.strftime("%d/%m/%Y %H:%M")
        return "Non envoyé"

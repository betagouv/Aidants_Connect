from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from aidants_connect_web.models import Autorisation, Journal


@receiver(user_logged_in)
def on_login(sender, user, request, **kwargs):
    Journal.objects.connection(user)


@receiver(post_save, sender=Autorisation)
def on_autorisation_change(sender, instance, created, **kwargs):
    if created:
        Journal.objects.autorisation_creation(instance)
    else:
        Journal.objects.autorisation_update(instance)

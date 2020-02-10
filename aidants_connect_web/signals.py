from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from aidants_connect_web.models import Journal, Mandat


@receiver(user_logged_in)
def on_login(sender, user, request, **kwargs):
    Journal.objects.connection(user)


@receiver(post_save, sender=Mandat)
def on_mandat_change(sender, instance, created, **kwargs):
    if created:
        Journal.objects.mandat_creation(instance)
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and ("last_used_date" in update_fields):
            Journal.objects.mandat_use(instance)
        else:
            Journal.objects.mandat_update(instance)

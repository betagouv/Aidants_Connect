from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings

from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.models import Aidant, Journal


@receiver(user_logged_in)
def log_connection_on_login(sender, user: Aidant, request, **kwargs):
    Journal.log_connection(user)


@receiver(user_logged_in)
def lower_totp_tolerance_on_login(sender, user: Aidant, request, **kwargs):
    if not settings.LOWER_TOTP_TOLERANCE_ON_LOGIN:
        return

    for device in TOTPDevice.objects.filter(
        user=user, tolerance__gte=2, confirmed=True
    ):
        device.tolerance = 1
        device.save()

def __2023_10_26_otp_devices_naming():
    from django.db.models import TextField, Value
    from django.db.models.functions import Cast, Concat

    from django_otp.plugins.otp_totp.models import TOTPDevice

    from aidants_connect_web.constants import OTP_APP_DEVICE_NAME

    # First delete orphaned TOTP devices that were once associated with a TOTP card
    TOTPDevice.objects.filter(totp_card__isnull=True, name__icontains="Carte").delete()
    TOTPDevice.objects.filter(
        totp_card__isnull=True,
    ).update(name=Concat(Value(OTP_APP_DEVICE_NAME % ""), Cast("user_id", TextField())))

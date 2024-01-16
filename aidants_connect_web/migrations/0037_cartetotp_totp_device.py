import contextlib

import django.db.models.deletion
from django.db import migrations, models


def populate_totp_device(apps, _):
    CarteTOTP = apps.get_model("aidants_connect_web", "CarteTOTP")
    TOTPDevice = apps.get_model("otp_totp", "TOTPDevice")

    for card in CarteTOTP.objects.all():
        with contextlib.suppress(TOTPDevice.DoesNotExist):
            card.totp_device = TOTPDevice.objects.get(
                user=card.aidant, name=f"Carte n° {card.serial_number}"
            )
            card.save()

    TOTPDevice.objects.filter(tolerance__gt=3).update(tolerance=1)


class Migration(migrations.Migration):
    dependencies = [
        ("otp_totp", "0002_auto_20190420_0723"),
        ("aidants_connect_web", "0036_alter_habilitationrequest_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartetotp",
            name="totp_device",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="totp_card",
                to="otp_totp.totpdevice",
            ),
        ),
        migrations.RunPython(
            populate_totp_device, reverse_code=migrations.RunPython.noop
        ),
    ]

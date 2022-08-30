from datetime import timedelta

from django.db import migrations

from pytz import timezone as pytz_timezone


def fix_pytz_timzeones(apps, schema_editor):
    hrqs = apps.get_model(
        "aidants_connect_web", "HabilitationRequest"
    ).objects.filter(date_test_pix__isnull=False).all()

    paris_tz = pytz_timezone("Europe/Paris")
    lmt_offset = timedelta()

    for offset, _, name in paris_tz._tzinfos.keys():
        if name == "LMT":
            lmt_offset = offset
            break

    for item in hrqs:
        # Dates use UTC TZ in DB, only with improper offset
        item.date_test_pix = item.date_test_pix + lmt_offset
        item.save()


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0010_auto_20220825_1121"),
    ]

    operations = [
        migrations.RunPython(fix_pytz_timzeones)
    ]

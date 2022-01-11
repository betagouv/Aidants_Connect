# flake8: noqa
from django.db import migrations

from aidants_connect.constants import RequestOriginConstants


def add_organisation_types(apps, schema_editor):
    OrganisationType = apps.get_model("aidants_connect_web", "OrganisationType")
    for type in RequestOriginConstants:
        OrganisationType.objects.get_or_create(id=type.value, name=type.label)


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0049_auto_20210321_2152"),
    ]

    operations = [
        migrations.RunPython(add_organisation_types),
        # Resets the starting value for AutoField
        # See https://docs.djangoproject.com/en/dev/ref/databases/#manually-specified-autoincrement-pk
        migrations.RunSQL(
            """SELECT setval(pg_get_serial_sequence('"aidants_connect_web_organisationtype"','id'), coalesce(max("id"), 1), max("id") IS NOT null) 
            FROM "aidants_connect_web_organisationtype";"""
        ),
    ]

from django.db import migrations

from aidants_connect_web.utilities import create_first_user_organisation_and_token


def populate_database(apps, _):
    create_first_user_organisation_and_token()


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0078_auto_20211122_1813"),
        ("otp_static", "__latest__"),
    ]

    operations = [
        migrations.RunPython(populate_database, reverse_code=migrations.RunPython.noop),
    ]

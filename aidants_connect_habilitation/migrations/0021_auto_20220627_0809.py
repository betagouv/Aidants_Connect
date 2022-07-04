from django.db import migrations

from aidants_connect_habilitation.utils import real_fix_orga_request_status


def fix_orga_request_without_status(apps, schema_editor):
    OrganisationRequest = apps.get_model('aidants_connect_habilitation',
                                         'OrganisationRequest')
    real_fix_orga_request_status(OrganisationRequest)


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0020_auto_20220420_0935'),
    ]

    operations = [
        migrations.RunPython(fix_orga_request_without_status)
    ]

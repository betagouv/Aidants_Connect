from django.db import migrations

from aidants_connect_web.utilities import (
    real_populate_department_table,
    real_populate_region_table,
)


def populate_region_table(apps, schema_editor):
    Region = apps.get_model('aidants_connect_web',
                                         'Region')
    real_populate_region_table(Region)

def populate_department_table(apps, schema_editor):
    Departement = apps.get_model('aidants_connect_web',
                                         'Departement')
    Region = apps.get_model('aidants_connect_web',
                                         'Region')
    real_populate_department_table(Departement, Region)


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0007_departement_region'),
    ]

    operations = [
        migrations.RunPython(populate_region_table),
        migrations.RunPython(populate_department_table)
    ]

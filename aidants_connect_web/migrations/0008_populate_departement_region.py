import os

from django.db import migrations

from aidants_connect import settings


def populate_region_table(apps, schema_editor):
    Region = apps.get_model('aidants_connect_web',
                                         'Region')

    try:
        import pandas as pd
        file_path = os.path.join(settings.STATIC_ROOT, "insee_files/region_2022.csv")
        df = pd.read_csv(file_path)
        for i, region in df.iterrows():
            Region.objects.get_or_create(name=region["LIBELLE"], codeinsee=region["REG"])
    except ImportError:
        # pandas was removed from dependencies in a migration refactor.
        # This will be removed later.
        pass


def populate_department_table(apps, schema_editor):
    Departement = apps.get_model('aidants_connect_web',
                                         'Departement')
    Region = apps.get_model('aidants_connect_web',
                                         'Region')

    try:
        import pandas as pd
        file_path = os.path.join(settings.STATIC_ROOT, "insee_files/departement_2022.csv")
        df = pd.read_csv(file_path)
        for i, departement in df.iterrows():
            region = Region.objects.get(codeinsee=departement["REG"])
            Departement.objects.get_or_create(
                name=departement["LIBELLE"], codeinsee=departement["DEP"], region=region
            )
    except ImportError:
        # pandas was removed from dependencies in a migration refactor.
        # This will be removed later.
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0007_departement_region'),
    ]

    operations = [
        migrations.RunPython(populate_region_table),
        migrations.RunPython(populate_department_table)
    ]

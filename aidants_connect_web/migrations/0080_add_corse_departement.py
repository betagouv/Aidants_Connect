from os.path import dirname, join as path_join
from json import loads as json_loads

import django
from django.db import migrations, models, transaction

import aidants_connect_web


def populate_corse_departement(apps, _):
    DatavizRegion = apps.get_model("aidants_connect_web", "DatavizRegion")
    DatavizDepartment = apps.get_model("aidants_connect_web", "DatavizDepartment")
    DatavizDepartmentsToRegion = apps.get_model(
        "aidants_connect_web", "DatavizDepartmentsToRegion"
    )
    departement, _ = DatavizDepartment.objects.get_or_create(
        zipcode=20, dep_name="Corse"
    )
    region = DatavizRegion.objects.get(name="Corse")
    DatavizDepartmentsToRegion.objects.get_or_create(
        department=departement, region=region
    )

    for zipcode in ["2A", "2B"]:
        try:
            departement = DatavizDepartment.objects.get(zipcode=zipcode)
            DatavizDepartmentsToRegion.objects.get(department=departement).delete()
            departement.delete()
        except (
            DatavizDepartment.DoesNotExist,
            DatavizDepartmentsToRegion.DoesNotExist,
        ):
            pass


def reverse_populate_corse_departement(apps, _):
    DatavizRegion = apps.get_model("aidants_connect_web", "DatavizRegion")
    DatavizDepartment = apps.get_model("aidants_connect_web", "DatavizDepartment")
    DatavizDepartmentsToRegion = apps.get_model(
        "aidants_connect_web", "DatavizDepartmentsToRegion"
    )

    try:
        departement = DatavizDepartment.objects.get(zipcode=20)
        DatavizDepartmentsToRegion.objects.get(department=departement).delete()
        departement.delete()
    except (
        DatavizDepartment.DoesNotExist,
        DatavizDepartmentsToRegion.DoesNotExist,
    ):
        pass

    region = DatavizRegion.objects.get(name="Corse")
    for zipcode, dep_name in [("2A", "Corse-du-Sud"), ("2B", "Haute-Corse")]:
        departement, _ = DatavizDepartment.objects.get_or_create(
            zipcode=zipcode, dep_name=dep_name
        )
        DatavizDepartmentsToRegion.objects.get_or_create(
            department=departement, region=region
        )


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0079_organisation_city"),
    ]

    operations = [
        migrations.RunPython(
            populate_corse_departement,
            reverse_code=reverse_populate_corse_departement,
        ),
    ]

from os.path import dirname, join as path_join
from json import loads as json_loads

import django
from django.db import migrations, models, transaction

import aidants_connect_web


def populate_departements_to_region_table(apps, _):
    # noinspection PyPep8Naming
    DatavizRegion = apps.get_model("aidants_connect_web", "DatavizRegion")
    # noinspection PyPep8Naming
    DatavizDepartment = apps.get_model("aidants_connect_web", "DatavizDepartment")
    # noinspection PyPep8Naming
    DatavizDepartmentsToRegion = apps.get_model(
        "aidants_connect_web", "DatavizDepartmentsToRegion"
    )

    fixture = path_join(
        dirname(aidants_connect_web.__file__), "fixtures", "departements_region.json"
    )

    with open(fixture) as f:
        json = json_loads(f.read())
        regions = sorted(set(item["region_name"] for item in json))

        for region in regions:
            DatavizRegion(name=region).save()

        for item in json:
            department = DatavizDepartment(
                zipcode=item["zipcode"], dep_name=item["dep_name"]
            )
            department.save()

            region = DatavizRegion.objects.get(name=item["region_name"])

            DatavizDepartmentsToRegion(department=department, region=region).save()


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0051_mandat_template_path"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatavizDepartment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "zipcode",
                    models.CharField(
                        max_length=10, unique=True, verbose_name="Code Postal"
                    ),
                ),
                (
                    "dep_name",
                    models.CharField(max_length=50, verbose_name="Nom de département"),
                ),
            ],
            options={
                "verbose_name": "Département",
                "db_table": "dataviz_department",
            },
        ),
        migrations.CreateModel(
            name="DatavizRegion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="Nom de région"
                    ),
                ),
            ],
            options={
                "verbose_name": "Région",
                "db_table": "dataviz_region",
            },
        ),
        migrations.CreateModel(
            name="DatavizDepartmentsToRegion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "department",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="aidants_connect_web.datavizdepartment",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="aidants_connect_web.datavizregion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assocation départments/région",
                "verbose_name_plural": "Assocations départments/région",
                "db_table": "dataviz_departements_to_region",
            },
        ),
        migrations.RunPython(
            populate_departements_to_region_table,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

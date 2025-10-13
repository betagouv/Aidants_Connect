import django.db.models.deletion
from django.db import migrations, models

import phonenumber_field.modelfields


def populate_manager_table(apps, _):
    Manager = apps.get_model("aidants_connect_habilitation", "Manager")
    OrganisationRequest = apps.get_model(
        "aidants_connect_habilitation", "OrganisationRequest"
    )

    for organisation_request in OrganisationRequest.objects.all():
        manager = Manager.objects.create(
            first_name=organisation_request.manager_first_name,
            last_name=organisation_request.manager_last_name,
            email=organisation_request.manager_email,
            profession=organisation_request.manager_profession,
            phone=organisation_request.manager_phone,
            address="Undefined",
            zipcode="00000",
            city="Undefined",
        )
        organisation_request.manager = manager
        organisation_request.save()


def reverse_populate_manager_table(apps, _):
    Manager = apps.get_model("aidants_connect_habilitation", "Manager")

    for manager in Manager.objects.all():
        organisation_request = manager.organisation
        organisation_request.manager_first_name = manager.first_name
        organisation_request.manager_last_name = manager.last_name
        organisation_request.manager_profession = manager.profession
        organisation_request.manager_email = manager.email
        organisation_request.manager_phone = manager.phone
        organisation_request.save()


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_habilitation", "0004_auto_20220118_1050"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_email",
            field=models.EmailField(
                default=None,
                max_length=150,
                null=True,
                verbose_name="Email du responsable",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_first_name",
            field=models.CharField(
                default=None,
                max_length=150,
                null=True,
                verbose_name="Prénom du responsable",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_last_name",
            field=models.CharField(
                default=None,
                max_length=150,
                null=True,
                verbose_name="Nom du responsable",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True,
                default=None,
                max_length=128,
                null=True,
                region=None,
                verbose_name="Téléphone du responsable",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_profession",
            field=models.CharField(
                default=None,
                max_length=150,
                null=True,
                verbose_name="Profession du responsable",
            ),
        ),
        migrations.CreateModel(
            name="DataPrivacyOfficer",
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
                ("first_name", models.CharField(max_length=150, verbose_name="Prénom")),
                ("last_name", models.CharField(max_length=150, verbose_name="Nom")),
                ("email", models.EmailField(max_length=150, verbose_name="Email")),
                (
                    "profession",
                    models.CharField(max_length=150, verbose_name="Profession"),
                ),
                (
                    "phone",
                    phonenumber_field.modelfields.PhoneNumberField(
                        blank=True,
                        max_length=128,
                        region=None,
                        verbose_name="Téléphone",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Manager",
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
                ("first_name", models.CharField(max_length=150, verbose_name="Prénom")),
                ("last_name", models.CharField(max_length=150, verbose_name="Nom")),
                ("email", models.EmailField(max_length=150, verbose_name="Email")),
                (
                    "profession",
                    models.CharField(max_length=150, verbose_name="Profession"),
                ),
                (
                    "phone",
                    phonenumber_field.modelfields.PhoneNumberField(
                        blank=True,
                        max_length=128,
                        region=None,
                        verbose_name="Téléphone",
                    ),
                ),
                ("address", models.TextField(verbose_name="Adresse")),
                (
                    "zipcode",
                    models.CharField(max_length=10, verbose_name="Code Postal"),
                ),
                (
                    "city",
                    models.CharField(max_length=255, verbose_name="Ville"),
                ),
                (
                    "is_aidant",
                    models.BooleanField(
                        default=False, verbose_name="C'est aussi un aidant"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="organisationrequest",
            name="data_privacy_officer",
            field=models.OneToOneField(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organisation",
                to="aidants_connect_habilitation.dataprivacyofficer",
                verbose_name="Délégué à la protection des données",
            ),
        ),
        migrations.AddField(
            model_name="organisationrequest",
            name="manager",
            field=models.OneToOneField(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organisation",
                to="aidants_connect_habilitation.manager",
                verbose_name="Responsable",
            ),
        ),
        migrations.RunPython(
            populate_manager_table, reverse_code=reverse_populate_manager_table
        ),
        migrations.RemoveField(
            model_name="organisationrequest",
            name="manager_email",
        ),
        migrations.RemoveField(
            model_name="organisationrequest",
            name="manager_first_name",
        ),
        migrations.RemoveField(
            model_name="organisationrequest",
            name="manager_last_name",
        ),
        migrations.RemoveField(
            model_name="organisationrequest",
            name="manager_phone",
        ),
        migrations.RemoveField(
            model_name="organisationrequest",
            name="manager_profession",
        ),
        migrations.AlterField(
            model_name="aidantrequest",
            name="profession",
            field=models.CharField(max_length=150, verbose_name="Profession"),
        ),
        migrations.AlterField(
            model_name="issuer",
            name="email",
            field=models.EmailField(max_length=150, verbose_name="Email"),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(("draft_id__isnull", True), ("manager__isnull", False)),
                    _connector="OR",
                ),
                name="manager_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(
                        ("draft_id__isnull", True),
                        ("data_privacy_officer__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="data_privacy_officer_set",
            ),
        ),
    ]

# Generated by Django 4.2.1 on 2023-05-23 07:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0001_initial'),
        ('aidants_connect_web', '0027_notification_notification_must_ack_conditions'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_future_aidant',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_future_trained_aidant',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation ayant bénéficié de la formation AC'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_operational_aidants',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants opérationnels (nombre d’aidants formés, test Pix et carte reliée/activée) '),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_organisation_requests',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de demandes d’habilitation de structures au total'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_organisation_with_accredited_aidants',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de structures ayant des aidants habilités (formés, test Pix, au moins un aidant avec compte activé, carte activée)'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_organisation_with_at_least_one_ac_usage',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de structures où il y a au moins une utilisation d’AC'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_trained_aidant_since_begining',
            field=models.PositiveIntegerField(default=0, verbose_name="Nb d'aidant formés depuis de le début (inactif compris)"),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_usage_of_ac',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre d’accompagnements réalisés via AC'),
        ),
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_validated_organisation_requests',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de validation de demandes d’habilitation de structures par l’équipe AC'),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_aidant_can_create_mandat',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants formés et habilités (pouvant créer des mandats)'),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_aidant_who_have_created_mandat',
            field=models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants qui ont créé des mandats"),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_aidant_with_login',
            field=models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants pouvant créer des mandats et s'étant connecté"),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_aidants_is_active',
            field=models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants 'actif au sens django' "),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_aidants_without_totp',
            field=models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants sans carte TOTP "),
        ),
        migrations.CreateModel(
            name='AidantStatistiquesbyRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date de création')),
                ('number_aidants', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidant")),
                ('number_aidants_is_active', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants 'actif au sens django' ")),
                ('number_responsable', models.PositiveIntegerField(default=0, verbose_name='Nb de responsable')),
                ('number_aidant_can_create_mandat', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants formés et habilités (pouvant créer des mandats)')),
                ('number_operational_aidants', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants opérationnels (nombre d’aidants formés, test Pix et carte reliée/activée) ')),
                ('number_aidants_without_totp', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants sans carte TOTP ")),
                ('number_aidant_with_login', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants pouvant créer des mandats et s'étant connecté")),
                ('number_aidant_who_have_created_mandat', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants qui ont créé des mandats")),
                ('number_future_aidant', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation')),
                ('number_trained_aidant_since_begining', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidant formés depuis de le début (inactif compris)")),
                ('number_future_trained_aidant', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation ayant bénéficié de la formation AC')),
                ('number_organisation_requests', models.PositiveIntegerField(default=0, verbose_name='Nombre de demandes d’habilitation de structures au total')),
                ('number_validated_organisation_requests', models.PositiveIntegerField(default=0, verbose_name='Nombre de validation de demandes d’habilitation de structures par l’équipe AC')),
                ('number_organisation_with_accredited_aidants', models.PositiveIntegerField(default=0, verbose_name='Nombre de structures ayant des aidants habilités (formés, test Pix, au moins un aidant avec compte activé, carte activée)')),
                ('number_organisation_with_at_least_one_ac_usage', models.PositiveIntegerField(default=0, verbose_name='Nombre de structures où il y a au moins une utilisation d’AC')),
                ('number_usage_of_ac', models.PositiveIntegerField(default=0, verbose_name='Nombre d’accompagnements réalisés via AC')),
                ('region', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='aidants_connect_common.region', verbose_name='Région')),
            ],
            options={
                'verbose_name': 'Statistiques aidants par région',
                'verbose_name_plural': 'Statistiques aidants par région',
            },
        ),
        migrations.CreateModel(
            name='AidantStatistiquesbyDepartment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date de création')),
                ('number_aidants', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidant")),
                ('number_aidants_is_active', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants 'actif au sens django' ")),
                ('number_responsable', models.PositiveIntegerField(default=0, verbose_name='Nb de responsable')),
                ('number_aidant_can_create_mandat', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants formés et habilités (pouvant créer des mandats)')),
                ('number_operational_aidants', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants opérationnels (nombre d’aidants formés, test Pix et carte reliée/activée) ')),
                ('number_aidants_without_totp', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants sans carte TOTP ")),
                ('number_aidant_with_login', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants pouvant créer des mandats et s'étant connecté")),
                ('number_aidant_who_have_created_mandat', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidants qui ont créé des mandats")),
                ('number_future_aidant', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation')),
                ('number_trained_aidant_since_begining', models.PositiveIntegerField(default=0, verbose_name="Nb d'aidant formés depuis de le début (inactif compris)")),
                ('number_future_trained_aidant', models.PositiveIntegerField(default=0, verbose_name='Nombre d’aidants en cours d’habilitation ayant bénéficié de la formation AC')),
                ('number_organisation_requests', models.PositiveIntegerField(default=0, verbose_name='Nombre de demandes d’habilitation de structures au total')),
                ('number_validated_organisation_requests', models.PositiveIntegerField(default=0, verbose_name='Nombre de validation de demandes d’habilitation de structures par l’équipe AC')),
                ('number_organisation_with_accredited_aidants', models.PositiveIntegerField(default=0, verbose_name='Nombre de structures ayant des aidants habilités (formés, test Pix, au moins un aidant avec compte activé, carte activée)')),
                ('number_organisation_with_at_least_one_ac_usage', models.PositiveIntegerField(default=0, verbose_name='Nombre de structures où il y a au moins une utilisation d’AC')),
                ('number_usage_of_ac', models.PositiveIntegerField(default=0, verbose_name='Nombre d’accompagnements réalisés via AC')),
                ('departement', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='aidants_connect_common.department', verbose_name='Département')),
            ],
            options={
                'verbose_name': 'Statistiques aidants par département',
                'verbose_name_plural': 'Statistiques aidants par département',
            },
        ),
    ]
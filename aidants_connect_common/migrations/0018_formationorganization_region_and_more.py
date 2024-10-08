# Generated by Django 4.2.15 on 2024-09-03 08:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0017_formationorganization_private_contacts_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formationorganization',
            name='region',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='aidants_connect_common.region'),
        ),
        migrations.AddField(
            model_name='formationorganization',
            name='type',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='aidants_connect_common.formationtype'),
        ),
    ]

# Generated by Django 4.2.15 on 2024-08-14 13:15

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0016_formationattendant_migrate_gfk'),
    ]

    operations = [
        migrations.AddField(
            model_name='formationorganization',
            name='private_contacts',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254),
                                                            blank=True, default=list, null=True, size=None, verbose_name='Contacts privés'),
        ),
        migrations.AlterField(
            model_name='formationorganization',
            name='contacts',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), blank=True, default=list, null=True, size=None, verbose_name='Contacts publics'),
        ),
    ]
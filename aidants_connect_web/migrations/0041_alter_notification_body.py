# Generated by Django 4.2.6 on 2023-10-25 11:33

from django.db import migrations

import aidants_connect_pico_cms.fields


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0040_organisation_and_multiple_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='body',
            field=aidants_connect_pico_cms.fields.MarkdownField(verbose_name='Contenu'),
        ),
    ]

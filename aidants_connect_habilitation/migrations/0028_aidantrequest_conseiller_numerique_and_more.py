# Generated by Django 4.2.10 on 2024-03-14 08:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0027_aidantrequest_habilitation_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidantrequest',
            name='conseiller_numerique',
            field=models.BooleanField(default=False, verbose_name='Est un conseiller numérique'),
        ),
        migrations.AddField(
            model_name='manager',
            name='conseiller_numerique',
            field=models.BooleanField(default=False, verbose_name='Est un conseiller numérique'),
        ),
    ]

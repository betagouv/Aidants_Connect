# Generated by Django 3.2.12 on 2022-04-05 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0015_remove_dpo_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisationrequest',
            name='data_pass_id',
            field=models.IntegerField(default=None, null=True, unique=True, verbose_name='Numéro Datapass'),
        ),
    ]

# Generated by Django 4.2.17 on 2025-05-20 07:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0070_habilitationrequest_connexion_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='habilitationrequest',
            name='created_by_fne',
            field=models.BooleanField(default=False, verbose_name='Création FNE'),
        ),
        migrations.AddField(
            model_name='organisation',
            name='created_by_fne',
            field=models.BooleanField(default=False, verbose_name='Création FNE'),
        ),
    ]

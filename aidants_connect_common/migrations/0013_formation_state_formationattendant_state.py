# Generated by Django 4.2.11 on 2024-05-07 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0012_remove_formationattendant_check_attendants_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formation',
            name='state',
            field=models.IntegerField(choices=[(1, 'Active'), (2, 'Annulé')], default=1, verbose_name='État de la formation'),
        ),
        migrations.AddField(
            model_name='formationattendant',
            name='state',
            field=models.IntegerField(choices=[(1, 'Par défaut'), (2, 'En attente'), (3, 'Annulé')], default=1, verbose_name='État de la demande'),
        ),
    ]
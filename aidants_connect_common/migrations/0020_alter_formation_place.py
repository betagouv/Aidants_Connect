# Generated by Django 4.2.17 on 2025-03-11 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0019_formation_intra'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formation',
            name='place',
            field=models.CharField(blank=True, default='Distanciel', max_length=500, verbose_name='Lieu'),
        ),
    ]

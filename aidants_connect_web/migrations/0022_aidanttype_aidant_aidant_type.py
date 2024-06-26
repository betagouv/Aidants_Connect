# Generated by Django 4.0.8 on 2023-03-21 15:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0021_organisation_france_services_label_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AidantType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=350, verbose_name='Nom')),
            ],
        ),
        migrations.AddField(
            model_name='aidant',
            name='aidant_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='aidants_connect_web.aidanttype', verbose_name="Type d'aidant"),
        ),
    ]

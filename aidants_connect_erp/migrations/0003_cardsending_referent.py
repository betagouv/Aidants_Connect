# Generated by Django 4.0.8 on 2023-03-23 08:26

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import aidants_connect_erp.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('aidants_connect_erp', '0002_alter_cardsending_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='cardsending',
            name='referent',
            field=models.ForeignKey(blank=True,  null=True, related_name='referent_for_sendings', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cardsending',
            name='code_responsable',
            field=models.CharField(blank=True, max_length=25, null=True, verbose_name='Code premier envoi'),
        ),
        migrations.AddField(
            model_name='cardsending',
            name='kit_quantity',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombres de kits'),
        ),
        migrations.AddField(
            model_name='cardsending',
            name='raison_envoi',
            field=models.TextField(blank=True, null=True, verbose_name="Raison de l'envoi"),
        ),
        migrations.AddField(
            model_name='cardsending',
            name='responsable',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='card_sendings', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='cardsending',
            name='quantity',
            field=models.PositiveIntegerField(default=1, verbose_name='Nombre de cartes'),
        )
    ]
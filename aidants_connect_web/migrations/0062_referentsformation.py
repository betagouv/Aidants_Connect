# Generated by Django 4.2.11 on 2024-04-04 15:51

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0061_alter_coreferentnonaidantrequest_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferentsFormation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150, verbose_name='Prénom')),
                ('last_name', models.CharField(max_length=150, verbose_name='Nom')),
                ('email', models.EmailField(max_length=150, verbose_name='Email professionnel')),
                ('organisation_name', models.TextField(default='No name provided', verbose_name='Nom')),
                ('address', models.TextField(default='No address provided', verbose_name='Adresse')),
                ('zipcode', models.CharField(default='0', max_length=10, verbose_name='Code Postal')),
                ('city', models.CharField(max_length=255, null=True, verbose_name='Ville')),
                ('city_insee_code', models.CharField(blank=True, max_length=5, null=True, verbose_name='Code INSEE de la ville')),
                ('formation_registration_dt', models.DateTimeField(auto_now_add=True, verbose_name='Date et heure de début de la formation')),
                ('formation_presence', models.BooleanField(default=False, verbose_name='Présent à la formation')),
                ('formation_registered', models.BooleanField(default=False, verbose_name='Inscrit à la formation')),
                ('formation_participated', models.BooleanField(default=False, verbose_name='A participé à la formation')),
                ('replay_seen', models.BooleanField(default=False, verbose_name='A vu le replay')),
                ('organisation', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='aidants_connect_web.organisation')),
                ('referent', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
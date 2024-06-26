# Generated by Django 4.2.3 on 2023-07-13 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0033_aidantstatistiques_number_aidants_in_zrr_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aidant',
            name='ff_otp_app',
            field=models.BooleanField(default=False, verbose_name='Le ou la référente peut ajouter une application OTP aux aidants de son organisation'),
        ),
        migrations.AlterField(
            model_name='aidantstatistiques',
            name='number_responsable',
            field=models.PositiveIntegerField(default=0, verbose_name='Nb de référent'),
        ),
        migrations.AlterField(
            model_name='aidantstatistiquesbydepartment',
            name='number_responsable',
            field=models.PositiveIntegerField(default=0, verbose_name='Nb de référent'),
        ),
        migrations.AlterField(
            model_name='aidantstatistiquesbyregion',
            name='number_responsable',
            field=models.PositiveIntegerField(default=0, verbose_name='Nb de référent'),
        ),
        migrations.AlterField(
            model_name='habilitationrequest',
            name='origin',
            field=models.CharField(choices=[('datapass', 'Datapass'), ('responsable', 'Référent Structure'), ('autre', 'Autre'), ('habilitation', 'Formulaire Habilitation')], default='autre', max_length=150, verbose_name='Origine'),
        ),
    ]

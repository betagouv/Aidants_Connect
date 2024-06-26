# Generated by Django 4.2.9 on 2024-02-01 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0049_alter_exportrequest_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidantstatistiques',
            name='number_aidants_with_otp_app',
            field=models.PositiveIntegerField(default=0, verbose_name="Nombre d'aidant possédant une application TOTP"),
        ),
        migrations.AddField(
            model_name='aidantstatistiquesbydepartment',
            name='number_aidants_with_otp_app',
            field=models.PositiveIntegerField(default=0, verbose_name="Nombre d'aidant possédant une application TOTP"),
        ),
        migrations.AddField(
            model_name='aidantstatistiquesbyregion',
            name='number_aidants_with_otp_app',
            field=models.PositiveIntegerField(default=0, verbose_name="Nombre d'aidant possédant une application TOTP"),
        ),
    ]

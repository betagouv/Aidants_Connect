# Generated by Django 3.2.14 on 2022-10-24 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0011_fix_pytz_timezones'),
    ]

    operations = [
        migrations.AddField(
            model_name='habilitationrequest',
            name='date_formation',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date de formation'),
        ),
    ]

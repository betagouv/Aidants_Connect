# Generated by Django 3.2.12 on 2022-03-28 22:05

from django.conf import settings
from django.db import migrations


def populate_datapass_generator(apps, _):
    IdGenerator = apps.get_model("aidants_connect_web", "IdGenerator")
    IdGenerator.objects.get_or_create(code=settings.DATAPASS_CODE_FOR_ID_GENERATOR,
                                      defaults={"last_id": 10000})


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_web', '0084_idgenerator'),
    ]

    operations = [
        migrations.RunPython(populate_datapass_generator),
    ]
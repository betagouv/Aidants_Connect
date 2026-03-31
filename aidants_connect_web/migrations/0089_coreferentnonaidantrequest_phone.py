from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0088_structurechangerequest_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="coreferentnonaidantrequest",
            name="phone",
            field=models.CharField(default="", max_length=20, verbose_name="Téléphone"),
            preserve_default=False,
        ),
    ]

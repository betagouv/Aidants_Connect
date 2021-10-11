from django.db import migrations, models
from django.db.models import deletion


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0072_aidant_multi_orga_admin"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aidant",
            name="organisation",
            field=models.ForeignKey(
                on_delete=deletion.CASCADE,
                related_name="current_aidants",
                to="aidants_connect_web.Organisation",
            ),
        ),
        migrations.AlterField(
            model_name="aidant",
            name="organisations",
            field=models.ManyToManyField(
                related_name="aidants",
                to="aidants_connect_web.Organisation",
                verbose_name="Membre des organisations",
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0092_habilitationrequest_pix_score"),
    ]

    operations = [
        migrations.AddField(
            model_name="aidantstatistiques",
            name="number_active_mandats",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Nombre de mandats actifs en cours"
            ),
        ),
        migrations.AddField(
            model_name="aidantstatistiquesbydepartment",
            name="number_active_mandats",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Nombre de mandats actifs en cours"
            ),
        ),
        migrations.AddField(
            model_name="aidantstatistiquesbyregion",
            name="number_active_mandats",
            field=models.PositiveIntegerField(
                default=0, verbose_name="Nombre de mandats actifs en cours"
            ),
        ),
    ]

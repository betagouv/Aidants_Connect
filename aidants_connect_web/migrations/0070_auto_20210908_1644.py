from django.db import migrations, models, transaction
import django.db.models.deletion


@transaction.atomic
def populate_carers(apps, _):
    objects = apps.get_model("aidants_connect_web", "Aidant").objects.filter(
        organisation__isnull=False
    )

    for obj in objects:
        obj.organisations.add(obj.organisation)


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0069_organisation_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="aidant",
            name="organisations",
            field=models.ManyToManyField(
                blank=True,
                related_name="aidants",
                to="aidants_connect_web.Organisation",
                verbose_name="Organisation active",
            ),
        ),
        migrations.AlterField(
            model_name="aidant",
            name="organisation",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="current_aidants",
                to="aidants_connect_web.organisation",
            ),
        ),
        migrations.RunPython(populate_carers, reverse_code=migrations.RunPython.noop),
    ]

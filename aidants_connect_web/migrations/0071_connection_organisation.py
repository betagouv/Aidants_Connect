from django.conf import settings
from django.db import migrations, models
from django.db.models import deletion, Subquery, OuterRef


def populate_organisation(apps, _):
    Connection = apps.get_model("aidants_connect_web", "Connection")

    Connection.objects.filter(aidant__isnull=False).update(
        organisation=Subquery(
            Connection.objects.filter(pk=OuterRef("pk")).values_list(
                "aidant__organisation"
            )[:1]
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0070_auto_20210908_1644"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aidant",
            name="organisations",
            field=models.ManyToManyField(
                blank=True,
                related_name="aidants",
                to="aidants_connect_web.Organisation",
                verbose_name="Membre des organisations…",
            ),
        ),
        migrations.AddField(
            model_name="connection",
            name="organisation",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=deletion.CASCADE,
                related_name="connections",
                to="aidants_connect_web.organisation",
            ),
        ),
        migrations.AlterField(
            model_name="connection",
            name="aidant",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=deletion.CASCADE,
                related_name="connections",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            populate_organisation, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("aidant__isnull", True), ("organisation__isnull", True)),
                    models.Q(
                        ("aidant__isnull", False), ("organisation__isnull", False)
                    ),
                    _connector="OR",
                ),
                name="aidant_and_organisation_set_together",
            ),
        ),
    ]

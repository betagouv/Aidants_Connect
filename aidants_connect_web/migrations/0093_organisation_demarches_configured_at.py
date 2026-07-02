from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def set_demarches_configured_at_for_customised_organisations(apps, schema_editor):
    Organisation = apps.get_model("aidants_connect_web", "Organisation")
    all_demarches = set(settings.DEMARCHES.keys())
    configured_at = timezone.now()

    for organisation in Organisation.objects.iterator():
        if set(organisation.allowed_demarches) != all_demarches:
            organisation.demarches_configured_at = configured_at
            organisation.save(update_fields=["demarches_configured_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0092_habilitationrequest_pix_score"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="demarches_configured_at",
            field=models.DateTimeField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Thématiques configurées le",
            ),
        ),
        migrations.RunPython(
            set_demarches_configured_at_for_customised_organisations,
            migrations.RunPython.noop,
        ),
    ]

from datetime import timedelta
from os import walk as os_walk
from os.path import dirname, join as path_join

from django.db import migrations, models, transaction
from django.template import loader

import aidants_connect_web
from aidants_connect import settings
from aidants_connect_web.utilities import generate_attestation_hash


@transaction.atomic
def populate_template_path(apps, _):
    # noinspection PyPep8Naming
    Journal = apps.get_model("aidants_connect_web", "Journal")
    # noinspection PyPep8Naming
    Mandat = apps.get_model("aidants_connect_web", "Mandat")

    for mandate in Mandat.objects.filter(template_path=None).all():
        journal = None

        journal_qset = Journal.objects.filter(
            action="create_attestation", mandat=mandate
        )
        if journal_qset.count() == 1:
            journal = journal_qset.first()
        else:
            start = mandate.creation_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=1)

            journal_qset = Journal.objects.filter(
                action="create_attestation",
                usager=mandate.usager,
                aidant__organisation=mandate.organisation,
                creation_date__range=(start, end),
            )

            if journal_qset.count() == 1:
                journal = journal_qset.first()

        # If we don't find a strong association between a journal
        # and a mandate, we give up. That's a choice.
        if journal is None:
            continue

        template_dir = dirname(
            loader.get_template(settings.MANDAT_TEMPLATE_PATH).origin.name
        )

        for _, _, filenames in os_walk(template_dir):
            for filename in filenames:
                file_hash = generate_attestation_hash(
                    journal.aidant,
                    mandate.usager,
                    [it.demarche for it in mandate.autorisations.all()],
                    mandate.expiration_date,
                    journal.creation_date.date().isoformat(),
                    path_join(settings.MANDAT_TEMPLATE_DIR, filename),
                )

                if file_hash == journal.attestation_hash:
                    mandate.template_path = path_join(
                        settings.MANDAT_TEMPLATE_DIR, filename
                    )
                    mandate.save()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("aidants_connect_web", "0050_auto_20210321_2154"),
    ]

    operations = [
        migrations.AddField(
            model_name="mandat",
            name="template_path",
            field=models.TextField(
                default=aidants_connect_web.utilities.mandate_template_path,
                editable=False,
                null=True,
                verbose_name="Template utilisé",
            ),
        ),
        migrations.RunPython(
            populate_template_path, reverse_code=migrations.RunPython.noop
        ),
    ]

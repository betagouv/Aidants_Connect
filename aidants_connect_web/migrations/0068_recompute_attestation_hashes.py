from django.db import migrations, transaction

from aidants_connect_web.constants import JournalActionKeywords
from aidants_connect_web.utilities import generate_attestation_hash


@transaction.atomic
def populate_template_path(apps, _):
    Journal = apps.get_model("aidants_connect_web", "Journal")

    for journal in Journal.objects.filter(
        action=JournalActionKeywords.CREATE_ATTESTATION
    ):
        journal.attestation_hash = generate_attestation_hash(
            organisation=journal.organisation,
            usager=journal.usager,
            demarches=journal.demarche,
            expiration_date=journal,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0067_auto_20210817_1534"),
    ]

    operations = [
        migrations.RunPython(
            populate_template_path, reverse_code=migrations.RunPython.noop
        ),
    ]

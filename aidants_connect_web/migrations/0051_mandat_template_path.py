from django.db import migrations, models

import aidants_connect_web
from aidants_connect_web.utilities import generate_attestation_hash


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
            migrations.RunPython.noop, reverse_code=migrations.RunPython.noop
        ),
    ]

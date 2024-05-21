import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('aidants_connect_web', '0058_alter_formationattendant_unique_together_and_more'),
        ('aidants_connect_habilitation', '0026_alter_manager_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='aidantrequest',
            name='habilitation_request',
            field=models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='aidant_request', to='aidants_connect_web.habilitationrequest'),
        ),
        migrations.RunSQL(
            """
            UPDATE aidants_connect_habilitation_aidantrequest ar
            SET habilitation_request_id = hr.id
            FROM aidants_connect_web_habilitationrequest hr
            WHERE LOWER(ar.email) = LOWER(hr.email)
            """,
            elidable=True
        )
    ]

from django.db import migrations, models
import django.db.models.deletion
import uuid

from aidants_connect_habilitation.models import _new_uuid


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_habilitation", "0003_auto_20220113_1811"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="organisationrequest",
            name="type_other_correctly_set",
        ),
        migrations.RemoveConstraint(
            model_name="organisationrequest",
            name="cgu_checked",
        ),
        migrations.RemoveConstraint(
            model_name="organisationrequest",
            name="dpo_checked",
        ),
        migrations.RemoveConstraint(
            model_name="organisationrequest",
            name="professionals_only_checked",
        ),
        migrations.RemoveConstraint(
            model_name="organisationrequest",
            name="without_elected_checked",
        ),
        migrations.AddField(
            model_name="issuer",
            name="issuer_id",
            field=models.UUIDField(
                default=_new_uuid, verbose_name="Identifiant de demandeur", unique=True
            ),
        ),
        migrations.AddField(
            model_name="organisationrequest",
            name="draft_id",
            field=models.UUIDField(
                default=_new_uuid,
                null=True,
                verbose_name="Identifiant de brouillon",
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="aidantrequest",
            name="email",
            field=models.EmailField(max_length=150, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="aidantrequest",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="aidant_requests",
                to="aidants_connect_habilitation.organisationrequest",
            ),
        ),
        migrations.AlterField(
            model_name="issuer",
            name="profession",
            field=models.CharField(max_length=150, verbose_name="Profession"),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="address",
            field=models.TextField(verbose_name="Adresse"),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="city",
            field=models.CharField(blank=True, max_length=255, verbose_name="Ville"),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="manager_profession",
            field=models.CharField(
                max_length=150, verbose_name="Profession du responsable"
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="name",
            field=models.TextField(verbose_name="Nom de la structure"),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="partner_administration",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Administration partenaire",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="public_service_delegation_attestation",
            field=models.FileField(
                blank=True,
                default="",
                upload_to="",
                verbose_name="Attestation de délégation de service public",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="type_other",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Type de structure si autre",
            ),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="web_site",
            field=models.URLField(blank=True, default="", verbose_name="Site web"),
        ),
        migrations.AlterField(
            model_name="organisationrequest",
            name="zipcode",
            field=models.CharField(max_length=10, verbose_name="Code Postal"),
        ),
        migrations.AlterField(
            model_name="requestmessage",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="aidants_connect_habilitation.organisationrequest",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        models.Q(("type_id", 12), _negated=True),
                        ("type_other__isnull_or_blank", True),
                    ),
                    models.Q(("type_id", 12), ("type_other__isnull_or_blank", False)),
                    _connector="OR",
                ),
                name="type_other_correctly_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(("draft_id__isnull", True), ("cgu", True)),
                    _connector="OR",
                ),
                name="cgu_checked",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(("draft_id__isnull", True), ("dpo", True)),
                    _connector="OR",
                ),
                name="dpo_checked",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(("draft_id__isnull", True), ("professionals_only", True)),
                    _connector="OR",
                ),
                name="professionals_only_checked",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisationrequest",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft_id__isnull", False),
                    models.Q(("draft_id__isnull", True), ("without_elected", True)),
                    _connector="OR",
                ),
                name="without_elected_checked",
            ),
        ),
    ]

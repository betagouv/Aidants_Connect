from django.db import migrations, models
import phonenumber_field.modelfields


def migrate_phone_field_blank_to_null(apps, _):
    Connection = apps.get_model("aidants_connect_web", "Connection")
    Connection.objects.filter(user_phone="").update(user_phone=None)


def migrate_phone_field_null_to_blank(apps, _):
    Connection = apps.get_model("aidants_connect_web", "Connection")
    Connection.objects.filter(user_phone=None).update(user_phone="")


class Migration(migrations.Migration):

    dependencies = [
        ("aidants_connect_web", "0057_auto_20210525_1559"),
    ]

    operations = [
        migrations.AddField(
            model_name="connection",
            name="consent_request_tag",
            field=models.CharField(default=None, max_length=36, null=True),
        ),
        migrations.AddField(
            model_name="connection",
            name="draft",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="journal",
            name="consent_request_tag",
            field=models.CharField(default=None, max_length=36, null=True),
        ),
        migrations.AddField(
            model_name="journal",
            name="user_phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                default=None, max_length=128, null=True, region=None
            ),
        ),
        migrations.AlterField(
            model_name="connection",
            name="user_phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                default=None, max_length=128, null=True, region=None
            ),
        ),
        migrations.AlterField(
            model_name="journal",
            name="action",
            field=models.CharField(
                choices=[
                    ("connect_aidant", "Connexion d'un aidant"),
                    ("activity_check_aidant", "Reprise de connexion d'un aidant"),
                    ("franceconnect_usager", "FranceConnexion d'un usager"),
                    ("update_email_usager", "L'email de l'usager a été modifié"),
                    ("update_phone_usager", "Le téléphone de l'usager a été modifié"),
                    ("create_attestation", "Création d'une attestation"),
                    ("create_autorisation", "Création d'une autorisation"),
                    ("use_autorisation", "Utilisation d'une autorisation"),
                    ("cancel_autorisation", "Révocation d'une autorisation"),
                    ("import_totp_cards", "Importation de cartes TOTP"),
                    (
                        "init_renew_mandat",
                        "Lancement d'une procédure de renouvellement",
                    ),
                    (
                        "consent_request_sent",
                        "Un SMS de demande de consentement a été envoyé",
                    ),
                    (
                        "agreement_of_consent_received",
                        "Un SMS d'accord de consentement a été reçu",
                    ),
                    (
                        "denial_of_consent_received",
                        "Un SMS de refus de consentement a été reçu",
                    ),
                ],
                max_length=30,
            ),
        ),
        migrations.AddConstraint(
            model_name="journal",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("user_phone__isnull", False),
                    ("consent_request_tag__isnull", False),
                ),
                fields=("action", "user_phone", "consent_request_tag"),
                name="journal_unique_consent_request_conversation",
            ),
        ),
        migrations.RunPython(
            migrate_phone_field_blank_to_null,
            reverse_code=migrate_phone_field_null_to_blank,
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("user_phone__isnull", False),
                    ("consent_request_tag__isnull", False),
                ),
                fields=("user_phone", "consent_request_tag"),
                name="connection_unique_consent_request_conversation",
            ),
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("draft", False),
                    models.Q(
                        ("draft", True),
                        ("user_phone__isnull", False),
                        ("consent_request_tag__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="connection_remote_mandate_constraint",
            ),
        ),
    ]

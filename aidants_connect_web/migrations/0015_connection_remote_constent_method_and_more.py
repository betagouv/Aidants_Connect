from django.db import migrations, models

import phonenumber_field.modelfields


def populate_remote_constent_method(apps, _):
    Connection = apps.get_model("aidants_connect_web", "Connection")
    Mandat = apps.get_model("aidants_connect_web", "Mandat")

    Connection.objects.filter(mandat_is_remote=True).update(
        remote_constent_method="LEGACY"
    )
    Mandat.objects.filter(is_remote=True).update(remote_constent_method="LEGACY")


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0014_organisation_is_experiment"),
    ]

    operations = [
        migrations.AddField(
            model_name="connection",
            name="remote_constent_method",
            field=models.CharField(
                blank=True,
                choices=[("LEGACY", "Par signature sur papier"), ("SMS", "Par SMS")],
                max_length=200,
                verbose_name="Méthode de consentement à distance",
            ),
        ),
        migrations.AddField(
            model_name="connection",
            name="consent_request_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.AddField(
            model_name="mandat",
            name="remote_constent_method",
            field=models.CharField(
                blank=True,
                choices=[("LEGACY", "Par signature sur papier"), ("SMS", "Par SMS")],
                max_length=200,
                verbose_name="Méthode de consentement à distance",
            ),
        ),
        migrations.AddField(
            model_name="mandat",
            name="consent_request_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.AddField(
            model_name="journal",
            name="consent_request_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.AddField(
            model_name="journal",
            name="remote_constent_method",
            field=models.CharField(
                blank=True,
                choices=[("LEGACY", "Par signature sur papier"), ("SMS", "Par SMS")],
                max_length=200,
                verbose_name="Méthode de consentement à distance",
            ),
        ),
        migrations.AddField(
            model_name="journal",
            name="user_phone",
            field=phonenumber_field.modelfields.PhoneNumberField(
                blank=True, max_length=128, region=None
            ),
        ),
        migrations.AlterField(
            model_name="journal",
            name="action",
            field=models.CharField(
                choices=[
                    ("connect_aidant", "Connexion d'un aidant"),
                    ("activity_check_aidant", "Reprise de connexion d'un aidant"),
                    ("card_association", "Association d'une carte à d'un aidant"),
                    ("card_validation", "Validation d'une carte associée à un aidant"),
                    ("card_dissociation", "Séparation d'une carte et d'un aidant"),
                    ("franceconnect_usager", "FranceConnexion d'un usager"),
                    ("update_email_usager", "L'email de l'usager a été modifié"),
                    ("update_phone_usager", "Le téléphone de l'usager a été modifié"),
                    ("create_attestation", "Création d'une attestation"),
                    ("create_autorisation", "Création d'une autorisation"),
                    ("use_autorisation", "Utilisation d'une autorisation"),
                    ("cancel_autorisation", "Révocation d'une autorisation"),
                    ("cancel_mandat", "Révocation d'un mandat"),
                    ("import_totp_cards", "Importation de cartes TOTP"),
                    (
                        "init_renew_mandat",
                        "Lancement d'une procédure de renouvellement",
                    ),
                    (
                        "transfer_mandat",
                        "Transférer un mandat à une autre organisation",
                    ),
                    ("switch_organisation", "Changement d'organisation"),
                    (
                        "remote_mandat_consent_received",
                        "Consentement reçu pour un mandat conclu à distance",
                    ),
                    (
                        "remote_mandat_denial_received",
                        "Refus reçu pour un mandat conclu à distance",
                    ),
                    (
                        "remote_mandat_consent_sent",
                        "Demande de consentement pour un mandat conclu à distance envoyé",
                    ),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="mandat",
            name="is_remote",
            field=models.BooleanField(
                default=False, verbose_name="Signé à distance\xa0?"
            ),
        ),
        migrations.RunPython(
            populate_remote_constent_method, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("mandat_is_remote", False),
                    models.Q(
                        ("mandat_is_remote", True),
                        models.Q(("remote_constent_method", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="connection_remote_mandate_method_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="mandat",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("is_remote", False),
                    models.Q(
                        ("is_remote", True),
                        models.Q(("remote_constent_method", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="mandat_remote_mandate_method_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("remote_constent_method", "SMS"), _negated=True),
                    models.Q(
                        ("remote_constent_method", "SMS"),
                        models.Q(("user_phone", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="connection_user_phone_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="connection",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("remote_constent_method__in", {"SMS"}), _negated=True),
                    models.Q(
                        ("remote_constent_method__in", {"SMS"}),
                        models.Q(("consent_request_id", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="connection_consent_request_id_set",
            ),
        ),
        migrations.AddConstraint(
            model_name="mandat",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("remote_constent_method__in", {"SMS"}), _negated=True),
                    models.Q(
                        ("remote_constent_method__in", {"SMS"}),
                        models.Q(("consent_request_id", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="mandat_consent_request_id_set",
            ),
        ),
    ]

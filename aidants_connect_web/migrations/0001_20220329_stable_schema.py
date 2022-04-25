import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import phonenumber_field.modelfields

import aidants_connect_web.models
import aidants_connect_web.utilities


class Migration(migrations.Migration):
    replaces = [
        ("aidants_connect_web", "0001_202101_stable_schema"),
        ("aidants_connect_web", "0044_auto_20201216_1047"),
        ("aidants_connect_web", "0045_journal_mandat"),
        ("aidants_connect_web", "0046_organisation_zipcode"),
        ("aidants_connect_web", "0047_cartetotp"),
        ("aidants_connect_web", "0048_auto_20210318_1536"),
        ("aidants_connect_web", "0049_auto_20210321_2152"),
        ("aidants_connect_web", "0050_auto_20210321_2154"),
        ("aidants_connect_web", "0051_mandat_template_path"),
        ("aidants_connect_web", "0052_add_departements_to_region_table"),
        ("aidants_connect_web", "0053_auto_20210421_1503"),
        ("aidants_connect_web", "0054_usager_phone"),
        ("aidants_connect_web", "0055_auto_20210503_1729"),
        ("aidants_connect_web", "0056_auto_20210518_0952"),
        ("aidants_connect_web", "0057_auto_20210525_1559"),
        ("aidants_connect_web", "0058_aidant_validated_cgu_version"),
        ("aidants_connect_web", "0059_fix_mandate_template_path"),
        ("aidants_connect_web", "0060_auto_20210615_1405"),
        ("aidants_connect_web", "0061_auto_20210706_1439"),
        ("aidants_connect_web", "0062_auto_20210720_1142"),
        ("aidants_connect_web", "0062_auto_20210712_1644"),
        ("aidants_connect_web", "0063_merge_20210802_1355"),
        ("aidants_connect_web", "0063_auto_20210803_1511"),
        ("aidants_connect_web", "0064_merge_20210804_1156"),
        ("aidants_connect_web", "0065_auto_20210806_1455"),
        ("aidants_connect_web", "0066_auto_20210817_1128"),
        ("aidants_connect_web", "0067_auto_20210817_1534"),
        ("aidants_connect_web", "0068_organisation_data_pass_id"),
        ("aidants_connect_web", "0069_organisation_is_active"),
        ("aidants_connect_web", "0070_auto_20210908_1644"),
        ("aidants_connect_web", "0071_connection_organisation"),
        ("aidants_connect_web", "0072_aidant_multi_orga_admin"),
        ("aidants_connect_web", "0073_add_aidant__organisation_non_null_constraint"),
        ("aidants_connect_web", "0074_auto_20211014_0921"),
        ("aidants_connect_web", "0075_auto_20211110_1434"),
        ("aidants_connect_web", "0076_auto_20211110_1437"),
        ("aidants_connect_web", "0077_aidant_phone"),
        ("aidants_connect_web", "0078_auto_20211122_1813"),
        ("aidants_connect_web", "0079_organisation_city"),
        ("aidants_connect_web", "0080_add_corse_departement"),
        ("aidants_connect_web", "0081_auto_20220208_1730"),
        ("aidants_connect_web", "0082_alter_habilitationrequest_options"),
        ("aidants_connect_web", "0083_alter_organisation_data_pass_id"),
        ("aidants_connect_web", "0084_idgenerator"),
        ("aidants_connect_web", "0085_auto_20220329_0005"),
    ]

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organisation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.TextField(default="No name provided", verbose_name="Nom"),
                ),
                ("siret", models.BigIntegerField(default=1, verbose_name="N° SIRET")),
                (
                    "address",
                    models.TextField(
                        default="No address provided", verbose_name="Adresse"
                    ),
                ),
                (
                    "zipcode",
                    models.CharField(
                        default="0", max_length=10, verbose_name="Code Postal"
                    ),
                ),
                (
                    "data_pass_id",
                    models.PositiveIntegerField(
                        null=True, unique=True, verbose_name="Datapass ID"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, editable=False, verbose_name="Est active"
                    ),
                ),
                (
                    "city",
                    models.CharField(max_length=255, null=True, verbose_name="Ville"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Usager",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("given_name", models.CharField(max_length=255, verbose_name="Prénom")),
                ("family_name", models.CharField(max_length=255, verbose_name="Nom")),
                (
                    "preferred_username",
                    models.CharField(blank=True, null=True, max_length=255),
                ),
                (
                    "gender",
                    models.CharField(
                        choices=[("female", "Femme"), ("male", "Homme")],
                        default="female",
                        max_length=6,
                        verbose_name="Genre",
                    ),
                ),
                ("birthdate", models.DateField(verbose_name="Date de naissance")),
                (
                    "birthplace",
                    models.CharField(
                        blank=True,
                        max_length=5,
                        null=True,
                        verbose_name="Lieu de naissance",
                    ),
                ),
                (
                    "birthcountry",
                    models.CharField(
                        default="99100", max_length=5, verbose_name="Pays de naissance"
                    ),
                ),
                ("sub", models.TextField(unique=True)),
                (
                    "email",
                    models.EmailField(
                        default="noemailprovided@aidantconnect.beta.gouv.fr",
                        max_length=254,
                    ),
                ),
                (
                    "creation_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="Date de création",
                    ),
                ),
                (
                    "phone",
                    phonenumber_field.modelfields.PhoneNumberField(
                        blank=True, max_length=128, region=None
                    ),
                ),
            ],
            options={
                "ordering": ["family_name", "given_name"],
            },
        ),
        migrations.CreateModel(
            name="Mandat",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "creation_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="Date de création",
                    ),
                ),
                (
                    "expiration_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="Date d'expiration",
                    ),
                ),
                (
                    "duree_keyword",
                    models.CharField(
                        choices=[
                            ("SHORT", "pour une durée de 1 jour"),
                            ("SEMESTER", "pour une durée de six mois (182) jours"),
                            ("LONG", "pour une durée de 1 an"),
                            (
                                "EUS_03_20",
                                "jusqu’à la fin de l’état d’urgence sanitaire ",
                            ),
                        ],
                        max_length=16,
                        null=True,
                        verbose_name="Durée",
                    ),
                ),
                (
                    "is_remote",
                    models.BooleanField(
                        default=False, verbose_name="Signé à distance ?"
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        default=aidants_connect_web.models.get_staff_organisation_name_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mandats",
                        to="aidants_connect_web.organisation",
                    ),
                ),
                (
                    "usager",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mandats",
                        to="aidants_connect_web.usager",
                    ),
                ),
                (
                    "template_path",
                    models.TextField(
                        default=aidants_connect_web.utilities.mandate_template_path,
                        editable=False,
                        null=True,
                        verbose_name="Template utilisé",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Autorisation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "demarche",
                    models.CharField(
                        choices=[
                            ("papiers", "Papiers - Citoyenneté"),
                            ("famille", "Famille"),
                            ("social", "Social - Santé"),
                            ("travail", "Travail"),
                            ("logement", "Logement"),
                            ("transports", "Transports"),
                            ("argent", "Argent"),
                            ("justice", "Justice"),
                            ("etranger", "Étranger"),
                            ("loisirs", "Loisirs"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "revocation_date",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Date de révocation"
                    ),
                ),
                ("last_renewal_token", models.TextField(default="No token provided")),
                (
                    "mandat",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="autorisations",
                        to="aidants_connect_web.mandat",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="OrganisationType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=350, verbose_name="Nom")),
            ],
        ),
        migrations.AddField(
            model_name="organisation",
            name="type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="aidants_connect_web.organisationtype",
            ),
        ),
        migrations.CreateModel(
            name="DatavizDepartment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "zipcode",
                    models.CharField(
                        max_length=10, unique=True, verbose_name="Code Postal"
                    ),
                ),
                (
                    "dep_name",
                    models.CharField(max_length=50, verbose_name="Nom de département"),
                ),
            ],
            options={
                "verbose_name": "Département",
                "db_table": "dataviz_department",
            },
        ),
        migrations.CreateModel(
            name="DatavizRegion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="Nom de région"
                    ),
                ),
            ],
            options={
                "verbose_name": "Région",
                "db_table": "dataviz_region",
            },
        ),
        migrations.CreateModel(
            name="DatavizDepartmentsToRegion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "department",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="aidants_connect_web.datavizdepartment",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="aidants_connect_web.datavizregion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assocation départments/région",
                "verbose_name_plural": "Assocations départments/région",
                "db_table": "dataviz_departements_to_region",
            },
        ),
        migrations.CreateModel(
            name="Aidant",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=254, verbose_name="email address"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of "
                        "deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                ("profession", models.TextField()),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of "
                        "their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="current_aidants",
                        to="aidants_connect_web.organisation",
                        verbose_name="Organisation courante",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.Permission",
                        verbose_name="user permissions",
                    ),
                ),
                (
                    "can_create_mandats",
                    models.BooleanField(
                        default=True,
                        help_text="Précise si l’utilisateur peut accéder à l’espace aidant pour créer des mandats.",
                        verbose_name="Aidant - Peut créer des mandats",
                    ),
                ),
                (
                    "responsable_de",
                    models.ManyToManyField(
                        blank=True,
                        related_name="responsables",
                        to="aidants_connect_web.Organisation",
                    ),
                ),
                ("validated_cgu_version", models.TextField(null=True)),
                (
                    "organisations",
                    models.ManyToManyField(
                        related_name="aidants",
                        to="aidants_connect_web.Organisation",
                        verbose_name="Membre des organisations",
                    ),
                ),
                ("phone", models.TextField(blank=True, verbose_name="Téléphone")),
            ],
            options={
                "verbose_name": "aidant",
            },
            managers=[
                ("objects", aidants_connect_web.models.AidantManager()),
            ],
        ),
        migrations.CreateModel(
            name="Connection",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("state", models.TextField()),
                ("nonce", models.TextField(default="No Nonce Provided")),
                (
                    "connection_type",
                    models.CharField(
                        choices=[("FS", "FC as FS"), ("FI", "FC as FI")],
                        default="FI",
                        max_length=2,
                    ),
                ),
                (
                    "demarches",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.TextField(default="No démarche"),
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "duree_keyword",
                    models.CharField(
                        choices=[
                            ("SHORT", "pour une durée de 1 jour"),
                            ("SEMESTER", "pour une durée de six mois (182) jours"),
                            ("LONG", "pour une durée de 1 an"),
                            (
                                "EUS_03_20",
                                "jusqu’à la fin de l’état d’urgence sanitaire ",
                            ),
                        ],
                        max_length=16,
                        null=True,
                        verbose_name="Durée",
                    ),
                ),
                ("mandat_is_remote", models.BooleanField(default=False)),
                (
                    "expires_on",
                    models.DateTimeField(
                        default=aidants_connect_web.models.default_connection_expiration_date
                    ),
                ),
                ("access_token", models.TextField(default="No token provided")),
                ("code", models.TextField()),
                ("demarche", models.TextField(default="No demarche provided")),
                ("complete", models.BooleanField(default=False)),
                (
                    "aidant",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "autorisation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections",
                        to="aidants_connect_web.autorisation",
                    ),
                ),
                (
                    "usager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections",
                        to="aidants_connect_web.usager",
                    ),
                ),
                (
                    "user_phone",
                    phonenumber_field.modelfields.PhoneNumberField(
                        blank=True, max_length=128, region=None
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="connections",
                        to="aidants_connect_web.organisation",
                    ),
                ),
            ],
            options={
                "verbose_name": "connexion",
            },
        ),
        migrations.CreateModel(
            name="CarteTOTP",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("serial_number", models.CharField(max_length=100, unique=True)),
                ("seed", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "aidant",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="carte_totp",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "carte TOTP",
                "verbose_name_plural": "cartes TOTP",
            },
        ),
        migrations.CreateModel(
            name="Journal",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("connect_aidant", "Connexion d'un aidant"),
                            (
                                "activity_check_aidant",
                                "Reprise de connexion d'un aidant",
                            ),
                            (
                                "card_association",
                                "Association d'une carte à d'un aidant",
                            ),
                            (
                                "card_validation",
                                "Validation d'une carte associée à un aidant",
                            ),
                            (
                                "card_dissociation",
                                "Séparation d'une carte et d'un aidant",
                            ),
                            ("franceconnect_usager", "FranceConnexion d'un usager"),
                            (
                                "update_email_usager",
                                "L'email de l'usager a été modifié",
                            ),
                            (
                                "update_phone_usager",
                                "Le téléphone de l'usager a été modifié",
                            ),
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
                        ],
                        max_length=30,
                    ),
                ),
                ("creation_date", models.DateTimeField(auto_now_add=True)),
                ("demarche", models.CharField(blank=True, max_length=100, null=True)),
                ("duree", models.IntegerField(blank=True, null=True)),
                ("access_token", models.TextField(blank=True, null=True)),
                ("autorisation", models.IntegerField(blank=True, null=True)),
                (
                    "attestation_hash",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("additional_information", models.TextField(blank=True, null=True)),
                ("is_remote_mandat", models.BooleanField(default=False)),
                (
                    "aidant",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "usager",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_entries",
                        to="aidants_connect_web.usager",
                    ),
                ),
                (
                    "mandat",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_entries",
                        to="aidants_connect_web.mandat",
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_entries",
                        to="aidants_connect_web.organisation",
                    ),
                ),
            ],
            options={
                "verbose_name": "entrée de journal",
                "verbose_name_plural": "entrées de journal",
            },
        ),
        migrations.CreateModel(
            name="HabilitationRequest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=150, verbose_name="Prénom")),
                ("last_name", models.CharField(max_length=150, verbose_name="Nom")),
                ("email", models.EmailField(max_length=150)),
                ("profession", models.CharField(max_length=150)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Nouvelle"),
                            ("processing", "En cours"),
                            ("validated", "Validée"),
                            ("refused", "Refusée"),
                            ("cancelled", "Annulée"),
                        ],
                        default="new",
                        max_length=150,
                        verbose_name="État",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Date de création"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Date de modification"
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="habilitation_requests",
                        to="aidants_connect_web.organisation",
                    ),
                ),
                (
                    "origin",
                    models.CharField(
                        choices=[
                            ("datapass", "Datapass"),
                            ("responsable", "Responsable Structure"),
                            ("autre", "Autre"),
                        ],
                        default="autre",
                        max_length=150,
                        verbose_name="Origine",
                    ),
                ),
            ],
            options={
                "verbose_name": "aidant à former",
                "verbose_name_plural": "aidants à former",
            },
        ),
        migrations.AddConstraint(
            model_name="habilitationrequest",
            constraint=models.UniqueConstraint(
                fields=("email", "organisation"), name="unique_email_per_orga"
            ),
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
        migrations.CreateModel(
            name="IdGenerator",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=100, unique=True)),
                ("last_id", models.PositiveIntegerField()),
            ],
        ),
    ]

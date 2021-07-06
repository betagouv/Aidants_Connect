from datetime import date, timedelta

from django.conf import settings
from django.db.models import TextChoices
from django.utils.timezone import now


class JournalActionKeywords:
    CONNECT_AIDANT = "connect_aidant"
    ACTIVITY_CHECK_AIDANT = "activity_check_aidant"
    CARD_ASSOCIATION = "card_association"
    CARD_VALIDATION = "card_validation"
    CARD_DISSOCIATION = "card_dissociation"
    FRANCECONNECT_USAGER = "franceconnect_usager"
    UPDATE_EMAIL_USAGER = "update_email_usager"
    UPDATE_PHONE_USAGER = "update_phone_usager"
    CREATE_ATTESTATION = "create_attestation"
    CREATE_AUTORISATION = "create_autorisation"
    USE_AUTORISATION = "use_autorisation"
    CANCEL_AUTORISATION = "cancel_autorisation"
    CANCEL_MANDAT = "cancel_mandat"
    IMPORT_TOTP_CARDS = "import_totp_cards"
    INIT_RENEW_MANDAT = "init_renew_mandat"


JOURNAL_ACTIONS = (
    (JournalActionKeywords.CONNECT_AIDANT, "Connexion d'un aidant"),
    (JournalActionKeywords.ACTIVITY_CHECK_AIDANT, "Reprise de connexion d'un aidant"),
    (JournalActionKeywords.CARD_ASSOCIATION, "Association d'une carte à d'un aidant"),
    (
        JournalActionKeywords.CARD_VALIDATION,
        "Validation d'une carte associée à un aidant",
    ),
    (JournalActionKeywords.CARD_DISSOCIATION, "Séparation d'une carte et d'un aidant"),
    (JournalActionKeywords.FRANCECONNECT_USAGER, "FranceConnexion d'un usager"),
    (JournalActionKeywords.UPDATE_EMAIL_USAGER, "L'email de l'usager a été modifié"),
    (
        JournalActionKeywords.UPDATE_PHONE_USAGER,
        "Le téléphone de l'usager a été modifié",
    ),
    (JournalActionKeywords.CREATE_ATTESTATION, "Création d'une attestation"),
    (JournalActionKeywords.CREATE_AUTORISATION, "Création d'une autorisation"),
    (JournalActionKeywords.USE_AUTORISATION, "Utilisation d'une autorisation"),
    (JournalActionKeywords.CANCEL_AUTORISATION, "Révocation d'une autorisation"),
    (JournalActionKeywords.CANCEL_MANDAT, "Révocation d'un mandat"),
    (JournalActionKeywords.IMPORT_TOTP_CARDS, "Importation de cartes TOTP"),
    (
        JournalActionKeywords.INIT_RENEW_MANDAT,
        "Lancement d'une procédure de renouvellement",
    ),
)


class AuthorizationDurations:
    SHORT = "SHORT"
    LONG = "LONG"
    EUS_03_20 = "EUS_03_20"

    @classmethod
    def duration(cls, value: str, fixed_date: date = None):
        fixed_date = fixed_date if fixed_date else now()
        result = {
            cls.SHORT: 1,
            cls.LONG: 365,
            cls.EUS_03_20: max(
                1 + (settings.ETAT_URGENCE_2020_LAST_DAY - fixed_date).days, 0
            ),
        }.get(value, None)

        if result is None:
            raise Exception(f"{value} is not an an authorized mandate duration keyword")

        return result

    @classmethod
    def expiration(cls, value: str, fixed_date: date = None):
        fixed_date = fixed_date if fixed_date else now()
        result = {
            cls.SHORT: fixed_date + timedelta(days=1),
            cls.LONG: fixed_date + timedelta(days=365),
            cls.EUS_03_20: settings.ETAT_URGENCE_2020_LAST_DAY,
        }.get(value, None)

        if result is None:
            raise Exception(f"{value} is not an an authorized mandate duration keyword")

        return result


class AuthorizationDurationChoices(TextChoices):
    SHORT = (
        AuthorizationDurations.SHORT,
        "pour une durée de 1 jour",
    )
    LONG = (
        AuthorizationDurations.LONG,
        "pour une durée de 1 an",
    )
    EUS_03_20 = (
        AuthorizationDurations.EUS_03_20,
        "jusqu’à la fin de l’état d’urgence sanitaire ",
    )

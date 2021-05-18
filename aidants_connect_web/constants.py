class JournalActionKeywords:
    CONNECT_AIDANT = "connect_aidant"
    ACTIVITY_CHECK_AIDANT = "activity_check_aidant"
    FRANCECONNECT_USAGER = "franceconnect_usager"
    UPDATE_EMAIL_USAGER = "update_email_usager"
    UPDATE_PHONE_USAGER = "update_phone_usager"
    CREATE_ATTESTATION = "create_attestation"
    CREATE_AUTORISATION = "create_autorisation"
    USE_AUTORISATION = "use_autorisation"
    CANCEL_AUTORISATION = "cancel_autorisation"
    IMPORT_TOTP_CARDS = "import_totp_cards"
    INIT_RENEW_MANDAT = "init_renew_mandat"
    CONSENT_REQUEST_SENT = "consent_request_sent"
    AGREEMENT_OF_CONSENT_RECEIVED = "agreement_of_consent_received"
    DENIAL_OF_CONSENT_RECEIVED = "denial_of_consent_received"


JOURNAL_ACTIONS = (
    (JournalActionKeywords.CONNECT_AIDANT, "Connexion d'un aidant"),
    (JournalActionKeywords.ACTIVITY_CHECK_AIDANT, "Reprise de connexion d'un aidant"),
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
    (JournalActionKeywords.IMPORT_TOTP_CARDS, "Importation de cartes TOTP"),
    (
        JournalActionKeywords.INIT_RENEW_MANDAT,
        "Lancement d'une procédure de renouvellement",
    ),
    (
        JournalActionKeywords.CONSENT_REQUEST_SENT,
        "Un SMS de demande de consentement a été envoyé",
    ),
    (
        JournalActionKeywords.AGREEMENT_OF_CONSENT_RECEIVED,
        "Un SMS d'accord de consentement a été reçu",
    ),
    (
        JournalActionKeywords.DENIAL_OF_CONSENT_RECEIVED,
        "Un SMS de refus de consentement a été reçu",
    ),
)


class RemotePendingResponses:
    INVALID_CONNECTION = "INVALID_CONNECTION"
    NOT_DRAFT_CONNECTION = "NOT_DRAFT_CONNECTION"
    NO_CONSENT = "NO_CONSENT"
    OK = "OK"

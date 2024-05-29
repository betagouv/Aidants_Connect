import enum
from datetime import date, timedelta
from typing import List, Tuple

from django.conf import settings
from django.db.models import Choices, IntegerChoices, TextChoices
from django.db.models.enums import ChoicesMeta as DjangoChoicesMeta
from django.utils.functional import Promise, classproperty
from django.utils.timezone import now

__all__ = [
    "DictChoices",
    "JournalActionKeywords",
    "JOURNAL_ACTIONS",
    "AuthorizationDurations",
    "AuthorizationDurationChoices",
    "RequestOriginConstants",
    "RequestStatusConstants",
    "MessageStakeholders",
    "FormationAttendantState",
]


class ChoicesMeta(DjangoChoicesMeta):
    def __new__(metacls, classname, bases, classdict, **kwds):
        """This is a 1:1 copy of Django's models.enums.ChoicesMeta
        but allowing dict as enum value and using enum labels rather
        that weird computation on enum names"""
        labels = []
        for key in classdict._member_names:
            value = classdict[key]
            if not (
                isinstance(value, (list, tuple))
                and len(value) > 1
                and isinstance(value[-1], (Promise, str, dict))
            ):
                value = (key, value)
            *value, label = value
            value = tuple(value)

            labels.append(label)
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        cls = super(DjangoChoicesMeta, metacls).__new__(
            metacls, classname, bases, classdict, **kwds
        )
        for member, label in zip(cls.__members__.values(), labels):
            member._label_ = label
            # Unpack enum.value if Enum kept it a tuple during creation
            if isinstance(member._value_, tuple):
                member._value_, *_ = member._value_
        return enum.unique(cls)


class DictChoicesMeta(ChoicesMeta):
    @property
    def model_choices(cls) -> List[Tuple]:
        empty = [(None, "__empty__")] if hasattr(cls, "__empty__") else []
        return empty + [(item.name, item._human_readable_name(item)) for item in cls]


class ChoicesEnum(Choices, metaclass=ChoicesMeta):
    pass


class TextChoicesEnum(str, ChoicesEnum):
    pass


class DictChoices(Choices, metaclass=DictChoicesMeta):
    """Use for Enums that have dictionnaries as values

    Provide a .model_choices property to use in models.Model
    classes fields
    """

    @staticmethod
    def _human_readable_name(enum_item):
        """Implement this to return a human readable string from
        an enum value for the models.Model field"""
        raise NotImplementedError()


class JournalActionKeywordsMeta(type):
    @property
    def activity_tracking_actions(cls):
        return (
            JournalActionKeywords.CREATE_ATTESTATION,
            JournalActionKeywords.USE_AUTORISATION,
            JournalActionKeywords.INIT_RENEW_MANDAT,
        )


class JournalActionKeywords(metaclass=JournalActionKeywordsMeta):
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
    TRANSFER_MANDAT = "transfer_mandat"
    SWITCH_ORGANISATION = "switch_organisation"
    REMOTE_SMS_CONSENT_RECEIVED = "remote_sms_consent_received"
    REMOTE_SMS_DENIAL_RECEIVED = "remote_sms_denial_received"
    REMOTE_SMS_CONSENT_SENT = "remote_sms_consent_sent"
    REMOTE_SMS_RECAP_SENT = "remote_sms_recap_sent"


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
    (
        JournalActionKeywords.TRANSFER_MANDAT,
        "Transférer un mandat à une autre organisation",
    ),
    (JournalActionKeywords.SWITCH_ORGANISATION, "Changement d'organisation"),
    (
        JournalActionKeywords.REMOTE_SMS_CONSENT_RECEIVED,
        "Consentement reçu pour un mandat conclu par SMS",
    ),
    (
        JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
        "Refus reçu pour un mandat conclu par SMS",
    ),
    (
        JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
        "Demande de consentement pour un mandat conclu par SMS envoyé",
    ),
    (
        JournalActionKeywords.REMOTE_SMS_RECAP_SENT,
        "Récapitulatif préalable pour mandat conclu par SMS envoyé",
    ),
)


class AuthorizationDurations:
    SHORT = "SHORT"
    MONTH = "MONTH"
    SEMESTER = "SEMESTER"
    LONG = "LONG"
    EUS_03_20 = "EUS_03_20"

    DAYS = {SHORT: 1, MONTH: 31, SEMESTER: 182, LONG: 365}

    @classmethod
    def duration(cls, value: str, fixed_date: date = None):
        fixed_date = fixed_date if fixed_date else now()

        try:
            result = (
                max(1 + (settings.ETAT_URGENCE_2020_LAST_DAY - fixed_date).days, 0)
                if value == cls.EUS_03_20
                else cls.DAYS[value]
            )
        except ValueError:
            raise Exception(f"{value} is not an an authorized mandate duration keyword")

        return result

    @classmethod
    def expiration(cls, value: str, fixed_date: date = None):
        fixed_date = fixed_date if fixed_date else now()

        try:
            result = (
                settings.ETAT_URGENCE_2020_LAST_DAY
                if value == cls.EUS_03_20
                else fixed_date + timedelta(days=cls.DAYS[value])
            )
        except ValueError:
            raise Exception(f"{value} is not an an authorized mandate duration keyword")

        return result


class AuthorizationDurationChoices(TextChoices):
    SHORT = (
        AuthorizationDurations.SHORT,
        "pour une durée de 1 jour",
    )
    MONTH = (
        AuthorizationDurations.MONTH,
        "pour une durée d'un mois "
        f"({AuthorizationDurations.DAYS[AuthorizationDurations.MONTH]} jours)",
    )
    SEMESTER = (
        AuthorizationDurations.SEMESTER,
        "pour une durée de six mois "
        f"({AuthorizationDurations.DAYS[AuthorizationDurations.SEMESTER]} jours)",
    )
    LONG = (
        AuthorizationDurations.LONG,
        "pour une durée de 1 an",
    )
    EUS_03_20 = (
        AuthorizationDurations.EUS_03_20,
        "jusqu’à la fin de l’état d’urgence sanitaire ",
    )


class RequestOriginConstants(IntegerChoices):
    FRANCE_SERVICE = (1, "France Services/MSAP")
    CCAS = (2, "CCAS")
    CENTRES_SOCIAUX = (3, "Centres sociaux")
    SECRETARIATS_MAIRIE = (4, "Sécrétariats de mairie")
    MAISONS_SOLIDARITE = (5, "Maisons départementales des solidarités")
    MEDIATHEQUE = (6, "Médiathèque")
    GUICHET_AUTRE = (7, "Autre guichet d’accueil de service public de proximité")
    GUICHET_OPERATEUR = (
        8,
        "Guichet d’accueil d’opérateur de service public (CAF, France Travail, etc.)",
    )
    AUTRES_ASSOS = (
        9,
        "Autres associations d’accompagnement des publics ou de médiation numérique",
    )
    SMS = (10, "Structure médico-sociale (CSAPA, CHU, CMS)")
    INDEP = (11, "Indépendant")
    OTHER = (12, "Autre")


class RequestStatusConstants(TextChoicesEnum):
    NEW = "Brouillon"
    AC_VALIDATION_PROCESSING = "En attente de validation par Aidants Connect"
    VALIDATED = "Validée"
    REFUSED = "Refusée"
    CLOSED = "Clôturée"
    CHANGES_REQUIRED = "Modifications demandées"
    CHANGES_PROPOSED = "Modifications proposées par Aidants Connect"

    @classproperty
    def modifiable(cls):
        return cls.NEW, cls.AC_VALIDATION_PROCESSING, cls.VALIDATED


class MessageStakeholders(TextChoicesEnum):
    AC = "Aidants Connect"
    ISSUER = "Demandeur"


class FormationAttendantState(IntegerChoices):
    DEFAULT = (enum.auto(), "Par défaut")
    WAITING = (enum.auto(), "En attente")
    CANCELLED = (enum.auto(), "Annulé")

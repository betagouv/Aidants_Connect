import enum
from datetime import date, timedelta
from typing import List, Tuple

from django.conf import settings
from django.db.models import Choices, IntegerChoices, TextChoices
from django.db.models.enums import ChoicesMeta as DjangoChoicesMeta
from django.utils.functional import Promise, classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.version import PY311

if PY311:
    from enum import property as enum_property
else:
    from types import DynamicClassAttribute as enum_property

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
    ASSOCIATIONS = (13, "Associations")
    COMCOMMUNE = (20, "Communautés de Commune")
    CLINIQUE_PRIVE = (557, "Clinique privée")
    CONSEIL_DEP = (242, "Conseils Départementaux (CD)")
    CHRS = (393, "Centres d’hébergement et de réinsertion sociale (CHRS)")
    CHU = (255, "Centres d’hébergement d’urgence (CHU)")
    CIAS = (91, " Centres intercommunaux d’action sociale (CIAS)")
    EHPAD = (
        247,
        "Établissement d’hébergement pour personnes âgées dépendantes (EHPAD)",
    )
    ESAT = (60, "Établissement ou service d’aide par le travail (ESAT)")
    GIP = (94, "Groupement d’intérêt public (GIP)")
    GUICHET = (8, "Guichet d’accueil d’opérateur de service public")
    EPCI = (32, "Intercommunalité (EPCI)")
    MAISON_EMPLOI = (144, "Maison de l’emploi")
    MAISON_QUARTIER = (238, "Maison de quartier")
    MAISON_JEUNE = (459, "Maison des jeunes et de la culture")
    MS_AGRICOLE = (578, "Mutualité Sociale Agricole")
    MISSION_LOCAL = (35, "Mission Locale")
    MUNICIPALITE = (30, "Municipalités")
    PIMMS = (577, "Point Information Médiation Multi Services (PIMMS)")
    PREF_SOUSPREF = (55, "Préfecture, Sous - Préfecture")
    REGIE_QUARTIER = (29, "Régie de quartier")
    TIERS_LIEU = (202, "Tiers-lieu")
    UDAF = (358, "Union Départementale d’Aide aux Familles (UDAF)")
    FRANCE_SERVICE = (1, "Réseau France Services")
    CCAS = (2, "Centres communaux d’action sociale (CCAS)")
    CENTRES_SOCIAUX = (3, "Centres sociaux")
    MEDIATHEQUE = (6, "Bibliothèque / Médiathèque")
    MAISONS_SOLIDARITE = (5, "Maisons départementales des solidarités")
    OTHER = (12, "Autre")


class RequestStatusConstants(TextChoicesEnum):
    NEW = "Brouillon"
    AC_VALIDATION_PROCESSING = mark_safe(
        "En attente de validation d’éligibilité avant inscription en "
        "formation des aidants"
    )
    VALIDATED = "Éligibilité validée"
    REFUSED = "Éligibilité Refusée"
    CLOSED = "Clôturée"
    CHANGES_REQUIRED = "Demande de modifications par l’équipe Aidants Connect"
    CHANGES_PROPOSED = "Modifications proposées par Aidants Connect"

    @enum_property
    def description(self):
        match self:
            case self.AC_VALIDATION_PROCESSING:
                return mark_safe(
                    "<p>Votre demande d’habilitation est en cours d’instruction "
                    "par nos équipes. Vous serez prochainement notifié de la "
                    "décision de nos équipes concernant votre dossier."
                )
            case self.VALIDATED:
                return mark_safe(
                    "<p>Félicitations, votre demande d’habilitation a été acceptée par "
                    "Aidants Connect !</p>"
                    "<p>Vous pouvez désormais inscrire le référent sur un webinaire "
                    "d’information dédié aux référents et inscrire les aidants en "
                    "formation.</p>"
                )
            case self.CHANGES_REQUIRED:
                return mark_safe(
                    "<p>L'équipe Aidants Connect a étudié votre demande d’habilitation "
                    "et souhaite que vous y apportiez des modifications. N’oubliez pas "
                    "de valider à nouveau votre demande d’habilitation en cliquant sur "
                    "le bouton « Soumettre la demande » pour que l'équipe Aidants "
                    "Connect prenne en compte vos modifications et valide votre "
                    "demande</p>"
                )
            case _:
                return ""

    @classproperty
    def personel_editable(cls):
        """Statuses that allow to edit issuer, and personel (manager and aidants)"""
        return (
            cls.NEW,
            cls.AC_VALIDATION_PROCESSING,
            cls.VALIDATED,
            cls.CHANGES_REQUIRED,
            cls.CHANGES_PROPOSED,
        )

    @classproperty
    def organisation_editable(cls):
        """Statuses that allow to edit organisation"""
        return (
            cls.NEW,
            cls.CHANGES_REQUIRED,
            cls.CHANGES_PROPOSED,
        )

    @classproperty
    def validatable(cls):
        """Statuses that allow to validate an habilitation request"""
        return cls.NEW, cls.CHANGES_REQUIRED, cls.CHANGES_PROPOSED


class MessageStakeholders(TextChoicesEnum):
    AC = "Aidants Connect"
    ISSUER = "Demandeur"


class FormationAttendantState(IntegerChoices):
    DEFAULT = (enum.auto(), "Par défaut")
    WAITING = (enum.auto(), "En attente")
    CANCELLED = (enum.auto(), "Annulé")

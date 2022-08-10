from aidants_connect_common.utils.constants import TextChoicesEnum


class SendingStatusChoices(TextChoicesEnum):
    PREPARING = "En préparation"

    SENDING = "En cours d'envoi"

    RECEIVED = "Colis livré"

    LOST = "Colis perdu"

    RETURNED = "Colis retour"

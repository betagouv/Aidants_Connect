from aidants_connect_common.constants import TextChoicesEnum


class SendingStatusChoices(TextChoicesEnum):
    PREPARING = "En préparation"

    SENDING = "En cours d'envoi"

    RECEIVED = "Colis livré"

    WAITING = "En attente"

    LOST = "Colis perdu"

    RETURNED = "Colis retour"

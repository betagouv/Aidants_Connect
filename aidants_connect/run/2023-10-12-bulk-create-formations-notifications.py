def __2023_10_12_bulk_create_formations_notifications():
    from aidants_connect_web.constants import NotificationType
    from aidants_connect_web.models import Aidant, Notification

    aidants_id = (
        Aidant.objects.filter(is_active=True, responsable_de__isnull=False)
        .distinct()
        .values_list("id", flat=True)
    )

    Notification.objects.bulk_create(
        [
            Notification(
                type=NotificationType.WARNING,
                aidant_id=aidant_id,
                must_ack=True,
                body=(
                    "Aucune formation Aidants Connect n'est disponible pour le moment. "
                    "De nouvelles modalités de formation seront expérimentées d'ici "
                    "fin 2023. Nous reviendrons vers vous si votre demande est "
                    "concernée les premières expérimentations."
                ),
            )
            for aidant_id in aidants_id
        ]
    )

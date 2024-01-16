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
                    "Nous travaillons à la mise en place de nouvelles modalités "
                    "de formation qui vous serons présentées début 2024."
                    "L’équipe Aidants Connect reprendra"
                    "contact avec vous et des webinaires seront proposés prochainement "
                    "pour vous communiquer les nouvelles modalités de formation.  "
                ),
            )
            for aidant_id in aidants_id
        ]
    )

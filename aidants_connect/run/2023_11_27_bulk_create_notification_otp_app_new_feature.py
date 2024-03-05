def __2023_11_27_bulk_create_notification_otp_app_new_feature():
    from django.templatetags.static import static

    from aidants_connect_common.utils import build_url
    from aidants_connect_web.constants import NotificationType
    from aidants_connect_web.models import Aidant, Notification

    pdf_url = build_url(static("guides_aidants_connect/AC_Guide_LierUneCarte.pdf"))
    resource_url = build_url("/ressources/")

    aidants_id = (
        Aidant.objects.filter(is_active=True, responsable_de__isnull=False)
        .distinct()
        .values_list("id", flat=True)
    )

    for aidant_id in aidants_id:
        Notification.objects.create(
            type=NotificationType.NEW_FEATURE,
            aidant_id=aidant_id,
            must_ack=True,
            body=(
                "La fonctionnalité qui permet de se connecter à son espace avec un "
                "téléphone est désormais disponible ! Un tutoriel est disponible sur "
                "votre espace référent (lien à mettre), dans "
                f"[la page ressources]({resource_url}) ou en "
                f"cliquant sur [le lien suivant]({pdf_url})."
            ),
        )

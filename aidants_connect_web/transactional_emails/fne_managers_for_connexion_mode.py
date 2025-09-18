from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from aidants_connect_common.utils import render_email
from aidants_connect_web.constants import CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE
from aidants_connect_web.models import Aidant, LogEmailSending


def get_managers_fne():
    return Aidant.objects.filter(created_by_fne=True, responsable_de__isnull=False)


def need_send_emails_to_manager(manager):
    if manager.has_a_totp_device_confirmed_or_not:
        return False

    last_sending = (
        LogEmailSending.objects.filter(
            code_email=CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE, aidant=manager
        )
        .order_by("-last_sending_date")
        .first()
    )

    if last_sending is None:
        return True

    if last_sending.last_sending_date + timezone.timedelta(days=14) < timezone.now():
        return True

    return False


def send_email_to_one_manager(manager):
    url_video = settings.EMAIL_FNE_MANAGER_COMODE_URLWEBINAR
    url_formulaire = "https://app.livestorm.co/aidants-connect/webinaire-referent"
    url_first_login = settings.EMAIL_FNE_MANAGER_COMODE_URLFLOGIN

    text_message, html_message = render_email(
        "email/fne_managers_for_connexion_modes.mjml",
        mjml_context={
            "url_video": url_video,
            "url_formulaire": url_formulaire,
            "url_first_login": url_first_login,
        },
    )
    send_mail(
        from_email=settings.SUPPORT_EMAIL,
        recipient_list=[manager.email],
        subject="🎉 Bienvenue sur Aidants Connect",
        message=text_message,
        html_message=html_message,
    )


def send_email_fne_managers_for_connexion_mode():
    managers = get_managers_fne()

    for manager in managers:
        if need_send_emails_to_manager(manager):
            send_email_to_one_manager(manager)
            log_email, _ = LogEmailSending.objects.get_or_create(
                code_email=CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE, aidant=manager
            )
            log_email.last_sending_date = timezone.now()
            log_email.save()

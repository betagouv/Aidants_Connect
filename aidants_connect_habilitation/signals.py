from django.core.mail import send_mail
from django.dispatch import receiver
from django.template import loader

from aidants_connect import settings
from aidants_connect_habilitation.models import (
    IssuerEmailConfirmation,
    email_confirmation_sent,
)


@receiver(email_confirmation_sent, sender=IssuerEmailConfirmation)
def send_email_confirmation(confirmation: IssuerEmailConfirmation, **_):
    context = {"confirmation": confirmation}
    text_message = loader.render_to_string("signals/email_confirmation.txt", context)
    html_message = loader.render_to_string("signals/email_confirmation.html", context)

    send_mail(
        from_email=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_FROM,
        recipient_list=[confirmation.issuer.email],
        subject=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_SUBJECT,
        message=text_message,
        html_message=html_message,
    )

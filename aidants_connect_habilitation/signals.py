from typing import Union

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpRequest
from django.urls import reverse

from aidants_connect_common.models import FormationAttendant
from aidants_connect_common.utils import build_url, render_email
from aidants_connect_habilitation.models import (
    AidantRequest,
    IssuerEmailConfirmation,
    Manager,
    OrganisationRequest,
    email_confirmation_sent,
)
from aidants_connect_web.models import HabilitationRequest


@receiver(email_confirmation_sent, sender=IssuerEmailConfirmation)
def send_email_confirmation(
    request: HttpRequest, confirmation: IssuerEmailConfirmation, **_
):
    confirmation_link = reverse(
        "habilitation_issuer_email_confirmation_confirm",
        kwargs={"issuer_id": confirmation.issuer.issuer_id, "key": confirmation.key},
    )
    confirmation_link = request.build_absolute_uri(confirmation_link)

    text_message, html_message = render_email(
        "email/email_confirmation.mjml", {"confirmation_link": confirmation_link}
    )

    send_mail(
        from_email=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_FROM,
        recipient_list=[confirmation.issuer.email],
        subject=settings.EMAIL_CONFIRMATION_EXPIRE_DAYS_EMAIL_SUBJECT,
        message=text_message,
        html_message=html_message,
    )


@receiver(post_save, sender=OrganisationRequest)
def notify_issuer_draft_request_saved(
    instance: OrganisationRequest, created: bool, **_
):
    if not created:
        return

    text_message, html_message = render_email(
        "email/draft_organisation_request_saved.mjml",
        {
            "url": build_url(
                reverse(
                    "habilitation_issuer_page",
                    kwargs={"issuer_id": str(instance.issuer.issuer_id)},
                )
            ),
            "organisation": instance,
        },
    )

    send_mail(
        from_email=settings.EMAIL_ORGANISATION_REQUEST_FROM,
        recipient_list=[instance.issuer.email],
        subject=settings.EMAIL_ORGANISATION_REQUEST_CREATION_SUBJECT,
        message=text_message,
        html_message=html_message,
    )


@receiver(post_save, sender=FormationAttendant)
def formation_aidant(instance: FormationAttendant, created: bool, **_):
    if not created:
        return

    person: Union[AidantRequest, Manager] = instance.attendant

    emails = set()
    if isinstance(person, HabilitationRequest):
        emails |= set(person.organisation.responsables.values_list("email", flat=True))
        try:
            person = person.manger_request or person.aidant_request
            emails.add(person.organisation.issuer.email)

            if person.organisation.manager:
                emails.add(person.organisation.manager.email)
        except AttributeError:
            pass

    if not emails:
        return

    organisation = instance.formation.organisation

    str_contact_emails = ", ".join(organisation.private_contacts)
    text_message, html_message = render_email(
        "email/formation-aidant.mjml",
        {
            "person": person,
            "formation": instance.formation,
            "formation_contacts": str_contact_emails,
        },
    )

    send_mail(
        from_email=settings.SUPPORT_EMAIL,
        recipient_list=[*emails],
        subject=f"La personne {person.get_full_name()} a bien été inscrite à une formation",  # noqa: E501
        message=text_message,
        html_message=html_message,
    )

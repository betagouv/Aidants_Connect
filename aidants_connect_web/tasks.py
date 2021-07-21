import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.template.defaultfilters import pluralize
from django.core.mail import send_mail
from django.template import loader
from django.utils import timezone

from celery import shared_task

from aidants_connect_web.models import Connection
from aidants_connect import settings
from aidants_connect_web.models import Aidant, HabilitationRequest, Mandat, Organisation

from typing import List


logger = logging.getLogger()


@shared_task
def delete_expired_connections():

    logger.info("Deleting expired connections...")

    expired_connections = Connection.objects.expired()
    deleted_connections_count, _ = expired_connections.delete()

    if deleted_connections_count > 0:
        logger.info(
            f"Successfully deleted {deleted_connections_count} "
            f"connection{pluralize(deleted_connections_count)}!"
        )
    else:
        logger.info("No connection to delete.")

    return deleted_connections_count


@shared_task
def notify_soon_expired_mandates():
    mandates_qset = Mandat.find_soon_expired(settings.MANDAT_EXPIRED_SOON)
    organisations: List[Organisation] = list(
        Organisation.objects.filter(
            pk__in=mandates_qset.values("organisation").distinct()
        )
    )

    for organisation in organisations:
        recipient_list = list(organisation.aidants.values_list("email", flat=True))

        org_mandates: List[Mandat] = list(
            mandates_qset.filter(organisation=organisation)
        )

        context = {"mandates": org_mandates}

        text_message = loader.render_to_string(
            "aidants_connect_web/managment/notify_soon_expired_mandates.txt",
            context,
        )
        html_message = loader.render_to_string(
            "aidants_connect_web/managment/notify_soon_expired_mandates.html",
            context,
        )

        send_mail(
            from_email=settings.MANDAT_EXPIRED_SOON_EMAIL_FROM,
            recipient_list=recipient_list,
            subject=settings.MANDAT_EXPIRED_SOON_EMAIL_SUBJECT,
            message=text_message,
            html_message=html_message,
        )


@shared_task
def notify_new_habilitation_requests():
    logger.info("Checking new habilitation requests...")
    recipient_list = list(
        Aidant.objects.filter(is_staff=True, is_active=True).values_list(
            "email", flat=True
        )
    )
    created_from = timezone.now() + timedelta(days=-7)
    habilitation_requests_count = HabilitationRequest.objects.filter(
        created_at__gt=created_from
    ).count()
    organisations = Organisation.objects.filter(
        habilitation_requests__created_at__gte=created_from
    ).annotate(
        num_requests=Count(
            "habilitation_requests",
            filter=Q(habilitation_requests__created_at__gt=created_from),
        )
    )

    context = {
        "organisations": organisations,
        "total_requests": habilitation_requests_count,
        "interval": 7,
    }

    text_message = loader.render_to_string(
        "aidants_connect_web/managment/notify_new_habilitation_requests.txt",
        context,
    )
    html_message = loader.render_to_string(
        "aidants_connect_web/managment/notify_new_habilitation_requests.html",
        context,
    )

    send_mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        subject=(
            f"[Aidants Connect] {habilitation_requests_count} "
            "nouvelles demandes d’habilitation"
        ),
        message=text_message,
        html_message=html_message,
    )


@shared_task()
def notify_no_totp_workers():
    workers_without_totp = Aidant.objects.filter(
        email__isnull_or_blank=True, carte_totp__isnull=True
    ).values_list("email", flat=True)

    text_message = loader.render_to_string(
        "aidants_connect_web/managment/notify_no_totp_workers.txt",
    )

    html_message = loader.render_to_string(
        "aidants_connect_web/managment/notify_no_totp_workers.html",
    )

    send_mail(
        from_email=settings.WORKERS_NO_TOTP_NOTIFY_EMAIL_FROM,
        recipient_list=workers_without_totp,
        subject=settings.WORKERS_NO_TOTP_NOTIFY_EMAIL_SUBJECT,
        message=text_message,
        html_message=html_message,
    )

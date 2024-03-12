import logging

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.db import connection
from django.db.models.signals import post_migrate, post_save
from django.dispatch import Signal, receiver
from django.templatetags.static import static
from django.urls import reverse

from django_otp.plugins.otp_totp.models import TOTPDevice
from ipware import get_client_ip
from ua_parser import user_agent_parser

from aidants_connect_common.constants import (
    JournalActionKeywords,
    RequestOriginConstants,
)
from aidants_connect_common.utils import build_url, render_email
from aidants_connect_web import tasks
from aidants_connect_web.constants import NotificationType
from aidants_connect_web.models import (
    Aidant,
    HabilitationRequest,
    Journal,
    Notification,
)
from aidants_connect_web.models.aidant import UserFingerprint

aidants__organisations_changed = Signal()
otp_challenge_failed = Signal()
card_associated_to_aidant = Signal()
aidant_activated = Signal()


logger = logging.getLogger()


@receiver(post_save, sender=HabilitationRequest)
def create_or_update_aidant_in_sandbox(
    sender, instance: HabilitationRequest, created: bool, **_
):
    if settings.SANDBOX_API_URL:
        tasks.create_or_update_aidant_in_sandbox_task.delay(instance.id)


@receiver(post_save, sender=Notification)
def send_email_on_new_notification(sender, instance: Notification, created: bool, **_):
    if instance.type != NotificationType.NEW_FEATURE or not created:
        return

    text_message, html_message = render_email(
        "email/new_feature.mjml",
        {
            "aidant": instance.aidant,
            "espace_aidant": build_url(
                reverse("espace_responsable_organisation")
                if instance.aidant.is_responsable_structure()
                else reverse("espace_aidant_home")
            ),
        },
    )
    send_mail(
        from_email=settings.EMAIL_AIDANT_NEW_FEATURE_NOTIFICATION_FROM,
        recipient_list=[instance.aidant.email],
        subject=settings.EMAIL_AIDANT_NEW_FEATURE_NOTIFICATION_SUBJECT,
        message=text_message,
        html_message=html_message,
    )


@receiver(aidant_activated)
def notify_referent_aidant_activated(sender, aidant: Aidant, **_):
    for referent in aidant.organisation.responsables.all():
        text_message, html_message = render_email(
            "email/aidant_activated.mjml",
            {
                "referent": referent,
                "aidant": aidant,
                "card_association_guide_url": build_url(
                    static("guides_aidants_connect/AC_Guide_LierUneCarte.pdf")
                ),
                "EMAIL_AIDANT_ACTIVATED_CONTACT_EMAIL": (
                    settings.EMAIL_AIDANT_ACTIVATED_CONTACT_EMAIL
                ),
            },
        )
        send_mail(
            from_email=settings.EMAIL_AIDANT_ACTIVATED_FROM,
            recipient_list=[referent.email],
            subject=settings.EMAIL_AIDANT_ACTIVATED_SUBJECT.format(
                aidant_name=aidant.get_full_name()
            ),
            message=text_message,
            html_message=html_message,
        )


@receiver(card_associated_to_aidant)
def send_user_welcome_email(sender, otp_device: TOTPDevice, **_):
    aidant: Aidant = otp_device.user
    if Journal.objects.find_card_association_logs_for_user(aidant).count() <= 1:
        from aidants_connect_web.tasks import email_welcome_aidant

        email_welcome_aidant(aidant.email, logger=logger)


@receiver(otp_challenge_failed)
def increase_tolerence_on_otp_challenge_failed(sender, user: Aidant, **_):
    totp_device: TOTPDevice = getattr(
        getattr(user, "carte_totp", None), "totp_device", None
    )
    if totp_device and totp_device.throttling_failure_count >= 3:
        totp_device.tolerance = settings.DRIFTED_OTP_CARD_TOLERANCE
        totp_device.save(update_fields={"tolerance"})


@receiver(user_logged_in)
def actions_on_login(sender, user: Aidant, request, **kwargs):
    Journal.log_connection(user)

    user.deactivation_warning_at = None
    user.save(update_fields={"deactivation_warning_at"})

    totp_device: TOTPDevice = getattr(
        getattr(user, "carte_totp", None), "totp_device", None
    )
    if totp_device:
        totp_device.tolerance = totp_device._meta.get_field("tolerance").default
        totp_device.save(update_fields={"tolerance"})


@receiver(user_logged_in)
def lower_totp_tolerance_on_login(sender, user: Aidant, request, **kwargs):
    if not settings.LOWER_TOTP_TOLERANCE_ON_LOGIN:
        return

    for device in TOTPDevice.objects.filter(
        user=user, tolerance__gte=2, confirmed=True
    ):
        device.tolerance = 1
        device.save()


@receiver(aidants__organisations_changed)
def send_mail_aidant__organisations_changed(instance: Aidant, diff: dict, **_):
    text_message, html_message = render_email(
        "email/aidant__organisations_changed.mjml",
        {"aidant": instance, **diff},
    )

    send_mail(
        from_email=settings.AIDANTS__ORGANISATIONS_CHANGED_EMAIL_FROM,
        recipient_list=[instance.email],
        subject=settings.AIDANTS__ORGANISATIONS_CHANGED_EMAIL_SUBJECT,
        message=text_message,
        html_message=html_message,
    )


"""Populate DB with initial data"""


@receiver(post_migrate)
def populate_organisation_type_table(app_config: AppConfig, **_):
    if app_config.name == "aidants_connect_web":
        OrganisationType = app_config.get_model("OrganisationType")
        for org_type in RequestOriginConstants:
            OrganisationType.objects.get_or_create(
                id=org_type.value, defaults={"name": org_type.label}
            )

        # Resets the starting value for AutoField
        # See https://docs.djangoproject.com/en/dev/ref/databases/#manually-specified-autoincrement-pk  # noqa
        regclass = (
            """pg_get_serial_sequence('"aidants_connect_web_organisationtype"', 'id')"""
        )
        bigint = 'coalesce(max("id"), 1)'
        boolean = 'max("id") IS NOT NULL'
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT setval({regclass}, {bigint}, {boolean})
                    FROM "aidants_connect_web_organisationtype";"""
            )


@receiver(post_save, sender=Journal)
def update_activity_tracking_on_new_journal(
    sender, instance: Journal, created: bool, **_
):
    if (
        not created
        or instance.action not in JournalActionKeywords.activity_tracking_actions
    ):
        return

    instance.aidant.activity_tracking_warning_at = None
    instance.aidant.save(update_fields=("activity_tracking_warning_at",))


@receiver(user_logged_in)
def log_user_fingerprint(sender, user: Aidant, request, **kwargs):
    try:
        client_ip, _ = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT")
        parsed_ua = user_agent_parser.Parse(ua)
        UserFingerprint.objects.create(
            user=request.user,
            ip_address=client_ip,
            user_agent=ua,
            parsed_user_agent=parsed_ua,
        )
    except Exception:
        logger.exception("Error while recording user fingerprint")

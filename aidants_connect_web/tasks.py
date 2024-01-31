import csv
from collections import defaultdict
from datetime import timedelta
from itertools import chain
from logging import Logger
from typing import List, Type

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Field, Model, Q
from django.db.models.constants import LOOKUP_SEP
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now

from celery import shared_task
from celery.utils.log import get_task_logger
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from aidants_connect_common.models import Department
from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_common.utils.email import render_email
from aidants_connect_common.utils.urls import build_url
from aidants_connect_web.models import (
    Aidant,
    Connection,
    ExportRequest,
    HabilitationRequest,
    Journal,
    Mandat,
    Notification,
    Organisation,
    Usager,
)
from aidants_connect_web.statistics import (
    compute_all_statistics,
    compute_reboarding_statistics_and_synchro_grist,
)


@shared_task
def delete_expired_connections(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

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
def delete_duplicated_static_tokens(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    logger.info("Deleting static devices for confirmed aidants...")
    obsolete_devices = (
        StaticDevice.objects.filter(user__is_staff=False)
        .filter(user__is_superuser=False)
        .filter(user__totpdevice__confirmed=True)
    )
    deleted_obsolete_devices, _ = obsolete_devices.delete()
    logger.info(f"Deleted {deleted_obsolete_devices} devices.")

    logger.info("Deleting duplicated tokens...")
    duplicated_tokens = (
        StaticToken.objects.values("device", "token")
        .annotate(id_count=Count("id"))
        .filter(id_count__gte=2)
    )

    for token in duplicated_tokens:
        device_id = token["device"]
        token_value = token["token"]
        token_count = token["id_count"]
        tokens_to_delete = StaticToken.objects.filter(device__id=device_id).filter(
            token=token_value
        )[: token_count - 1]
        for token in tokens_to_delete:
            token.delete()


def get_recipient_list_for_organisation(organisation):
    return list(
        organisation.aidants.filter(can_create_mandats=True).values_list(
            "email", flat=True
        )
    )


@shared_task
def notify_soon_expired_mandates():
    mandates_qset = Mandat.find_soon_expired(settings.MANDAT_EXPIRED_SOON)
    organisations: List[Organisation] = list(
        Organisation.objects.filter(
            pk__in=mandates_qset.values("organisation").distinct()
        )
    )

    for organisation in organisations:
        recipient_list = get_recipient_list_for_organisation(organisation)

        org_mandates: List[Mandat] = list(
            mandates_qset.filter(organisation=organisation)
        )

        text_message, html_message = render_email(
            "email/notify_soon_expired_mandates.mjml",
            {"mandates": org_mandates},
        )

        send_mail(
            from_email=settings.MANDAT_EXPIRED_SOON_EMAIL_FROM,
            recipient_list=recipient_list,
            subject=settings.MANDAT_EXPIRED_SOON_EMAIL_SUBJECT,
            message=text_message,
            html_message=html_message,
        )


@shared_task
def notify_new_habilitation_requests(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    logger.info("Checking new habilitation requests...")
    recipient_list = list(
        Aidant.objects.filter(is_staff=True, is_active=True).values_list(
            "email", flat=True
        )
    )
    created_from = timezone.now() + timedelta(days=-7)

    # new aidants à former
    habilitation_requests_count = HabilitationRequest.objects.filter(
        created_at__gt=created_from,
        origin=HabilitationRequest.ORIGIN_RESPONSABLE,
    ).count()
    organisations = Organisation.objects.filter(
        habilitation_requests__created_at__gte=created_from,
        habilitation_requests__origin=HabilitationRequest.ORIGIN_RESPONSABLE,
    ).annotate(
        num_requests=Count(
            "habilitation_requests",
            filter=Q(
                habilitation_requests__created_at__gt=created_from,
                habilitation_requests__origin=HabilitationRequest.ORIGIN_RESPONSABLE,
            ),
        )
    )

    orga_per_region = defaultdict(list)
    for org in organisations:
        departement_query = Department.objects.filter(
            insee_code=org.department_insee_code
        )
        if departement_query.exists():
            dep = departement_query[0]
            orga_per_region[dep.region.name] += [org]
        else:
            orga_per_region["Région non précisé"] += [org]
    orga_per_region.default_factory = None

    # aidants à former test PIX
    new_test_pix_count = HabilitationRequest.objects.filter(
        date_test_pix__gt=created_from
    ).count()

    aidants_with_test_pix = HabilitationRequest.objects.filter(
        date_test_pix__gt=created_from
    )

    if habilitation_requests_count == 0 and new_test_pix_count == 0:
        return

    text_message, html_message = render_email(
        "email/notify_new_habilitation_requests.mjml",
        {
            "organisations": organisations,
            "organisations_per_region": orga_per_region,
            "total_requests": habilitation_requests_count,
            "interval": 7,
            "nb_new_test_pix": new_test_pix_count,
            "aidants_with_test_pix": aidants_with_test_pix,
        },
    )

    send_mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        subject=(
            f"[Aidants Connect] {habilitation_requests_count} "
            "nouveaux aidants à former"
        ),
        message=text_message,
        html_message=html_message,
    )


@shared_task()
def notify_no_totp_workers():
    def none_if_blank(value):
        return (
            None
            if value is None or isinstance(value, str) and len(value.strip()) == 0
            else value
        )

    workers_without_totp = (
        Aidant.objects.filter(email__isnull_or_blank=False, carte_totp__isnull=True)
        .order_by("organisation__responsables__email")
        .values("organisation__responsables__email", "email", "first_name", "last_name")
    )

    workers_without_totp_dict = {}

    for item in workers_without_totp:
        manager_email = item.pop("organisation__responsables__email")

        if manager_email not in workers_without_totp_dict:
            workers_without_totp_dict[manager_email] = {
                "users": [],
                "notify_self": False,
                "espace_responsable_url": (
                    f"{settings.HOST}{reverse('espace_responsable_organisation')}"
                ),
            }

        if item["email"] == manager_email:
            workers_without_totp_dict[manager_email]["notify_self"] = True
        else:
            first_name = none_if_blank(item.pop("first_name", None))
            last_name = none_if_blank(item.pop("last_name", None))

            item["full_name"] = (
                f"{first_name} {last_name}"
                if first_name is not None and last_name is not None
                else None
            )

            workers_without_totp_dict[manager_email]["users"].append(item)

    for manager_email, context in workers_without_totp_dict.items():
        text_message, html_message = render_email(
            "email/notify_no_totp_workers.mjml", context
        )

        send_mail(
            from_email=settings.WORKERS_NO_TOTP_NOTIFY_EMAIL_FROM,
            recipient_list=[manager_email],
            subject=settings.WORKERS_NO_TOTP_NOTIFY_EMAIL_SUBJECT,
            message=text_message,
            html_message=html_message,
        )


@shared_task
def compute_aidants_statistics(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    logger.info("Compute Aidants Stastistics...")
    compute_all_statistics()


@shared_task
def compute_reboarding_statistics_and_synchro_grist_task(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    logger.info("compute_reboarding_statistics_and_synchro_grist ...")
    compute_reboarding_statistics_and_synchro_grist()


@shared_task
def email_welcome_aidant(aidant_email: str, *, logger=None):
    if not settings.FF_WELCOME_AIDANT:
        return

    logger: Logger = logger or get_task_logger(__name__)

    text_message, html_message = render_email(
        "email/aidant_bienvenue.mjml",
        {
            "EMAIL_WELCOME_AIDANT_GUIDE_URL": settings.EMAIL_WELCOME_AIDANT_GUIDE_URL,
            "EMAIL_WELCOME_AIDANT_RESSOURCES_URL": (
                settings.EMAIL_WELCOME_AIDANT_RESSOURCES_URL
            ),
            "EMAIL_WELCOME_AIDANT_FAQ_URL": settings.EMAIL_WELCOME_AIDANT_FAQ_URL,
            "EMAIL_WELCOME_AIDANT_FICHES_TANGIBLES": (
                settings.EMAIL_WELCOME_AIDANT_FICHES_TANGIBLES
            ),
            "EMAIL_WELCOME_AIDANT_CONTACT_URL": (
                settings.EMAIL_WELCOME_AIDANT_CONTACT_URL
            ),
        },
    )

    send_mail(
        from_email=settings.EMAIL_WELCOME_AIDANT_FROM,
        subject=settings.EMAIL_WELCOME_AIDANT_SUBJECT,
        recipient_list=[aidant_email],
        message=text_message,
        html_message=html_message,
    )

    logger.info(f"Welcome email sent to {aidant_email}")


@shared_task
def email_old_aidants(*, logger=None):
    if not settings.FF_DEACTIVATE_OLD_AIDANT:
        return

    logger: Logger = logger or get_task_logger(__name__)

    @shared_task
    def email_one_aidant(a: Aidant):
        text_message, html_message = render_email(
            "email/old_aidant_deactivation_warning.mjml",
            {
                "email_title": "Votre compte va être désactivé, réagissez !",
                "user": a,
                "webinaire_sub_form": settings.WEBINAIRE_SUBFORM_URL,
            },
        )

        send_mail(
            from_email=settings.EMAIL_AIDANT_DEACTIVATION_WARN_FROM,
            subject=settings.EMAIL_AIDANT_DEACTIVATION_WARN_SUBJECT,
            recipient_list=[a.email],
            message=text_message,
            html_message=html_message,
        )

        a.deactivation_warning_at = timezone.now()
        a.save()

        logger.info(
            f"Sent warning notice for aidant {a.get_full_name()} "
            "not connected recently"
        )

    aidants = Aidant.objects.deactivation_warnable().all()

    logger.info(
        f"Sending warning notice for {len(aidants)} aidants not connected recently"
    )

    for aidant in aidants:
        email_one_aidant(aidant)

    logger.info(
        f"Sent warning notice for {len(aidants)} aidants not connected recently"
    )


@shared_task
def deactivate_warned_aidants(*, logger=None):
    if not settings.FF_DEACTIVATE_OLD_AIDANT:
        return

    logger: Logger = logger or get_task_logger(__name__)

    @shared_task
    def email_one_aidant(a: Aidant):
        text_message, html_message = render_email(
            "email/old_aidant_deactivation_notice.mjml",
            {
                "email_title": "Votre compte a été désactivé",
                "user": a,
                "cgu_url": build_url(reverse("cgu")),
            },
        )

        send_mail(
            from_email=settings.EMAIL_AIDANT_DEACTIVATION_NOTICE_FROM,
            subject=settings.EMAIL_AIDANT_DEACTIVATION_NOTICE_SUBJECT,
            recipient_list=[a.email],
            message=text_message,
            html_message=html_message,
        )

    deactivable = Aidant.objects.deactivable()

    for aidant in deactivable:
        aidant.deactivate()
        email_one_aidant(aidant)

    logger.info(f"Deactivated {len(deactivable)} aidants")


@shared_task
def send_email_on_new_notification_task(notification: Notification):
    from aidants_connect_web.signals import send_email_on_new_notification

    send_email_on_new_notification(sender=None, instance=notification, created=True)


@shared_task
def export_for_bizdevs(request_pk: int, create_file=True):
    class Serializer:
        fields_to_serialize = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "profession",
            "can_create_mandats",
            "active_totp_card",
            "has_otp_app",
            "is_active",
            "organisation__name",
            "organisation__data_pass_id",
            "organisation__siret",
            "organisation__address",
            "organisation__zipcode",
            "organisation__city",
            "organisation__department_insee_code",
            "organisation__region",
            "organisation__type__name",
            "organisation__legal_category",
            "organisation__legal_cat_level_one",
            "organisation__legal_cat_level_two",
            "organisation__legal_cat_level_three",
            "organisation__nb_mandat_created",
            "organisation__nb_mandat_remote_created",
            "organisation__nb_usager",
        )

        def __init__(self, a: Aidant):
            self.aidant = a

        @staticmethod
        def __model_fields(model: Type[Model] | None) -> dict[str, Field]:
            result = {}
            if not hasattr(model, "_meta"):
                return result

            for field in model._meta.fields:
                result[field.name] = field
                result[field.attname] = field
            return result

        def organisation__region(self):
            qs = Department.objects.filter(
                insee_code=self.aidant.organisation.department_insee_code
            )
            if not qs.exists():
                return None
            return qs[0].insee_code

        organisation__region.csv_column = "Organisation: Code INSEE de la région"

        def active_totp_card(self):
            return getattr(
                getattr(
                    getattr(self.aidant, "carte_totp", False), "totp_device", False
                ),
                "confirmed",
                False,
            )

        active_totp_card.csv_column = "Carte TOTP active"

        def has_otp_app(self):
            return self.aidant.has_otp_app

        has_otp_app.csv_column = "App OTP"

        def organisation__nb_mandat_created(self):
            return Journal.objects.filter(
                organisation=self.aidant.organisation,
                action=JournalActionKeywords.CREATE_ATTESTATION,
            ).count()

        organisation__nb_mandat_created.csv_column = (
            "Organisation: Nombre de mandats créés"
        )

        def organisation__nb_mandat_remote_created(self):
            return Journal.objects.filter(
                organisation=self.aidant.organisation,
                action=JournalActionKeywords.CREATE_ATTESTATION,
                is_remote_mandat=True,
            ).count()

        organisation__nb_mandat_remote_created.csv_column = (
            "Organisation: Nombre de mandats à distance créés"
        )

        def organisation__nb_usager(self):
            return Usager.objects.active().visible_by(self.aidant).count()

        organisation__nb_usager.csv_column = "Organisation: Nombre d'usagers"

        def values(self) -> list[str]:
            result = []
            model_fields = self.__model_fields(Aidant)

            for requested_field in self.fields_to_serialize:
                if hasattr(self, requested_field):
                    value = getattr(self, requested_field)
                    if callable(value):
                        value = value()
                    result.append(f"{value}")
                elif requested_field in model_fields:
                    result.append(getattr(self.aidant, f"{requested_field}"))
                elif LOOKUP_SEP in requested_field:
                    related_fields = requested_field.split(LOOKUP_SEP)
                    value = self.aidant
                    for related_field in related_fields:
                        value = getattr(value, related_field, None)
                    result.append(f"{value}")
                else:
                    raise AttributeError(
                        f"No field could be found in model {Aidant} of method on class "
                        f"{self.__class__.__name__} with name '{requested_field}' "
                    )

            return result

        @classmethod
        def header(cls) -> list[str]:
            model_fields = cls.__model_fields(Aidant)

            result = []
            for requested_field in cls.fields_to_serialize:
                if hasattr(cls, requested_field):
                    result.append(
                        getattr(
                            getattr(cls, requested_field),
                            "csv_column",
                            requested_field,
                        )
                    )
                elif requested_field in model_fields:
                    result.append(f"{model_fields[requested_field].verbose_name}")
                elif LOOKUP_SEP in requested_field:
                    model = Aidant
                    related_model_fields = model_fields
                    related_fields = requested_field.split(LOOKUP_SEP)
                    final_field = None
                    for related_field in related_fields:
                        """A bit of introspection here to resolve related fields
                        expressed in the form 'organisation__name'"""
                        final_field = related_model_fields.get(related_field, None)
                        if final_field is None:
                            raise AttributeError(
                                f"{related_field} is not a valid field on model {model}"
                            )
                        model = final_field.related_model
                        related_model_fields = cls.__model_fields(model)

                    result.append(
                        f"{final_field.model._meta.verbose_name.capitalize()}: {final_field.verbose_name}"  # noqa: E501
                    )
                else:
                    raise AttributeError(
                        f"No field could be found in model {Aidant} of method on class "
                        f"{cls.__class__.__name__} with name '{requested_field}' "
                    )
            return result

    try:
        request = ExportRequest.objects.get(pk=request_pk)
    except ExportRequest.DoesNotExist:
        return

    if not request.aidant.is_staff:
        raise AssertionError("Only staff member can start an export")

    if create_file:
        request.file_path.touch(mode=0o640, exist_ok=True)

    with open(request.file_path, mode="w") as f:
        try:
            writer = csv.writer(f)
            writer.writerow(Serializer.header())

            qs = Aidant.objects.order_by("organisation__name").prefetch_related(
                "organisation"
            )
            nb_aidants = qs.count()
            paging_iterator = chain(range(0, nb_aidants, 500), [nb_aidants])

            first = next(paging_iterator)
            for second in paging_iterator:
                for aidant in qs[first:second]:
                    writer.writerow(Serializer(aidant).values())
                first = second

            request.state = ExportRequest.ExportRequestState.DONE
            request.save(update_fields={"state"})
        except Exception as e:
            f.write(str(e))
            request.state = ExportRequest.ExportRequestState.ERROR
            request.save(update_fields={"state"})
            raise


@shared_task
def email_activity_tracking_warning(*, logger=None):
    logger: Logger = logger or get_task_logger(__name__)

    aidants = Aidant.objects.without_activity_for_90_days().filter(
        activity_tracking_warning_at=None
    )
    for aidant in aidants.all():
        text_message, html_message = render_email(
            "email/activity_tracking_warning.mjml", {"user": aidant}
        )

        send_mail(
            from_email=settings.EMAIL_ACTIVITY_TRACKING_WARN_FROM,
            subject="Accompagnez vos usagers avec Aidants Connect",
            recipient_list=[aidant.email],
            message=text_message,
            html_message=html_message,
        )

        aidant.activity_tracking_warning_at = now()
        aidant.save(update_fields=("activity_tracking_warning_at",))

    logger.info(f"Emailed activity warning to {aidants.count()} aidants")

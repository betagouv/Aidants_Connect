from json import loads as json_loads
from os.path import dirname
from os.path import join as path_join

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.db import connection
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.template import loader

from django_otp.plugins.otp_totp.models import TOTPDevice

import aidants_connect_web
from aidants_connect.common.constants import RequestOriginConstants
from aidants_connect_web.models import Aidant, Journal, aidants__organisations_changed


@receiver(user_logged_in)
def log_connection_on_login(sender, user: Aidant, request, **kwargs):
    Journal.log_connection(user)


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
    context = {"aidant": instance, **diff}
    text_message = loader.render_to_string(
        "signals/aidant__organisations_changed.txt", context
    )
    html_message = loader.render_to_string(
        "signals/aidant__organisations_changed.html", context
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


@receiver(post_migrate)
def populate_dataviz_tables(app_config: AppConfig, **_):
    if app_config.name == "aidants_connect_web":
        DatavizRegion = app_config.get_model("DatavizRegion")
        DatavizDepartment = app_config.get_model("DatavizDepartment")
        DatavizDepartmentsToRegion = app_config.get_model("DatavizDepartmentsToRegion")

        fixture = path_join(
            dirname(aidants_connect_web.__file__),
            "fixtures",
            "departements_region.json",
        )

        with open(fixture) as f:
            json = json_loads(f.read())
            regions = sorted(set(item["region_name"] for item in json))

            for region in regions:
                DatavizRegion.objects.get_or_create(name=region)

            for item in json:
                department, _ = DatavizDepartment.objects.get_or_create(
                    zipcode=item["zipcode"], defaults={"dep_name": item["dep_name"]}
                )

                region = DatavizRegion.objects.get(name=item["region_name"])

                DatavizDepartmentsToRegion.objects.get_or_create(
                    department=department, region=region
                )


@receiver(post_migrate)
def populate_id_generator_table(app_config: AppConfig, **_):
    if app_config.name == "aidants_connect_web":
        IdGenerator = app_config.get_model("IdGenerator")
        IdGenerator.objects.get_or_create(
            code=settings.DATAPASS_CODE_FOR_ID_GENERATOR, defaults={"last_id": 10000}
        )

from django.conf import settings

from .models import Aidant, AidantStatistiques, Journal


def compute_statistics():
    stafforg = settings.STAFF_ORGANISATION_NAME
    ads = Aidant.objects.exclude(organisation__name=stafforg)
    number_aidants = ads.count()
    number_aidants_is_active = ads.filter(is_active=True).count()
    number_responsable = ads.filter(is_active=True, can_create_mandats=False).count()
    number_aidant_can_create_mandat = ads.filter(
        is_active=True, can_create_mandats=True
    ).count()
    number_aidants_without_totp = ads.filter(
        is_active=True, can_create_mandats=True, carte_totp__isnull=True
    ).count()
    number_aidant_with_login = ads.filter(
        is_active=True, can_create_mandats=True, last_login__isnull=False
    ).count()
    aids_id = set(
        list(
            Journal.objects.filter(action="create_attestation").values_list(
                "aidant_id", flat=True
            )
        )
    )
    number_aidant_who_have_created_mandat = ads.filter(
        is_active=True, can_create_mandats=True, pk__in=aids_id
    ).count()

    stats = AidantStatistiques(
        number_aidants=number_aidants,
        number_aidants_is_active=number_aidants_is_active,
        number_responsable=number_responsable,
        number_aidant_can_create_mandat=number_aidant_can_create_mandat,
        number_aidants_without_totp=number_aidants_without_totp,
        number_aidant_with_login=number_aidant_with_login,
        number_aidant_who_have_created_mandat=number_aidant_who_have_created_mandat,
    )
    stats.save()
    return stats

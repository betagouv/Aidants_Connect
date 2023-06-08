from typing import Union

from django.conf import settings
from django.db.models import Q

from aidants_connect_common.models import Department, Region
from aidants_connect_common.utils.constants import (
    JournalActionKeywords,
    RequestStatusConstants,
)
from aidants_connect_habilitation.models import OrganisationRequest

from .models import (
    Aidant,
    AidantStatistiques,
    AidantStatistiquesbyDepartment,
    AidantStatistiquesbyRegion,
    HabilitationRequest,
    Journal,
    Organisation,
)


def compute_all_statistics():
    global_stat = compute_statistics(AidantStatistiques())
    dep_stats = []
    region_stats = []
    for one_dep in Department.objects.all():
        dep_stats.append(
            compute_statistics(AidantStatistiquesbyDepartment(departement=one_dep))
        )

    for one_region in Region.objects.all():
        region_stats.append(
            compute_statistics(AidantStatistiquesbyRegion(region=one_region))
        )

    return [global_stat] + dep_stats + region_stats


def compute_statistics(
    ostat: Union[
        AidantStatistiques,
        AidantStatistiquesbyDepartment,
        AidantStatistiquesbyRegion,
    ],
) -> Union[
    AidantStatistiques, AidantStatistiquesbyDepartment, AidantStatistiquesbyRegion, None
]:
    stafforg = settings.STAFF_ORGANISATION_NAME
    if isinstance(ostat, AidantStatistiques):
        ads = Aidant.objects.exclude(organisation__name=stafforg)
        orgas = Organisation.objects.exclude(name=stafforg)
        hab_requests = HabilitationRequest.objects.all()
        orga_requests = OrganisationRequest.objects.all()
        journals = Journal.objects.all()
    elif isinstance(ostat, AidantStatistiquesbyDepartment):
        departement_insee_code = ostat.departement.insee_code
        ads = Aidant.objects.exclude(organisation__name=stafforg).filter(
            Q(organisation__department_insee_code=departement_insee_code)
        )
        orgas = Organisation.objects.exclude(name=stafforg).filter(
            Q(department_insee_code=departement_insee_code)
        )
        hab_requests = HabilitationRequest.objects.filter(
            Q(organisation__department_insee_code=departement_insee_code)
        )
        orga_requests = OrganisationRequest.objects.filter(
            Q(organisation__department_insee_code=departement_insee_code)
        )
        journals = Journal.objects.all().filter(
            Q(organisation__department_insee_code=departement_insee_code)
        )
    elif isinstance(ostat, AidantStatistiquesbyRegion):
        dpts_insee_code = list(
            ostat.region.department.all().values_list("insee_code", flat=True)
        )
        ads = Aidant.objects.exclude(organisation__name=stafforg).filter(
            Q(organisation__department_insee_code__in=dpts_insee_code)
        )
        orgas = Organisation.objects.exclude(name=stafforg).filter(
            Q(department_insee_code__in=dpts_insee_code)
        )
        hab_requests = HabilitationRequest.objects.filter(
            Q(organisation__department_insee_code__in=dpts_insee_code)
        )
        orga_requests = OrganisationRequest.objects.filter(
            Q(organisation__department_insee_code__in=dpts_insee_code)
        )
        journals = Journal.objects.all().filter(
            Q(organisation__department_insee_code__in=dpts_insee_code)
        )
    else:
        return None

    number_aidants = ads.count()
    qs_aidants_is_active = ads.filter(is_active=True)
    number_aidants_is_active = qs_aidants_is_active.count()

    qs_responsable = ads.filter(is_active=True, can_create_mandats=False)
    number_responsable = qs_responsable.count()

    qs_aidant_can_create_mandat = ads.filter(is_active=True, can_create_mandats=True)
    number_aidant_can_create_mandat = qs_aidant_can_create_mandat.count()

    qs_aidants_without_totp = ads.filter(
        is_active=True, can_create_mandats=True, carte_totp__isnull=True
    )
    number_aidants_without_totp = qs_aidants_without_totp.count()

    qs_aidant_with_login = ads.filter(
        is_active=True, can_create_mandats=True, last_login__isnull=False
    )
    number_aidant_with_login = qs_aidant_with_login.count()

    aids_id = set(
        list(
            journals.filter(action="create_attestation").values_list(
                "aidant_id", flat=True
            )
        )
    )
    qs_aidant_who_have_created_mandat = ads.filter(
        is_active=True, can_create_mandats=True, pk__in=aids_id
    )
    number_aidant_who_have_created_mandat = qs_aidant_who_have_created_mandat.count()

    qs_operational_aidants = ads.filter(
        is_active=True, can_create_mandats=True, carte_totp__isnull=False
    )
    number_operational_aidants = qs_operational_aidants.count()

    qs_future_aidant = hab_requests.exclude(
        status__in=[
            HabilitationRequest.STATUS_REFUSED,
            HabilitationRequest.STATUS_CANCELLED,
            HabilitationRequest.STATUS_VALIDATED,
        ]
    )
    number_future_aidant = qs_future_aidant.count()

    qs_trained_aidant_since_begining = ads.filter(can_create_mandats=True)
    number_trained_aidant_since_begining = qs_trained_aidant_since_begining.count()

    qs_future_trained_aidant = hab_requests.filter(formation_done=True).exclude(
        status__in=[
            HabilitationRequest.STATUS_VALIDATED,
        ],
    )
    number_future_trained_aidant = qs_future_trained_aidant.count()

    nb_structures = orgas.count()

    qs_orga_requests = orga_requests.exclude(
        status=RequestStatusConstants.VALIDATED.name
    )
    nb_orga_requests = qs_orga_requests.count()

    qs_validated_orga_requests = orga_requests.filter(
        status=RequestStatusConstants.VALIDATED.name
    )
    nb_validated_orga_requests = qs_validated_orga_requests.count()

    number_organisation_requests = nb_structures + nb_orga_requests
    number_validated_organisation_requests = nb_structures + nb_validated_orga_requests

    qs_organisation_with_accredited_aidants = orgas.filter(
        aidants__in=qs_operational_aidants
    )
    number_organisation_with_accredited_aidants = (
        qs_organisation_with_accredited_aidants.count()
    )

    qs_organisation_with_at_least_one_ac_usage = orgas.filter(
        journal_entries__action__in=[
            JournalActionKeywords.FRANCECONNECT_USAGER,
            JournalActionKeywords.CREATE_ATTESTATION,
            JournalActionKeywords.CREATE_AUTORISATION,
            JournalActionKeywords.USE_AUTORISATION,
            JournalActionKeywords.INIT_RENEW_MANDAT,
        ]
    ).distinct()

    number_organisation_with_at_least_one_ac_usage = (
        qs_organisation_with_at_least_one_ac_usage.count()
    )

    qs_usage_of_ac = journals.filter(
        action__in=[JournalActionKeywords.USE_AUTORISATION]
    )
    number_usage_of_ac = qs_usage_of_ac.count()

    ostat.number_aidants = number_aidants
    ostat.number_aidants_is_active = number_aidants_is_active
    ostat.number_responsable = number_responsable
    ostat.number_aidant_can_create_mandat = number_aidant_can_create_mandat
    ostat.number_aidants_without_totp = number_aidants_without_totp
    ostat.number_aidant_with_login = number_aidant_with_login
    ostat.number_aidant_who_have_created_mandat = number_aidant_who_have_created_mandat
    ostat.number_operational_aidants = number_operational_aidants
    ostat.number_future_aidant = number_future_aidant
    ostat.number_trained_aidant_since_begining = number_trained_aidant_since_begining
    ostat.number_future_trained_aidant = number_future_trained_aidant
    ostat.number_organisation_requests = number_organisation_requests
    ostat.number_validated_organisation_requests = (
        number_validated_organisation_requests
    )
    ostat.number_organisation_with_accredited_aidants = (
        number_organisation_with_accredited_aidants
    )
    ostat.number_organisation_with_at_least_one_ac_usage = (
        number_organisation_with_at_least_one_ac_usage
    )
    ostat.number_usage_of_ac = number_usage_of_ac
    ostat.save()

    return ostat

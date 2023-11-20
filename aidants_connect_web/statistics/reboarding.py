from django.conf import settings
from django.db.models import Q
from django.utils.timezone import datetime, timedelta

from grist_api import GristDocAPI

from aidants_connect_common.utils.constants import JournalActionKeywords

from ..models import Aidant, Journal, ReboardingAidantStatistiques


def get_date_from_grist_string(date_string):
    return datetime.strptime(date_string, "['%Y-%m-%d %H:%M']")


def compute_reboarding_statistics_and_synchro_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    table_id = settings.GRIST_REBORDING_TABLE_ID
    api_key = settings.GRIST_API_KEY

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    reboarding_rable = api_grist.fetch_table(table_id)

    for one_row in reboarding_rable:
        if one_row.Date_webinaire is not None:
            if isinstance(one_row.Date_webinaire, int):
                date_reboarding = datetime.fromtimestamp(one_row.Date_webinaire).date()
            else:
                date_reboarding = datetime.strptime(
                    one_row.Date_webinaire, "['%Y-%m-%d %H:%M']"
                )

            email_aidant = (
                one_row.Email_renseigner_celui_utilise_lors_de_l_habilitation_Aidants_Connect_  # noqa
            )
            aidant = Aidant.objects.filter(email=email_aidant).first()
            if aidant:
                (
                    reboarding_stats,
                    created,
                ) = ReboardingAidantStatistiques.objects.get_or_create(
                    aidant=aidant, reboarding_session_date=date_reboarding
                )

                if created:
                    if aidant.deactivation_warning_at:
                        reboarding_stats.warning_date = aidant.deactivation_warning_at
                        aidant.deactivation_warning_at = None
                        aidant.save()
                        reboarding_stats.save()

                reboarding_stats = compute_reboarding_statistics_for_aidant(
                    reboarding_stats
                )
                synchro_grist_data(api_grist, one_row.id, reboarding_stats)


def synchro_grist_data(
    api_grist: GristDocAPI, row_id: int, stats: ReboardingAidantStatistiques
):
    dict_update_grist = {"id": row_id}

    dict_update_grist[
        "Avant_session_nombre_connexions"
    ] = stats.connexions_before_reboarding
    dict_update_grist["J30_nombre_connexions"] = stats.connexions_j30_after
    dict_update_grist["J90_nombre_connexions"] = stats.connexions_j90_after

    dict_update_grist[
        "Avant_session_nombre_de_mandats_crees"
    ] = stats.created_mandats_before_reboarding
    dict_update_grist["J30_nombre_de_mandats_crees"] = stats.created_mandats_j30_after
    dict_update_grist["J90_nombre_de_mandats_crees"] = stats.created_mandats_j90_after

    dict_update_grist[
        "Avant_session_nombre_de_demarches_realisees"
    ] = stats.demarches_before_reboarding
    dict_update_grist["J30_nombre_de_demarches_realisees"] = stats.demarches_j30_after
    dict_update_grist["J90_nombre_de_demarches_realisees"] = stats.demarches_j90_after

    dict_update_grist[
        "Avant_session_nombre_usagers_accompagnes"
    ] = stats.usagers_before_reboarding
    dict_update_grist["J30_nombre_usagers_accompagnes"] = stats.usagers_j30_after
    dict_update_grist["J90_nombre_usagers_accompagnes"] = stats.usagers_j90_after

    api_grist.update_records(
        "Version_finale_webinaire_rattrapage_1_", [dict_update_grist]
    )


def compute_reboarding_statistics_for_aidant(
    stats: ReboardingAidantStatistiques,
) -> ReboardingAidantStatistiques:
    aidant = stats.aidant
    boarding_date = stats.reboarding_session_date
    date_j30 = boarding_date + timedelta(days=30)
    date_j90 = boarding_date + timedelta(days=90)
    q_30 = Q(creation_date__gte=boarding_date) & Q(creation_date__lte=date_j30)
    q_90 = Q(creation_date__gte=boarding_date) & Q(creation_date__lte=date_j90)

    qs_connexion = Journal.objects.filter(
        action=JournalActionKeywords.CONNECT_AIDANT, aidant=aidant
    )
    qs_mandats = Journal.objects.filter(
        action=JournalActionKeywords.CREATE_ATTESTATION, aidant=aidant
    )
    qs_demarches = Journal.objects.filter(
        action=JournalActionKeywords.USE_AUTORISATION, aidant=aidant
    )
    qs_usagers = Journal.objects.filter(
        action=JournalActionKeywords.USE_AUTORISATION, aidant=aidant
    )

    stats.connexions_before_reboarding = qs_connexion.filter(
        creation_date__lte=boarding_date
    ).count()
    stats.connexions_j30_after = qs_connexion.filter(q_30).count()
    stats.connexions_j90_after = qs_connexion.filter(q_90).count()

    stats.created_mandats_before_reboarding = qs_mandats.filter(
        creation_date__lte=boarding_date
    ).count()
    stats.created_mandats_j30_after = qs_mandats.filter(q_30).count()
    stats.created_mandats_j90_after = qs_mandats.filter(q_90).count()

    stats.demarches_before_reboarding = qs_demarches.filter(
        creation_date__lte=boarding_date
    ).count()
    stats.demarches_j30_after = qs_demarches.filter(q_30).count()
    stats.demarches_j90_after = qs_demarches.filter(q_90).count()

    nb_b = (
        qs_usagers.filter(creation_date__lte=boarding_date)
        .values_list("usager_id", flat=True)
        .distinct()
        .count()
    )
    nb_j30 = (
        qs_usagers.filter(q_30).values_list("usager_id", flat=True).distinct().count()
    )
    nb_j90 = (
        qs_usagers.filter(q_90).values_list("usager_id", flat=True).distinct().count()
    )
    stats.usagers_before_reboarding = nb_b
    stats.usagers_j30_after = nb_j30
    stats.usagers_j90_after = nb_j90

    stats.save()
    return stats

from django.conf import settings
from django.utils.timezone import datetime

from grist_api import GristDocAPI

from aidants_connect_common.models import (
    Formation,
    FormationOrganization,
    FormationType,
)


def get_organisme_formations_from_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    orga_f_table_id = settings.GRIST_FORMATION_ORGANIZATION_TABLE_ID
    api_key = settings.GRIST_API_KEY

    api_grist = GristDocAPI(doc_id, api_key, server=server)

    orga_formation_table = api_grist.fetch_table(orga_f_table_id)
    for form_orga in orga_formation_table:
        FormationOrganization.objects.get_or_create(
            id=form_orga.id, name=form_orga.Organismes_de_formation
        )


def get_formations_from_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    table_id = settings.GRIST_FORMATION_REPORTING_TABLE_ID
    api_key = settings.GRIST_API_KEY
    GRIST_ID_MEDNUM = settings.GRIST_ID_MEDNUM
    GRIST_ID_FAMILLE_RURALES = settings.GRIST_ID_FAMILLE_RURALES
    GRIST_ID_PIMMS = settings.GRIST_ID_PIMMMS

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    formation_table = api_grist.fetch_table(table_id)
    mednum, _ = FormationType.objects.get_or_create(label="Mednum")
    frurales, _ = FormationType.objects.get_or_create(label="Familles Rurales")
    pimms, _ = FormationType.objects.get_or_create(label="PIMMS")

    for one_row in formation_table:
        if one_row.Statut != "Programmée":
            continue
        if one_row.Reseau not in [
            GRIST_ID_MEDNUM,
            GRIST_ID_FAMILLE_RURALES,
            GRIST_ID_PIMMS,
        ]:
            continue
        if one_row.Session_a_publier != "Oui":
            continue
        grist_id = one_row.ID_Unique_de_la_Session
        try:
            Formation.objects.get(id_grist=grist_id)
            continue
        except Formation.DoesNotExist:
            formation = Formation(id_grist=grist_id, publish_or_not=True)

        formation.description = one_row.Date_et_horaires
        formation.place = one_row.Lieu if one_row.Lieu else ""

        formation.organisation_id = one_row.Organisme_de_formation
        formation.description = one_row.Date_et_horaires
        formation.place = one_row.Lieu if one_row.Lieu else ""
        if one_row.Reseau == GRIST_ID_MEDNUM:
            formation.type = mednum
        if one_row.Reseau == GRIST_ID_FAMILLE_RURALES:
            formation.type = frurales
        if one_row.Reseau == GRIST_ID_PIMMS:
            formation.type = pimms

        if one_row.Session_intra:
            formation.intra = True

        formation.max_attendants = settings.FORMATION_MAX_ATTENDANTS

        try:
            duration = int(one_row.Duree_de_la_formation.replace(" heures", ""))
            formation.duration = duration
        except Exception:
            formation.duration = 0

        if one_row.Presentiel_ou_a_distance == "Distanciel":
            formation.status = Formation.Status.REMOTE.value
        else:
            formation.status = Formation.Status.PRESENTIAL.value

        if isinstance(one_row.Date_de_debut, int):
            start_datetime = datetime.fromtimestamp(one_row.Date_de_debut)
        else:
            start_datetime = datetime.strptime(one_row.Date_de_debut, "%d-%m-%Y")

        formation.start_datetime = start_datetime

        if one_row.Date_de_fin:
            if isinstance(one_row.Date_de_fin, int):
                end_datetime = datetime.fromtimestamp(one_row.Date_de_fin)
            else:
                end_datetime = datetime.strptime(one_row.Date_de_fin, "%d-%m-%Y")
            formation.end_datetime = end_datetime

        formation.save()

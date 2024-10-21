from django.conf import settings

from grist_api import GristDocAPI

from aidants_connect_common.models import Department, FormationAttendant


def push_attendees_in_grist(pk_attent=None):
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    table_id = settings.GRIST_ATTENDEES_TABLE_ID
    api_key = settings.GRIST_API_KEY
    formations_table_id = settings.GRIST_FORMATION_REPORTING_TABLE_ID
    orga_f_table_id = settings.GRIST_FORMATION_ORGANIZATION_TABLE_ID
    GRIST_ID_MEDNUM = settings.GRIST_ID_MEDNUM
    GRIST_ID_FAMILLE_RURALES = settings.GRIST_ID_FAMILLE_RURALES

    api_grist = GristDocAPI(doc_id, api_key, server=server)

    dict_formations = dict()
    dict_orga_form = dict()

    formation_table = api_grist.fetch_table(formations_table_id)
    for one_row in formation_table:
        if one_row.Statut != "Programmée" and one_row.Statut != "Annulée":
            continue
        if one_row.Reseau not in [GRIST_ID_FAMILLE_RURALES, GRIST_ID_MEDNUM]:
            continue
        grist_id = one_row.ID_Unique_de_la_Session
        dict_formations[grist_id] = one_row

    orga_formation_table = api_grist.fetch_table(orga_f_table_id)
    for form_orga in orga_formation_table:
        dict_orga_form[form_orga.id] = form_orga

    attendees = FormationAttendant.objects.filter(id_grist="")
    if pk_attent is not None:
        attendees = attendees.filter(pk__gt=pk_attent)
    for attendee in attendees:
        formation = attendee.formation
        orga = attendee.attendant.organisation
        referent = orga.responsables.all().first()
        dept = Department.objects.filter(insee_code=orga.department_insee_code).first()
        dict_grist = {
            "IdTechniqueInscription": attendee.pk,
            "Session_de_pre_inscription": formation.id_grist,
            "Date_de_l_inscription": attendee.updated_at.strftime("%d/%m/%Y"),
            "Siret_de_la_structure": orga.siret,
            "Nom_de_la_structure": orga.name,
            "Nom_referent": referent.last_name if referent else "",
            "Prenom_referent": referent.first_name if referent else "",
            "Mail_referent": referent.email if referent else "",
            "Telephone_referent_Aidants_Connect": referent.phone if referent else "",
            "Nom_aidant": attendee.attendant.last_name,
            "Prenom_aidant": attendee.attendant.first_name,
            "Email_aidant": attendee.attendant.email,
            "Adresse_postale_de_la_structure": orga.address,
            "Code_postal": orga.zipcode,
            "Ville": orga.city,
            "Departement": dept.name if dept else "",
            "Region": orga.region.name if orga.region else "",
            "Aidant_Conseiller_Numerique_": (
                "OUI" if attendee.attendant.conseiller_numerique else "NON"
            ),
        }
        result = api_grist.add_records(table_id, [dict_grist])
        attendee.id_grist = str(result[0])
        attendee.save()

from django.conf import settings

from grist_api import GristDocAPI

from aidants_connect_common.models import Department
from aidants_connect_common.utils import generate_new_datapass_id
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation


def get_hr_queryset_for_push_in_grist():
    qs_hr = (
        HabilitationRequest.objects.filter(
            status="processing",
            formations__isnull=True,
            test_pix_passed=False,
            date_test_pix__isnull=True,
            organisation__legal_category__startswith="7",
            conseiller_numerique=False,
            id_grist_fne="",
        )
        .exclude(profession__iexact="conseillère numérique")
        .exclude(profession__iexact="Conseiller numérique")
        .order_by("-created_at")
    )
    return qs_hr


def push_hrequests_in_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID_FNE
    table_id = settings.GRIST_HR_FNE_TABLE_ID
    api_key = settings.GRIST_API_KEY
    dep_table_id = settings.GRIST_DEPARTMENT_TABLE_ID

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    dict_dept = dict()
    dep_table = api_grist.fetch_table(dep_table_id)
    for one_line_dep in dep_table:
        dict_dept[one_line_dep.Nom_du_departement] = one_line_dep.id

    qs_hr = get_hr_queryset_for_push_in_grist()

    for one_hr in qs_hr:
        if one_hr.id_grist_fne:
            continue
        orga = one_hr.organisation
        dept_name = ""
        try:
            dept_name = Department.objects.get(
                insee_code=orga.department_insee_code
            ).name
        except Exception as e:
            print("Exception occured dept_name: ", e)
        try:
            aidant_request = one_hr.aidant_request
        except Exception as e:
            print(e)
            aidant_request = None
        email_issuer = "Sans demandeur"
        if aidant_request and aidant_request.organisation:
            email_issuer = aidant_request.organisation.issuer.email
        referent = orga.responsables.all().first()
        fne_dept = dict_dept[dept_name] if dept_name in dict_dept else "NC"
        dict_grist = {
            "Date_de_la_demande": one_hr.created_at.strftime("%d/%m/%Y"),
            "Nom_de_la_structure": orga.name,
            "Type_de_structure": str(orga.type),
            "Adresse": orga.address,
            "Code_postal": orga.zipcode,
            "Ville": orga.city,
            "Departement": fne_dept,
            "E_mail_de_contact": email_issuer,
            "Numero_Siret": orga.siret,
            "Numero_d_habilitation_Aidants_Connect": orga.data_pass_id,
            "Nom_du_professionnel": one_hr.last_name,
            "Prenom_du_professionnel": one_hr.first_name,
            "Eligibilite_validee": True,
            "Adresse_e_mail": one_hr.email,
            "Profession": one_hr.profession,
            "Nom_du_referent_Aidants_Connect": referent.last_name if referent else "NC",
            "Prenom_du_referent_Aidants_Connect": (
                referent.first_name if referent else "NC"
            ),
            "E_mail_du_referent_Aidants_Connect": referent.email if referent else "",
            "Numero_de_telephone_du_referent_Aidants_Connect": (
                referent.phone if referent else ""
            ),
            "Profession_du_referent_Aidants_Connect": (
                referent.profession if referent else ""
            ),
            "ID_Django_aidant": one_hr.id,
            "Choix_de_la_formation": "Aidants Connect",
        }
        result = api_grist.add_records(table_id, [dict_grist])
        one_hr.id_grist_fne = str(result[0])
        one_hr.save()


def pull_hrequests_from_grist_fne():

    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID_FNE
    table_id = settings.GRIST_HR_FNE_TABLE_ID
    api_key = settings.GRIST_API_KEY

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    fne_hr_table = api_grist.fetch_table(table_id)
    for one_row in fne_hr_table:
        if (
            one_row.Validation_du_financement
            and one_row.Eligibilite_validee
            and one_row.Choix_de_la_formation == "Aidants Connect"
        ):
            grist_siret = int(one_row.Numero_Siret.replace(" ", ""))
            orga_name = one_row.Nom_de_la_structure.strip()

            orga = None
            if one_row.Numero_d_habilitation_Aidants_Connect.strip():
                orga = Organisation.objects.filter(
                    data_pass_id=one_row.Numero_d_habilitation_Aidants_Connect.strip()
                ).first()

            if orga is None:
                orga = Organisation.objects.filter(
                    siret=grist_siret, name__iexact=orga_name
                ).first()

            if orga is not None:
                hr, created = HabilitationRequest.objects.get_or_create(
                    email=one_row.Adresse_e_mail,
                    organisation=orga,
                    defaults={
                        "first_name": one_row.Prenom_du_professionnel,
                        "last_name": one_row.Nom_du_professionnel,
                        "profession": one_row.Profession,
                        "status": ReferentRequestStatuses.STATUS_PROCESSING,
                        "created_by_fne": True,
                        "id_fne": str(one_row.id),
                    },
                )
                if one_row.A_participe_a_la_session:
                    hr.formation_done = True
                    hr.save()
                if hr.id_fne != str(one_row.id):
                    hr.id_fne = str(one_row.id)
                    hr.save()
            else:
                zipcode = one_row.Code_postal
                data_pass_id = int(f"{zipcode[:3]}{generate_new_datapass_id()}")
                orga = Organisation(
                    data_pass_id=data_pass_id,
                    name=orga_name,
                    siret=grist_siret,
                    address=one_row.Adresse,
                    city=one_row.Ville,
                    zipcode=zipcode,
                    created_by_fne=True,
                    id_fne=str(one_row.id),
                )
                orga.save()
                if (
                    one_row.Nom_du_referent_Aidants_Connect
                    == one_row.Nom_du_professionnel
                ):
                    referent_aidant, created_by_fne = Aidant.objects.get_or_create(
                        username=one_row.Adresse_e_mail.lower(),
                        email=one_row.Adresse_e_mail.lower(),
                        defaults={
                            "organisation": orga,
                            "first_name": one_row.Prenom_du_professionnel,
                            "last_name": one_row.Nom_du_professionnel,
                            "profession": one_row.Profession,
                            "created_by_fne": True,
                            "id_fne": str(one_row.id),
                        },
                    )
                    if referent_aidant.id_fne != str(one_row.id):
                        referent_aidant.id_fne = str(one_row.id)
                        referent_aidant.save()
                    if not referent_aidant.phone:
                        referent_aidant.phone = (
                            one_row.Numero_de_telephone_mobile_du_referent_Aidants_Connect  # noqa
                        )
                        referent_aidant.save()
                    referent_aidant.save()
                    referent_aidant.organisation = orga
                    referent_aidant.organisations.add(orga)
                    referent_aidant.responsable_de.add(orga)
                else:
                    referent, created_by_fne = Aidant.objects.get_or_create(
                        username=one_row.E_mail_du_referent_Aidants_Connect.lower(),
                        email=one_row.E_mail_du_referent_Aidants_Connect.lower(),
                        defaults={
                            "organisation": orga,
                            "first_name": one_row.Prenom_du_referent_Aidants_Connect,
                            "last_name": one_row.Nom_du_referent_Aidants_Connect,
                            "profession": one_row.Profession_du_referent_Aidants_Connect,  # noqa
                            "created_by_fne": True,
                            "id_fne": str(one_row.id),
                        },
                    )
                    if referent.id_fne != str(one_row.id):
                        referent.id_fne = str(one_row.id)
                        referent.save()
                    if not referent.phone:
                        referent.phone = (
                            one_row.Numero_de_telephone_mobile_du_referent_Aidants_Connect  # noqa
                        )
                        referent.save()
                    referent.organisation = orga
                    referent.organisations.add(orga)
                    referent.responsable_de.add(orga)

                hr, created = HabilitationRequest.objects.get_or_create(
                    email=one_row.Adresse_e_mail.lower(),
                    organisation=orga,
                    defaults={
                        "first_name": one_row.Prenom_du_professionnel,
                        "last_name": one_row.Nom_du_professionnel,
                        "profession": one_row.Profession,
                        "status": ReferentRequestStatuses.STATUS_PROCESSING,
                        "created_by_fne": True,
                        "id_fne": str(one_row.id),
                    },
                )
                if not created:
                    hr.organisation = orga
                if one_row.A_participe_a_la_session:
                    hr.formation_done = True
                hr.id_fne = str(one_row.id)
                hr.save()

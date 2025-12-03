from django.conf import settings
from django.utils.timezone import datetime

from grist_api import GristDocAPI

from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import Aidant, HabilitationRequest, Organisation

from .constants import SendingStatusChoices
from .models import CardSending


def get_card_sending_from_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    sendings_table_id = settings.GRIST_SENDING_TABLE_ID
    users_table_id = settings.GRIST_USERS_TABLE_ID
    api_key = settings.GRIST_API_KEY

    dict_users = {}

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    users_table = api_grist.fetch_table(users_table_id)

    for one_user in users_table:
        dict_users[one_user.id] = Aidant.objects.filter(email=one_user.Email).first()

    sendings_table = api_grist.fetch_table(sendings_table_id)

    for one_sending in sendings_table:

        try:
            orga = Organisation.objects.filter(
                data_pass_id=int(one_sending.Datapass_ID)
            ).first()
            if orga is None:
                print("On ne trouve pas l'orga", one_sending.Datapass_ID)
                continue
        except Exception as e:
            print("datapasse Id", e, one_sending.Datapass_ID)
            continue

        db_sending = CardSending.objects.filter(id_grist=one_sending.id).first()
        if db_sending is None:
            db_sending = CardSending(id_grist=one_sending.id)
            db_sending.organisation = orga
            referent = orga.responsables.filter(
                email=one_sending.Email_Responsable
            ).first()
            if referent is None:
                print("on ne trouve pas le réferent")
                db_sending.name_referent = one_sending.Nom_du_contact
                db_sending.phone_referent = one_sending.Email_Responsable
                db_sending.email_referent = one_sending.Numero_de_telephone
            else:
                db_sending.referent = referent
            db_sending.code_referent = one_sending.Code_de_1ere_connexion[:22]
            if one_sending.Referent in dict_users:
                db_sending.bizdev == dict_users[one_sending.Referent]

        db_sending.quantity = int(one_sending.Qte_cartes)
        db_sending.raison_envoi = one_sending.Cause_de_l_envoi
        if one_sending.Date_d_envoi:
            db_sending.status = SendingStatusChoices.SENDING
            if isinstance(one_sending.Date_d_envoi, int):
                db_sending.sending_date = datetime.fromtimestamp(
                    one_sending.Date_d_envoi
                )
            else:
                try:
                    db_sending.sending_date = datetime.strptime(
                        one_sending.Date_d_envoi, "%d-%m-%Y"
                    )
                except ValueError:
                    pass
        else:
            db_sending.status = SendingStatusChoices.PREPARING

        db_sending.save()


def get_connexion_model_from_grist():
    server = settings.GRIST_URL_SERVER
    doc_id = settings.GRIST_DOCUMENT_ID
    connexion_mode_table_id = settings.GRIST_CONNEXION_MODE_ID
    api_key = settings.GRIST_API_KEY

    GRIST_LABEL_CARD = "Carte physique"
    GRIST_LABEL_PHONE = "Application mobile"

    api_grist = GristDocAPI(doc_id, api_key, server=server)
    connexion_mode_table = api_grist.fetch_table(connexion_mode_table_id)
    status_list = [
        ReferentRequestStatuses.STATUS_PROCESSING,
        ReferentRequestStatuses.STATUS_VALIDATED,
        ReferentRequestStatuses.STATUS_PROCESSING_P2P,
    ]
    for one_row in connexion_mode_table:
        habrequest = HabilitationRequest.objects.filter(
            email=one_row.E_mail_aidant, status__in=status_list
        ).first()
        if habrequest:
            if one_row.Moyen_de_connexion == GRIST_LABEL_CARD:
                habrequest.connexion_mode = HabilitationRequest.CONNEXION_MODE_CARD

            if one_row.Moyen_de_connexion == GRIST_LABEL_PHONE:
                habrequest.connexion_mode = HabilitationRequest.CONNEXION_MODE_PHONE
            habrequest.save()

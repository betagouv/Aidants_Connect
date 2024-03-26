import logging
from datetime import datetime, timedelta
from textwrap import dedent
from unittest import mock
from unittest.mock import MagicMock
from uuid import uuid4

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.timezone import now

import pytz
from celery.result import AsyncResult
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from aidants_connect_common.constants import AuthorizationDurations
from aidants_connect_habilitation.tasks import update_pix_and_create_aidant
from aidants_connect_web.constants import ReferentRequestStatuses
from aidants_connect_web.models import (
    Aidant,
    CarteTOTP,
    ExportRequest,
    HabilitationRequest,
    Journal,
    Mandat,
)
from aidants_connect_web.tasks import (
    email_old_aidants,
    export_for_bizdevs,
    get_recipient_list_for_organisation,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
    MandatFactory,
    OrganisationFactory,
)


class UtilsTaskTests(TestCase):
    def test_get_recipient_list_for_organisation(self):
        orga = OrganisationFactory()
        AidantFactory(organisation=orga, can_create_mandats=True)
        AidantFactory(organisation=orga, can_create_mandats=False)
        AidantFactory(organisation=orga, can_create_mandats=True, is_active=False)
        self.assertEqual(2, Aidant.objects.filter(can_create_mandats=True).count())
        self.assertEqual(1, len(get_recipient_list_for_organisation(orga)))


class ImportPixTests(TestCase):
    def test_import_pix_results_and_create_new_aidant(self):
        aidant_a_former = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
        )
        self.assertEqual(aidant_a_former.test_pix_passed, False)
        self.assertEqual(aidant_a_former.date_test_pix, None)
        self.assertEqual(
            aidant_a_former.status,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertTrue(aidant_a_former.test_pix_passed)
        self.assertEqual(
            aidant_a_former.status, ReferentRequestStatuses.STATUS_VALIDATED.value
        )

        self.assertEqual(1, Aidant.objects.filter(email=aidant_a_former.email).count())

    def test_import_pix_results_and_do_not_create_new_aidant(self):
        aidant_a_former = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr"
        )
        self.assertEqual(aidant_a_former.formation_done, False)
        self.assertEqual(aidant_a_former.date_formation, None)
        self.assertEqual(aidant_a_former.test_pix_passed, False)
        self.assertEqual(aidant_a_former.date_test_pix, None)
        self.assertEqual(
            aidant_a_former.status,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertTrue(aidant_a_former.test_pix_passed)
        self.assertEqual(
            aidant_a_former.status,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )

        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

    def test_import_pix_results_aidant_has_two_orgas(self):
        organisation_1 = OrganisationFactory(name="MAIRIE", siret="121212122")
        aidant_a_former_1 = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=organisation_1,
        )
        organisation_2 = OrganisationFactory(name="MAIRIE2", siret="121212123")
        aidant_a_former_2 = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
            organisation=organisation_2,
        )
        self.assertEqual(aidant_a_former_1.test_pix_passed, False)
        self.assertEqual(aidant_a_former_1.date_test_pix, None)
        self.assertEqual(aidant_a_former_2.test_pix_passed, False)
        self.assertEqual(aidant_a_former_2.date_test_pix, None)
        self.assertEqual(
            aidant_a_former_1.status,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )
        self.assertEqual(
            aidant_a_former_2.status,
            ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value,
        )
        self.assertEqual(
            0, Aidant.objects.filter(email=aidant_a_former_1.email).count()
        )

        data = [
            {
                "date d'envoi": "2022-01-01",
                "email saisi": "marina.botteau@aisne.gouv.fr",
            }
        ]
        update_pix_and_create_aidant(data)

        aidant_a_former_1 = HabilitationRequest.objects.filter(
            email=aidant_a_former_1.email
        )[0]
        self.assertTrue(aidant_a_former_1.test_pix_passed)
        self.assertEqual(
            aidant_a_former_1.status, ReferentRequestStatuses.STATUS_VALIDATED.value
        )

        aidant_a_former_2 = HabilitationRequest.objects.filter(
            email=aidant_a_former_1.email
        )[1]
        self.assertTrue(aidant_a_former_2.test_pix_passed)
        self.assertEqual(
            aidant_a_former_2.status, ReferentRequestStatuses.STATUS_VALIDATED.value
        )

        self.assertEqual(
            1, Aidant.objects.filter(email=aidant_a_former_1.email).count()
        )
        aidant = Aidant.objects.filter(email=aidant_a_former_1.email)[0]
        self.assertIn(organisation_1, aidant.organisations.all())
        self.assertIn(organisation_2, aidant.organisations.all())


NOW = timezone.now()


class EmailOldAidants(TestCase):
    @classmethod
    def setUpTestData(cls):
        with freeze_time(NOW):
            cls.aidants_selected = AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=None,
            )
            warnable_totp = CarteTOTPFactory(aidant=cls.aidants_selected)
            CarteTOTP.objects.filter(pk=warnable_totp.pk).update(
                created_at=timezone.now() - relativedelta(months=7)
            )

    @freeze_time(NOW)
    @override_settings(FF_DEACTIVATE_OLD_AIDANT=True)
    def test_notify_old_aidants(self):
        logger = logging.getLogger()
        logger.info = MagicMock()

        self.assertEqual(0, len(mail.outbox))
        self.assertNotEqual(NOW, self.aidants_selected.deactivation_warning_at)

        email_old_aidants(logger=logger)

        logger.info.assert_any_call(
            "Sending warning notice for 1 aidants not connected recently"
        )
        logger.info.assert_any_call(
            "Sent warning notice for aidant "
            f"{self.aidants_selected.get_full_name()} not connected recently"
        )
        logger.info.assert_any_call(
            "Sent warning notice for 1 aidants not connected recently",
        )

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(
            [self.aidants_selected.email],
            mail.outbox[0].to,
        )

        self.aidants_selected.refresh_from_db()
        self.assertEqual(NOW, self.aidants_selected.deactivation_warning_at)


class ExportForBizdevs(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_aidant_org = OrganisationFactory(
            address="45 avenue du Général de Gaulle",
            zipcode="27120",
            city="HOULBEC COCHEREL",
            department_insee_code="27",
            type_id=1,
        )
        cls.staff_aidant: Aidant = AidantFactory(
            is_staff=True, organisation=cls.staff_aidant_org
        )

        # Create 4 mandates including 2 remote
        cls.mandat1: Mandat = MandatFactory(
            organisation=cls.staff_aidant.organisation,
            post__create_authorisations=["papiers"],
        )
        cls.mandat2: Mandat = MandatFactory(organisation=cls.staff_aidant.organisation)
        cls.mandat3: Mandat = MandatFactory(
            organisation=cls.staff_aidant.organisation, is_remote=True
        )
        cls.mandat4: Mandat = MandatFactory(
            organisation=cls.staff_aidant.organisation, is_remote=True
        )
        # Create 1 outdated mandate
        cls.mandat5: Mandat = MandatFactory(
            organisation=cls.staff_aidant.organisation,
            expiration_date=now() - timedelta(days=1),
        )

        # Create journals for these mandates
        for mandat in (cls.mandat1, cls.mandat2, cls.mandat3, cls.mandat4, cls.mandat5):
            Journal.log_attestation_creation(
                aidant=cls.staff_aidant,
                usager=mandat.usager,
                demarches=list(mandat.autorisations.values_list("demarche", flat=True)),
                duree=AuthorizationDurations.duration(mandat.duree_keyword, now()),
                is_remote_mandat=mandat.is_remote,
                access_token="",
                attestation_hash="",
                mandat=mandat,
                remote_constent_method=mandat.remote_constent_method,
                user_phone=mandat.usager.phone,
                consent_request_id="",
            )

    def test_export_for_bizdevs(self):
        self.maxDiff = None

        with mock.patch.object(
            export_for_bizdevs, "apply_async", return_value=AsyncResult(str(uuid4()))
        ) as export_for_bizdevs_mock:
            # Prevent running the export when creating the request
            request = ExportRequest.objects.create(aidant=self.staff_aidant)
            export_for_bizdevs_mock.assert_called_with(
                (request.pk,), compression="zlib"
            )

        result = export_for_bizdevs(request.pk)
        self.assertEqual(
            dedent(
                f"""
                prénom,nom,adresse électronique,Téléphone,profession,Est référent,Aidant - Peut créer des mandats,Carte TOTP active,Carte TOTP décallée,totp_card_drift,Date activation carte TOTP,App OTP,actif,Organisation: Nom,Organisation: Datapass ID,Organisation: N° SIRET,Organisation: Adresse,Organisation: Code Postal,Organisation: Ville,Organisation: Code INSEE du département,Organisation: Code INSEE de la région,Organisation type: Nom,Organisation: Labellisation France Services,Organisation: categorieJuridiqueUniteLegale,Organisation: Niveau I catégories juridiques,Organisation: Niveau II catégories juridiques,Organisation: Niveau III catégories juridiques,Organisation: Nombre de mandats créés,Organisation: Nombre de mandats à distance créés,Organisation: Nombre de mandats révoqués,Organisation: Nombre de mandats renouvelés,Organisation: Nombre d'usagers
                Thierry,Goneau,{self.staff_aidant.email},,secrétaire,False,True,False,None,None,None,False,True,COMMUNE D'HOULBEC COCHEREL,None,123,45 avenue du Général de Gaulle,27120,HOULBEC COCHEREL,27,27,France Services/MSAP,False,0,None,None,None,5,2,0,0,4
                """  # noqa: E501
            ).strip(),
            # Replace Windows' newline separator by Unix'
            result.replace("\r\n", "\n").strip(),
        )

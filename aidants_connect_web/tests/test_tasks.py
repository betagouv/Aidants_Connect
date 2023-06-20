import logging
from datetime import datetime
from unittest.mock import MagicMock

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

import pytz
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from aidants_connect_habilitation.tasks import update_pix_and_create_aidant
from aidants_connect_web.models import Aidant, CarteTOTP, HabilitationRequest
from aidants_connect_web.tasks import (
    email_old_aidants,
    get_recipient_list_for_organisation,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    CarteTOTPFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


class UtilsTaskTests(TestCase):
    def test_get_recipient_list_for_organisation(self):
        orga = OrganisationFactory()
        AidantFactory(organisation=orga, can_create_mandats=True)
        AidantFactory(organisation=orga, can_create_mandats=False)
        self.assertEqual(1, Aidant.objects.filter(can_create_mandats=True).count())
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
            aidant_a_former.status, HabilitationRequest.STATUS_WAITING_LIST_HABILITATION
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
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_VALIDATED)

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
            aidant_a_former.status, HabilitationRequest.STATUS_WAITING_LIST_HABILITATION
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
            aidant_a_former.status, HabilitationRequest.STATUS_WAITING_LIST_HABILITATION
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
            HabilitationRequest.STATUS_WAITING_LIST_HABILITATION,
        )
        self.assertEqual(
            aidant_a_former_2.status,
            HabilitationRequest.STATUS_WAITING_LIST_HABILITATION,
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
        self.assertEqual(aidant_a_former_1.status, HabilitationRequest.STATUS_VALIDATED)

        aidant_a_former_2 = HabilitationRequest.objects.filter(
            email=aidant_a_former_1.email
        )[1]
        self.assertTrue(aidant_a_former_2.test_pix_passed)
        self.assertEqual(aidant_a_former_2.status, HabilitationRequest.STATUS_VALIDATED)

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

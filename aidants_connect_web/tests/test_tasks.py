from datetime import datetime

from django.core.management import call_command
from django.test import TestCase

import pytz

from aidants_connect_web.models import Aidant, HabilitationRequest
from aidants_connect_web.tests.factories import HabilitationRequestFactory


class ImportPixTests(TestCase):
    def test_import_pix_results_and_create_new_aidant(self):
        aidant_a_former = HabilitationRequestFactory(
            email="marina.botteau@aisne.gouv.fr",
            formation_done=True,
            date_formation=datetime(2022, 1, 1, tzinfo=pytz.UTC),
        )
        self.assertEqual(aidant_a_former.test_pix_passed, False)
        self.assertEqual(aidant_a_former.date_test_pix, None)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        call_command("import_pix_results")

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertEqual(aidant_a_former.test_pix_passed, True)
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
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)
        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

        call_command("import_pix_results")

        aidant_a_former = HabilitationRequest.objects.filter(
            email=aidant_a_former.email
        )[0]
        self.assertEqual(aidant_a_former.test_pix_passed, True)
        self.assertEqual(aidant_a_former.status, HabilitationRequest.STATUS_NEW)

        self.assertEqual(0, Aidant.objects.filter(email=aidant_a_former.email).count())

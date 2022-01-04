from django.db import IntegrityError
from django.test import tag, TestCase

from aidants_connect.constants import RequestOriginConstants
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory


@tag("models")
class OrganisationRequestTests(TestCase):
    def test_type_other_correctly_set_constraint(self):
        OrganisationRequestFactory(
            type_id=RequestOriginConstants.CCAS.value, type_other=None
        )

        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(
                type_id=RequestOriginConstants.OTHER.value, type_other=None
            )
        self.assertIn("type_other_correctly_set", str(cm.exception))

    def test_cgu_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(cgu=False)
        self.assertIn("cgu_checked", str(cm.exception))

    def test_dpo_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(dpo=False)
        self.assertIn("dpo_checked", str(cm.exception))

    def test_professionals_only_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(professionals_only=False)
        self.assertIn("professionals_only_checked", str(cm.exception))

    def test_without_elected_checked_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            OrganisationRequestFactory(without_elected=False)
        self.assertIn("without_elected_checked", str(cm.exception))

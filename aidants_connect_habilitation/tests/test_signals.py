from django.test import TestCase, tag

from aidants_connect_common.tests.factories import FormationFactory
from aidants_connect_web.tests.factories import HabilitationRequestFactory

from ..signals import get_email_messages_for_inscription_validation


@tag("signal")
class UtilsSignalFormationEmailSendingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr_not_conum = HabilitationRequestFactory(
            first_name="JeanNotConum", conseiller_numerique=False
        )
        cls.hr_conum = HabilitationRequestFactory(
            first_name="JeanConum", conseiller_numerique=True
        )

        cls.formation = FormationFactory()

    def test_use_email_not_conum_for_person_not_conum(self):
        text_message, html_message = get_email_messages_for_inscription_validation(
            self.hr_not_conum, self.formation, "str_emails_contact"
        )
        self.assertTrue("ce simulateur" in text_message)
        self.assertTrue(
            'https://tally.so/r/mO0Xkg">ce simulateur</a> pour' in html_message
        )
        self.assertTrue("str_emails_contact" in html_message)
        self.assertTrue("str_emails_contact" in text_message)

    def test_use_email_not_conum_for_person_conum(self):
        text_message, html_message = get_email_messages_for_inscription_validation(
            self.hr_conum, self.formation, "str_emails_contact"
        )
        self.assertTrue("Pour les conseillers numériques" in text_message)
        self.assertTrue("Pour les conseillers numériques" in html_message)
        self.assertTrue("str_emails_contact" in text_message)
        self.assertTrue("str_emails_contact" in html_message)

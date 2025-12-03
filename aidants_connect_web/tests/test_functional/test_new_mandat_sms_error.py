from unittest import mock
from unittest.mock import Mock

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    FunctionalTestCase,
    async_test,
)
from aidants_connect_common.utils.sms_api import SmsApi
from aidants_connect_web.tests.factories import (
    AidantFactory,
    ConnectionFactory,
    UsagerFactory,
)

UUID = "1f75d571-4127-445b-a141-ea837580da14"


class NewMandatSmsErrorTests(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        # Utiliser un port dynamique (0) au lieu d'un port fixe
        cls.port = 0
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.aidant = AidantFactory(post__with_otp_device=True)
        self.otp_token = self.aidant.staticdevice_set.first().token_set.first().token

        self.usager = UsagerFactory()
        self.connection = ConnectionFactory(
            aidant=self.aidant,
            organisation=self.aidant.organisation,
            usager=self.usager,
            demarches=["papiers", "logement"],
            duree_keyword="SHORT",
        )

    async def trigger_sms_error(self):
        """Helper method to trigger SMS error and navigate to error page"""
        await self.login_aidant(self.aidant, self.otp_token)
        await self.navigate_to_url("/usagers/")
        await self.page.click("#add_usager")
        await self.wait_for_path_match("new_mandat")

        # fill-in new_mandate form
        await self.page.click("#id_demarche_argent ~ label")
        await self.page.click("#id_demarche_famille ~ label")
        await self.page.click("#id_duree_short ~ label")

        # Select remote method
        await self.page.click("#id_is_remote ~ label")
        # Wait for remote consent method fields to become required
        await self.page.wait_for_selector("#id_remote_constent_method_sms[required]")
        # Select SMS consent method
        await self.page.click("#id_remote_constent_method_sms ~ label")
        # Wait for phone fields to become required
        await self.page.wait_for_selector("#id_user_phone[required]")
        await self.page.wait_for_selector("#id_user_remote_contact_verified[required]")

        # fill phone number and verify contact
        await self.page.fill("#id_user_phone", "0 800 840 800")
        await self.page.click("#id_user_remote_contact_verified ~ label")

        # Click submit - this will trigger the SMS error and
        # redirect to espace_aidant_home
        await self.page.click(".fr-connect")
        await self.wait_for_path_match("espace_aidant_home")
        await self.page.wait_for_load_state("networkidle")

    @async_test
    @override_settings(
        SMS_API_DISABLED=False,
        LM_SMS_SERVICE_USERNAME="username",
        LM_SMS_SERVICE_PASSWORD="password",
        LM_SMS_SERVICE_BASE_URL=f"http://localhost:{settings.FC_AS_FS_TEST_PORT}",
        LM_SMS_SERVICE_OAUTH2_ENDPOINT=reverse("test_sms_api_token"),
        LM_SMS_SERVICE_SND_SMS_ENDPOINT=reverse("test_sms_api_sms"),
    )
    @mock.patch("aidants_connect_web.views.mandat.uuid4")
    @mock.patch("aidants_connect_common.utils.sms_api.SmsApiImpl.send_sms")
    async def test_accessibility_sms_error_page(self, mock_send_sms, uuid4_mock: Mock):
        """Test accessibility of espace_aidant_home page when SMS sending fails"""
        uuid4_mock.return_value = UUID

        # Configure mock to raise SMS exception
        mock_send_sms.side_effect = SmsApi.HttpRequestExpection(500, "Erreur API SMS")

        await self.trigger_sms_error()

        # Check that error message is displayed
        error_alert = await self.page.query_selector(".fr-alert--error")
        self.assertIsNotNone(error_alert, "Error alert should be present")

        error_text = await error_alert.text_content()
        self.assertIn(
            "Une erreur est survenue pendant l'envoi du SMS récapitulatif", error_text
        )

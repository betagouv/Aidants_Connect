from django_otp.plugins.otp_totp.models import TOTPDevice
from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    FunctionalTestCase,
    async_test,
)
from aidants_connect_web.constants import OTP_APP_DEVICE_NAME
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AidantFactory, OrganisationFactory


class EspaceResponsableFicheAidantFunctionalTests(FunctionalTestCase):
    def setUp(self):
        super().setUp()
        organisation = OrganisationFactory()
        # Create managers
        self.responsable_tom = AidantFactory(
            username="tom@tom.fr",
            first_name="Tom",
            last_name="Onier",
            post__with_otp_device=True,
            organisation=organisation,
        )
        self.responsable_tom.responsable_de.add(organisation)
        self.otp_token = (
            self.responsable_tom.staticdevice_set.first().token_set.first().token
        )
        TOTPDevice.objects.create(
            user=self.responsable_tom,
            name=OTP_APP_DEVICE_NAME % self.responsable_tom.pk,
        )

        self.responsable_marie = AidantFactory(
            username="marie@marie.fr",
            first_name="Marie",
            last_name="Onier",
            post__with_otp_device=True,
            organisation=organisation,
        )
        self.responsable_marie.responsable_de.add(organisation)

        TOTPDevice.objects.create(
            user=self.responsable_marie,
            name=OTP_APP_DEVICE_NAME % self.responsable_marie.pk,
        )

        self.aidant_tim: Aidant = AidantFactory(
            username="tim@tim.fr",
            organisation=organisation,
            first_name="Tim",
            last_name="Onier",
        )

        self.aidant_sarah: Aidant = AidantFactory(
            username="sarah@sarah.fr",
            organisation=organisation,
            first_name="Sarah",
            last_name="Onier",
            post__with_carte_totp=True,
            post__with_carte_totp_confirmed=True,
        )

        self.deactivated_aidant: Aidant = AidantFactory(
            username="deactivated@deactivated.fr",
            organisation=organisation,
            first_name="Deactivated",
            last_name="Onier",
            is_active=False,
        )

    @async_test
    async def test_otp_card_shows_active_badge(self):
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url + f"/espace-responsable/aidant/{self.aidant_sarah.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_sarah.id},
        )

        section_otp_card = self.page.locator("#section-otp-card")
        await expect(section_otp_card.locator("text=ASSOCIÉ")).to_be_visible()

        section_mobile_app = self.page.locator("#section-mobile-app")
        await expect(section_mobile_app.locator("text=INACTIF")).to_be_visible()

        await expect(self.page.get_by_text("Délier la carte")).to_be_visible()
        await expect(
            self.page.get_by_text("Associer une application mobile")
        ).to_be_visible()

    @async_test
    async def test_mobile_app_shows_active_badge(self):
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.responsable_tom.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.responsable_tom.id},
        )

        section_otp_card = self.page.locator("#section-otp-card")
        await expect(section_otp_card.locator("text=INACTIF")).to_be_visible()

        section_mobile_app = self.page.locator("#section-mobile-app")
        await expect(section_mobile_app.locator("text=ASSOCIÉ")).to_be_visible()

        await expect(
            self.page.get_by_text("Associer un moyen de connexion")
        ).to_be_visible()
        await expect(
            self.page.get_by_text("Délier l'application mobile")
        ).to_be_visible()

    @async_test
    async def test_helper_manager_cannot_deactivate_himself(self):
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.responsable_tom.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.responsable_tom.id},
        )

        await expect(
            self.page.get_by_text("Désigner comme référent")
        ).not_to_be_visible()
        await expect(self.page.get_by_text("Désactiver")).not_to_be_visible()

    @async_test
    async def test_helper_manager_can_deactivate_another_helper_manager(self):
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.responsable_marie.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.responsable_marie.id},
        )

        await expect(
            self.page.get_by_text("Désigner comme référent")
        ).not_to_be_visible()
        await expect(self.page.get_by_text("Désactiver")).to_be_visible()

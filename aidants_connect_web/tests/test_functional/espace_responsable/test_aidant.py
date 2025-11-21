from django.utils.timezone import now

from django_otp.plugins.otp_totp.models import TOTPDevice
from playwright.async_api import expect

from aidants_connect_common.tests.factories import FormationAttendantFactory
from aidants_connect_common.tests.test_accessibility.test_playwright import (
    FunctionalTestCase,
    async_test,
)
from aidants_connect_web.constants import (
    OTP_APP_DEVICE_NAME,
    HabilitationRequestCourseType,
)
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


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

        # cas formation FNE, inscrit
        self.aidant_fne_inscrit: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_fne = HabilitationRequestFactory(
            first_name=self.aidant_fne_inscrit.first_name,
            last_name=self.aidant_fne_inscrit.last_name,
            email=self.aidant_fne_inscrit.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.CLASSIC,
            formation_done=False,
            created_by_fne=True,
        )
        self.formation_attendant_fne = FormationAttendantFactory(
            attendant=self.habilitation_request_fne,
        )
        # cas formation FNE, formé
        self.aidant_fne_done: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_fne_done = HabilitationRequestFactory(
            first_name=self.aidant_fne_done.first_name,
            last_name=self.aidant_fne_done.last_name,
            email=self.aidant_fne_done.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.CLASSIC,
            formation_done=True,
            created_by_fne=True,
            test_pix_passed=True,
            date_test_pix=now(),
        )
        self.formation_attendant_fne_done = FormationAttendantFactory(
            attendant=self.habilitation_request_fne_done,
        )
        self.aidant_fne_done_no_attendant: Aidant = AidantFactory(
            organisation=organisation
        )
        self.habilitation_request_fne_done_no_attendant = HabilitationRequestFactory(
            first_name=self.aidant_fne_done_no_attendant.first_name,
            last_name=self.aidant_fne_done_no_attendant.last_name,
            email=self.aidant_fne_done_no_attendant.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.CLASSIC,
            formation_done=True,
            created_by_fne=True,
            test_pix_passed=True,
            date_test_pix=now(),
        )

        # cas formation P2P, inscrit
        self.aidant_p2p_inscrit: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_p2p = HabilitationRequestFactory(
            first_name=self.aidant_p2p_inscrit.first_name,
            last_name=self.aidant_p2p_inscrit.last_name,
            email=self.aidant_p2p_inscrit.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.P2P,
            formation_done=False,
            created_by_fne=False,
        )
        self.formation_attendant_p2p = FormationAttendantFactory(
            attendant=self.habilitation_request_p2p,
        )
        # cas formation P2P, formé, pas de test PIX
        self.aidant_p2p_done: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_p2p_done = HabilitationRequestFactory(
            first_name=self.aidant_p2p_done.first_name,
            last_name=self.aidant_p2p_done.last_name,
            email=self.aidant_p2p_done.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.P2P,
            formation_done=True,
            created_by_fne=False,
            test_pix_passed=False,
        )
        self.formation_attendant_p2p_done = FormationAttendantFactory(
            attendant=self.habilitation_request_p2p_done,
        )
        self.aidant_p2p_done_no_attendant: Aidant = AidantFactory(
            organisation=organisation
        )
        self.habilitation_request_p2p_done_no_attendant = HabilitationRequestFactory(
            first_name=self.aidant_p2p_done_no_attendant.first_name,
            last_name=self.aidant_p2p_done_no_attendant.last_name,
            email=self.aidant_p2p_done_no_attendant.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.P2P,
            formation_done=True,
            created_by_fne=False,
            test_pix_passed=False,
        )

        # cas formation classique, inscrit
        self.aidant_classic_inscrit: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_classic = HabilitationRequestFactory(
            first_name=self.aidant_classic_inscrit.first_name,
            last_name=self.aidant_classic_inscrit.last_name,
            email=self.aidant_classic_inscrit.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.CLASSIC,
            formation_done=False,
            created_by_fne=False,
        )
        self.formation_attendant_classic = FormationAttendantFactory(
            attendant=self.habilitation_request_classic,
        )

        self.aidant_classic_done: Aidant = AidantFactory(organisation=organisation)
        self.habilitation_request_classic_done = HabilitationRequestFactory(
            first_name=self.aidant_classic_done.first_name,
            last_name=self.aidant_classic_done.last_name,
            email=self.aidant_classic_done.email,
            organisation=organisation,
            course_type=HabilitationRequestCourseType.CLASSIC,
            formation_done=True,
            created_by_fne=False,
            test_pix_passed=True,
            date_test_pix=now(),
        )
        self.formation_attendant_classic_done = FormationAttendantFactory(
            attendant=self.habilitation_request_classic_done,
        )

        self.aidant_classic_done_no_attendant: Aidant = AidantFactory(
            organisation=organisation
        )
        self.habilitation_request_classic_done_no_attendant = (
            HabilitationRequestFactory(
                first_name=self.aidant_classic_done_no_attendant.first_name,
                last_name=self.aidant_classic_done_no_attendant.last_name,
                email=self.aidant_classic_done_no_attendant.email,
                organisation=organisation,
                course_type=HabilitationRequestCourseType.CLASSIC,
                formation_done=True,
                created_by_fne=False,
                test_pix_passed=True,
                date_test_pix=now(),
            )
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

    @async_test
    async def test_formation_fne_inscrit(self):
        """Test l'affichage pour un aidant inscrit à une formation FNE"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_fne_inscrit.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_fne_inscrit.id},
        )

        await expect(
            self.page.get_by_text("Inscrit à une formation FNE")
        ).to_be_visible()
        await expect(self.page.get_by_text("Information :")).to_be_hidden()

    @async_test
    async def test_formation_fne_done(self):
        """Test l'affichage pour un aidant formé à une formation FNE"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_fne_done.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_fne_done.id},
        )

        date_formation = self.formation_attendant_fne.formation.start_datetime.strftime(
            "%d/%m/%Y"
        )
        date_pix = self.habilitation_request_fne_done.date_test_pix.strftime("%d/%m/%Y")

        await expect(
            self.page.get_by_text(f"Formation FNE réalisée le {date_formation}")
        ).to_be_visible()
        await expect(
            self.page.get_by_text(f"Test PIX réalisé le {date_pix}")
        ).to_be_visible()

    @async_test
    async def test_formation_fne_done_no_attendant(self):
        """Test l'affichage pour un aidant formé à une formation FNE"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_fne_done_no_attendant.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_fne_done_no_attendant.id},
        )

        date_pix = (
            self.habilitation_request_fne_done_no_attendant.date_test_pix.strftime(
                "%d/%m/%Y"
            )
        )

        await expect(self.page.get_by_text("Formation FNE réalisée\n")).to_be_visible()
        await expect(
            self.page.get_by_text(f"Test PIX réalisé le {date_pix}")
        ).to_be_visible()

    @async_test
    async def test_formation_p2p_inscrit_display(self):
        """Test l'affichage pour un aidant inscrit à une formation P2P"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_p2p_inscrit.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_p2p_inscrit.id},
        )

        await expect(
            self.page.get_by_text("Inscrit à une formation pair à pair")
        ).to_be_visible()
        await expect(self.page.get_by_text("Information :")).to_be_hidden()

    @async_test
    async def test_formation_p2p_done(self):
        """Test l'affichage pour un aidant formé à une formation pair à pair"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_p2p_done.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_p2p_done.id},
        )

        await expect(self.page.get_by_text("Formation pair à pair")).to_be_visible()
        await expect(self.page.get_by_text("Test PIX réalisé le")).to_be_hidden()

    @async_test
    async def test_formation_p2p_done_no_attendant(self):
        """Test l'affichage pour un aidant formé à une formation pair à pair"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_p2p_done_no_attendant.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_p2p_done_no_attendant.id},
        )

        await expect(self.page.get_by_text("Formation pair à pair\n")).to_be_visible()
        await expect(self.page.get_by_text("Test PIX réalisé le")).to_be_hidden()

    @async_test
    async def test_formation_classic_inscrit_display(self):
        """Test l'affichage pour un aidant inscrit à une formation clasique"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_classic_inscrit.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_classic_inscrit.id},
        )

        date_formation = (
            self.formation_attendant_classic.formation.start_datetime.strftime(
                "%d/%m/%Y"
            )
        )
        of = self.formation_attendant_classic.formation.organisation.name
        email = self.formation_attendant_classic.formation.organisation.contacts[0]

        await expect(
            self.page.get_by_text(
                f"Inscrit à la formation du {date_formation} par {of}"
            )
        ).to_be_visible()
        await expect(self.page.get_by_text("Information :")).to_be_visible()
        await expect(self.page.get_by_text(email)).to_be_visible()

    @async_test
    async def test_formation_classic_done(self):
        """Test l'affichage pour un aidant formé à une formation classique"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_classic_done.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_classic_done.id},
        )

        date_formation = (
            self.formation_attendant_classic_done.formation.start_datetime.strftime(
                "%d/%m/%Y"
            )
        )
        of = self.formation_attendant_classic_done.formation.organisation.name
        date_pix = self.habilitation_request_classic_done.date_test_pix.strftime(
            "%d/%m/%Y"
        )

        await expect(
            self.page.get_by_text(
                f"Formation classique réalisée le {date_formation} par {of}"
            )
        ).to_be_visible()
        await expect(
            self.page.get_by_text(f"Test PIX réalisé le {date_pix}")
        ).to_be_visible()

    @async_test
    async def test_formation_classic_done_no_attendant(self):
        """Test l'affichage pour un aidant formé à une formation classique"""
        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(
            self.live_server_url
            + f"/espace-responsable/aidant/{self.aidant_classic_done_no_attendant.id}/"
        )
        await self.wait_for_path_match(
            "espace_responsable_aidant",
            kwargs={"aidant_id": self.aidant_classic_done_no_attendant.id},
        )

        date_pix = (
            self.habilitation_request_classic_done_no_attendant.date_test_pix.strftime(
                "%d/%m/%Y"
            )
        )

        await expect(
            self.page.get_by_text("Formation classique réalisée\n")
        ).to_be_visible()
        await expect(
            self.page.get_by_text(f"Test PIX réalisé le {date_pix}")
        ).to_be_visible()

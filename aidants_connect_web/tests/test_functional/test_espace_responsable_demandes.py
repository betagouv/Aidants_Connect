from playwright.async_api import expect

from aidants_connect_common.tests.test_accessibility.test_playwright import (
    FunctionalTestCase,
    async_test,
)
from aidants_connect_web.constants import (
    HabilitationRequestCourseType,
    ReferentRequestStatuses,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    OrganisationFactory,
)


class EspaceResponsableDemandesFunctionalTests(FunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.organisation = OrganisationFactory()

        # Créer un responsable avec OTP
        self.responsable_tom = AidantFactory(
            username="tom@tom.fr",
            first_name="Tom",
            last_name="Responsable",
            post__with_otp_device=True,
            organisation=self.organisation,
        )
        self.responsable_tom.responsable_de.add(self.organisation)
        self.otp_token = (
            self.responsable_tom.staticdevice_set.first().token_set.first().token
        )
        self.request_processing = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_PROCESSING,
            first_name="Alice",
            last_name="Validée",
            email="alice.validee@example.com",
            created_by_fne=False,
            course_type=HabilitationRequestCourseType.CLASSIC,
        )

        self.request_processing_p2p = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_PROCESSING_P2P,
            first_name="Bob",
            last_name="ValidéP2P",
            email="bob.valide.p2p@example.com",
            created_by_fne=False,
            course_type=HabilitationRequestCourseType.P2P,
        )

        # Créer des demandes en cours
        self.request_new = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_NEW,
            first_name="Charlie",
            last_name="Nouveau",
            email="charlie.nouveau@example.com",
            created_by_fne=False,
        )

        self.request_waiting = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION,
            first_name="Diana",
            last_name="Attente",
            email="diana.attente@example.com",
            created_by_fne=False,
        )

        # Créer des demandes refusées
        self.request_refused = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_REFUSED,
            first_name="Eve",
            last_name="Refusée",
            email="eve.refusee@example.com",
            created_by_fne=False,
        )

        self.request_cancelled = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_CANCELLED,
            first_name="Frank",
            last_name="Annulé",
            email="frank.annule@example.com",
            created_by_fne=False,
        )

        self.request_cancelled_by_responsable = HabilitationRequestFactory(
            organisation=self.organisation,
            status=ReferentRequestStatuses.STATUS_CANCELLED_BY_RESPONSABLE,
            first_name="Grace",
            last_name="AnnuléeParRéférent",
            email="grace.annulee@example.com",
            created_by_fne=False,
        )

    @async_test
    async def test_display_validated_habilitation_requests(self):
        """Test l'affichage des demandes dont l'égilibitée est validée"""

        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(self.live_server_url + "/espace-responsable/aidants/")
        await self.wait_for_path_match("espace_responsable_aidants")

        await expect(self.page.get_by_text("Demandes en cours")).to_be_visible()
        await self.page.get_by_role("tab", name="Demandes en cours").click()

        await expect(self.page.get_by_text("Alice Validée")).to_be_visible()
        await expect(self.page.get_by_text("Inscrire à une session")).to_be_visible()

        await expect(self.page.get_by_text("Bob ValidéP2P")).to_be_visible()
        await expect(self.page.get_by_text("Formation pair à pair")).to_be_visible()

        # Vérifier que le bouton "Inscrire à une session" est présent
        # pour les demandes classiques
        await expect(
            self.page.locator(
                f"#register-habilitation-request-{self.request_processing.id}"
            )
        ).to_be_visible()

        # Vérifier que le bouton n'est pas présent pour les demandes P2P
        await expect(
            self.page.locator(
                f"#register-habilitation-request-{self.request_processing_p2p.id}"
            )
        ).not_to_be_visible()

        # Vérifier que les noms des aidants ne sont pas clicables
        await expect(self.page.locator("table td:first-child a")).to_have_count(0)

    @async_test
    async def test_display_pending_habilitation_requests(self):
        """Test l'affichage des demandes d'habilitation en cours"""

        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(self.live_server_url + "/espace-responsable/aidants/")
        await self.wait_for_path_match("espace_responsable_aidants")

        await expect(self.page.get_by_text("Demandes en cours")).to_be_visible()
        await self.page.get_by_role("tab", name="Demandes en cours").click()

        await expect(self.page.get_by_text("Charlie Nouveau")).to_be_visible()
        await expect(self.page.get_by_text("Diana Attente")).to_be_visible()

        # Vérifier que les noms ne sont pas clicables dans cette section aussi
        pending_table = (
            self.page.locator("h2:has-text('Demandes en cours')")
            .locator("..")
            .locator("table")
        )
        await expect(pending_table.locator("td:first-child a")).to_have_count(0)

    @async_test
    async def test_display_refused_habilitation_requests(self):
        """Test l'affichage des demandes d'habilitation refusées"""

        await self.login_aidant(self.responsable_tom, self.otp_token)
        await self.page.goto(self.live_server_url + "/espace-responsable/aidants/")
        await self.wait_for_path_match("espace_responsable_aidants")

        await expect(self.page.get_by_text("Demandes en cours")).to_be_visible()
        await self.page.get_by_role("tab", name="Demandes en cours").click()

        await expect(self.page.get_by_text("Eve Refusée")).to_be_visible()

        await expect(self.page.get_by_text("Frank Annulé")).to_be_visible()

        await expect(self.page.get_by_text("Grace AnnuléeParRéférent")).to_be_visible()

        await expect(self.page.get_by_text("Refusée", exact=True)).to_be_visible()
        await expect(self.page.get_by_text("Annulée", exact=True)).to_be_visible()
        await expect(
            self.page.get_by_text("Annulée par le ou la référente", exact=True)
        ).to_be_visible()

        # Vérifier que les noms ne sont pas clicables dans cette section
        refused_table = (
            self.page.locator("h2:has-text('Demandes en cours')")
            .locator("..")
            .locator("table")
        )
        await expect(refused_table.locator("td:first-child a")).to_have_count(0)

        # Vérifier qu'il n'y a pas de boutons d'action pour les demandes refusées
        await expect(
            self.page.locator(f"#cancel-habilitation-request-{self.request_refused.id}")
        ).not_to_be_visible()
        await expect(
            self.page.locator(
                f"#cancel-habilitation-request-{self.request_cancelled.id}"
            )
        ).not_to_be_visible()
        await expect(
            self.page.locator(
                "#cancel-habilitation-request-"
                f"{self.request_cancelled_by_responsable.id}"
            )
        ).not_to_be_visible()

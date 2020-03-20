import time
from datetime import timedelta
from selenium.webdriver.common.keys import Keys

from django.conf import settings
from django.test import tag, override_settings
from django.utils import timezone

from aidants_connect_web.tests.factories import (
    AidantFactory,
    UsagerFactory,
    MandatFactory,
)
from aidants_connect_web.utilities import generate_sha256_hash
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase


TEST_FC_AS_FS_TEST_PORT = 4242


@tag("functional", "espace_usager")
@override_settings(
    FC_AS_FS_CALLBACK_URL="http://localhost:4242",
    FC_AS_FS_TEST_PORT=TEST_FC_AS_FS_TEST_PORT,
)
class ViewEspaceUsager(FunctionalTestCase):
    @classmethod
    def setUpClass(cls):
        # FC only calls back on specific port
        cls.port = TEST_FC_AS_FS_TEST_PORT
        cls.aidant = AidantFactory()
        cls.usager_sub_fc = (
            "b6048e95bb134ec5b1d1e1fa69f287172e91722b9354d637a1bcf2ebb0fd2ef5v1"
        )
        cls.usager_sub = generate_sha256_hash(
            f"{cls.usager_sub_fc}{settings.FC_AS_FI_HASH_SALT}".encode()
        )
        cls.usager_angela = UsagerFactory(
            given_name="Angela Claire Louise",
            family_name="ST-DUBOIS",
            sub=cls.usager_sub,
        )
        MandatFactory(
            aidant=cls.aidant,
            usager=cls.usager_angela,
            demarche="argent",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        super().setUpClass()

    def setUp(self):
        self.selenium.get("https://fcp.integ01.dev-franceconnect.fr")
        self.selenium.delete_all_cookies()
        time.sleep(2)
        self.selenium.get("https://fournisseur-d-identite.dev-franceconnect.fr")
        self.selenium.delete_all_cookies()
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_existing_usager_can_access_espace_usager(self):
        self.open_live_url("/")

        welcome_usager = self.selenium.find_elements_by_tag_name("h3")[1].text
        self.assertEqual(welcome_usager, "Je suis un Usager")

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("connect_usager")
        fc_button.click()
        time.sleep(2)

        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element_by_id(
            "fi-identity-provider-example"
        )
        demonstration_hex.click()
        time.sleep(2)

        # FC - Use the Angela credentials
        demo_title = self.selenium.find_element_by_tag_name("h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        submit_button = self.selenium.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(2)

        # FC - Validate the information
        submit_button = self.selenium.find_element_by_tag_name("input")
        submit_button.click()
        time.sleep(2)

        # espace usager
        espace_usager_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertIn("Bienvenue sur votre Espace Usager", espace_usager_title)
        self.assertEqual(len(self.selenium.find_elements_by_tag_name("tr")), 2)

        # logout
        logout_button = self.selenium.find_elements_by_css_selector("nav ul li")[1]
        logout_button.click()
        time.sleep(2)

        # home
        welcome_home = self.selenium.find_elements_by_tag_name("h1")[0].text
        self.assertEqual(welcome_home, "Bienvenue sur Aidants Connect")

    def test_new_usager_can_not_access_espace_usager(self):
        self.open_live_url("/")

        welcome_usager = self.selenium.find_elements_by_tag_name("h3")[1].text
        self.assertEqual(welcome_usager, "Je suis un Usager")

        # FranceConnect
        fc_button = self.selenium.find_element_by_id("connect_usager")
        fc_button.click()
        time.sleep(2)

        fc_title = self.selenium.title
        self.assertEqual("Connexion - choix du compte", fc_title)
        time.sleep(2)

        # Click on the 'Démonstration' identity provider
        demonstration_hex = self.selenium.find_element_by_id(
            "fi-identity-provider-example"
        )
        demonstration_hex.click()
        time.sleep(2)

        # FC - Use the Paul Louis credentials
        demo_title = self.selenium.find_element_by_tag_name("h3").text
        self.assertEqual(demo_title, "Fournisseur d'identité de démonstration")
        username_input = self.selenium.find_elements_by_tag_name("input")[0]
        username_input.send_keys(4 * Keys.BACKSPACE)
        username_input.send_keys("sans_nom_dusage")
        submit_button = self.selenium.find_elements_by_tag_name("input")[2]
        self.assertEqual(submit_button.get_attribute("type"), "submit")
        submit_button.click()
        time.sleep(2)

        # FC - Validate the information
        submit_button = self.selenium.find_element_by_tag_name("input")
        submit_button.click()
        time.sleep(2)

        # home page
        home_page_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(home_page_title, "Bienvenue sur Aidants Connect")

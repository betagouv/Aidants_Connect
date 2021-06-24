from django.test import tag

from aidants_connect_web.tests.factories import (
    AidantFactory,
)
from aidants_connect_web.tests.test_functional.testcases import FunctionalTestCase
from django.core import mail

from selenium.webdriver.support.ui import WebDriverWait


@tag("functional")
class CancelAutorisationTests(FunctionalTestCase):
    def setUp(self):
        self.aidant_thierry = AidantFactory()
        device = self.aidant_thierry.staticdevice_set.create(id=self.aidant_thierry.id)
        device.token_set.create(token="123456")
        super().setUpClass()

    def test_aidant_can_login(self):
        self.open_live_url("/accounts/login/")
        login_field = self.selenium.find_element_by_id("id_email")
        login_field.send_keys("thierry@thierry.com")
        otp_field = self.selenium.find_element_by_id("id_otp_token")
        otp_field.send_keys("123456")
        submit_button = self.selenium.find_element_by_xpath("//button")
        submit_button.click()
        email_sent_title = self.selenium.find_element_by_tag_name("h1").text
        self.assertEqual(
            email_sent_title, "Un email vous a été envoyé pour vous connecter."
        )
        self.assertEqual(len(mail.outbox), 1)
        token_email = mail.outbox[0].body
        line_containing_magic_link = token_email.split("\n")[2]
        magic_link_https = line_containing_magic_link.split()[-1]
        magic_link_http = magic_link_https.replace("https", "http", 1)
        self.selenium.get(magic_link_http)
        WebDriverWait(self.selenium, 5).until(
            lambda selenium: "chargement" not in selenium.current_url,
            message="The magicauth wait JavaScript did not work - check CSP compliance",
        )

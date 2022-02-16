from django.core import mail

from selenium.webdriver.common.by import By


def login_aidant(self, aidant_email: str = "thierry@thierry.com"):
    login_field = self.selenium.find_element(By.ID, "id_email")
    login_field.send_keys(aidant_email)
    otp_field = self.selenium.find_element(By.ID, "id_otp_token")
    otp_field.send_keys("123456")
    submit_button = self.selenium.find_element(By.XPATH, "//button")
    submit_button.click()
    email_sent_title = self.selenium.find_element(By.TAG_NAME, "h1").text
    self.assertEqual(
        email_sent_title, "Un email vous a été envoyé pour vous connecter."
    )
    self.assertEqual(len(mail.outbox), 1)
    token_email = mail.outbox[0].body
    line_containing_magic_link = token_email.split("\n")[2]
    magic_link_https = line_containing_magic_link.split()[-1]
    magic_link_http = magic_link_https.replace("https", "http", 1)
    magic_link_no_wait = magic_link_http.replace("chargement/code", "code", 1)
    self.selenium.get(magic_link_no_wait)

from unittest import TestCase
from urllib.parse import quote

from aidants_connect.templatetags.ac_common import mailto


class Test(TestCase):
    def test_mailto(self):
        mail_link = "Cliquez sur ce lien"
        recipient = "test@test.test"
        subject = "Objet: test"
        body = "Ceci est un mail de test"
        self.assertEqual(
            mailto(mail_link, recipient, subject, body),
            f'<a href="mailto:{recipient}?subject={quote(subject, "")}&'
            f'body={quote(body, "")}">{mail_link}</a>',
        )

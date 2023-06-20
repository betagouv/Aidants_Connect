import logging
from unittest import mock
from unittest.mock import MagicMock

from django.template import loader
from django.test import TestCase

from aidants_connect_common.utils.email import render_email


class Test(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template_name = "login/email_template.mjml"

    def test_render_email(self):
        logger = logging.getLogger()
        logger.error = MagicMock()

        _, html_email = render_email(self.template_name, context={})
        self.assertIn("<html", html_email)
        logger.error.assert_not_called()

        logger.error.reset_mock()

        with mock.patch(
            "aidants_connect_common.utils.email.mjml2html"
        ) as mock_mjml2html:
            # Simulate mjml2html doesn't render correctly
            mock_mjml2html.side_effect = lambda mjml, *args, **kwargs: mjml

            context = {}

            _, html_email = render_email(self.template_name, context)
            html_email_str = loader.render_to_string(self.template_name, context)

            self.assertIn("<mjml>", html_email)
            logger.error.assert_called_once_with(
                "MJML was not correctly rendered.\n"
                f"Template email:{html_email_str},\n"
                f"Rendered MJML: {html_email}"
            )

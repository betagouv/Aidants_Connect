from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase


class EmailTemplateTests(TestCase):

    def test_email_template_use_https(self):
        context = {"token": {"key": "KEY"}}
        rendered = render_to_string(settings.MAGICAUTH_EMAIL_HTML_TEMPLATE,
                                    context=context)

        assert '<td align="center"> <a href="https://' in rendered

from textwrap import dedent
from urllib.parse import quote

from django.template import Context, Template
from django.test import TestCase

from aidants_connect_common.templatetags.ac_common import mailto


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


class LinebreaklessTests(TestCase):
    def test_linebreaks_are_stripped(self):
        result = self._render_template(
            """{% load ac_common %}
            {% linebreakless %}
            <p>
                This is a test with a list
            </p>
            <ul>
                <li>item 1</li>
                <li>item 2</li>
                <li>item 3</li>
            </ul>
            {% endlinebreakless %}"""
        )

        self.assertEqual(
            "<p>This is a test with a list</p><ul><li>item 1</li><li>item 2</li>"
            "<li>item 3</li></ul>",
            result.strip(),
        )

    def test_keeplinebreak_keeps_linebreaks(self):
        result = self._render_template(
            """
            {% load ac_common %}
            {% linebreakless %}
            <p>
                This is a test with a list
            </p>
            <ul>{% keeplinebreak %}
                <li>item 1</li>{% keeplinebreak %}
                <li>item 2</li>{% keeplinebreak %}
                <li>item 3</li>{% keeplinebreak %}
            </ul>
            {% endlinebreakless %}"""
        )

        self.assertEqual(
            "<p>This is a test with a list</p><ul>\n<li>item 1</li>\n<li>item 2</li>\n"
            "<li>item 3</li>\n</ul>",
            result.strip(),
        )

    def test_keeplinebreak_keeps_witespace_on_option(self):
        result = self._render_template(
            dedent(
                """\
                {% load ac_common %}
                {% linebreakless dont_rstrip=True %}
                This is a line;
                 this is line
                {% endlinebreakless %}"""
            )
        )

        self.assertEqual("This is a line; this is line", result.strip())

        result = self._render_template(
            dedent(
                """\
                {% load ac_common %}
                {% linebreakless dont_lstrip=True %}
                This is a line; 
                this is line
                {% endlinebreakless %}"""  # noqa: W291
            )
        )

        self.assertEqual("This is a line; this is line", result.strip())

    def test_keeplinebreak_throws_expception_when_not_followed_by_a_linebreak(self):
        template = """
            {% load ac_common %}
            {% linebreakless %}
            <p>
                This is a test with a list
            </p>
            <ul>
                <li>item 1</li>
                <li>item 2</li>
                <li>item 3</li>
            </ul>
            {% keeplinebreak %}{% endlinebreakless %}"""

        with self.assertRaises(ValueError):
            self._render_template(template)

    def _render_template(self, string, context=None):
        return Template(string).render(Context(context or {}))

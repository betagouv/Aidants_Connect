from django.template import Context, Template
from django.test import TestCase


class LinebreaklessTests(TestCase):
    def test_linebreaks_are_stripped(self):
        result = self._render_template(
            """{% load ac_extras %}
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
            {% load ac_extras %}
            {% linebreakless %}
            <p>
                This is a test with a list
            </p>
            <ul>{% keeplinebreak %}
                <li>item 1</li>{% keeplinebreak %}
                <li>item 2</li>{% keeplinebreak %}
                <li>item 3</li>{% keeplinebreak %}
            </ul>
            {% endlinebreakless %}
        """
        )

        self.assertEqual(
            "<p>This is a test with a list</p><ul>\n<li>item 1</li>\n<li>item 2</li>\n"
            "<li>item 3</li>\n</ul>",
            result.strip(),
        )

    def test_keeplinebreak_throws_expception_when_not_followed_by_a_linebreak(self):
        template = """
            {% load ac_extras %}
            {% linebreakless %}
            <p>
                This is a test with a list
            </p>
            <ul>
                <li>item 1</li>
                <li>item 2</li>
                <li>item 3</li>
            </ul>
            {% keeplinebreak %}{% endlinebreakless %}
        """
        with self.assertRaises(ValueError):
            self._render_template(template)

    def _render_template(self, string, context=None):
        return Template(string).render(Context(context or {}))

from django.test import tag, TestCase
from aidants_connect_web.models import Aidant, Autorisation, Usager


@tag("fixtures")
class FixturesTests(TestCase):
    fixtures = [
        "aidants_connect_web/fixtures/admin.json",
        "aidants_connect_web/fixtures/usager_autorisation.json",
    ]

    def test_fixtures_loads_successfully(self):
        self.assertEqual(Aidant.objects.count(), 1)
        self.assertEqual(Usager.objects.count(), 1)
        self.assertEqual(Autorisation.objects.count(), 2)

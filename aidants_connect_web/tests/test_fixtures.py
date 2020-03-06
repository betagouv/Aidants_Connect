from django.test import tag, TestCase
from aidants_connect_web.models import Aidant, Usager, Mandat


@tag("fixtures")
class FixturesTest(TestCase):
    fixtures = [
        "aidants_connect_web/fixtures/admin.json",
        "aidants_connect_web/fixtures/usager_mandat.json",
    ]

    def test_fixtures_loads_successfully(self):
        self.assertEqual(Aidant.objects.count(), 1)
        self.assertEqual(Usager.objects.count(), 1)
        self.assertEqual(Mandat.objects.count(), 2)

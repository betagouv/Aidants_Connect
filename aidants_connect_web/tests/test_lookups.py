from django.test import TestCase, tag

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import JournalFactory, OrganisationFactory


@tag("lookups")
class TestIsNullOrBlank(TestCase):
    @classmethod
    def setUpTestData(cls):
        o = OrganisationFactory()
        cls.journal_null_demarche = JournalFactory(demarche=None, organisation=o)
        cls.journal_blank_demarche = JournalFactory(demarche="", organisation=o)
        cls.journal_white_demarche = JournalFactory(demarche="   ", organisation=o)
        cls.journal_non_empty_demarche = JournalFactory(
            demarche="papier", organisation=o
        )

    def test_lookup(self):
        qset = Journal.objects.filter(demarche__isnull_or_blank=False)
        self.assertEqual(qset.count(), 1)
        self.assertEqual(qset.first(), self.journal_non_empty_demarche)

        qset = Journal.objects.filter(demarche__isnull_or_blank=True)
        self.assertEqual(qset.count(), 3)

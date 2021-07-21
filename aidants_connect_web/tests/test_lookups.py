from django.test import tag, TestCase

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import JournalFactory, AidantFactory


@tag("lookups")
class TestIsNullOrBlank(TestCase):
    @classmethod
    def setUpTestData(cls):
        w = AidantFactory()
        cls.journal_null_demarche = JournalFactory(demarche=None, aidant=w)
        cls.journal_blank_demarche = JournalFactory(demarche="", aidant=w)
        cls.journal_white_demarche = JournalFactory(demarche="   ", aidant=w)
        cls.journal_non_empty_demarche = JournalFactory(demarche="papier", aidant=w)

    def test_lookup(self):
        qset = Journal.objects.filter(demarche__isnull_or_blank=False)
        self.assertEqual(qset.count(), 1)
        self.assertEqual(qset.first(), self.journal_non_empty_demarche)

        qset = Journal.objects.filter(demarche__isnull_or_blank=True)
        self.assertEqual(qset.count(), 3)

from django.test import TestCase, tag

from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import JournalFactory, OrganisationFactory


@tag("lookups")
class TestIsNullOrBlank(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.o = OrganisationFactory()
        cls.o2 = OrganisationFactory()
        cls.journal_null_demarche = JournalFactory(demarche=None, organisation=cls.o)
        cls.journal_empty_demarche = JournalFactory(demarche="", organisation=cls.o)
        cls.journal_blank_demarche = JournalFactory(demarche="   ", organisation=cls.o)
        cls.journal_non_empty_demarche = JournalFactory(
            demarche="papier", organisation=cls.o
        )

        cls.journal_null_additional_information = JournalFactory(
            additional_information=None, organisation=cls.o2
        )
        cls.journal_empty_additional_information = JournalFactory(
            additional_information="", organisation=cls.o2
        )
        cls.journal_blank_additional_information = JournalFactory(
            additional_information="   ", organisation=cls.o2
        )
        cls.journal_non_empty_additional_information = JournalFactory(
            additional_information="papier", organisation=cls.o2
        )

    def test_charfield_lookup(self):
        qset = Journal.objects.filter(
            demarche__isnull_or_blank=False, organisation=self.o
        )
        self.assertEqual(qset.count(), 1)
        self.assertIn(self.journal_non_empty_demarche, qset)

        qset = Journal.objects.filter(
            demarche__isnull_or_blank=True, organisation=self.o
        )
        self.assertEqual(qset.count(), 3)

        for item in [
            self.journal_blank_demarche,
            self.journal_empty_demarche,
            self.journal_blank_demarche,
        ]:
            self.assertIn(item, qset)

    def test_textfield_lookup(self):
        qset = Journal.objects.filter(
            additional_information__isnull_or_blank=False, organisation=self.o2
        )
        self.assertEqual(qset.count(), 1)
        self.assertIn(self.journal_non_empty_additional_information, qset)

        qset = Journal.objects.filter(
            additional_information__isnull_or_blank=True, organisation=self.o2
        )
        self.assertEqual(qset.count(), 3)
        for item in [
            self.journal_blank_additional_information,
            self.journal_empty_additional_information,
            self.journal_blank_additional_information,
        ]:
            self.assertIn(item, qset)

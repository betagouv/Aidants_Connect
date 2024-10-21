from django.core import serializers
from django.test import TestCase

from aidants_connect_web.tests.factories import AidantFactory


class TestCSVSerializer(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidants = [AidantFactory() for _ in range(10)]

    def test_csv_serializer(self):
        from aidants_connect_web.models import Aidant

        result = serializers.serialize("csv", Aidant.objects.all())

        # 10 records +  header
        self.assertEqual(11, len(result.splitlines()))

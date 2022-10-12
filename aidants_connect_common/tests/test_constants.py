from django.test import TestCase

from aidants_connect_common.utils.constants import DictChoices, TextChoicesEnum


class TestChoicesMeta(TestCase):
    def test_DictChoices_with_simple_declaration(self):
        class TestDictChoices(DictChoices):
            TEST_1 = {
                "label": "Test 1",
                "description": "This is a test",
            }
            TEST_2 = {
                "label": "Test 2",
                "description": "This is also a test",
            }

            @staticmethod
            def _human_readable_name(enum_item):
                return enum_item.label["description"]

        names, values = zip(*TestDictChoices.choices)
        names, values = zip(*TestDictChoices.choices)
        self.assertSequenceEqual(["TEST_1", "TEST_2"], names)
        self.assertSequenceEqual(
            [
                {"label": "Test 1", "description": "This is a test"},
                {"label": "Test 2", "description": "This is also a test"},
            ],
            values,
        )
        names, values = zip(*TestDictChoices.model_choices)
        self.assertSequenceEqual(["TEST_1", "TEST_2"], names)
        self.assertSequenceEqual(["This is a test", "This is also a test"], values)

    def test_DictChoices_with_labels_declaration(self):
        class TestDictChoices(DictChoices):
            TEST_1 = (
                "TEST_LABEL_1",
                {
                    "label": "Test 1",
                    "description": "This is a test",
                },
            )
            TEST_2 = (
                "TEST_LABEL_2",
                {
                    "label": "Test 2",
                    "description": "This is also a test",
                },
            )

            @staticmethod
            def _human_readable_name(enum_item):
                return enum_item.label["description"]

        names, values = zip(*TestDictChoices.choices)
        self.assertSequenceEqual(["TEST_LABEL_1", "TEST_LABEL_2"], names)
        self.assertSequenceEqual(
            [
                {"label": "Test 1", "description": "This is a test"},
                {"label": "Test 2", "description": "This is also a test"},
            ],
            values,
        )
        names, values = zip(*TestDictChoices.model_choices)
        self.assertSequenceEqual(["TEST_1", "TEST_2"], names)
        self.assertSequenceEqual(["This is a test", "This is also a test"], values)

    def test_TextChoicesEnum_with_simple_declaration(self):
        class TestTextChoicesEnum(TextChoicesEnum):
            TEST_1 = "Test 1"
            TEST_2 = "Test 2"

        names, values = zip(*TestTextChoicesEnum.choices)
        self.assertSequenceEqual(["TEST_1", "TEST_2"], names)
        self.assertSequenceEqual(
            ["Test 1", "Test 2"],
            values,
        )

    def test_TextChoicesEnum_with_labels_declaration(self):
        class TestTextChoicesEnum(TextChoicesEnum):
            TEST_1 = ("TEST_LABEL_1", "Test 1")
            TEST_2 = ("TEST_LABEL_2", "Test 2")

        names, values = zip(*TestTextChoicesEnum.choices)
        self.assertSequenceEqual(["TEST_LABEL_1", "TEST_LABEL_2"], names)
        self.assertSequenceEqual(
            ["Test 1", "Test 2"],
            values,
        )

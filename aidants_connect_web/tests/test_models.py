from django.test import TestCase
from django.db.utils import IntegrityError
from aidants_connect_web.models import Connection, User, Usager, Mandat
from datetime import date


class ConnectionModelTest(TestCase):
    def test_saving_and_retrieving_connexion(self):
        first_connexion = Connection()
        first_connexion.state = "aZeRtY"
        first_connexion.code = "ert"
        first_connexion.nonce = "varg"
        first_connexion.save()

        second_connexion = Connection()
        second_connexion.state = "QsDfG"
        second_connexion.save()

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.state, "aZeRtY")
        self.assertEqual(first_saved_item.nonce, "varg")
        self.assertEqual(second_saved_item.state, "QsDfG")


class UsagerModelTest(TestCase):
    def test_saving_and_retrieving_usager(self):
        first_usager = Usager()
        first_usager.given_name = "TEST NAME"
        first_usager.family_name = "TEST Family Name éèà"
        first_usager.preferred_username = "I prefer being called this"
        first_usager.birthdate = date(1902, 6, 30)
        first_usager.gender = "female"
        first_usager.birthplace = 27681
        first_usager.birthcountry = 99100
        first_usager.email = "user@test.user"
        first_usager.sub = "1233"
        first_usager.save()

        second_usager = Usager()
        second_usager.given_name = "TEST SECOND NAME"
        second_usager.family_name = "TEST Family Name éèà"
        second_usager.preferred_username = "I prefer being called this"
        second_usager.birthdate = date(1945, 10, 20)
        second_usager.gender = "male"
        second_usager.birthplace = 84016
        second_usager.birthcountry = 99100
        second_usager.email = "other_user@test.user"
        second_usager.sub = "1234"
        second_usager.save()

        saved_items = Usager.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.given_name, "TEST NAME")
        self.assertEqual(str(first_saved_item.birthdate), "1902-06-30")
        self.assertEqual(second_saved_item.family_name, "TEST Family Name éèà")


class MandatModelTest(TestCase):
    def test_saving_and_retrieving_mandat(self):
        first_mandat = Mandat()
        first_mandat.aidant = User.objects.create(username="Marge")

        first_mandat.usager = Usager.objects.create(
            given_name="Homer",
            family_name="Simpson",
            birthdate="1902-06-30",
            gender="male",
            birthplace=27681,
            birthcountry=99100,
            email="homer@simpson.com",
            sub="123",
        )
        first_mandat.perimeter = ["Carte grise", "Changement d'adresse"]
        first_mandat.duration = 3
        first_mandat.save()

        second_mandat = Mandat()
        second_mandat.aidant = User.objects.create(username="Patricia")
        second_mandat.usager = Usager.objects.create(
            given_name="Ned",
            family_name="Flanders",
            birthdate="1902-06-30",
            gender="male",
            birthplace=26934,
            birthcountry=99100,
            email="ned@flanders.com",
            sub="1234",
        )
        second_mandat.perimeter = ["Revenus"]
        second_mandat.duration = 6
        second_mandat.save()

        saved_items = Mandat.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.aidant.username, "Marge")
        self.assertEqual(
            first_saved_item.perimeter, ["Carte grise", "Changement d'adresse"]
        )
        self.assertEqual(second_saved_item.usager.family_name, "Flanders")


class UserModelTest(TestCase):
    def test_what_happens_to_password_when_not_set(self):
        aidant = User.objects.create(username="Marge")
        self.assertEqual(aidant.password, "")

    def test_what_happens_when_username_not_set(self):
        aidant = User.objects.create()
        self.assertEqual(aidant.username, "")

    def test_what_happens_when_a_user_tries_to_use_same_username(self):
        User.objects.create(username="Marge")
        self.assertRaises(IntegrityError, User.objects.create, username="Marge")

    def test_aidant_fills_all_the_information(self):
        self.assertEqual(len(User.objects.all()), 0)
        User.objects.create(username="bhameau@domain.user")
        self.assertEqual(len(User.objects.all()), 1)
        User.objects.create(username="cgireau@domain.user")
        self.assertEqual(len(User.objects.all()), 2)

from datetime import date, datetime, timedelta
from freezegun import freeze_time
from pytz import timezone as pytz_timezone

from django.test import TestCase, tag
from django.db.utils import IntegrityError
from django.utils import timezone

from aidants_connect_web.models import (
    Connection,
    Aidant,
    Usager,
    Mandat,
    Journal,
    Organisation,
)
from aidants_connect_web.tests.factories import (
    UserFactory,
    UsagerFactory,
    OrganisationFactory,
)


@tag("models")
class ConnectionModelTest(TestCase):
    def test_saving_and_retrieving_connexion(self):
        first_connexion = Connection()
        first_connexion.state = "aZeRtY"
        first_connexion.code = "ert"
        first_connexion.nonce = "varg"
        first_connexion.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate="1969-12-15",
            gender="female",
            birthplace="70447",
            birthcountry="99100",
            sub="123",
            email="User@user.domain",
        )
        first_connexion.save()

        second_connexion = Connection()
        second_connexion.state = "QsDfG"
        second_connexion.usager = Usager.objects.create(
            given_name="Fabrice",
            family_name="MERCIER",
            preferred_username="TROIS",
            birthdate="1981-07-27",
            gender="male",
            birthplace="70447",
            birthcountry="99100",
            sub="124",
            email="User@user.domain",
        )
        second_connexion.save()

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.state, "aZeRtY")
        self.assertEqual(first_saved_item.nonce, "varg")
        self.assertEqual(first_saved_item.usager.given_name, "Joséphine")
        self.assertEqual(second_saved_item.state, "QsDfG")
        self.assertEqual(second_saved_item.usager.gender, "male")


@tag("models")
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


@tag("models")
class MandatModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = UserFactory(username="Marge")
        cls.aidant_patricia = UserFactory(username="Patricia")
        cls.usager_homer = Usager.objects.create(
            given_name="Homer",
            family_name="Simpson",
            birthdate="1902-06-30",
            gender="male",
            birthplace=27681,
            birthcountry=99100,
            email="homer@simpson.com",
            sub="123",
        )
        cls.usager_ned = Usager.objects.create(
            given_name="Ned",
            family_name="Flanders",
            birthdate="1902-06-30",
            gender="male",
            birthplace=26934,
            birthcountry=99100,
            email="ned@flanders.com",
            sub="1234",
        )

    def test_saving_and_retrieving_mandat(self):
        first_mandat = Mandat.objects.create(
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Carte grise",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        second_mandat = Mandat.objects.create(
            aidant=self.aidant_patricia,
            usager=self.usager_ned,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        self.assertEqual(Mandat.objects.count(), 2)

        journal_entries = Journal.objects.all()
        self.assertEqual(journal_entries.count(), 2)
        self.assertEqual(journal_entries[0].action, "create_mandat")
        self.assertEqual(journal_entries[1].action, "create_mandat")

        self.assertEqual(first_mandat.aidant.username, "Marge")
        self.assertEqual(first_mandat.demarche, "Carte grise")
        self.assertEqual(second_mandat.usager.family_name, "Flanders")

    def test_cannot_have_two_mandat_for_user_demarche_tuple(self):
        Mandat.objects.create(
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Logement",
            expiration_date=timezone.now() + timedelta(days=3),
        )
        self.assertEqual(Mandat.objects.count(), 1)

        self.assertRaises(
            IntegrityError,
            Mandat.objects.create,
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Logement",
            expiration_date=timezone.now() + timedelta(days=6),
        )

    fake_date = datetime(2019, 1, 14, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(fake_date)
    def test_mandat_expiration_date_setting(self):
        mandat_1 = Mandat.objects.create(
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Carte grise",
            expiration_date=timezone.now() + timedelta(days=3),
        )
        self.assertEqual(
            mandat_1.creation_date,
            datetime(2019, 1, 14, tzinfo=pytz_timezone("Europe/Paris")),
        )
        self.assertEqual(
            mandat_1.expiration_date,
            datetime(2019, 1, 17, tzinfo=pytz_timezone("Europe/Paris")),
        )


@tag("models")
class OrganisationModelTest(TestCase):
    def test_create_and_retrieve_organisation(self):
        Organisation.objects.create(
            name="Girard S.A.R.L",
            siret="123",
            address="3 rue du chat, 27120 Houlbec-Cocherel",
        )
        self.assertEqual(Organisation.objects.count(), 1)
        organisation = Organisation.objects.all()[0]
        self.assertEqual(organisation.name, "Girard S.A.R.L")
        self.assertEqual(organisation.address, "3 rue du chat, 27120 Houlbec-Cocherel")


@tag("models", "aidant")
class AidantModelTest(TestCase):
    def test_what_happens_to_password_when_not_set(self):
        aidant = Aidant.objects.create(username="Marge")
        self.assertEqual(aidant.password, "")

    def test_what_happens_when_username_not_set(self):
        aidant = Aidant.objects.create()
        self.assertEqual(aidant.username, "")

    def test_what_happens_when_an_aidant_tries_to_use_same_username(self):
        Aidant.objects.create(username="Marge")
        self.assertRaises(IntegrityError, Aidant.objects.create, username="Marge")

    def test_aidant_fills_all_the_information(self):
        self.assertEqual(len(Aidant.objects.all()), 0)
        Aidant.objects.create(username="bhameau@domain.user")
        self.assertEqual(len(Aidant.objects.all()), 1)
        Aidant.objects.create(username="cgireau@domain.user")
        self.assertEqual(len(Aidant.objects.all()), 2)

    def test_get_aidant_organization(self):
        orga = Organisation.objects.create(
            name="COMMUNE DE HOULBEC COCHEREL",
            siret=123,
            address="45 avenue du Général de Gaulle, 90210 Beverly Hills",
        )
        aidant = Aidant.objects.create(
            username="bhameau@domain.user", organisation=orga
        )
        self.assertEqual(aidant.organisation.name, "COMMUNE DE HOULBEC COCHEREL")


@tag("models", "aidant")
class AidantModelMethodsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = UserFactory(username="Marge")
        cls.aidant_patricia = UserFactory(username="Patricia")
        cls.usager_homer = UsagerFactory(given_name="Homer", sub="123")
        cls.usager_ned = UsagerFactory(given_name="Ned", sub="1234")
        cls.usager_bart = UsagerFactory(given_name="Bart", sub="1235")
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="Carte grise",
            expiration_date=timezone.now() - timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="social",
            expiration_date=timezone.now() + timedelta(days=365),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="Logement",
            expiration_date=timezone.now() - timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="transports",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="famille",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="social",
            expiration_date=timezone.now() + timedelta(days=6),
        )
        Mandat.objects.create(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="travail",
            expiration_date=timezone.now() + timedelta(days=6),
        )

    def test_get_usagers(self):
        self.assertEqual(len(self.aidant_marge.get_usagers()), 2)
        self.assertEqual(len(self.aidant_patricia.get_usagers()), 0)

    def test_active_usagers(self):
        active_usagers = Usager.objects.active()
        self.assertEqual(len(active_usagers), 2)

    def test_get_usagers_with_active_mandat(self):
        self.assertEqual(len(self.aidant_marge.get_usagers_with_active_mandat()), 2)
        self.assertEqual(len(self.aidant_patricia.get_usagers_with_active_mandat()), 0)

    def test_get_active_mandats_for_usager(self):
        self.assertEqual(
            len(self.aidant_marge.get_active_mandats_for_usager(self.usager_homer)), 2
        )
        self.assertEqual(
            len(self.aidant_marge.get_active_mandats_for_usager(self.usager_ned)), 4
        )
        self.assertEqual(
            len(self.aidant_marge.get_active_mandats_for_usager(self.usager_bart)), 0
        )

    def test_get_expired_mandats_for_usager(self):
        self.assertEqual(
            len(self.aidant_marge.get_expired_mandats_for_usager(self.usager_homer)), 1
        )
        self.assertEqual(
            len(self.aidant_marge.get_expired_mandats_for_usager(self.usager_ned)), 1
        )
        self.assertEqual(
            len(self.aidant_marge.get_expired_mandats_for_usager(self.usager_bart)), 0
        )

    def test_get_active_demarches_for_usager(self):
        self.assertEqual(
            list(self.aidant_marge.get_active_demarches_for_usager(self.usager_homer)),
            ["Revenus", "social"],
        )
        self.assertEqual(
            list(self.aidant_marge.get_active_demarches_for_usager(self.usager_ned)),
            ["famille", "social", "transports", "travail"],
        )


@tag("models", "journal")
class JournalModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.entry1 = Journal.objects.create(action="connect_aidant", initiator="ABC")
        cls.aidant_thierry = Aidant.objects.create_user(
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
            organisation=OrganisationFactory(name="Commune de Vernon"),
        )
        cls.usager_ned = Usager.objects.create(
            given_name="Ned",
            family_name="Flanders",
            birthdate="1902-06-30",
            gender="male",
            birthplace=26934,
            birthcountry=99100,
            email="ned@flanders.com",
            sub="1234",
        )

        cls.first_mandat = Mandat.objects.create(
            aidant=cls.aidant_thierry,
            usager=cls.usager_ned,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )

    def test_a_journal_entry_can_be_created(self):
        # Aidant connects and first mandat is created
        self.assertEqual(len(Journal.objects.all()), 2)

    def test_logging_of_aidant_conection(self):
        entry = Journal.objects.connection(aidant=self.aidant_thierry)
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "connect_aidant")
        self.assertEqual(
            entry.initiator, "Thierry Martin - Commune de Vernon - thierry@thierry.com"
        )

    def test_log_mandat_creation_complete(self):
        mandat = Mandat.objects.create(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="logement",
            expiration_date=timezone.now() + timedelta(days=365),
        )

        self.assertEqual(len(Journal.objects.all()), 3)

        entry = Journal.objects.all().last()
        self.assertEqual(entry.action, "create_mandat")
        self.assertIn("Ned Flanders", entry.usager)
        self.assertEqual(entry.mandat, mandat.id)

    def test_log_mandat_use_complete(self):
        entry = Journal.objects.mandat_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            mandat=self.first_mandat,
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "use_mandat")
        self.assertEqual(entry.demarche, "transports")

    def test_it_is_impossible_to_change_an_existing_entry(self):
        entry = Journal.objects.mandat_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            mandat=self.first_mandat,
        )

        entry.demarches = ["logement"]
        self.assertRaises(NotImplementedError, lambda: entry.save())
        self.assertEqual(Journal.objects.get(id=entry.id).demarche, "transports")

    def test_it_is_impossible_to_delete_an_existing_entry(self):
        entry = Journal.objects.mandat_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            mandat=self.first_mandat,
        )

        self.assertRaises(NotImplementedError, lambda: entry.delete())
        self.assertEqual(Journal.objects.get(id=entry.id).demarche, "transports")

    def test_a_print_mandat_journal_entry_can_be_created(self):
        entry = Journal.objects.mandat_papier(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarches=["transports", "logement"],
            expiration_date=timezone.now() + timedelta(days=6),
        )

        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "print_mandat")
        self.assertEqual(entry.hash_data["demarches_list"], "logement,transports")

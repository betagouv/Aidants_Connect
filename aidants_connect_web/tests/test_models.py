from datetime import date, datetime, timedelta

from django.db.utils import IntegrityError
from django.test import tag, TestCase
from django.utils import timezone
from django.conf import settings

from freezegun import freeze_time
from pytz import timezone as pytz_timezone

from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    Connection,
    Journal,
    Organisation,
    Usager,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    MandatFactory,
    AutorisationFactory,
    OrganisationFactory,
    UsagerFactory,
)
from aidants_connect_web.utilities import (
    generate_file_sha256_hash,
    validate_attestation_hash,
)
from aidants_connect_web.views.new_mandat import generate_attestation_hash


@tag("models")
class ConnectionModelTests(TestCase):
    def test_saving_and_retrieving_connection(self):
        first_connection = Connection()
        first_connection.state = "aZeRtY"
        first_connection.code = "ert"
        first_connection.nonce = "varg"
        first_connection.usager = UsagerFactory(given_name="Joséphine")
        first_connection.save()

        second_connection = Connection()
        second_connection.state = "QsDfG"
        second_connection.usager = UsagerFactory(given_name="Fabrice")
        second_connection.save()

        saved_items = Connection.objects.all()
        self.assertEqual(saved_items.count(), 2)

        first_saved_item = saved_items[0]
        second_saved_item = saved_items[1]

        self.assertEqual(first_saved_item.state, "aZeRtY")
        self.assertEqual(first_saved_item.nonce, "varg")
        self.assertEqual(first_saved_item.usager.given_name, "Joséphine")
        self.assertEqual(second_saved_item.state, "QsDfG")
        self.assertEqual(second_saved_item.usager.gender, Usager.GENDER_MALE)


@tag("models")
class UsagerModelTests(TestCase):
    def test_usager_with_null_birthplace(self):
        first_usager = Usager()
        first_usager.given_name = "TEST NAME"
        first_usager.family_name = "TEST Family Name éèà"
        first_usager.preferred_username = "I prefer being called this"
        first_usager.birthdate = date(1902, 6, 30)
        first_usager.gender = Usager.GENDER_FEMALE
        first_usager.birthplace = None
        first_usager.birthcountry = Usager.BIRTHCOUNTRY_FRANCE
        first_usager.email = "user@test.user"
        first_usager.sub = "1233"
        first_usager.save()
        saved_items = Usager.objects.all()
        self.assertEqual(saved_items.count(), 1)

    def test_saving_and_retrieving_usager(self):
        first_usager = Usager()
        first_usager.given_name = "TEST NAME"
        first_usager.family_name = "TEST Family Name éèà"
        first_usager.preferred_username = "I prefer being called this"
        first_usager.birthdate = date(1902, 6, 30)
        first_usager.gender = Usager.GENDER_FEMALE
        first_usager.birthplace = "27681"
        first_usager.birthcountry = Usager.BIRTHCOUNTRY_FRANCE
        first_usager.email = "user@test.user"
        first_usager.sub = "1233"
        first_usager.save()

        second_usager = Usager()
        second_usager.given_name = "TEST SECOND NAME"
        second_usager.family_name = "TEST Family Name éèà"
        second_usager.preferred_username = "I prefer being called this"
        second_usager.birthdate = date(1945, 10, 20)
        second_usager.gender = Usager.GENDER_MALE
        second_usager.birthplace = "84016"
        second_usager.birthcountry = Usager.BIRTHCOUNTRY_FRANCE
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
        self.assertEqual(second_usager.sub, "1234")

    def test_normalize_birthplace(self):
        usager = UsagerFactory(birthplace="123")
        usager.normalize_birthplace()
        self.assertEqual(usager.birthplace, "00123")

        usager = UsagerFactory(birthplace="1234")
        usager.normalize_birthplace()
        self.assertEqual(usager.birthplace, "01234")

        usager = UsagerFactory(birthplace="12345")
        usager.normalize_birthplace()
        self.assertEqual(usager.birthplace, "12345")


@tag("models")
class AutorisationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = AidantFactory(username="Marge")
        cls.aidant_patricia = AidantFactory(username="Patricia")
        cls.usager_homer = UsagerFactory(given_name="Homer")
        cls.usager_ned = UsagerFactory(family_name="Flanders")

    def test_saving_and_retrieving_autorisation(self):
        first_autorisation = AutorisationFactory(
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Carte grise",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        second_autorisation = AutorisationFactory(
            aidant=self.aidant_patricia,
            usager=self.usager_ned,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        self.assertEqual(Autorisation.objects.count(), 2)

        journal_entries = Journal.objects.all()
        self.assertEqual(journal_entries.count(), 2)
        self.assertEqual(journal_entries[0].action, "create_autorisation")
        self.assertEqual(journal_entries[1].action, "create_autorisation")

        self.assertEqual(first_autorisation.aidant.username, "Marge")
        self.assertEqual(first_autorisation.demarche, "Carte grise")
        self.assertEqual(second_autorisation.usager.family_name, "Flanders")

    fake_date = datetime(2019, 1, 14, tzinfo=pytz_timezone("Europe/Paris"))

    @freeze_time(fake_date)
    def test_autorisation_expiration_date_setting(self):
        autorisation_1 = AutorisationFactory(
            aidant=self.aidant_marge,
            usager=self.usager_homer,
            demarche="Carte grise",
            expiration_date=timezone.now() + timedelta(days=3),
        )
        self.assertEqual(
            autorisation_1.creation_date,
            datetime(2019, 1, 14, tzinfo=pytz_timezone("Europe/Paris")),
        )
        self.assertEqual(
            autorisation_1.expiration_date,
            datetime(2019, 1, 17, tzinfo=pytz_timezone("Europe/Paris")),
        )


@tag("models")
class OrganisationModelTests(TestCase):
    def test_create_and_retrieve_organisation(self):
        OrganisationFactory(
            name="Girard S.A.R.L",
            siret="123",
            address="3 rue du chat, 27120 Houlbec-Cocherel",
        )
        self.assertEqual(Organisation.objects.count(), 1)
        organisation = Organisation.objects.all()[0]
        self.assertEqual(organisation.name, "Girard S.A.R.L")
        self.assertEqual(organisation.address, "3 rue du chat, 27120 Houlbec-Cocherel")


@tag("models", "aidant")
class AidantModelTests(TestCase):
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
        AidantFactory(username="bhameau@domain.user")
        self.assertEqual(len(Aidant.objects.all()), 1)
        AidantFactory(username="cgireau@domain.user")
        self.assertEqual(len(Aidant.objects.all()), 2)

    def test_get_aidant_organization(self):
        orga = OrganisationFactory(
            name="COMMUNE DE HOULBEC COCHEREL",
            siret=123,
            address="45 avenue du Général de Gaulle, 90210 Beverly Hills",
        )
        aidant = AidantFactory(username="bhameau@domain.user", organisation=orga)
        self.assertEqual(aidant.organisation.name, "COMMUNE DE HOULBEC COCHEREL")


@tag("models", "aidant")
class AidantModelMethodsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = AidantFactory(username="Marge")
        cls.aidant_lisa = AidantFactory(
            username="Lisa", organisation=cls.aidant_marge.organisation
        )
        cls.aidant_patricia = AidantFactory(username="Patricia")
        cls.usager_homer = UsagerFactory(given_name="Homer")
        cls.usager_ned = UsagerFactory(given_name="Ned")
        cls.usager_bart = UsagerFactory(given_name="Bart")
        cls.mandat_marge_homer_1 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        cls.mandat_marge_homer_2 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.mandat_marge_homer_3 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        cls.mandat_marge_ned_1 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        cls.mandat_marge_ned_2 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="Carte grise",
            mandat=cls.mandat_marge_homer_1,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="Revenus",
            mandat=cls.mandat_marge_homer_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
            demarche="social",
            mandat=cls.mandat_marge_homer_3,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="Logement",
            mandat=cls.mandat_marge_ned_1,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="transports",
            mandat=cls.mandat_marge_ned_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="famille",
            mandat=cls.mandat_marge_ned_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="social",
            mandat=cls.mandat_marge_ned_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="travail",
            mandat=cls.mandat_marge_ned_2,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            aidant=cls.aidant_marge,
            usager=cls.usager_ned,
            demarche="papiers",
            mandat=cls.mandat_marge_ned_2,
            expiration_date=timezone.now() + timedelta(days=6),
            revocation_date=timezone.now(),
        )

    def test_get_usagers(self):
        self.assertEqual(len(self.aidant_marge.get_usagers()), 2)
        self.assertEqual(len(self.aidant_lisa.get_usagers()), 2)
        self.assertEqual(len(self.aidant_patricia.get_usagers()), 0)

    def test_active_usagers(self):
        active_usagers = Usager.objects.active()
        self.assertEqual(len(active_usagers), 2)

    def test_get_usagers_with_active_autorisation(self):
        self.assertEqual(
            len(self.aidant_marge.get_usagers_with_active_autorisation()), 2
        )
        self.assertEqual(
            len(self.aidant_lisa.get_usagers_with_active_autorisation()), 2
        )
        self.assertEqual(
            len(self.aidant_patricia.get_usagers_with_active_autorisation()), 0
        )

    def test_get_active_autorisations_for_usager(self):
        self.assertEqual(
            len(
                self.aidant_marge.get_active_autorisations_for_usager(self.usager_homer)
            ),
            2,
        )
        self.assertEqual(
            len(self.aidant_marge.get_active_autorisations_for_usager(self.usager_ned)),
            4,
        )
        self.assertEqual(
            len(
                self.aidant_marge.get_active_autorisations_for_usager(self.usager_bart)
            ),
            0,
        )
        self.assertEqual(
            len(
                self.aidant_lisa.get_active_autorisations_for_usager(self.usager_homer)
            ),
            2,
        )
        self.assertEqual(
            len(self.aidant_lisa.get_active_autorisations_for_usager(self.usager_ned)),
            4,
        )
        self.assertEqual(
            len(self.aidant_lisa.get_active_autorisations_for_usager(self.usager_bart)),
            0,
        )

    def test_get_inactive_autorisations_for_usager(self):
        self.assertEqual(
            len(
                self.aidant_marge.get_inactive_autorisations_for_usager(
                    self.usager_homer
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                self.aidant_marge.get_inactive_autorisations_for_usager(self.usager_ned)
            ),
            2,
        )
        self.assertEqual(
            len(
                self.aidant_marge.get_inactive_autorisations_for_usager(
                    self.usager_bart
                )
            ),
            0,
        )
        self.assertEqual(
            len(
                self.aidant_lisa.get_inactive_autorisations_for_usager(
                    self.usager_homer
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                self.aidant_lisa.get_inactive_autorisations_for_usager(self.usager_ned)
            ),
            2,
        )
        self.assertEqual(
            len(
                self.aidant_lisa.get_inactive_autorisations_for_usager(self.usager_bart)
            ),
            0,
        )

    def test_get_active_demarches_for_usager(self):
        self.assertCountEqual(
            list(self.aidant_marge.get_active_demarches_for_usager(self.usager_homer)),
            ["Revenus", "social"],
        )
        self.assertCountEqual(
            list(self.aidant_marge.get_active_demarches_for_usager(self.usager_ned)),
            ["famille", "social", "transports", "travail"],
        )
        self.assertCountEqual(
            list(self.aidant_lisa.get_active_demarches_for_usager(self.usager_homer)),
            ["Revenus", "social"],
        )
        self.assertCountEqual(
            list(self.aidant_lisa.get_active_demarches_for_usager(self.usager_ned)),
            ["famille", "social", "transports", "travail"],
        )


@tag("models", "journal")
class JournalModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.entry1 = Journal.objects.create(action="connect_aidant", initiator="ABC")
        cls.aidant_thierry = AidantFactory(
            username="Thierry",
            email="thierry@thierry.com",
            first_name="Thierry",
            last_name="Martin",
            organisation=OrganisationFactory(name="Commune de Vernon"),
        )
        cls.usager_ned = UsagerFactory(given_name="Ned", family_name="Flanders")

        cls.first_autorisation = AutorisationFactory(
            aidant=cls.aidant_thierry,
            usager=cls.usager_ned,
            demarche="Revenus",
            expiration_date=timezone.now() + timedelta(days=6),
        )

    def test_a_journal_entry_can_be_created(self):
        # Aidant connects and first autorisation is created
        self.assertEqual(len(Journal.objects.all()), 2)

    def test_logging_of_aidant_conection(self):
        entry = Journal.objects.connection(aidant=self.aidant_thierry)
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "connect_aidant")
        self.assertEqual(
            entry.initiator, "Thierry Martin - Commune de Vernon - thierry@thierry.com"
        )

    def test_a_franceconnect_usager_journal_entry_can_be_created(self):
        entry = Journal.objects.franceconnection_usager(
            aidant=self.aidant_thierry, usager=self.usager_ned,
        )

        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "franceconnect_usager")

    def test_log_autorisation_creation_complete(self):
        autorisation = AutorisationFactory(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="logement",
            expiration_date=timezone.now() + timedelta(days=365),
        )

        journal_entries = Journal.objects.all()
        self.assertEqual(len(journal_entries), 3)

        last_entry = journal_entries.last()
        self.assertEqual(last_entry.action, "create_autorisation")
        self.assertIn("Ned Flanders", last_entry.usager)
        self.assertEqual(last_entry.autorisation, autorisation.id)

    def test_log_autorisation_use_complete(self):
        entry = Journal.objects.autorisation_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            autorisation=self.first_autorisation,
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "use_autorisation")
        self.assertEqual(entry.demarche, "transports")

    def test_log_autorisation_update_complete(self):
        entry = Journal.objects.autorisation_update(
            autorisation=self.first_autorisation, aidant=self.aidant_thierry
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "update_autorisation")

    def test_log_autorisation_cancel_complete(self):
        entry = Journal.objects.autorisation_cancel(
            autorisation=self.first_autorisation, aidant=self.aidant_thierry
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "cancel_autorisation")

    def test_it_is_impossible_to_change_an_existing_entry(self):
        entry = Journal.objects.autorisation_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            autorisation=self.first_autorisation,
        )

        entry.demarches = ["logement"]
        self.assertRaises(NotImplementedError, entry.save)
        self.assertEqual(Journal.objects.get(id=entry.id).demarche, "transports")

    def test_it_is_impossible_to_delete_an_existing_entry(self):
        entry = Journal.objects.autorisation_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            autorisation=self.first_autorisation,
        )

        self.assertRaises(NotImplementedError, entry.delete)
        self.assertEqual(Journal.objects.get(id=entry.id).demarche, "transports")

    def test_a_create_attestation_journal_entry_can_be_created(self):
        demarches = ["transports", "logement"]
        expiration_date = timezone.now() + timedelta(days=6)
        entry = Journal.objects.attestation(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarches=demarches,
            duree=6,
            is_remote_mandat=False,
            access_token="fjfgjfdkldlzlsmqqxxcn",
            attestation_hash=generate_attestation_hash(
                self.aidant_thierry, self.usager_ned, demarches, expiration_date
            ),
        )

        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "create_attestation")

        attestation_string = ";".join(
            [
                str(self.aidant_thierry.id),
                date.today().isoformat(),
                "logement,transports",
                expiration_date.date().isoformat(),
                str(self.aidant_thierry.organisation.id),
                generate_file_sha256_hash(settings.MANDAT_TEMPLATE_PATH),
                self.usager_ned.sub,
            ]
        )
        self.assertTrue(
            validate_attestation_hash(attestation_string, entry.attestation_hash)
        )

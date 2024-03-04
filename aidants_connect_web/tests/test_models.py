from datetime import date, datetime, timedelta
from os.path import join as path_join
from unittest.mock import Mock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase, tag
from django.utils import timezone
from django.utils.timezone import now

from dateutil.relativedelta import relativedelta
from django_otp.plugins.otp_totp.models import TOTPDevice
from freezegun import freeze_time
from phonenumbers import PhoneNumberFormat, format_number
from phonenumbers import parse as parse_number

from aidants_connect_common.utils.constants import JournalActionKeywords
from aidants_connect_habilitation.tests.factories import AidantRequestFactory
from aidants_connect_web.constants import (
    ReferentRequestStatuses,
    RemoteConsentMethodChoices,
)
from aidants_connect_web.models import (
    Aidant,
    Autorisation,
    CarteTOTP,
    Connection,
    HabilitationRequest,
    Journal,
    Mandat,
    Notification,
    Organisation,
    OrganisationType,
    Usager,
)
from aidants_connect_web.models.other_models import FormationAttendant
from aidants_connect_web.tests.factories import (
    AidantFactory,
    AttestationJournalFactory,
    AutorisationFactory,
    CarteTOTPFactory,
    CoReferentNonAidantRequestFactory,
    FormationFactory,
    HabilitationRequestFactory,
    JournalFactory,
    MandatFactory,
    NotificationFactory,
    OrganisationFactory,
    OrganisationTypeFactory,
    RevokedMandatFactory,
    UsagerFactory,
)
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    generate_file_sha256_hash,
    validate_attestation_hash,
)


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

    def test_save_prevents_saving_invalid_number(self):
        connection = Connection()
        connection.state = "aZeRtY"
        connection.code = "ert"
        connection.nonce = "varg"
        connection.usager = UsagerFactory(given_name="Joséphine")
        connection.remote_constent_method = RemoteConsentMethodChoices.SMS
        connection.consent_request_id = str(uuid4())
        connection.user_phone = "665544"

        with self.assertRaises(IntegrityError) as cm:
            connection.save()

        self.assertEqual(
            "Phone number 665544 is not valid in any of "
            f"the french region among {settings.FRENCH_REGION_CODES}",
            str(cm.exception),
        )

    def test_save_lets_saving_valid_number(self):
        connection = Connection()
        connection.state = "aZeRtY"
        connection.code = "ert"
        connection.nonce = "varg"
        connection.usager = UsagerFactory(given_name="Joséphine")
        connection.remote_constent_method = RemoteConsentMethodChoices.SMS
        connection.consent_request_id = str(uuid4())
        # Valid Pierre-er-Miquelon number of Miquelon-Langlade's town hall
        connection.user_phone = "41 05 60"

        connection.save()
        connection.refresh_from_db()

        self.assertEqual("+508410560", str(connection.user_phone))


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

    def test_active_usager_excludes_usager_with_revoked_mandats(self):
        usager = UsagerFactory()
        mandat_1 = MandatFactory(usager=usager)
        AutorisationFactory(
            mandat=mandat_1,
            demarche="justice",
            revocation_date=timezone.now() - timedelta(minutes=1),
        )
        usagers = Usager.objects.all()
        self.assertEqual(usagers.count(), 1)
        self.assertEqual(usagers.active().count(), 0)

    def test_active_usager_excludes_usager_with_expired_mandats(self):
        usager = UsagerFactory()
        mandat_1 = MandatFactory(
            usager=usager, expiration_date=timezone.now() - timedelta(minutes=1)
        )
        AutorisationFactory(mandat=mandat_1, demarche="justice")
        usagers = Usager.objects.all()
        self.assertEqual(usagers.count(), 1)
        self.assertEqual(usagers.active().count(), 0)


@tag("models")
class MandatModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation_1 = OrganisationFactory()
        cls.aidant_1 = AidantFactory()

        cls.usager_1 = UsagerFactory()
        cls.mandat_1 = Mandat.objects.create(
            organisation=cls.organisation_1,
            usager=cls.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        AutorisationFactory(
            mandat=cls.mandat_1,
            demarche="justice",
        )

        cls.usager_2 = UsagerFactory(sub="anothersub")
        cls.mandat_2 = Mandat.objects.create(
            organisation=cls.organisation_1,
            usager=cls.usager_2,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        AutorisationFactory(
            mandat=cls.mandat_2,
            demarche="argent",
        )
        AutorisationFactory(
            mandat=cls.mandat_2,
            demarche="transport",
        )

    def test_saving_and_retrieving_mandats(self):
        self.assertEqual(Mandat.objects.count(), 2)

    def test_save_prevents_saving_without_phone(self):
        usager = UsagerFactory(phone="")
        mandat = Mandat(
            organisation=self.organisation_1,
            usager=usager,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=1),
            remote_constent_method=RemoteConsentMethodChoices.SMS,
        )
        with self.assertRaises(IntegrityError) as cm:
            mandat.save()

        self.assertEqual(
            "User phone must be set when remote consent is SMS", str(cm.exception)
        )

    def test_mandat_can_have_one_autorisation(self):
        self.assertEqual(len(self.mandat_1.autorisations.all()), 1)

    def test_mandat_can_have_two_autorisations(self):
        self.assertEqual(len(self.mandat_2.autorisations.all()), 2)

    def test_active_queryset_method_exclude_fully_revoked_mandats(self):
        fully_revoked_mandat = Mandat.objects.create(
            organisation=self.organisation_1,
            usager=self.usager_2,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        AutorisationFactory(
            mandat=fully_revoked_mandat,
            demarche="papiers",
            revocation_date=timezone.now() - timedelta(minutes=1),
        )
        AutorisationFactory(
            mandat=fully_revoked_mandat,
            demarche="loisirs",
            revocation_date=timezone.now() - timedelta(minutes=1),
        )
        active_mandats = Mandat.objects.active().count()
        inactive_mandats = Mandat.objects.inactive().count()

        self.assertEqual(active_mandats, 2)
        self.assertEqual(inactive_mandats, 1)

    def test_active_queryset_method_include_partially_revoked_mandat(self):
        partially_revoked_mandat = Mandat.objects.create(
            organisation=self.organisation_1,
            usager=self.usager_2,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=1),
        )
        AutorisationFactory(
            mandat=partially_revoked_mandat,
            demarche="papiers",
            revocation_date=timezone.now() - timedelta(minutes=1),
        )
        AutorisationFactory(
            mandat=partially_revoked_mandat,
            demarche="loisirs",
        )
        active_mandats = Mandat.objects.active().count()
        inactive_mandats = Mandat.objects.inactive().count()

        self.assertEqual(active_mandats, 3)
        self.assertEqual(inactive_mandats, 0)

    def test_active_queryset_method_excludes_expired_mandat(self):
        expired_mandat = Mandat.objects.create(
            organisation=self.organisation_1,
            usager=self.usager_2,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() - timedelta(days=1),
        )
        AutorisationFactory(
            mandat=expired_mandat,
            demarche="papiers",
        )

        active_mandats = Mandat.objects.active().count()
        inactive_mandats = Mandat.objects.inactive().count()

        self.assertEqual(active_mandats, 2)
        self.assertEqual(inactive_mandats, 1)

    def test_revocation_date_valid_mandate_valid_auths(self):
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        for procedure in ["transports", "logement"]:
            Autorisation.objects.create(mandat=mandate, demarche=procedure)

        self.assertEqual(mandate.revocation_date, None)

    def test_revocation_date_valid_mandate_one_revoked_auth(self):
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        Autorisation.objects.create(
            mandat=mandate, demarche="transports", revocation_date=timezone.now()
        )
        Autorisation.objects.create(mandat=mandate, demarche="logement")

        self.assertEqual(mandate.revocation_date, None)

    def test_revocation_date_valid_mandate_all_revoked_auths(self):
        revocation_date = timezone.now()
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        for procedure in ["transports", "logement"]:
            Autorisation.objects.create(
                mandat=mandate, demarche=procedure, revocation_date=revocation_date
            )

        self.assertEqual(mandate.revocation_date, revocation_date)

    def was_explicitly_revoked_valid_mandate_valid_auths(self):
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        for procedure in ["transports", "logement"]:
            Autorisation.objects.create(mandat=mandate, demarche=procedure)

        self.assertEqual(mandate.was_explicitly_revoked, False)

    def was_explicitly_revoked_valid_mandate_one_revoked_auth(self):
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        Autorisation.objects.create(
            mandat=mandate, demarche="transports", revocation_date=timezone.now()
        )
        Autorisation.objects.create(mandat=mandate, demarche="logement")

        self.assertEqual(mandate.was_explicitly_revoked, False)

    def was_explicitly_revoked_valid_mandate_all_revoked_auths(self):
        revocation_date = timezone.now()
        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=timezone.now() + timedelta(days=6),
        )

        for procedure in ["transports", "logement"]:
            Autorisation.objects.create(
                mandat=mandate, demarche=procedure, revocation_date=revocation_date
            )

        self.assertEqual(mandate.was_explicitly_revoked, True)

    def test__get_template_path_from_journal_hash_nominal(self):
        tpl_name = "20200511_mandat.html"
        procedures = ["transports", "logement"]
        expiration_date = timezone.now() + timedelta(days=6)
        attestation_hash = generate_attestation_hash(
            self.aidant_1,
            self.usager_1,
            procedures,
            expiration_date,
            mandat_template_path=path_join(settings.MANDAT_TEMPLATE_DIR, tpl_name),
        )

        AttestationJournalFactory(
            aidant=self.aidant_1,
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            demarche=",".join(procedures),
            attestation_hash=attestation_hash,
        )

        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=expiration_date,
        )

        for procedure in procedures:
            Autorisation.objects.create(mandat=mandate, demarche=procedure)

            # Add another active mandate with auths so that we have a real life example
            other_mandate = MandatFactory(
                organisation=self.aidant_1.organisation, usager=self.usager_1
            )
            AutorisationFactory(mandat=other_mandate)

        result = mandate._get_mandate_template_path_from_journal_hash()

        self.assertEqual(result, f"aidants_connect_web/mandat_templates/{tpl_name}")

    def test__get_template_path_from_journal_hash_with_old_mandate(self):
        tpl_name = "20200511_mandat.html"
        procedures = ["transports", "logement"]
        expiration_date = timezone.now() - timedelta(days=6)
        creation_date = timezone.now() - timedelta(days=12)
        attestation_hash = generate_attestation_hash(
            self.aidant_1,
            self.usager_1,
            procedures,
            expiration_date,
            creation_date=creation_date.date().isoformat(),
            mandat_template_path=path_join(settings.MANDAT_TEMPLATE_DIR, tpl_name),
        )

        AttestationJournalFactory(
            aidant=self.aidant_1,
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            demarche=",".join(procedures),
            attestation_hash=attestation_hash,
            creation_date=creation_date,
        )

        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=creation_date,
            duree_keyword="SHORT",
            expiration_date=expiration_date,
        )

        for procedure in procedures:
            Autorisation.objects.create(
                mandat=mandate,
                demarche=procedure,
                revocation_date=timezone.now() - timedelta(days=6),
            )

            # Add another active mandate with auths so that we have a real life example
            other_mandate = MandatFactory(
                organisation=self.aidant_1.organisation, usager=self.usager_1
            )
            AutorisationFactory(mandat=other_mandate)

        result = mandate._get_mandate_template_path_from_journal_hash()

        self.assertEqual(result, f"aidants_connect_web/mandat_templates/{tpl_name}")

    def test__get_template_path_from_journal_hash_with_old_delegation(self):
        tpl_name = "20200511_mandat.html"
        procedures = ["transports", "logement"]
        expiration_date = timezone.now() + timedelta(days=6)
        attestation_hash = generate_attestation_hash(
            self.aidant_1,
            self.usager_1,
            procedures,
            expiration_date,
            mandat_template_path=path_join(settings.MANDAT_TEMPLATE_DIR, tpl_name),
        )

        old_attestation_hash = generate_attestation_hash(
            self.aidant_1,
            self.usager_1,
            procedures,
            expiration_date,
            mandat_template_path=path_join(
                settings.MANDAT_TEMPLATE_DIR, "20200201_mandat.html"
            ),
        )

        AttestationJournalFactory(
            aidant=self.aidant_1,
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            demarche=",".join(procedures),
            attestation_hash=attestation_hash,
        )

        AttestationJournalFactory(
            aidant=self.aidant_1,
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            demarche=",".join(procedures),
            attestation_hash=old_attestation_hash,
            creation_date=timezone.now() - timedelta(weeks=1),
        )

        mandate = Mandat.objects.create(
            organisation=self.aidant_1.organisation,
            usager=self.usager_1,
            creation_date=timezone.now(),
            duree_keyword="SHORT",
            expiration_date=expiration_date,
        )

        for procedure in procedures:
            Autorisation.objects.create(mandat=mandate, demarche=procedure)

            # Add another active mandate with auths so that we have a real life example
            other_mandate = MandatFactory(
                organisation=self.aidant_1.organisation, usager=self.usager_1
            )
            AutorisationFactory(mandat=other_mandate)

        result = mandate._get_mandate_template_path_from_journal_hash()

        self.assertEqual(result, f"aidants_connect_web/mandat_templates/{tpl_name}")


@tag("models")
class AutorisationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = AidantFactory()
        cls.aidant_patricia = AidantFactory()
        cls.usager_homer = UsagerFactory()
        cls.usager_ned = UsagerFactory(family_name="Flanders", sub="nedflanders")

        cls.mandat_marge_homer_6 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.mandat_patricia_ned_6 = MandatFactory(
            organisation=cls.aidant_patricia.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() + timedelta(days=6),
        )

    def test_saving_and_retrieving_autorisation(self):
        first_autorisation = AutorisationFactory(
            mandat=self.mandat_marge_homer_6,
            demarche="Carte grise",
        )
        second_autorisation = AutorisationFactory(
            mandat=self.mandat_patricia_ned_6,
            demarche="Revenus",
        )
        self.assertEqual(Autorisation.objects.count(), 2)

        self.assertEqual(
            first_autorisation.mandat.organisation,
            self.mandat_marge_homer_6.organisation,
        )
        self.assertEqual(first_autorisation.demarche, "Carte grise")
        self.assertEqual(second_autorisation.mandat.usager.family_name, "Flanders")

    fake_date = datetime(2019, 1, 14, tzinfo=ZoneInfo("Europe/Paris"))

    @freeze_time(fake_date)
    def test_autorisation_expiration_date_setting(self):
        mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=self.usager_homer,
            expiration_date=timezone.now() + timedelta(days=3),
        )
        autorisation = AutorisationFactory(
            mandat=mandat,
            demarche="Carte grise",
        )
        self.assertEqual(
            autorisation.creation_date,
            datetime(2019, 1, 14, tzinfo=ZoneInfo("Europe/Paris")),
        )
        self.assertEqual(
            autorisation.mandat.expiration_date,
            datetime(2019, 1, 17, tzinfo=ZoneInfo("Europe/Paris")),
        )

    def test_was_separately_revoked_auth_not_revoked(self):
        mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=self.usager_homer,
            expiration_date=timezone.now() + timedelta(days=3),
        )
        autorisation: Autorisation = AutorisationFactory(
            mandat=mandat,
            demarche="Carte grise",
        )

        self.assertFalse(autorisation.was_separately_revoked)

    def test_was_separately_revoked_mandate_not_revoked(self):
        mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=self.usager_homer,
            expiration_date=timezone.now() + timedelta(days=3),
        )

        AutorisationFactory(
            mandat=mandat,
            demarche="logement",
        )

        autorisation: Autorisation = AutorisationFactory(
            mandat=mandat, demarche="papiers", revocation_date=timezone.now()
        )

        self.assertTrue(autorisation.was_separately_revoked)

    def test_was_separately_revoked_mandate_revoked_false(self):
        mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=self.usager_homer,
            expiration_date=timezone.now() + timedelta(days=3),
        )

        AutorisationFactory(
            mandat=mandat, demarche="logement", revocation_date=timezone.now()
        )

        autorisation: Autorisation = AutorisationFactory(
            mandat=mandat, demarche="papiers", revocation_date=timezone.now()
        )

        self.assertFalse(autorisation.was_separately_revoked)

    def test_was_separately_revoked_mandate_revoked_true(self):
        mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=self.usager_homer,
            expiration_date=timezone.now() + timedelta(days=3),
        )

        AutorisationFactory(
            mandat=mandat, demarche="logement", revocation_date=timezone.now()
        )

        autorisation: Autorisation = AutorisationFactory(
            mandat=mandat,
            demarche="papiers",
            revocation_date=timezone.now() - timedelta(days=1),
        )

        self.assertTrue(autorisation.was_separately_revoked)


@tag("models")
class OrganisationModelTests(TestCase):
    def test_create_and_retrieve_organisation(self):
        self.assertEqual(OrganisationType.objects.count(), 12)
        o_type = OrganisationTypeFactory(name="CCAS")
        OrganisationFactory(
            name="Girard S.A.R.L",
            siret="123",
            type=o_type,
            address="3 rue du chat, 27120 Houlbec-Cocherel",
        )
        self.assertEqual(Organisation.objects.count(), 1)
        self.assertEqual(OrganisationType.objects.count(), 13)
        organisation = Organisation.objects.all()[0]
        self.assertEqual(organisation.name, "Girard S.A.R.L")
        self.assertEqual(organisation.type, o_type)
        self.assertEqual(organisation.address, "3 rue du chat, 27120 Houlbec-Cocherel")

    def test_count_accredited_organisations_for_statistics(self):
        self.assertEqual(Organisation.objects.accredited().count(), 0)
        self.assertEqual(Organisation.objects.not_yet_accredited().count(), 0)

        for _ in range(5):  # generate accredited organisations (with valid aidants)
            orga = OrganisationFactory()
            for _ in range(3):
                aidant = AidantFactory(organisation=orga)
                CarteTOTPFactory(aidant=aidant)

        for _ in range(7):  # generate non-accredited organisations
            orga = OrganisationFactory()
            for _ in range(3):
                AidantFactory(organisation=orga)

        self.assertEqual(Organisation.objects.accredited().count(), 5)
        self.assertEqual(Organisation.objects.not_yet_accredited().count(), 7)

    def test_display_address(self):
        organisation_no_address = Organisation(name="L'Internationale")
        organisation_address = Organisation(
            name="COMMUNE D'HOULBEC COCHEREL",
            siret=123,
            address="45 avenue du Général de Gaulle, 27120 HOULBEC COCHEREL",
        )

        organisation_no_address.save()
        organisation_address.save()

        self.assertEqual(organisation_no_address.display_address, "__________")
        self.assertNotEqual(
            organisation_no_address.display_address,
            Organisation._meta.get_field("address").default,
        )
        self.assertEqual(
            organisation_address.display_address, organisation_address.address
        )

    def test_deactivate_organisation(self):
        orga_one = OrganisationFactory(name="L'Internationale")
        orga_two = OrganisationFactory()
        aidant_marge = AidantFactory(organisation=orga_one)
        aidant_lisa = AidantFactory(organisation=orga_one)
        aidant_homer = AidantFactory(organisation=orga_two)

        self.assertTrue(orga_one.is_active)
        self.assertTrue(orga_two.is_active)
        orga_one.deactivate_organisation()
        orga_one.refresh_from_db()
        aidant_marge.refresh_from_db()
        aidant_lisa.refresh_from_db()
        aidant_homer.refresh_from_db()
        self.assertFalse(orga_one.is_active)
        self.assertTrue(orga_two.is_active)

        self.assertFalse(aidant_marge.is_active)
        self.assertFalse(aidant_lisa.is_active)
        self.assertTrue(aidant_homer.is_active)

    def test_deactivate_organisation_with_multistruct_aidant(self):
        orga_one = OrganisationFactory(name="Ouane")
        orga_two = OrganisationFactory(name="Tou")
        aidant_nour = AidantFactory(organisation=orga_one)
        aidant_nour.organisations.add(orga_two)

        self.assertTrue(orga_one.is_active)
        self.assertTrue(orga_two.is_active)
        self.assertTrue(aidant_nour.is_active)
        self.assertEqual(aidant_nour.organisation, orga_one)

        orga_one.deactivate_organisation()
        orga_one.refresh_from_db()
        aidant_nour.refresh_from_db()

        self.assertFalse(orga_one.is_active)
        self.assertTrue(orga_two.is_active)
        self.assertTrue(aidant_nour.is_active)
        self.assertEqual(aidant_nour.organisation, orga_two)

    def test_activate_organisation(self):
        orga = OrganisationFactory(name="L'Internationale", is_active=False)
        orga.activate_organisation()
        orga.refresh_from_db()
        self.assertTrue(orga.is_active)

    def test_set_empty_zipcode_from_address(self):
        organisation_no_address = Organisation(name="L'Internationale")
        organisation_no_address.save()
        self.assertEqual("0", organisation_no_address.zipcode)
        organisation_no_address.set_empty_zipcode_from_address()
        organisation_no_address.refresh_from_db()
        self.assertEqual("0", organisation_no_address.zipcode)

        organisation_with_address = Organisation(
            name="L'Internationale", address=" blaa 13013 Paris"
        )
        organisation_with_address.save()
        self.assertEqual("0", organisation_with_address.zipcode)
        organisation_with_address.set_empty_zipcode_from_address()
        organisation_with_address.refresh_from_db()
        self.assertEqual("13013", organisation_with_address.zipcode)

        organisation_with_zipcode = Organisation(
            name="L'Internationale", zipcode="75015", address=" blaa 13013 Paris"
        )
        organisation_with_zipcode.save()
        self.assertEqual("75015", organisation_with_zipcode.zipcode)
        organisation_with_zipcode.set_empty_zipcode_from_address()
        organisation_with_zipcode.refresh_from_db()
        self.assertEqual("75015", organisation_with_zipcode.zipcode)

    def test_count_mandats(self):
        def create_active_mandats(count, organisation):
            for _ in range(count):
                MandatFactory(
                    organisation=organisation,
                    expiration_date=timezone.now() + timedelta(days=6),
                )

        def create_expired_mandats(count, organisation):
            for _ in range(count):
                MandatFactory(
                    organisation=organisation,
                    expiration_date=timezone.now() - timedelta(days=6),
                )

        def create_revoked_mandats(count, organisation):
            for _ in range(count):
                RevokedMandatFactory(
                    organisation=organisation,
                    expiration_date=timezone.now() + timedelta(days=5),
                    post__create_authorisations=["argent", "famille", "logement"],
                )

        org_without_mandats = OrganisationFactory(name="Licornes")
        self.assertEqual(0, org_without_mandats.num_mandats)
        self.assertEqual(0, org_without_mandats.num_active_mandats)

        org_with_active_mandats = OrganisationFactory(name="Dragons")
        create_active_mandats(3, org_with_active_mandats)
        self.assertEqual(3, org_with_active_mandats.num_mandats)
        self.assertEqual(3, org_with_active_mandats.num_active_mandats)

        org_with_active_and_inactive_mandats = OrganisationFactory(name="Libellules")
        create_active_mandats(3, org_with_active_and_inactive_mandats)
        create_expired_mandats(4, org_with_active_and_inactive_mandats)
        create_revoked_mandats(2, org_with_active_and_inactive_mandats)
        self.assertEqual(9, org_with_active_and_inactive_mandats.num_mandats)
        self.assertEqual(3, org_with_active_and_inactive_mandats.num_active_mandats)

    def test_count_usagers(self):
        def create_6_mandats_for_2_usagers(organisation):
            thomas = UsagerFactory(given_name="Thomas")
            for _ in range(5):
                MandatFactory(organisation=organisation, usager=thomas)
            MandatFactory(organisation=organisation)

        organisation = OrganisationFactory()
        create_6_mandats_for_2_usagers(organisation=organisation)
        self.assertEqual(2, organisation.num_usagers)

    def test_count_aidants(self):
        orga_a = OrganisationFactory(name="A")
        orga_b = OrganisationFactory(name="Baker Street")
        for _ in range(2):
            aidant_a = AidantFactory(organisation=orga_a)
            aidant_a.organisations.set((orga_a, orga_b))
        for _ in range(3):
            aidant_b = AidantFactory(organisation=orga_b)
            aidant_b.organisations.set((orga_a, orga_b))
        for _ in range(4):
            aidant_c = AidantFactory(organisation=orga_a, is_active=False)
            aidant_c.organisations.set((orga_a, orga_b))
        self.assertEqual(orga_a.num_active_aidants, 5)


@tag("models", "aidant")
class AidantModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser_org = OrganisationFactory()

    def test_i_can_create_a_superuser(self):
        self.assertEqual(Aidant.objects.filter(is_superuser=True).count(), 0)
        Aidant.objects.create_superuser(
            username="admin", organisation=self.superuser_org
        )
        self.assertEqual(Aidant.objects.filter(is_superuser=True).count(), 1)

    def test_what_happens_to_password_when_not_set(self):
        aidant = Aidant.objects.create(
            username="Marge", organisation=self.superuser_org
        )
        self.assertEqual(aidant.password, "")

    def test_what_happens_when_username_not_set(self):
        aidant = Aidant.objects.create(organisation=self.superuser_org)
        self.assertEqual(aidant.username, "")

    def test_what_happens_when_an_aidant_tries_to_use_same_username(self):
        Aidant.objects.create(username="Marge", organisation=self.superuser_org)
        self.assertRaises(IntegrityError, Aidant.objects.create, username="Marge")

    def test_what_happens_when_an_aidant_tries_to_use_same_email(self):
        Aidant.objects.create(email="Test@test.test", organisation=self.superuser_org)
        self.assertRaises(
            IntegrityError, Aidant.objects.create, username="TEST@TEST.TEST"
        )

    def test_get_aidant_organisation(self):
        orga = OrganisationFactory(
            name="COMMUNE DE HOULBEC COCHEREL",
            siret=123,
            address="45 avenue du Général de Gaulle, 90210 Beverly Hills",
        )
        aidant = AidantFactory(organisation=orga)
        self.assertEqual(aidant.organisation.name, "COMMUNE DE HOULBEC COCHEREL")

    def test_get_active_aidants(self):
        AidantFactory()
        AidantFactory(is_active=False)
        self.assertEqual(Aidant.objects.active().count(), 1)

    def test_get_aidants_not_connected_recently(self):
        now = timezone.now()

        with freeze_time(now):
            AidantFactory(is_active=True, last_login=timezone.now())
            AidantFactory(
                is_active=True,
                last_login=timezone.now()
                - relativedelta(months=5)
                + relativedelta(days=1),
            )
            AidantFactory(
                is_active=False, last_login=timezone.now() - relativedelta(year=1)
            )

            aidants_selected = [
                AidantFactory(
                    is_active=True,
                    last_login=timezone.now() - relativedelta(months=5),
                ),
                AidantFactory(
                    is_active=True, last_login=timezone.now() - relativedelta(year=1)
                ),
            ]

            self.assertEqual(
                aidants_selected, list(Aidant.objects.not_connected_recently())
            )

    def test_get_aidants_warnable(self):
        now = timezone.now()

        with freeze_time(now):
            AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=timezone.now()
                - relativedelta(months=5)
                + relativedelta(days=1),
            )

            # Référents aren't warnable
            AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=None,
                can_create_mandats=False,
            )

            # Aidant without ToTtp aren't warnable
            AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=None,
            )

            # Aidant with a recent card aren't warnable
            not_warnable = AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=None,
            )
            not_warnable_totp = CarteTOTPFactory(aidant=not_warnable)
            CarteTOTP.objects.filter(pk=not_warnable_totp.pk).update(
                created_at=timezone.now() - relativedelta(months=3)
            )

            warnable = AidantFactory(
                is_active=True,
                last_login=timezone.now() - relativedelta(months=5),
                deactivation_warning_at=None,
            )
            warnable_totp = CarteTOTPFactory(aidant=warnable)
            CarteTOTP.objects.filter(pk=warnable_totp.pk).update(
                created_at=timezone.now() - relativedelta(months=7)
            )

            aidants_selected = [warnable]

            self.assertEqual(
                aidants_selected, list(Aidant.objects.deactivation_warnable())
            )

    def test_get_users_without_activity_for_90_days(self):
        # Inactive aidants don't appear in results
        AidantFactory(is_active=False)

        # Aidants who have no activity don't appear in results
        AidantFactory(is_active=True)

        # Aidants who have an activity for less than 90 days don't appear in results
        for action in (
            JournalActionKeywords.CREATE_ATTESTATION,
            JournalActionKeywords.USE_AUTORISATION,
            JournalActionKeywords.INIT_RENEW_MANDAT,
        ):
            aidant = AidantFactory(is_active=True)
            JournalFactory(
                aidant=aidant, creation_date=now() - timedelta(days=89), action=action
            )

        warnable_aidants = set()

        # Aidants who have an activity for more than 90 days appear in results
        for action in (
            JournalActionKeywords.CREATE_ATTESTATION,
            JournalActionKeywords.USE_AUTORISATION,
            JournalActionKeywords.INIT_RENEW_MANDAT,
        ):
            aidant = AidantFactory(is_active=True)
            JournalFactory(
                aidant=aidant, creation_date=now() - timedelta(days=91), action=action
            )
            warnable_aidants.add(aidant)

        self.assertEqual(
            warnable_aidants, set(Aidant.objects.without_activity_for_90_days())
        )

    def test_referent_non_aidant_and_can_create_mandats_incompatible_constraint(self):
        AidantFactory(referent_non_aidant=False, can_create_mandats=False)
        AidantFactory(referent_non_aidant=True, can_create_mandats=False)
        AidantFactory(referent_non_aidant=False, can_create_mandats=True)
        with self.assertRaises(IntegrityError):
            AidantFactory(referent_non_aidant=True, can_create_mandats=True)


@tag("models", "aidant")
class AidantModelMethodsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Aidants : Marge & Lisa belong to the same organisation, Patricia does not
        cls.aidant_marge: Aidant = AidantFactory(validated_cgu_version="0.1")
        cls.aidant_lisa = AidantFactory(
            organisation=cls.aidant_marge.organisation,
            validated_cgu_version=settings.CGU_CURRENT_VERSION,
        )
        cls.aidant_patricia = AidantFactory()

        # Juliette is responsible in the same structure as Marge & Lisa
        cls.respo_juliette: Aidant = AidantFactory(
            organisation=cls.aidant_marge.organisation,
        )
        cls.respo_juliette.responsable_de.add(cls.aidant_marge.organisation)
        cls.respo_juliette_org2 = OrganisationFactory()
        cls.respo_juliette.organisations.add(cls.respo_juliette_org2)
        cls.respo_juliette.responsable_de.add(cls.respo_juliette_org2)

        cls.respo_juliette_org3 = OrganisationFactory()
        cls.respo_juliette.organisations.add(cls.respo_juliette_org2)
        cls.aidant_sarah: Aidant = AidantFactory(organisation=cls.respo_juliette_org3)

        # TOTP Device
        device = TOTPDevice(user=cls.aidant_marge)
        device.save()
        for _ in range(2):
            device = TOTPDevice(user=cls.aidant_patricia)
            device.save()

        # Active Usagers
        cls.usager_homer = UsagerFactory(given_name="Homer")
        cls.usager_ned = UsagerFactory(given_name="Ned")

        # Usager with no mandat
        cls.usager_bart = UsagerFactory(given_name="Bart")

        # Inactive Usagers
        cls.usager_sophie = UsagerFactory(given_name="Sophie")
        cls.usager_lola = UsagerFactory(given_name="Lola")

        # Mandats Marge
        cls.mandat_marge_homer_1 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_homer_1,
            demarche="Carte grise",
        )

        cls.mandat_marge_homer_2 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_homer_2,
            demarche="Revenus",
        )

        cls.mandat_marge_homer_3 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() + timedelta(days=365),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_homer_3,
            demarche="social",
        )

        cls.mandat_marge_ned_1 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_ned_1,
            demarche="Logement",
        )

        # Partially revoked mandat
        cls.mandat_marge_ned_2 = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_ned_2,
            demarche="transports",
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_ned_2,
            demarche="famille",
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_ned_2,
            demarche="social",
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_ned_2,
            demarche="travail",
        )

        AutorisationFactory(
            demarche="papiers",
            mandat=cls.mandat_marge_ned_2,
            revocation_date=timezone.now(),
        )
        # Expired mandat
        cls.mandat_marge_sophie = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_sophie,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        AutorisationFactory(
            mandat=cls.mandat_marge_sophie,
            demarche="transports",
        )
        # Revoked mandat
        cls.mandat_marge_lola = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_lola,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            demarche="papiers",
            mandat=cls.mandat_marge_lola,
            revocation_date=timezone.now(),
        )

        # Mandat Patricia
        cls.mandat_marge_lola = MandatFactory(
            organisation=cls.aidant_patricia.organisation,
            usager=cls.usager_lola,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        AutorisationFactory(
            demarche="papiers",
            mandat=cls.mandat_marge_lola,
        )

    def test_get_usagers(self):
        self.assertEqual(len(self.aidant_marge.get_usagers()), 4)
        self.assertEqual(len(self.aidant_lisa.get_usagers()), 4)
        self.assertEqual(len(self.aidant_patricia.get_usagers()), 1)

    def test_get_usager(self):
        usager_john = UsagerFactory()
        self.assertIsNone(self.aidant_marge.get_usager(usager_john.id))
        self.assertEqual(
            self.aidant_marge.get_usager(self.usager_homer.id), self.usager_homer
        )

    def test_active_usagers(self):
        usagers = Usager.objects.all()
        self.assertEqual(len(usagers), 5)
        active_usagers = usagers.active()
        self.assertEqual(len(active_usagers), 3)

    def test_get_usagers_with_active_autorisation(self):
        self.assertEqual(
            len(self.aidant_marge.get_usagers_with_active_autorisation()), 2
        )
        self.assertEqual(
            len(self.aidant_lisa.get_usagers_with_active_autorisation()), 2
        )
        self.assertEqual(
            len(self.aidant_patricia.get_usagers_with_active_autorisation()), 1
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
        self.assertEqual(
            len(self.aidant_lisa.get_active_autorisations_for_usager(self.usager_lola)),
            0,
        )
        self.assertEqual(
            len(
                self.aidant_patricia.get_active_autorisations_for_usager(
                    self.usager_lola
                )
            ),
            1,
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

    def test_get_valid_autorisation_method(self):
        # A valid mandat with one revoked autorisation
        usager_charles = UsagerFactory(given_name="Charles", sub="Charles")
        active_mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=usager_charles,
        )
        valid_autorisation = AutorisationFactory(
            mandat=active_mandat,
            demarche="papiers",
            revocation_date=None,
        )
        AutorisationFactory(
            mandat=active_mandat,
            demarche="transport",
            revocation_date=timezone.now() - timedelta(days=1),
        )
        self.assertEqual(
            self.aidant_marge.get_valid_autorisation("papiers", usager_charles),
            valid_autorisation,
        )
        self.assertEqual(
            self.aidant_marge.get_valid_autorisation("transport", usager_charles), None
        )

        # An expired Mandat
        expired_mandat = MandatFactory(
            organisation=self.aidant_marge.organisation,
            usager=usager_charles,
            expiration_date=timezone.now() - timedelta(days=1),
        )
        AutorisationFactory(
            mandat=expired_mandat,
            demarche="social",
            revocation_date=None,
        )

        self.assertEqual(
            self.aidant_marge.get_valid_autorisation("social", usager_charles), None
        )

    def test_is_in_organisation(self):
        self.assertTrue(
            self.aidant_marge.is_in_organisation(self.aidant_lisa.organisation),
            "Aidant.is_in_organisation devrait indiquer que la personne fait partie de "
            "sa propre organisation.",
        )
        self.assertFalse(
            self.aidant_marge.is_in_organisation(OrganisationFactory()),
            "Aidant.is_in_organisation devrait indiquer que la personne ne fait pas "
            "partie d'une organisation étrangère.",
        )

    def test_is_responsable_structure(self):
        # an aidant without further modification is not référent structure
        self.assertFalse(self.aidant_lisa.is_responsable_structure())
        # however Juliette is référente structure
        self.assertTrue(self.respo_juliette.is_responsable_structure())

    def test_can_see_aidant(self):
        # respo_juliette is referent for their current organisation and
        # aidant_marge is member of this organisation
        self.assertTrue(self.respo_juliette.can_manage_aidant(self.aidant_marge))

        # aidant_marge's organisation is not respo_juliette's current organisation
        self.respo_juliette.organisation = self.respo_juliette_org2
        self.respo_juliette.save()
        self.respo_juliette.refresh_from_db()
        self.assertFalse(self.respo_juliette.can_manage_aidant(self.aidant_marge))

        # aidant_patricia is not in any of respo_juliette's organisation
        self.assertFalse(self.respo_juliette.can_manage_aidant(self.aidant_patricia))

        # respo_juliette is in aidant_sarah's organisation
        # but not on of their referents
        self.assertFalse(self.respo_juliette.can_manage_aidant(self.aidant_sarah))

    def test_must_validate_cgu(self):
        # an aidant without further modification must validate user conditions
        self.assertTrue(self.aidant_patricia.must_validate_cgu())
        # an aidant who has validated current version of user conditions
        # does not need to revalidate them
        self.assertFalse(self.aidant_lisa.must_validate_cgu())
        # an aidant who has validated an outaded version of CGU
        # must validate them again
        self.assertTrue(self.aidant_marge.must_validate_cgu())

    def test_has_a_totp_device(self):
        self.assertFalse(self.aidant_lisa.has_a_totp_device)
        self.assertTrue(self.aidant_marge.has_a_totp_device)
        self.assertTrue(self.aidant_patricia.has_a_totp_device)

    def test_remove_user_from_organisation_deactivate_user(self):
        aidant: Aidant = AidantFactory()
        organisation: Organisation = aidant.organisation
        self.assertTrue(aidant.is_active, "L'aidant n'est pas actif")
        aidant.remove_from_organisation(aidant.organisation)
        self.assertFalse(
            aidant.is_active,
            "L'aidant est toujours actif après la tentative de suppression de son "
            "organisation.",
        )
        self.assertSequenceEqual([organisation], list(aidant.organisations.all()))

    def test_remove_user_from_organisation(self):
        aidant: Aidant = AidantFactory()
        organisation: Organisation = aidant.organisation
        supplementary_organisation_1 = OrganisationFactory()
        supplementary_organisation_2 = OrganisationFactory()
        aidant.organisations.add(
            supplementary_organisation_1, supplementary_organisation_2
        )

        self.assertTrue(aidant.is_active, "L'aidant n'est pas actif")
        aidant.remove_from_organisation(supplementary_organisation_1)
        self.assertTrue(
            aidant.is_active,
            "L'aidant n'est plus actif après la tentative de suppression d'une "
            "organisation surnuméraire",
        )
        self.assertSequenceEqual(
            [organisation, supplementary_organisation_2],
            list(aidant.organisations.order_by("id").all()),
        )

    def test_remove_user_from_organisation_set_main_org(self):
        aidant: Aidant = AidantFactory()
        organisation: Organisation = aidant.organisation
        supplementary_organisation_1 = OrganisationFactory()
        supplementary_organisation_2 = OrganisationFactory()
        aidant.organisations.add(
            supplementary_organisation_1, supplementary_organisation_2
        )

        self.assertTrue(aidant.is_active, "L'aidant n'est pas actif")
        aidant.remove_from_organisation(organisation)
        self.assertTrue(
            aidant.is_active,
            "L'aidant n'est plus actif après la tentative de suppression d'une "
            "organisation surnuméraire",
        )
        self.assertSequenceEqual(
            [supplementary_organisation_1, supplementary_organisation_2],
            list(aidant.organisations.order_by("id").all()),
        )
        self.assertEqual(
            supplementary_organisation_1,
            aidant.organisation,
            "L'organisation principale de l'aidant n'a pas été remplacée par une "
            "organisation valide après que l'aidant en a été retiré",
        )

    def test_remove_user_from_organisation_does_not_change_main_org(self):
        aidant: Aidant = AidantFactory()
        supplementary_organisation_1 = OrganisationFactory()
        supplementary_organisation_2 = OrganisationFactory()
        supplementary_organisation_to_remove = OrganisationFactory()
        aidant.organisations.add(
            supplementary_organisation_1,
            supplementary_organisation_2,
            supplementary_organisation_to_remove,
            OrganisationFactory(),
            OrganisationFactory(),
            OrganisationFactory(),
        )

        aidant.organisation = supplementary_organisation_1

        self.assertEqual(aidant.organisation, supplementary_organisation_1)

        aidant.remove_from_organisation(supplementary_organisation_to_remove)

        self.assertEqual(aidant.organisation, supplementary_organisation_1)

    @patch("aidants_connect_web.signals.aidants__organisations_changed.send")
    def test_remove_user_from_organisation_sends_signal(self, send: Mock):
        aidant: Aidant = AidantFactory()
        supplementary_organisation_1 = OrganisationFactory()
        aidant.organisations.add(supplementary_organisation_1)

        aidant.remove_from_organisation(supplementary_organisation_1)

        send.assert_called_once_with(
            sender=aidant.__class__,
            instance=aidant,
            diff={"removed": [supplementary_organisation_1], "added": []},
        )

    def test_set_organisations_raises_error_when_removing_everything(self):
        aidant: Aidant = AidantFactory()

        with self.assertRaises(ValueError) as err:
            aidant.set_organisations([])
        self.assertEqual(
            "Can't remove all the organisations from aidant", f"{err.exception}"
        )

    def test_set_organisations_correctly_sets_organisations(self):
        aidant: Aidant = AidantFactory()

        organisation_to_remove = OrganisationFactory()
        aidant.organisations.add(organisation_to_remove)

        organisation_to_set_1 = OrganisationFactory()
        organisation_to_set_2 = OrganisationFactory()

        self.assertSequenceEqual(
            [aidant.organisation, organisation_to_remove],
            list(aidant.organisations.order_by("id")),
        )

        aidant.set_organisations(
            [aidant.organisation, organisation_to_set_1, organisation_to_set_2]
        )

        self.assertSequenceEqual(
            [aidant.organisation, organisation_to_set_1, organisation_to_set_2],
            list(aidant.organisations.order_by("id")),
        )

    def test_set_organisations_set_current_active_organisation_when_removed(self):
        aidant: Aidant = AidantFactory()

        organisation_to_set_1 = OrganisationFactory()
        organisation_to_set_2 = OrganisationFactory()

        aidant.set_organisations([organisation_to_set_1, organisation_to_set_2])

        self.assertSequenceEqual(
            [organisation_to_set_1, organisation_to_set_2],
            list(aidant.organisations.order_by("id")),
        )
        self.assertEqual(organisation_to_set_1, aidant.organisation)

    def test_set_organisations_does_not_change_main_org(self):
        aidant: Aidant = AidantFactory()
        supplementary_organisation_1 = OrganisationFactory()
        supplementary_organisation_2 = OrganisationFactory()
        supplementary_organisation_to_remove = OrganisationFactory()
        aidant.organisations.add(
            supplementary_organisation_1,
            supplementary_organisation_2,
            supplementary_organisation_to_remove,
            OrganisationFactory(),
            OrganisationFactory(),
            OrganisationFactory(),
        )

        aidant.organisation = supplementary_organisation_1

        self.assertEqual(aidant.organisation, supplementary_organisation_1)

        aidant.set_organisations(
            set(aidant.organisations.all()) - {supplementary_organisation_to_remove}
        )

        self.assertEqual(aidant.organisation, supplementary_organisation_1)

    @patch("aidants_connect_web.signals.aidants__organisations_changed.send")
    def test_set_organisations_sends_signal(self, send: Mock):
        aidant: Aidant = AidantFactory()
        previous_organisation = aidant.organisation

        organisation_to_remove = OrganisationFactory()
        aidant.organisations.add(organisation_to_remove)

        organisation_to_set_1 = OrganisationFactory()
        organisation_to_set_2 = OrganisationFactory()

        aidant.set_organisations([organisation_to_set_1, organisation_to_set_2])

        send.assert_called_once_with(
            sender=aidant.__class__,
            instance=aidant,
            diff={
                "removed": [previous_organisation, organisation_to_remove],
                "added": [organisation_to_set_1, organisation_to_set_2],
            },
        )

    def test_has_a_carte_totp(self):
        self.assertFalse(self.aidant_marge.has_a_carte_totp)
        CarteTOTPFactory(aidant=self.aidant_patricia)
        self.assertTrue(self.aidant_patricia.has_a_carte_totp)

    def test_number_totp_card(self):
        self.assertEqual(self.aidant_marge.number_totp_card, "Pas de Carte")
        CarteTOTPFactory(aidant=self.aidant_patricia, serial_number="12121212")
        self.assertTrue(self.aidant_patricia.number_totp_card, "12121212")

    def test_save_adds_current_and_referents_organisation_to_aidant(self):
        aidant: Aidant = AidantFactory()
        aidant_referent = [OrganisationFactory(), OrganisationFactory()]
        aidant_former_org = aidant.organisation
        aidant_current_org = OrganisationFactory()

        aidant.refresh_from_db()
        self.assertEqual({aidant_former_org}, set(aidant.organisations.all()))

        aidant.organisation = aidant_current_org
        aidant.responsable_de.add(*aidant_referent)
        aidant.save()
        aidant.refresh_from_db()

        self.assertEqual(
            {*aidant_referent, aidant_former_org, aidant_current_org},
            set(aidant.organisations.all()),
        )


@tag("models", "journal")
class JournalModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_thierry = AidantFactory(
            email="thierry@thierry.com",
            first_name="Thierry",
            last_name="Martin",
            organisation=OrganisationFactory(name="Commune de Vernon"),
        )
        cls.journal_entry = Journal.objects.create(
            action="connect_aidant",
            aidant=cls.aidant_thierry,
            organisation=cls.aidant_thierry.organisation,
        )
        cls.usager_ned = UsagerFactory(given_name="Ned", family_name="Flanders")

        cls.first_mandat = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() + timedelta(days=6),
        )
        cls.first_autorisation = AutorisationFactory(
            mandat=cls.first_mandat,
            demarche="Revenus",
        )
        Journal.log_autorisation_creation(
            cls.first_autorisation, aidant=cls.aidant_thierry
        )

        cls.mandat_thierry_ned_365 = MandatFactory(
            organisation=cls.aidant_thierry.organisation,
            usager=cls.usager_ned,
            expiration_date=timezone.now() + timedelta(days=365),
        )

    def test_a_journal_entry_can_be_created(self):
        # Aidant connects and first autorisation is created
        self.assertEqual(len(Journal.objects.all()), 2)

    def test_logging_of_aidant_conection(self):
        entry = Journal.log_connection(aidant=self.aidant_thierry)
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "connect_aidant")
        self.assertEqual(entry.aidant.id, self.aidant_thierry.id)

    def test_a_franceconnect_usager_journal_entry_can_be_created(self):
        entry = Journal.log_franceconnection_usager(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
        )

        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "franceconnect_usager")

    def test_log_autorisation_creation_complete(self):
        autorisation = AutorisationFactory(
            mandat=self.mandat_thierry_ned_365,
            demarche="logement",
        )
        Journal.log_autorisation_creation(autorisation, self.aidant_thierry)

        journal_entries = Journal.objects.all()
        self.assertEqual(len(journal_entries), 3)

        last_entry = journal_entries.last()
        self.assertEqual(last_entry.action, "create_autorisation")
        self.assertEqual(last_entry.usager.id, self.usager_ned.id)
        self.assertEqual(last_entry.autorisation, autorisation.id)

    def test_log_autorisation_use_complete(self):
        entry = Journal.log_autorisation_use(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarche="transports",
            access_token="fjfgjfdkldlzlsmqqxxcn",
            autorisation=self.first_autorisation,
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "use_autorisation")
        self.assertEqual(entry.demarche, "transports")

    def test_log_autorisation_cancel_complete(self):
        entry = Journal.log_autorisation_cancel(
            autorisation=self.first_autorisation, aidant=self.aidant_thierry
        )
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(entry.action, "cancel_autorisation")

    def test_it_is_impossible_to_change_an_existing_entry(self):
        entry = Journal.log_autorisation_use(
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
        entry = Journal.log_autorisation_use(
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
        mandat = MandatFactory()
        entry = Journal.log_attestation_creation(
            aidant=self.aidant_thierry,
            usager=self.usager_ned,
            demarches=demarches,
            duree=6,
            is_remote_mandat=False,
            access_token="fjfgjfdkldlzlsmqqxxcn",
            attestation_hash=generate_attestation_hash(
                self.aidant_thierry, self.usager_ned, demarches, expiration_date
            ),
            mandat=mandat,
            remote_constent_method="",
            user_phone="",
            consent_request_id="",
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
                generate_file_sha256_hash(f"templates/{settings.MANDAT_TEMPLATE_PATH}"),
                self.usager_ned.sub,
            ]
        )
        self.assertTrue(
            validate_attestation_hash(attestation_string, entry.attestation_hash)
        )

    def test_infos_set_remote_mandate_by_sms_constraint(self):
        # Journal logged
        journal = Journal._log_sms_event(
            JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
            self.aidant_thierry,
            "logement,transports",
            "SHORT",
            RemoteConsentMethodChoices.SMS.value,
            parse_number("0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION),
            str(uuid4()),
            "message",
        )

        self.assertEqual("message=message", journal.additional_information)

        # Test I can't create a SMS related journal without a aidant
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                    aidant=None,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.SMS.value,
                    is_remote_mandat=True,
                    user_phone=format_number(
                        parse_number(
                            "0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION
                        ),
                        PhoneNumberFormat.E164,
                    ),
                    consent_request_id=str(uuid4()),
                    additional_information="message",
                )

        # Test I can't create a SMS related journal with remote field false
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                    aidant=None,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.SMS.value,
                    is_remote_mandat=False,
                    user_phone=format_number(
                        parse_number(
                            "0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION
                        ),
                        PhoneNumberFormat.E164,
                    ),
                    consent_request_id=str(uuid4()),
                    additional_information="message",
                )

        # Test I can't create a SMS related journal without a phone number
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                    aidant=None,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.SMS.value,
                    is_remote_mandat=False,
                    user_phone="",
                    consent_request_id=str(uuid4()),
                    additional_information="message",
                )

        # Test I can't create a SMS related journal with another remote method
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
                    aidant=None,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.LEGACY.value,
                    is_remote_mandat=False,
                    user_phone=format_number(
                        parse_number(
                            "0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION
                        ),
                        PhoneNumberFormat.E164,
                    ),
                    consent_request_id=str(uuid4()),
                    additional_information="message",
                )

        # Test I can't create a SMS related journal without a message
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_DENIAL_RECEIVED,
                    aidant=self.aidant_thierry,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.SMS.value,
                    is_remote_mandat=True,
                    user_phone=format_number(
                        parse_number(
                            "0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION
                        ),
                        PhoneNumberFormat.E164,
                    ),
                    consent_request_id=str(uuid4()),
                )

        # Test I can't create a SMS related journal without a consent request ID
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Journal.objects.create(
                    action=JournalActionKeywords.REMOTE_SMS_CONSENT_SENT,
                    aidant=self.aidant_thierry,
                    demarche="logement,transports",
                    duree=365,
                    remote_constent_method=RemoteConsentMethodChoices.SMS.value,
                    is_remote_mandat=True,
                    user_phone=format_number(
                        parse_number(
                            "0 800 840 800", settings.PHONENUMBER_DEFAULT_REGION
                        ),
                        PhoneNumberFormat.E164,
                    ),
                    additional_information="message",
                )


@tag("models", "habilitation_request")
class HabilitationRequestMethodTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def test_validate_when_all_is_fine(self):
        for habilitation_request in (
            HabilitationRequestFactory(
                status=ReferentRequestStatuses.STATUS_PROCESSING.value
            ),
            HabilitationRequestFactory(status=ReferentRequestStatuses.STATUS_NEW.value),
            HabilitationRequestFactory(
                status=ReferentRequestStatuses.STATUS_WAITING_LIST_HABILITATION.value  # noqa: E501
            ),
        ):
            self.assertEqual(
                0, Aidant.objects.filter(email=habilitation_request.email).count()
            )
            self.assertTrue(habilitation_request.validate_and_create_aidant())
            self.assertEqual(
                1, Aidant.objects.filter(email=habilitation_request.email).count()
            )
            db_hab_request = HabilitationRequest.objects.get(id=habilitation_request.id)
            self.assertEqual(
                db_hab_request.status,
                ReferentRequestStatuses.STATUS_VALIDATED.value,
            )

    def test_validate_if_active_aidant_already_exists(self):
        aidant = AidantFactory()
        habilitation_request = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING.value,
            email=aidant.email,
        )
        self.assertTrue(habilitation_request.validate_and_create_aidant())
        self.assertEqual(
            1, Aidant.objects.filter(email=habilitation_request.email).count()
        )
        habilitation_request.refresh_from_db()
        self.assertEqual(
            habilitation_request.status,
            ReferentRequestStatuses.STATUS_VALIDATED.value,
        )
        aidant.refresh_from_db()
        self.assertIn(habilitation_request.organisation, aidant.organisations.all())

    def test_validate_if_inactive_aidant_already_exists(self):
        aidant = AidantFactory(is_active=False)
        self.assertFalse(aidant.is_active)
        habilitation_request = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_PROCESSING.value,
            email=aidant.email,
        )
        self.assertTrue(habilitation_request.validate_and_create_aidant())
        self.assertEqual(
            1, Aidant.objects.filter(email=habilitation_request.email).count()
        )
        habilitation_request.refresh_from_db()
        self.assertEqual(
            habilitation_request.status,
            ReferentRequestStatuses.STATUS_VALIDATED.value,
        )
        aidant.refresh_from_db()
        self.assertTrue(aidant.is_active)
        self.assertIn(habilitation_request.organisation, aidant.organisations.all())

    def test_do_not_validate_if_invalid_status(self):
        habilitation_request = HabilitationRequestFactory(
            status=ReferentRequestStatuses.STATUS_REFUSED.value
        )
        self.assertEqual(
            0, Aidant.objects.filter(email=habilitation_request.email).count()
        )
        self.assertFalse(habilitation_request.validate_and_create_aidant())
        self.assertEqual(
            0, Aidant.objects.filter(email=habilitation_request.email).count()
        )
        db_hab_request = HabilitationRequest.objects.get(id=habilitation_request.id)
        self.assertEqual(
            db_hab_request.status, ReferentRequestStatuses.STATUS_REFUSED.value
        )


@tag("models", "manndat", "usager", "journal")
class UsagerDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant_marge = AidantFactory()
        cls.usager_homer = UsagerFactory(given_name="Homer")
        cls.mandat_marge_homer = MandatFactory(
            organisation=cls.aidant_marge.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        cls.autorisation = AutorisationFactory(
            mandat=cls.mandat_marge_homer,
            demarche="Carte grise",
        )
        Journal.log_autorisation_creation(cls.autorisation, aidant=cls.aidant_marge)
        Journal.log_franceconnection_usager(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
        )
        Journal.log_mandat_cancel(
            aidant=cls.aidant_marge, mandat=cls.mandat_marge_homer
        )

    def test_usager_clean_journal_entries_and_delete_mandats(self):
        self.assertEqual(len(Journal.objects.all()), 3)
        testing = "Add by clean_journal_entries_and_delete_mandats"
        self.usager_homer.clean_journal_entries_and_delete_mandats()
        self.assertEqual(len(Journal.objects.all()), 3)
        self.assertEqual(
            len(Journal.objects.filter(additional_information__icontains=testing)),
            3,
        )
        self.usager_homer.delete()
        self.assertEqual(len(Usager.objects.all()), 0)
        self.assertEqual(len(Mandat.objects.all()), 0)
        self.assertEqual(len(Journal.objects.all()), 3)


@tag("models", "manndat", "organisation", "journal")
class OrganisationDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory()
        cls.organisation2 = OrganisationFactory()
        cls.aidant_marge = AidantFactory(organisation=cls.organisation)
        cls.usager_homer = UsagerFactory(given_name="Homer")
        cls.mandat_marge_homer = MandatFactory(
            organisation=cls.organisation,
            usager=cls.usager_homer,
            expiration_date=timezone.now() - timedelta(days=6),
        )
        cls.autorisation = AutorisationFactory(
            mandat=cls.mandat_marge_homer,
            demarche="Carte grise",
        )
        Journal.log_connection(aidant=cls.aidant_marge)
        Journal.log_autorisation_creation(cls.autorisation, aidant=cls.aidant_marge)
        Journal.log_franceconnection_usager(
            aidant=cls.aidant_marge,
            usager=cls.usager_homer,
        )
        Journal.log_mandat_cancel(
            aidant=cls.aidant_marge, mandat=cls.mandat_marge_homer
        )

    def test_dont_delete_organisation_with_aidants(self):
        result = self.organisation.clean_journal_entries_and_delete_mandats()
        self.assertFalse(result)

    def test_organisation_clean_journal_entries_and_delete_mandats(self):
        self.aidant_marge.set_organisations([self.organisation2])
        self.organisation.refresh_from_db()
        self.assertEqual(len(Journal.objects.all()), 4)
        testing = "Add by clean_journal_entries_and_delete_mandats"
        self.assertTrue(self.organisation.clean_journal_entries_and_delete_mandats())
        self.assertEqual(len(Journal.objects.all()), 4)
        self.assertEqual(
            len(Journal.objects.filter(additional_information__icontains=testing)),
            4,
        )
        self.organisation.delete()
        self.assertEqual(len(Organisation.objects.all()), 1)
        self.assertEqual(len(Mandat.objects.all()), 0)
        self.assertEqual(len(Journal.objects.all()), 4)


class TestNotification(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.notification_type = ""
        cls.aidant: Aidant = AidantFactory()

    def test_constraints(self):
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Notification.objects.create(
                    type=self.notification_type,
                    aidant=self.aidant,
                    must_ack=False,
                    was_ack=True,
                )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Notification.objects.create(
                    type=self.notification_type,
                    aidant=self.aidant,
                    must_ack=False,
                    auto_ack_date=None,
                )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Notification.objects.create(
                    type=self.notification_type,
                    aidant=self.aidant,
                    must_ack=True,
                    auto_ack_date=date.today(),
                )

        with transaction.atomic():
            Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=True,
                auto_ack_date=None,
                was_ack=False,
            )

        with transaction.atomic():
            Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=False,
                auto_ack_date=date.today(),
                was_ack=False,
            )

    def test_mark_read(self):
        notification: Notification = NotificationFactory(was_ack=False)
        notification.refresh_from_db()
        self.assertFalse(notification.was_ack)
        notification.mark_read()
        notification.refresh_from_db()
        self.assertTrue(notification.was_ack)

    def test_mark_unread(self):
        notification: Notification = NotificationFactory(was_ack=True)
        notification.refresh_from_db()
        self.assertTrue(notification.was_ack)
        notification.mark_unread()
        notification.refresh_from_db()
        self.assertFalse(notification.was_ack)

    def test_get_displayable_for_user(self):
        with transaction.atomic():
            self.notif_1 = Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=True,
                auto_ack_date=None,
                was_ack=False,
            )
            self.notif_2 = Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=True,
                auto_ack_date=None,
                was_ack=True,
            )
            self.notif_3 = Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=False,
                auto_ack_date=date.today(),
                was_ack=False,
            )
            self.notif_4 = Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=False,
                auto_ack_date=date.today() + timedelta(days=1),
                was_ack=False,
            )
            self.notif_5 = Notification.objects.create(
                type=self.notification_type,
                aidant=self.aidant,
                must_ack=False,
                auto_ack_date=date.today() - timedelta(days=1),
                was_ack=False,
            )

        self.assertEqual(
            {self.notif_1, self.notif_4},
            set(Notification.objects.get_displayable_for_user(self.aidant)),
        )


class CoReferentNonAidantRequestTests(TestCase):
    def test_create_referent_non_aidant(self):
        request = CoReferentNonAidantRequestFactory()
        aidant = request.create_referent_non_aidant()
        self.assertTrue(aidant.referent_non_aidant)
        self.assertFalse(aidant.can_create_mandats)
        self.assertEqual(request.first_name, aidant.first_name)
        self.assertEqual(request.last_name, aidant.last_name)
        self.assertEqual(request.profession, aidant.profession)
        self.assertEqual(request.email, aidant.email)
        self.assertEqual(request.organisation, aidant.organisation)
        self.assertIn(aidant, request.organisation.responsables.all())


class FormationAttendantTests(TestCase):
    def test_I_cant_regester_more_aidant_than_max_attendees(self):
        formation = FormationFactory(max_attendants=2)
        aidant_request = AidantRequestFactory()
        habilitation_request = HabilitationRequestFactory()

        FormationAttendant.objects.create(formation=formation, attendant=aidant_request)

        last = FormationAttendant.objects.create(
            formation=formation, attendant=habilitation_request
        )

        self.assertEqual(
            2, FormationAttendant.objects.filter(formation=formation).count()
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                FormationAttendant.objects.create(
                    formation=formation, attendant=AidantRequestFactory()
                )

        self.assertEqual(
            2, FormationAttendant.objects.filter(formation=formation).count()
        )

        # Can unregister an attendant and register a new one
        with transaction.atomic():
            last.delete()

        self.assertEqual(
            1, FormationAttendant.objects.filter(formation=formation).count()
        )

        FormationAttendant.objects.create(
            formation=formation, attendant=AidantRequestFactory()
        )

        self.assertEqual(
            2, FormationAttendant.objects.filter(formation=formation).count()
        )

        with self.assertRaises(IntegrityError):
            FormationAttendant.objects.create(
                formation=formation, attendant=AidantRequestFactory()
            )

    def test_I_cant_register_an_attendant_to_a_formation_twice(self):
        formation = FormationFactory(max_attendants=2)
        aidant_request = AidantRequestFactory()

        FormationAttendant.objects.create(formation=formation, attendant=aidant_request)

        with self.assertRaises(IntegrityError):
            FormationAttendant.objects.create(
                formation=formation, attendant=aidant_request
            )

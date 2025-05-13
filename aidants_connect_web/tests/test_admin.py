from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.test import TestCase, tag
from django.test.client import RequestFactory
from django.utils.timezone import now

from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_common.constants import AuthorizationDurations
from aidants_connect_common.models import Region
from aidants_connect_habilitation.models import Manager
from aidants_connect_web.admin import (
    AidantAdmin,
    HabilitationRequestAdmin,
    OrganisationAdmin,
)
from aidants_connect_web.admin.aidant import (
    AidantInPreDesactivationZoneFilter,
    AidantWithMandatsFilter,
)
from aidants_connect_web.models import (
    Aidant,
    HabilitationRequest,
    Journal,
    Mandat,
    Organisation,
)
from aidants_connect_web.tests.factories import (
    AidantFactory,
    HabilitationRequestFactory,
    MandatFactory,
    OrganisationFactory,
)


@tag("admin")
class TestAidantInPreDesactivationZoneFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation1 = OrganisationFactory()

        cls.aidant1 = AidantFactory(
            organisation=cls.organisation1, deactivation_warning_at=None
        )

        cls.aidant2 = AidantFactory(
            organisation=cls.organisation1, deactivation_warning_at=now()
        )

    def test_queryset(self):
        all_filter = AidantInPreDesactivationZoneFilter(
            self.client.get("/"), {}, Aidant, AidantAdmin
        )

        self.assertEqual(
            set(Aidant.objects.all()),
            set(all_filter.queryset(self.client.get("/"), Aidant.objects.all())),
        )

        not_in_desactivation_zone = AidantInPreDesactivationZoneFilter(
            self.client.get("/"),
            {AidantInPreDesactivationZoneFilter.parameter_name: "false"},
            Aidant,
            AidantAdmin,
        )

        self.assertEqual(
            {self.aidant1},
            set(
                not_in_desactivation_zone.queryset(
                    self.client.get("/"), Aidant.objects.all()
                )
            ),
        )

        in_desactivation_zone = AidantInPreDesactivationZoneFilter(
            self.client.get("/"),
            {AidantInPreDesactivationZoneFilter.parameter_name: "true"},
            Aidant,
            AidantAdmin,
        )
        self.assertEqual(
            {self.aidant2},
            set(
                in_desactivation_zone.queryset(
                    self.client.get("/"),
                    Aidant.objects.filter(organisation=self.organisation1),
                ).order_by("pk")
            ),
        )


@tag("admin")
class TestAidantAdmin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation1 = OrganisationFactory()
        cls.aidant_marge = AidantFactory(
            first_name="Marge",
            organisation=cls.organisation1,
            can_create_mandats=False,
            email="marge@simpson.com",
        )
        cls.aidant_marge.responsable_de.add(cls.organisation1)
        cls.aidant_homer = AidantFactory(
            first_name="Homer",
            organisation=cls.organisation1,
            can_create_mandats=True,
            email="homer@simpson.com",
        )

    def test_add_habilitationrequest_to_manager(self):
        self.assertEqual(0, HabilitationRequest.objects.count())
        AidantAdmin._add_habilitationrequest_to_manager(Aidant.objects.all())
        self.assertEqual(1, HabilitationRequest.objects.count())
        self.assertEqual(
            1, HabilitationRequest.objects.filter(email="marge@simpson.com").count()
        )

    def test_add_habilitationrequest_to_manager2(self):
        self.assertEqual(0, HabilitationRequest.objects.count())
        for one_aidant in Aidant.objects.all():
            Manager.objects.create(
                address="adr",
                zipcode="ZIP",
                city="City",
                is_aidant=True,
                phone="0112121212",
                email=one_aidant.email,
                first_name=one_aidant.first_name,
                last_name=one_aidant.last_name,
            )

        AidantAdmin._add_habilitationrequest_to_manager(Aidant.objects.all())
        self.assertEqual(1, HabilitationRequest.objects.count())
        self.assertEqual(
            1, HabilitationRequest.objects.filter(email="marge@simpson.com").count()
        )
        hr = HabilitationRequest.objects.filter(email="marge@simpson.com").first()
        self.assertEqual(
            1, Manager.objects.filter(habilitation_request__isnull=False).count()
        )
        self.assertTrue(Manager.objects.filter(habilitation_request=hr))


@tag("admin")
class TestAidantWithMandatsFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation1 = OrganisationFactory()
        cls.organisation2 = OrganisationFactory()

        cls.aidant_with_mandat1 = AidantFactory(organisation=cls.organisation1)
        cls.mandat1: Mandat = MandatFactory()
        Journal.log_attestation_creation(
            aidant=cls.aidant_with_mandat1,
            usager=cls.mandat1.usager,
            demarches=list(
                cls.mandat1.autorisations.values_list("demarche", flat=True)
            ),
            duree=AuthorizationDurations.duration(cls.mandat1.duree_keyword, now()),
            is_remote_mandat=False,
            access_token="",
            attestation_hash="",
            mandat=cls.mandat1,
            remote_constent_method="",
            user_phone="",
            consent_request_id="",
        )

        cls.aidant_without_mandat1 = AidantFactory(organisation=cls.organisation1)
        cls.aidant_with_mandat2 = AidantFactory(organisation=cls.organisation2)
        cls.mandat2 = MandatFactory()
        Journal.log_attestation_creation(
            aidant=cls.aidant_with_mandat2,
            usager=cls.mandat2.usager,
            demarches=list(
                cls.mandat2.autorisations.values_list("demarche", flat=True)
            ),
            duree=AuthorizationDurations.duration(cls.mandat2.duree_keyword, now()),
            is_remote_mandat=False,
            access_token="",
            attestation_hash="",
            mandat=cls.mandat2,
            remote_constent_method="",
            user_phone="",
            consent_request_id="",
        )
        cls.aidant_without_mandat2 = AidantFactory(organisation=cls.organisation2)

    def test_queryset(self):
        all_filter = AidantWithMandatsFilter(
            self.client.get("/"), {}, Aidant, AidantAdmin
        )

        self.assertEqual(
            set(Aidant.objects.all()),
            set(all_filter.queryset(self.client.get("/"), Aidant.objects.all())),
        )

        with_mandates_filter = AidantWithMandatsFilter(
            self.client.get("/"),
            {AidantWithMandatsFilter.parameter_name: "true"},
            Aidant,
            AidantAdmin,
        )

        self.assertEqual(
            {self.aidant_with_mandat1, self.aidant_with_mandat2},
            set(
                with_mandates_filter.queryset(
                    self.client.get("/"), Aidant.objects.all()
                )
            ),
        )

        self.assertEqual(
            {self.aidant_with_mandat1},
            set(
                with_mandates_filter.queryset(
                    self.client.get("/"),
                    Aidant.objects.filter(organisation=self.organisation1),
                ).order_by("pk")
            ),
        )


@tag("admin")
class DepartmentFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rf = RequestFactory()

    def test_generate_filter_list(self):
        result = DepartmentFilter.generate_filter_list()
        self.assertEqual(len(result), 102)
        self.assertEqual(("01", "Ain (01)"), result[0])
        self.assertEqual(("2A", "Corse-du-Sud (20)"), result[19])

    def test_lookup(self):
        request = self.rf.get("/")
        dep_filter = DepartmentFilter(request, {}, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 102)

    def test_lookups_with_selected_region(self):
        params = {
            "region": Region.objects.get(name="Provence-Alpes-Côte d'Azur").insee_code
        }
        request = self.rf.get("/", params)
        dep_filter = DepartmentFilter(request, params, Organisation, OrganisationAdmin)
        self.assertEqual(len(dep_filter.lookups(request, {})), 6)

    def test_queryset(self):
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="20000")
        OrganisationFactory(zipcode="0")
        corse_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "20"}, Organisation, OrganisationAdmin
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        bdc_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "13"}, Organisation, OrganisationAdmin
        )
        queryset_bdc = bdc_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(2, queryset_bdc.count())
        self.assertEqual("13013", queryset_bdc[0].zipcode)

        other_filter = DepartmentFilter(
            self.rf.get("/"), {"department": "other"}, Organisation, OrganisationAdmin
        )
        queryset_other = other_filter.queryset(
            self.rf.get("/"), Organisation.objects.all()
        )
        self.assertEqual(1, queryset_other.count())
        self.assertEqual("0", queryset_other[0].zipcode)


@tag("admin")
class RegionFilterTests(TestCase):
    def test_queryset(self):
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="13013")
        OrganisationFactory(zipcode="20000")
        OrganisationFactory(zipcode="0")
        corse_filter = RegionFilter(
            None,
            {"region": Region.objects.get(name="Corse").insee_code},
            Organisation,
            OrganisationAdmin,
        )
        queryset_corse = corse_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_corse.count())
        self.assertEqual("20000", queryset_corse[0].zipcode)

        paca_filter = RegionFilter(
            None,
            {
                "region": Region.objects.get(
                    name="Provence-Alpes-Côte d'Azur"
                ).insee_code
            },
            Organisation,
            OrganisationAdmin,
        )
        queryset_paca = paca_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(2, queryset_paca.count())
        self.assertEqual("13013", queryset_paca[0].zipcode)

        other_filter = RegionFilter(
            None, {"region": "other"}, Organisation, OrganisationAdmin
        )
        queryset_other = other_filter.queryset(None, Organisation.objects.all())
        self.assertEqual(1, queryset_other.count())
        self.assertEqual("0", queryset_other[0].zipcode)


@tag("admin")
class HabilitationRequestAdminTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.habilitation_request_admin = HabilitationRequestAdmin(
            HabilitationRequest, AdminSite()
        )

    @classmethod
    def setUpTestData(cls):
        cls.organisation = OrganisationFactory()
        cls.habilitation_request = HabilitationRequestFactory(
            organisation=cls.organisation
        )
        cls.manager = AidantFactory(
            organisation=cls.organisation, post__is_organisation_manager=True
        )

        cls.inactive_manager = AidantFactory(
            is_active=False,
            organisation=cls.organisation,
            post__is_organisation_manager=True,
        )

    def test_send_validation_email(self):
        self.assertEqual(len(mail.outbox), 0)

        self.habilitation_request_admin.send_validation_email(self.habilitation_request)

        self.assertEqual(len(mail.outbox), 1)

        validation_message = mail.outbox[0]

        self.assertIn(
            str(self.habilitation_request.first_name), validation_message.subject
        )

        self.assertEqual(len(validation_message.recipients()), 1)
        self.assertTrue(
            all(
                manager.email in validation_message.recipients()
                for manager in self.habilitation_request.organisation.responsables.filter(  # noqa
                    is_active=True
                )
            )
        )

    def test_send_refusal_email(self):
        self.assertEqual(len(mail.outbox), 0)

        self.habilitation_request_admin.send_refusal_email(self.habilitation_request)

        self.assertEqual(len(mail.outbox), 1)

        refusal_message = mail.outbox[0]

        self.assertIn(
            str(self.habilitation_request.first_name), refusal_message.subject
        )

        self.assertEqual(len(refusal_message.recipients()), 1)
        self.assertTrue(
            all(
                manager.email in refusal_message.recipients()
                for manager in self.habilitation_request.organisation.responsables.filter(  # noqa
                    is_active=True
                )
            )
        )

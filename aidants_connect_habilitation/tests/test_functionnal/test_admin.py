from urllib.parse import urlparse

from django.test import tag
from django.urls import reverse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import url_matches
from selenium.webdriver.support.wait import WebDriverWait

from aidants_connect_common.tests.testcases import FunctionalTestCase
from aidants_connect_common.utils.constants import RequestStatusConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory
from aidants_connect_web.models import Aidant
from aidants_connect_web.tests.factories import AdminFactory


@tag("functional")
class OrganisationRequestAdminTests(FunctionalTestCase):
    def setUp(self):
        super().setUp()
        self.password = "123456789"
        self.otp = "123456"
        self.aidant: Aidant = AdminFactory(
            password=self.password, post__with_otp_device=self.otp
        )

    def test_filters_are_presereved_throughout_acceptance_process(self):
        self.admin_login(self.aidant.email, self.password, self.otp)

        organisation_status = RequestStatusConstants.AC_VALIDATION_PROCESSING

        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=organisation_status.name
        )

        # Open the list of organisation requests
        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        self.open_live_url(path)

        # Filter by status
        self.selenium.find_element(
            By.CSS_SELECTOR, f'[title="{organisation_status.value}"'
        ).click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

        # Navigate to the organisation detail
        self.selenium.find_element(
            By.XPATH, f"//a[normalize-space(text())='{organisation.name}']"
        ).click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_change",
            kwargs={"object_id": organisation.id},
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        href = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_accept",
            kwargs={"object_id": organisation.id},
        )

        # Move to second step
        self.selenium.find_element(By.XPATH, f'//a[contains(@href, "{href}")]').click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{href}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        # Definitely accept request
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

    def test_filters_are_presereved_throughout_refusal_process(self):
        self.admin_login(self.aidant.email, self.password, self.otp)

        organisation_status = RequestStatusConstants.AC_VALIDATION_PROCESSING

        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=organisation_status.name
        )

        # Open the list of organisation requests
        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        self.open_live_url(path)

        # Filter by status
        self.selenium.find_element(
            By.CSS_SELECTOR, f'[title="{organisation_status.value}"'
        ).click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

        # Navigate to the organisation detail
        self.selenium.find_element(
            By.XPATH, f"//a[normalize-space(text())='{organisation.name}']"
        ).click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_change",
            kwargs={"object_id": organisation.id},
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        href = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_refuse",
            kwargs={"object_id": organisation.id},
        )

        # Move to second step
        self.selenium.find_element(By.XPATH, f'//a[contains(@href, "{href}")]').click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{href}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        # Definitely deny request
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

    def test_filters_are_presereved_throughout_requiring_modification_process(self):
        self.admin_login(self.aidant.email, self.password, self.otp)

        organisation_status = RequestStatusConstants.AC_VALIDATION_PROCESSING

        organisation: OrganisationRequest = OrganisationRequestFactory(
            status=organisation_status.name
        )

        # Open the list of organisation requests
        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )
        self.open_live_url(path)

        # Filter by status
        self.selenium.find_element(
            By.CSS_SELECTOR, f'[title="{organisation_status.value}"'
        ).click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

        # Navigate to the organisation detail
        self.selenium.find_element(
            By.XPATH, f"//a[normalize-space(text())='{organisation.name}']"
        ).click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_change",
            kwargs={"object_id": organisation.id},
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        href = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_requirechanges",
            kwargs={"object_id": organisation.id},
        )

        # Move to second step
        self.selenium.find_element(By.XPATH, f'//a[contains(@href, "{href}")]').click()

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{href}\\?([^=]+=[^=]+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"_changelist_filters=status__exact%3D{organisation_status.name}",
        )

        # Definitely require changes
        self.selenium.find_element(By.CSS_SELECTOR, '[type="submit"]').click()

        path = reverse(
            "otpadmin:aidants_connect_habilitation_organisationrequest_changelist"
        )

        WebDriverWait(self.selenium, 10).until(
            url_matches(f"^.+{path}\\?(\\w+=\\w+)+$")
        )

        # Check filters were preserved
        self.assertEqual(
            urlparse(self.selenium.current_url).query,
            f"status__exact={organisation_status.name}",
        )

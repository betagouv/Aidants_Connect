import base64
import re
from unittest import mock
from unittest.mock import Mock

from django.test import TestCase, tag
from django.urls import resolve, reverse

from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from aidants_connect_web.constants import OTP_APP_DEVICE_NAME
from aidants_connect_web.models import Journal
from aidants_connect_web.tests.factories import AidantFactory
from aidants_connect_web.views import espace_responsable


@tag("responsable-structure", "otp-tunnel")
class OtpTunnelWelcomeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)
        cls.referent_with_otp = AidantFactory(post__is_organisation_manager=True)
        TOTPDevice.objects.create(
            user=cls.referent_with_otp,
            name=OTP_APP_DEVICE_NAME % cls.referent_with_otp.pk,
            confirmed=True,
        )
        cls.simple_aidant = AidantFactory()

    def test_url_resolves_to_welcome_view(self):
        found = resolve(reverse("espace_referent:otp_tunnel_welcome"))
        self.assertEqual(found.func.view_class, espace_responsable.OtpTunnelWelcomeView)

    def test_welcome_page_uses_correct_template(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_welcome"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/otp_tunnel/welcome.html",
        )

    def test_welcome_page_contains_expected_content(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_welcome"))
        self.assertContains(response, "Bienvenue")
        self.assertContains(response, "première connexion à l’espace référent")
        self.assertContains(response, "Faire plus tard")
        self.assertContains(response, "Associer l’application d’authentification")
        self.assertContains(response, "Associer une carte physique")

    def test_referent_with_otp_is_redirected_away_from_welcome(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_welcome"))
        self.assertRedirects(response, reverse("espace_referent:home"))

    def test_non_referent_aidant_cannot_access_welcome(self):
        self.client.force_login(self.simple_aidant)
        response = self.client.get(reverse("espace_referent:otp_tunnel_welcome"))
        # Non-referent users are redirected by the `@responsable_logged_required`
        # decorator to the aidant home (via login_url).
        self.assertNotEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        url = reverse("espace_referent:otp_tunnel_welcome")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)


@tag("responsable-structure", "otp-tunnel")
class OtpTunnelDismissViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)

    def test_url_resolves_to_dismiss_view(self):
        found = resolve(reverse("espace_referent:otp_tunnel_dismiss"))
        self.assertEqual(found.func.view_class, espace_responsable.OtpTunnelDismissView)

    def test_dismiss_redirects_to_home_and_sets_session_flag(self):
        self.client.force_login(self.referent_without_otp)

        response = self.client.post(
            reverse("espace_referent:otp_tunnel_dismiss"),
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.client.session.get(espace_responsable.OTP_TUNNEL_DISMISSED_SESSION_KEY)
        )

    def test_dismiss_rejects_get_to_avoid_state_change_via_get(self):
        self.client.force_login(self.referent_without_otp)

        response = self.client.get(reverse("espace_referent:otp_tunnel_dismiss"))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(
            self.client.session.get(espace_responsable.OTP_TUNNEL_DISMISSED_SESSION_KEY)
        )

    def test_dismiss_prevents_home_view_from_redirecting_to_tunnel(self):
        self.client.force_login(self.referent_without_otp)

        response = self.client.get(reverse("espace_referent:home"))
        self.assertRedirects(response, reverse("espace_referent:otp_tunnel_welcome"))

        self.client.post(reverse("espace_referent:otp_tunnel_dismiss"))

        response = self.client.get(reverse("espace_referent:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/home.html"
        )


@tag("responsable-structure", "otp-tunnel")
class OtpTunnelDownloadAppViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)
        cls.referent_with_otp = AidantFactory(post__is_organisation_manager=True)
        TOTPDevice.objects.create(
            user=cls.referent_with_otp,
            name=OTP_APP_DEVICE_NAME % cls.referent_with_otp.pk,
            confirmed=True,
        )
        cls.simple_aidant = AidantFactory()

    def test_url_resolves_to_download_app_view(self):
        found = resolve(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertEqual(
            found.func.view_class, espace_responsable.OtpTunnelDownloadAppView
        )

    def test_download_app_uses_correct_template(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/otp_tunnel/download_app.html",
        )

    def test_download_app_contains_expected_content(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertContains(response, "Télécharger une application d’authentification")
        self.assertContains(response, "Étape 1 sur 3")
        self.assertContains(response, "FreeOTP Authenticator")
        self.assertContains(response, "Google Authenticator")
        self.assertContains(response, "Microsoft Authenticator")
        self.assertContains(response, "Retour")
        self.assertContains(response, "Étape suivante")

    def test_download_app_back_button_points_to_welcome(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertContains(response, reverse("espace_referent:otp_tunnel_welcome"))

    def test_download_app_exposes_stepper_context(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertEqual(response.context["wizard_step"], 1)
        self.assertEqual(
            response.context["wizard_total_steps"],
            espace_responsable.OTP_TUNNEL_TOTAL_STEPS,
        )

    def test_referent_with_otp_is_redirected_away_from_download_app(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertRedirects(response, reverse("espace_referent:home"))

    def test_non_referent_aidant_cannot_access_download_app(self):
        self.client.force_login(self.simple_aidant)
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertNotEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("espace_referent:otp_tunnel_download_app"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)


@tag("responsable-structure", "otp-tunnel")
class OtpTunnelScanQrCodeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)
        cls.referent_with_otp = AidantFactory(post__is_organisation_manager=True)
        TOTPDevice.objects.create(
            user=cls.referent_with_otp,
            name=OTP_APP_DEVICE_NAME % cls.referent_with_otp.pk,
            confirmed=True,
        )
        cls.simple_aidant = AidantFactory()

    def test_url_resolves_to_scan_qr_code_view(self):
        found = resolve(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertEqual(
            found.func.view_class, espace_responsable.OtpTunnelScanQrCodeView
        )

    def test_scan_qr_code_uses_correct_template(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/otp_tunnel/scan_qr_code.html",
        )

    def test_scan_qr_code_contains_expected_content(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertContains(response, "Étape 2 sur 3")
        self.assertContains(
            response, "Ajouter le compte Aidants Connect sur l’application"
        )
        self.assertContains(
            response,
            "Utilisez votre application d’Authentification pour scanner le code QR",
        )
        self.assertContains(
            response,
            "Entrez le code de vérification à 6 chiffres affiché sur votre applicat",
        )
        self.assertContains(response, "Afficher la clé")
        self.assertContains(response, "data-key-summary-label")
        self.assertContains(response, "Retour")
        self.assertContains(response, "Étape suivante")

    def test_scan_qr_code_exposes_otp_code_input(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        otp_input = re.search(
            r'<input[^>]*id="id_otp_token"[^>]*>',
            response.content.decode(),
        )
        self.assertIsNotNone(otp_input)
        self.assertIn('name="otp_token"', otp_input.group())
        self.assertIn('type="text"', otp_input.group())

    def test_scan_qr_code_back_button_points_to_download_app(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertContains(
            response, reverse("espace_referent:otp_tunnel_download_app")
        )

    def test_scan_qr_code_exposes_stepper_context(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertEqual(response.context["wizard_step"], 2)
        self.assertEqual(
            response.context["wizard_total_steps"],
            espace_responsable.OTP_TUNNEL_TOTAL_STEPS,
        )

    def test_scan_qr_code_displays_qr_code_as_data_uri(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertIn("otp_device_qr_code_href", response.context)
        self.assertTrue(
            response.context["otp_device_qr_code_href"].startswith(
                "data:image/png;base64,"
            )
        )
        self.assertContains(response, "data:image/png;base64,")

    def test_scan_qr_code_displays_secret_key_in_base32(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        session_device = self.client.session[
            espace_responsable.OTP_TUNNEL_DEVICE_SESSION_KEY
        ]
        device = TOTPDevice(
            **espace_responsable.OtpTunnelScanQrCodeView._device_kwargs_from_session(
                session_device
            )
        )
        expected_secret = base64.b32encode(device.bin_key).decode("ascii")
        self.assertEqual(response.context["otp_device_secret_key"], expected_secret)
        self.assertEqual(len(expected_secret), 32)
        self.assertContains(response, expected_secret)

    def test_scan_qr_code_stores_unconfirmed_otp_device_in_session(self):
        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        session_device = self.client.session.get(
            espace_responsable.OTP_TUNNEL_DEVICE_SESSION_KEY
        )
        self.assertIsNotNone(session_device)
        # The device owner is intentionally not stored in session; it is always
        # rebuilt from request.user on POST.
        self.assertNotIn("user", session_device)
        self.assertEqual(
            session_device["name"],
            OTP_APP_DEVICE_NAME % self.referent_without_otp.pk,
        )
        self.assertFalse(session_device["confirmed"])

    def test_scan_qr_code_does_not_persist_otp_device_in_database_on_get(self):
        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertFalse(
            TOTPDevice.objects.filter(user=self.referent_without_otp).exists()
        )

    @mock.patch.object(TOTP, "verify")
    def test_scan_qr_code_invalid_otp_token_does_not_create_device(
        self, mock_verify: Mock
    ):
        mock_verify.return_value = False

        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))

        response = self.client.post(
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            data={"otp_token": "654321"},
        )
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/otp_tunnel/scan_qr_code.html",
        )
        self.assertFalse(
            TOTPDevice.objects.filter(user=self.referent_without_otp).exists()
        )

    @mock.patch.object(TOTP, "verify")
    def test_scan_qr_code_valid_otp_token_creates_confirmed_device_and_redirects(
        self, mock_verify: Mock
    ):
        mock_verify.return_value = True

        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))

        response = self.client.post(
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            data={"otp_token": "123456"},
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:otp_tunnel_congratulations"),
            fetch_redirect_response=False,
        )

        device_qs = TOTPDevice.objects.filter(user=self.referent_without_otp)
        self.assertEqual(device_qs.count(), 1)
        device = device_qs.first()
        self.assertTrue(device.confirmed)
        self.assertEqual(
            device.name, OTP_APP_DEVICE_NAME % self.referent_without_otp.pk
        )

        self.assertNotIn(
            espace_responsable.OTP_TUNNEL_DEVICE_SESSION_KEY, self.client.session
        )

    @mock.patch.object(TOTP, "verify")
    def test_scan_qr_code_valid_otp_token_logs_card_association_journal_entry(
        self, mock_verify: Mock
    ):
        mock_verify.return_value = True

        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))

        previous_journal_count = Journal.objects.count()
        self.client.post(
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            data={"otp_token": "123456"},
        )
        self.assertGreater(Journal.objects.count(), previous_journal_count)

    @mock.patch.object(TOTP, "verify")
    def test_scan_qr_code_confirms_device_for_current_referent_only(
        self, mock_verify: Mock
    ):
        # Even if the session payload carries a foreign owner (e.g. left over
        # from another OTP flow), the confirmed device must belong to the
        # logged-in referent and never to that other user.
        mock_verify.return_value = True

        self.client.force_login(self.referent_without_otp)
        self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))

        session = self.client.session
        session[espace_responsable.OTP_TUNNEL_DEVICE_SESSION_KEY][
            "user"
        ] = self.simple_aidant.pk
        session.save()

        self.client.post(
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            data={"otp_token": "123456"},
        )

        self.assertFalse(TOTPDevice.objects.filter(user=self.simple_aidant).exists())
        self.assertTrue(
            TOTPDevice.objects.filter(
                user=self.referent_without_otp, confirmed=True
            ).exists()
        )

    def test_scan_qr_code_post_without_session_restarts_at_scan_qr_code(self):
        self.client.force_login(self.referent_without_otp)
        # No prior GET → no device in session → POST should redirect back.
        response = self.client.post(
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            data={"otp_token": "123456"},
        )
        self.assertRedirects(
            response,
            reverse("espace_referent:otp_tunnel_scan_qr_code"),
            fetch_redirect_response=False,
        )

    def test_referent_with_otp_is_redirected_away_from_scan_qr_code(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertRedirects(response, reverse("espace_referent:home"))

    def test_non_referent_aidant_cannot_access_scan_qr_code(self):
        self.client.force_login(self.simple_aidant)
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertNotEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("espace_referent:otp_tunnel_scan_qr_code"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)


@tag("responsable-structure", "otp-tunnel")
class OtpTunnelCongratulationsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)
        cls.referent_with_otp = AidantFactory(post__is_organisation_manager=True)
        TOTPDevice.objects.create(
            user=cls.referent_with_otp,
            name=OTP_APP_DEVICE_NAME % cls.referent_with_otp.pk,
            confirmed=True,
        )
        cls.simple_aidant = AidantFactory()

    def test_url_resolves_to_congratulations_view(self):
        found = resolve(reverse("espace_referent:otp_tunnel_congratulations"))
        self.assertEqual(
            found.func.view_class, espace_responsable.OtpTunnelCongratulationsView
        )

    def test_congratulations_uses_correct_template(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "aidants_connect_web/espace_responsable/otp_tunnel/congratulations.html",
        )

    def test_congratulations_contains_expected_content(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertContains(response, "Félicitations")
        self.assertContains(response, "Étape 3 sur 3")
        self.assertContains(response, "Accéder à l’espace référent")
        self.assertContains(response, "L’application est associée à votre compte")
        self.assertNotContains(response, "Faire plus tard")

    def test_congratulations_navigation_links_point_to_expected_urls(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertContains(response, reverse("espace_referent:home"))

    def test_congratulations_exposes_stepper_context(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertEqual(response.context["wizard_step"], 3)
        self.assertEqual(
            response.context["wizard_total_steps"],
            espace_responsable.OTP_TUNNEL_TOTAL_STEPS,
        )

    def test_referent_without_otp_is_redirected_to_download_app(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertRedirects(
            response, reverse("espace_referent:otp_tunnel_download_app")
        )

    def test_non_referent_aidant_cannot_access_congratulations(self):
        self.client.force_login(self.simple_aidant)
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertNotEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("espace_referent:otp_tunnel_congratulations")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)


@tag("responsable-structure", "otp-tunnel")
class HomeViewOtpTunnelRedirectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.referent_without_otp = AidantFactory(post__is_organisation_manager=True)
        cls.referent_with_otp = AidantFactory(post__is_organisation_manager=True)
        TOTPDevice.objects.create(
            user=cls.referent_with_otp,
            name=OTP_APP_DEVICE_NAME % cls.referent_with_otp.pk,
            confirmed=True,
        )

    def test_referent_without_otp_is_redirected_to_welcome(self):
        self.client.force_login(self.referent_without_otp)
        response = self.client.get(reverse("espace_referent:home"))
        self.assertRedirects(response, reverse("espace_referent:otp_tunnel_welcome"))

    def test_referent_with_otp_lands_on_home_normally(self):
        self.client.force_login(self.referent_with_otp)
        response = self.client.get(reverse("espace_referent:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "aidants_connect_web/espace_responsable/home.html"
        )

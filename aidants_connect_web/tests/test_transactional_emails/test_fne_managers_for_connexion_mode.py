from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import now

from aidants_connect_web.constants import CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE
from aidants_connect_web.tests.factories import (
    AidantFactory,
    LogEmailSendingFactory,
    OrganisationFactory,
    TOTPDeviceFactory,
)
from aidants_connect_web.transactional_emails.fne_managers_for_connexion_mode import (
    get_managers_fne,
    need_send_emails_to_manager,
)


class FNEManagerConnexionModeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.orga = OrganisationFactory()
        cls.referent_fne = AidantFactory(created_by_fne=True, last_login=now())
        cls.referent_fne.responsable_de.add(cls.orga)

        cls.referent_fne_without_login = AidantFactory(
            created_by_fne=True, last_login=None
        )
        cls.referent_fne_without_login.responsable_de.add(cls.orga)

        cls.aidant_fne = AidantFactory(created_by_fne=True, last_login=now())

        cls.referent_not_fne = AidantFactory(created_by_fne=False, last_login=None)
        cls.referent_not_fne.responsable_de.add(cls.orga)

        cls.referent_fne_with_totpd = AidantFactory(
            created_by_fne=True, last_login=now()
        )
        cls.referent_fne_with_totpd.responsable_de.add(cls.orga)
        TOTPDeviceFactory(user=cls.referent_fne_with_totpd)

    def test_get_managers_fne(self):
        managers = get_managers_fne()
        self.assertEqual(len(managers), 3)
        self.assertTrue(self.referent_fne in managers)
        self.assertTrue(self.referent_fne_without_login in managers)
        self.assertTrue(self.referent_fne_with_totpd in managers)

    def test_need_send_emails_to_manager(self):

        self.assertTrue(need_send_emails_to_manager(self.referent_fne))
        self.assertTrue(need_send_emails_to_manager(self.referent_fne_without_login))
        self.assertFalse(need_send_emails_to_manager(self.referent_fne_with_totpd))

        LogEmailSendingFactory(
            code_email=CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE,
            aidant=self.referent_fne,
            last_sending_date=now(),
        )
        self.assertFalse(need_send_emails_to_manager(self.referent_fne))

        LogEmailSendingFactory(
            code_email=CODE_EMAIL_FNE_MANAGER_CONNEXION_MODE,
            aidant=self.referent_fne,
            last_sending_date=now() - timezone.timedelta(days=16),
        )
        self.assertTrue(need_send_emails_to_manager(self.referent_fne_without_login))

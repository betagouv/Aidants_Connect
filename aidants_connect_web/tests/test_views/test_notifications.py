from django.test import TestCase
from django.urls import resolve, reverse

from aidants_connect_web.models import Notification
from aidants_connect_web.tests.factories import AidantFactory, NotificationFactory
from aidants_connect_web.views import notifications


class NotificationsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory()
        cls.unread_notification: Notification = NotificationFactory(
            was_ack=False, aidant=cls.aidant
        )
        cls.read_notification: Notification = NotificationFactory(
            was_ack=True, aidant=cls.aidant
        )

    def test_triggers_correct_view(self):
        found = resolve(reverse("notification_list"))
        self.assertEqual(found.func.view_class, notifications.Notifications)

    def test_renders_correct_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(reverse("notification_list"))
        self.assertTemplateUsed(
            response, "aidants_connect_web/notifications/notification_list.html"
        )


class NotificationDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aidant = AidantFactory()
        cls.aidant2 = AidantFactory()
        cls.notification: Notification = NotificationFactory(
            was_ack=False, aidant=cls.aidant
        )

    def test_triggers_correct_view(self):
        found = resolve(
            reverse(
                "notification_detail", kwargs={"notification_id": self.notification.pk}
            )
        )
        self.assertEqual(found.func.view_class, notifications.NotificationDetail)

    def test_renders_correct_template(self):
        self.client.force_login(self.aidant)
        response = self.client.get(
            reverse(
                "notification_detail", kwargs={"notification_id": self.notification.pk}
            )
        )
        self.assertTemplateUsed(
            response, "aidants_connect_web/notifications/notification_detail.html"
        )

    def test_delete_fails_on_other_aidant_notification(self):
        self.client.force_login(self.aidant2)
        response = self.client.get(
            reverse(
                "notification_detail", kwargs={"notification_id": self.notification.pk}
            )
        )
        self.assertEqual(404, response.status_code)


class MarkNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Notification should be dismissable even if aidant can't create mandats
        cls.aidant = AidantFactory(can_create_mandats=False)
        cls.aidant2 = AidantFactory(can_create_mandats=False)

        cls.unread_notification: Notification = NotificationFactory(
            was_ack=False, aidant=cls.aidant
        )
        cls.read_notification: Notification = NotificationFactory(
            was_ack=True, aidant=cls.aidant
        )

    def test_post(self):
        self.assertFalse(self.unread_notification.was_ack)
        self.client.force_login(self.aidant)
        response = self.client.post(
            reverse(
                "notification_mark",
                kwargs={"notification_id": self.unread_notification.pk},
            )
        )
        self.assertEqual(200, response.status_code)
        self.unread_notification.refresh_from_db()
        self.assertFalse(self.unread_notification.was_ack)

    def test_post_fails_on_other_aidant_notification(self):
        self.client.force_login(self.aidant2)
        response = self.client.post(
            reverse(
                "notification_mark",
                kwargs={"notification_id": self.unread_notification.pk},
            )
        )
        self.assertEqual(404, response.status_code)

    def test_delete(self):
        self.assertTrue(self.read_notification.was_ack)
        self.client.force_login(self.aidant)
        response = self.client.delete(
            reverse(
                "notification_mark",
                kwargs={"notification_id": self.read_notification.pk},
            )
        )
        self.assertEqual(200, response.status_code)
        self.read_notification.refresh_from_db()
        self.assertTrue(self.read_notification.was_ack)

    def test_delete_fails_on_other_aidant_notification(self):
        self.client.force_login(self.aidant2)
        response = self.client.post(
            reverse(
                "notification_mark",
                kwargs={"notification_id": self.unread_notification.pk},
            )
        )
        self.assertEqual(404, response.status_code)

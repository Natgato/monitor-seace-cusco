import unittest
from dataclasses import replace

from seace_monitor.config import Config
from seace_monitor.notifier import NotificationError, build_email


class EmailNotifierTests(unittest.TestCase):
    def test_builds_multipart_email_without_sending(self):
        config = replace(Config(), notification_channel="gmail", gmail_address="monitor@example.com", gmail_app_password="secret", alert_email_to="destino@example.com")
        message = build_email(config, ["<b>Nueva contratación</b>"])
        self.assertEqual(message["To"], "destino@example.com")
        self.assertTrue(message.is_multipart())

    def test_requires_all_gmail_credentials(self):
        config = replace(Config(), notification_channel="gmail", gmail_address=None, gmail_app_password=None, alert_email_to=None)
        with self.assertRaises(NotificationError):
            build_email(config, ["mensaje"])

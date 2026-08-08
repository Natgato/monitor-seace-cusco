import unittest
from dataclasses import replace

from seace_monitor.config import Config
from seace_monitor.notifier import EmailAttachment, NotificationError, build_email, email_recipients


class EmailNotifierTests(unittest.TestCase):
    def setUp(self):
        self.config = replace(
            Config(),
            notification_channel="gmail",
            gmail_address="monitor@example.com",
            gmail_app_password="secret",
            alert_email_to="destino@example.com",
        )

    def test_builds_multipart_email_without_sending(self):
        message = build_email(self.config, ["<b>Nueva contratación</b>"])
        self.assertEqual(message["To"], "destino@example.com")
        self.assertTrue(message.is_multipart())

    def test_attaches_pdf(self):
        attachment = EmailAttachment("informe.pdf", b"%PDF-test", subtype="pdf")
        message = build_email(self.config, ["resumen"], attachments=[attachment])
        files = list(message.iter_attachments())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].get_filename(), "informe.pdf")
        self.assertEqual(files[0].get_content_type(), "application/pdf")

    def test_parses_multiple_recipients_and_removes_duplicates(self):
        recipients = email_recipients("uno@example.com, DOS@example.com; uno@example.com")
        self.assertEqual(recipients, ["uno@example.com", "DOS@example.com"])

    def test_requires_all_gmail_credentials(self):
        config = replace(self.config, gmail_address=None, gmail_app_password=None, alert_email_to=None)
        with self.assertRaises(NotificationError):
            build_email(config, ["mensaje"])

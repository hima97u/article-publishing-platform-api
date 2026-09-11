from unittest.mock import patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase

from core_apps.common.email import CeleryEmailBackend


class CeleryEmailBackendTests(SimpleTestCase):
    @patch("core_apps.common.email.deliver_email.delay")
    def test_queues_alternative_email_with_binary_attachment(self, delay):
        message = EmailMultiAlternatives(
            "Subject",
            "Plain text",
            "from@example.com",
            ["to@example.com"],
        )
        message.attach_alternative("<p>HTML</p>", "text/html")
        message.attach("report.txt", b"report", "text/plain")

        result = CeleryEmailBackend().send_messages([message])

        self.assertEqual(result, 1)
        delay.assert_called_once()
        payload = delay.call_args.args[0]
        self.assertEqual(payload["alternatives"][0]["mimetype"], "text/html")
        self.assertEqual(payload["attachments"][0]["content"], "report")
        self.assertFalse(payload["attachments"][0]["encoded"])

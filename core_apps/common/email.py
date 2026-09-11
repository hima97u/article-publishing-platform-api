import base64

from django.core.mail.backends.base import BaseEmailBackend

from .tasks import deliver_email


class CeleryEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        queued = 0
        for message in email_messages:
            if not message.recipients():
                continue
            deliver_email.delay(self._serialize_message(message))
            queued += 1
        return queued

    @staticmethod
    def _serialize_message(message):
        alternatives = []
        for alternative in message.alternatives:
            if isinstance(alternative, dict):
                content = alternative["content"]
                mimetype = alternative["mimetype"]
            else:
                content, mimetype = alternative
            alternatives.append({"content": content, "mimetype": mimetype})

        attachments = []
        for attachment in message.attachments:
            if isinstance(attachment, dict):
                content = attachment["content"]
                is_binary = isinstance(content, bytes)
                attachments.append(
                    {
                        **attachment,
                        "content": base64.b64encode(content).decode("ascii")
                        if is_binary
                        else content,
                        "encoded": is_binary,
                    }
                )
                continue
            filename, content, mimetype = attachment
            is_binary = isinstance(content, bytes)
            attachments.append(
                {
                    "filename": filename,
                    "content": base64.b64encode(content).decode("ascii")
                    if is_binary
                    else content,
                    "encoded": is_binary,
                    "mimetype": mimetype,
                }
            )

        return {
            "subject": message.subject,
            "body": message.body,
            "from_email": message.from_email,
            "to": message.to,
            "bcc": message.bcc,
            "cc": message.cc,
            "reply_to": message.reply_to,
            "headers": message.extra_headers,
            "alternatives": alternatives,
            "attachments": attachments,
        }

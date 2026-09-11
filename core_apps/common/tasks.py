import base64

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend


@shared_task(
    bind=True,
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def deliver_email(self, message_data):
    message = EmailMultiAlternatives(
        subject=message_data["subject"],
        body=message_data["body"],
        from_email=message_data["from_email"],
        to=message_data["to"],
        bcc=message_data["bcc"],
        cc=message_data["cc"],
        reply_to=message_data["reply_to"],
        headers=message_data["headers"],
    )
    for alternative in message_data["alternatives"]:
        message.attach_alternative(alternative["content"], alternative["mimetype"])
    for attachment in message_data["attachments"]:
        message.attach(
            attachment["filename"],
            base64.b64decode(attachment["content"])
            if attachment.get("encoded", False)
            else attachment["content"],
            attachment["mimetype"],
        )
    with EmailBackend(fail_silently=False) as connection:
        connection.send_messages([message])

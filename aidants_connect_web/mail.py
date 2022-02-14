import json
from smtplib import SMTPException

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.message import EmailMessage, sanitize_address


class ForceSpecificSenderBackend(EmailBackend):
    """
    An email backend which forces sender email to settings.EMAIL_SENDER,
    leaving original sender email in header "reply-to",
    and add extra headers to emails (provided in JSON in settings.EMAIL_EXTRA_HEADERS).
    """

    def _send(self, email_message: EmailMessage):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        encoding = email_message.encoding or settings.DEFAULT_CHARSET
        # Specific
        email_message.extra_headers["Reply-To"] = sanitize_address(
            email_message.from_email, encoding
        )
        email_message.from_email = settings.EMAIL_SENDER
        for key, value in json.loads(settings.EMAIL_EXTRA_HEADERS).items():
            email_message.extra_headers[key] = value
        # /Specific
        from_email = sanitize_address(email_message.from_email, encoding)
        recipients = [
            sanitize_address(addr, encoding) for addr in email_message.recipients()
        ]
        message = email_message.message()
        try:
            self.connection.sendmail(
                from_email, recipients, message.as_bytes(linesep="\r\n")
            )
        except SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True

from smtplib import SMTPException

from django.conf import settings

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.message import EmailMessage, sanitize_address


class DolistBackend(EmailBackend):
    """
    An email backend dedicated to DoList, with an extra header to provide account id
    """

    def _send(self, email_message: EmailMessage):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        encoding = email_message.encoding or settings.DEFAULT_CHARSET
        # Dolist specific
        email_message.extra_headers["X-Account-ID"] = settings.DOLIST_ACCOUNT
        email_message.reply_to = sanitize_address(email_message.from_email, encoding)
        email_message.from_email = settings.DOLIST_SENDER
        # /Dolist specific
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

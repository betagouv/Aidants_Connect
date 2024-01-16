from pathlib import Path
from typing import Iterable

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.filebased import EmailBackend as FileBasedEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class DebugEmailBackend(FileBasedEmailBackend):
    def write_message(self, message):
        html = next(
            (
                content
                for content, mime_type in getattr(message, "alternatives", [])
                if mime_type == "text/html"
            ),
            None,
        )
        if html:
            path = Path(self._get_filename()).resolve()
            for email_addr in message.to:
                path = path.parent / f"{path.stem}-{email_addr}.html"
                with open(path, "w") as f:
                    f.writelines(html)

        super().write_message(message)


class LoggedEmailBackend(SMTPEmailBackend):
    def send_messages(self, email_messages: Iterable[EmailMultiAlternatives]):
        result = super().send_messages(email_messages)
        for message in email_messages:
            from aidants_connect_common.models import EmailDebug

            EmailDebug.objects.create(
                text_email=message.body,
                html_email=next(
                    (
                        content
                        for content, mime_type in message.alternatives
                        if mime_type == "text/html"
                    ),
                    "---Pas de contenu HTML---",
                ),
                email_adress=message.to[0],
            )
        return result

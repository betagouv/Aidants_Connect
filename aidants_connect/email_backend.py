from pathlib import Path
from typing import Iterable

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.filebased import EmailBackend as FileBasedEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class DebugEmailBackend(FileBasedEmailBackend):
    def write_message(self, message: EmailMultiAlternatives):
        path = Path(self._get_filename()).resolve()
        path = path.parent / f"{path.stem}.html"
        if isinstance(message, EmailMultiAlternatives):
            alternatives = [
                content
                for content, mime_type in message.alternatives
                if mime_type == "text/html"
            ]
            if len(alternatives) == 1:
                with open(path, "a") as f:
                    f.writelines(alternatives[0])

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

from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.filebased import EmailBackend


class DebugEmailBackend(EmailBackend):
    def write_message(self, message: EmailMultiAlternatives):
        path = Path(self._get_filename()).resolve()
        path = path.parent / f"{path.stem}.html"
        if isinstance(message, EmailMultiAlternatives):
            alternatives = [
                content
                for content, mime_type in message.alternatives
                if mime_type == "text/html"
            ]
            with open(path, "a") as f:
                f.writelines(alternatives[0])

        super().write_message(message)

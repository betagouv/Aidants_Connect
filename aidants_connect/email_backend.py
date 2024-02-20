from pathlib import Path

from django.core.mail.backends.filebased import EmailBackend as FileBasedEmailBackend


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

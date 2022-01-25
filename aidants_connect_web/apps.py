from django.apps import AppConfig


class AidantConnectWebConfig(AppConfig):
    name = "aidants_connect_web"

    def ready(self):
        import aidants_connect_web.signals  # noqa
        import aidants_connect.lookups  # noqa

        from django.conf import settings

        if settings.DEBUG and settings.WITH_SCSS_WATCH:
            from django.core.management import call_command

            call_command("scss", "--watch")

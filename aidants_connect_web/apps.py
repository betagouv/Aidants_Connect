from django.apps import AppConfig


class AidantConnectWebConfig(AppConfig):
    name = "aidants_connect_web"

    def ready(self):
        import aidants_connect_web.signals  # noqa

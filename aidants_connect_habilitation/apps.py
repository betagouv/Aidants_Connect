from django.apps import AppConfig


class AidantConnectHabilitationConfig(AppConfig):
    name = "aidants_connect_habilitation"

    def ready(self):
        import aidants_connect_common.lookups  # noqa
        import aidants_connect_habilitation.signals  # noqa

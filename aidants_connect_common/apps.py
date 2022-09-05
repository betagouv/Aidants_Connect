from django.apps import AppConfig


class AidantsConnectCommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aidants_connect_common"

    def ready(self):
        import aidants_connect_common.lookups  # noqa
        import aidants_connect_common.signals  # noqa

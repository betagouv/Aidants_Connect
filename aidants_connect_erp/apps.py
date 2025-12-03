from django.apps import AppConfig


class AidantsConnectErpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aidants_connect_erp"

    def ready(self):
        import aidants_connect_erp.signals  # noqa

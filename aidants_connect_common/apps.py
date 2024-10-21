from django.apps import AppConfig


class AidantsConnectCommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aidants_connect_common"

    def ready(self):
        from django.core.serializers import register_serializer

        import aidants_connect_common.lookups  # noqa
        import aidants_connect_common.signals  # noqa
        from aidants_connect_common.serializers import csv

        register_serializer("csv", csv.__name__)

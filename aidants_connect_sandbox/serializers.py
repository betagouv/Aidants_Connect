from django.conf import settings

import tablib
from rest_framework import serializers

from .admin import AidantSandboxResource


class AutomaticCreationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    profession = serializers.CharField(max_length=150)
    email = serializers.CharField(max_length=150)
    organisation__data_pass_id = serializers.CharField(max_length=150)
    organisation__name = serializers.CharField(max_length=250)
    organisation__siret = serializers.CharField(max_length=25)
    organisation__address = serializers.CharField(max_length=500)
    datapass_id_managers = serializers.CharField(max_length=250, required=False)

    def save(self):
        import_data = tablib.Dataset(
            headers=[
                "id",
                "first_name",
                "last_name",
                "email",
                "organisation__data_pass_id",
                "organisation__name",
                "organisation__siret",
                "organisation__address",
                "organisation__city",
                "organisation__zipcode",
                "organisation__type__id",
                "organisation__type__name",
                "datapass_id_managers",
            ]
        )
        import_ressource = AidantSandboxResource()
        if "datapass_id_managers" in self.validated_data:
            datapass_id_managers = self.validated_data["datapass_id_managers"]
        else:
            datapass_id_managers = ""
        import_data.append(
            [
                1,
                self.validated_data["first_name"],
                self.validated_data["last_name"],
                self.validated_data["email"],
                self.validated_data["organisation__data_pass_id"],
                self.validated_data["organisation__name"],
                self.validated_data["organisation__siret"],
                self.validated_data["organisation__address"],
                "",
                "",
                None,
                "",
                datapass_id_managers,
            ]
        )
        import_ressource.import_data(import_data, dry_run=False)

    def validate_token(self, value):
        if settings.AUTO_CREATE_SANDBOX_TOKEN is None:
            raise serializers.ValidationError("Invalid Token")

        if value == settings.AUTO_CREATE_SANDBOX_TOKEN:
            return value
        else:
            raise serializers.ValidationError("Invalid Token")

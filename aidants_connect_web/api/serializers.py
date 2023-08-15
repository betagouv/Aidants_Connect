from rest_framework import serializers

from aidants_connect_web.models import Organisation

_organisation_meta = Organisation()._meta


class OrganisationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ModelField(model_field=_organisation_meta.get_field("uuid"))
    nom = serializers.ModelField(model_field=_organisation_meta.get_field("name"))
    pivot = serializers.ModelField(model_field=_organisation_meta.get_field("siret"))
    commune = serializers.ModelField(model_field=_organisation_meta.get_field("city"))
    code_postal = serializers.ModelField(
        model_field=_organisation_meta.get_field("zipcode")
    )
    code_insee = serializers.ModelField(
        model_field=_organisation_meta.get_field("city_insee_code")
    )
    adresse = serializers.ModelField(
        model_field=_organisation_meta.get_field("address")
    )
    service = serializers.SerializerMethodField()

    def get_service(self, _):
        return "Réaliser des démarches administratives avec un accompagnement"

    class Meta:
        model = Organisation
        fields = [
            "id",
            "url",
            "pivot",
            "nom",
            "commune",
            "code_postal",
            "code_insee",
            "adresse",
            "service",
        ]
        extra_kwargs = {"url": {"lookup_field": "uuid"}}

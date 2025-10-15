from rest_framework import serializers

from aidants_connect_web.models import Aidant, Organisation

_organisation_meta = Organisation()._meta
_aidant_meta = Aidant()._meta


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
    date_de_creation = serializers.ModelField(
        model_field=_organisation_meta.get_field("created_at")
    )
    date_de_modification = serializers.ModelField(
        model_field=_organisation_meta.get_field("updated_at")
    )

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
            "date_de_creation",
            "date_de_modification",
        ]
        extra_kwargs = {"url": {"lookup_field": "uuid"}}


class FNEOrganisationSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="fne_organisations-detail", lookup_field="uuid"
    )

    class Meta:
        model = Organisation
        fields = [
            "id",
            "uuid",
            "is_active",
            "url",
            "name",
            "siret",
            "city",
            "zipcode",
            "city_insee_code",
            "address",
            "created_at",
            "updated_at",
            "num_mandats",
            "france_services_label",
            "france_services_number",
        ]


class FNEAidantSerializer(serializers.HyperlinkedModelSerializer):
    formation_fne = serializers.SerializerMethodField(method_name="get_formation_fne")
    organisation = FNEOrganisationSerializer(many=False, read_only=True)
    url = serializers.HyperlinkedIdentityField(
        view_name="fne_aidants-detail", lookup_field="id"
    )

    def get_formation_fne(self, obj):
        return True

    class Meta:
        model = Aidant
        fields = [
            "id",
            "url",
            "first_name",
            "last_name",
            "is_active",
            "created_at",
            "updated_at",
            "formation_fne",
            "organisation",
            "profession",
            "conseiller_numerique",
            "get_supports_number",
        ]

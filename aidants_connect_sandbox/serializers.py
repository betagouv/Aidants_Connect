from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned

from django_otp.plugins.otp_static.lib import add_static_token
from rest_framework import serializers

from aidants_connect_web.models import Aidant, Organisation


class AutomaticCreationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    profession = serializers.CharField(max_length=150)
    email = serializers.CharField(max_length=150)
    organisation__data_pass_id = serializers.CharField(max_length=150)
    organisation__name = serializers.CharField(max_length=250)
    organisation__city = serializers.CharField(max_length=250)
    organisation__siret = serializers.CharField(max_length=25)
    organisation__zipcode = serializers.CharField(max_length=10)
    organisation__address = serializers.CharField(max_length=500)
    datapass_id_managers = serializers.CharField(max_length=250, required=False)

    class Meta:
        fields = (
            "first_name",
            "last_name",
            "profession",
            "email",
            "organisation__data_pass_id",
            "organisation__name",
            "organisation__siret",
            "organisation__address",
            "datapass_id_managers",
            "organisation__zipcode",
            "organisation__city",
        )

    def save(self):
        self.validated_data["email"] = self.validated_data["email"].strip().lower()

        if self.validated_data["organisation__data_pass_id"]:
            orga, _ = Organisation.objects.get_or_create(
                data_pass_id=self.validated_data["organisation__data_pass_id"],
                defaults={
                    "name": self.validated_data["organisation__name"],
                    "siret": self.validated_data["organisation__siret"],
                    "address": self.validated_data["organisation__address"],
                    "city": self.validated_data["organisation__city"],
                    "zipcode": self.validated_data["organisation__zipcode"],
                },
            )
        else:
            try:
                orga, created_orga = Organisation.objects.get_or_create(
                    name=self.validated_data["organisation__name"],
                    siret=self.validated_data["organisation__siret"],
                    address=self.validated_data["organisation__address"],
                    city=self.validated_data["organisation__city"],
                    zipcode=self.validated_data["organisation__zipcode"],
                )
            except MultipleObjectsReturned:
                orga = Organisation.objects.filter(
                    name=self.validated_data["organisation__name"],
                    siret=self.validated_data["organisation__siret"],
                    address=self.validated_data["organisation__address"],
                    city=self.validated_data["organisation__city"],
                    zipcode=self.validated_data["organisation__zipcode"],
                )[0]

        new_aidant, created_aidant = Aidant.objects.get_or_create(
            username=self.validated_data["email"],
            email=self.validated_data["email"],
            last_name=self.validated_data["last_name"],
            first_name=self.validated_data["first_name"],
            defaults={"organisation": orga},
        )

        if (
            "datapass_id_managers" in self.validated_data
            and self.validated_data["datapass_id_managers"]
        ):
            respo_orgas = []
            data_pass_ids = self.validated_data["datapass_id_managers"].split("|")
            for str_one_id in data_pass_ids:
                if str_one_id and str_one_id.isdigit():
                    one_id = int(str_one_id)
                    orgas = Organisation.objects.filter(data_pass_id=one_id)
                    if orgas.exists():
                        respo_orgas.append(orgas.first())

            try:
                for one_orga in respo_orgas:
                    new_aidant.responsable_de.add(one_orga)
            except Exception:
                pass
        if created_aidant:
            add_static_token(new_aidant.email, 123456)

    def validate_token(self, value):
        if settings.AUTO_CREATE_SANDBOX_TOKEN is None:
            raise serializers.ValidationError("Invalid Token")

        if value == settings.AUTO_CREATE_SANDBOX_TOKEN:
            return value
        else:
            raise serializers.ValidationError("Invalid Token")

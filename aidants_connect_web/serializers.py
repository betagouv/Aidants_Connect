from rest_framework import serializers
from aidants_connect_web.models import Demarche, Mandat


class MandatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mandat
        fields = "__all__"


class DemarcheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demarche
        fields = "__all__"

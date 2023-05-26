from rest_framework import viewsets

from aidants_connect_web.api.serializers import OrganisationSerializer
from aidants_connect_web.models import Organisation


class OrganisationViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    queryset = Organisation.objects.filter(is_active=True).order_by("pk").all()
    serializer_class = OrganisationSerializer

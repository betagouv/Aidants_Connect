from rest_framework import generics

from .serializers import AutomaticCreationSerializer


class AutomaticCreationViewAPI(generics.CreateAPIView):
    serializer_class = AutomaticCreationSerializer

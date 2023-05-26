from rest_framework import routers

from aidants_connect_web.api.views import OrganisationViewSet

router = routers.DefaultRouter()
router.register(r"organisations", OrganisationViewSet)

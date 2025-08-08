from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.authtoken.models import Token

from aidants_connect.admin import admin_site
from aidants_connect_web.models import (
    Aidant,
    AidantStatistiques,
    AidantStatistiquesbyDepartment,
    AidantStatistiquesbyRegion,
    AidantType,
    CarteTOTP,
    Connection,
    HabilitationRequest,
    Journal,
    Mandat,
    MobileAskingUser,
    Organisation,
    ReboardingAidantStatistiques,
    Usager,
)

from .aidant import AidantAdmin, MobileAskingUserAdmin
from .habilitation_request import HabilitationRequestAdmin
from .journal import JournalAdmin
from .mandat import MandatAdmin
from .notification import NotificationAdmin  # noqa: F401
from .organisation import OrganisationAdmin
from .other_models import ConnectionAdmin, TokenAdmin
from .otp_device import CarteTOTPAdmin, StaticDeviceStaffAdmin, TOTPDeviceStaffAdmin
from .statistiques import (
    AidantStatistiquesAdmin,
    AidantStatistiquesbyDepartmentAdmin,
    AidantStatistiquesbyRegionAdmin,
    ReboardingAidantStatistiquesAdmin,
)
from .usager import UsagerAdmin

# Display the following tables in the admin
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Aidant, AidantAdmin)
admin_site.register(AidantType)
admin_site.register(AidantStatistiques, AidantStatistiquesAdmin)
admin_site.register(AidantStatistiquesbyDepartment, AidantStatistiquesbyDepartmentAdmin)
admin_site.register(AidantStatistiquesbyRegion, AidantStatistiquesbyRegionAdmin)
admin_site.register(ReboardingAidantStatistiques, ReboardingAidantStatistiquesAdmin)

admin_site.register(HabilitationRequest, HabilitationRequestAdmin)
admin_site.register(Usager, UsagerAdmin)
admin_site.register(Mandat, MandatAdmin)
admin_site.register(Journal, JournalAdmin)
admin_site.register(Connection, ConnectionAdmin)

admin_site.register(StaticDevice, StaticDeviceStaffAdmin)
admin_site.register(TOTPDevice, TOTPDeviceStaffAdmin)
admin_site.register(CarteTOTP, CarteTOTPAdmin)

admin_site.register(Token, TokenAdmin)

admin_site.register(MobileAskingUser, MobileAskingUserAdmin)

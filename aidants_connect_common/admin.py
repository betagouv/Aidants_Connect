from aidants_connect.admin import admin_site
from aidants_connect_common.models import Department, Region

admin_site.register(Region)
admin_site.register(Department)

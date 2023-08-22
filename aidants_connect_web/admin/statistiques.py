import logging

from django.contrib.admin import ModelAdmin

from aidants_connect.admin import VisibleToAdminMetier

logger = logging.getLogger()


class AidantStatistiquesAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "created_at",
        "number_aidants",
        "number_aidants_is_active",
        "number_responsable",
        "number_aidants_without_totp",
        "number_aidant_can_create_mandat",
        "number_aidant_with_login",
        "number_aidant_who_have_created_mandat",
    )


class AidantStatistiquesbyDepartmentAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "created_at",
        "departement",
        "number_aidants",
        "number_aidants_is_active",
        "number_responsable",
        "number_aidants_without_totp",
        "number_aidant_can_create_mandat",
        "number_aidant_with_login",
        "number_aidant_who_have_created_mandat",
    )


class AidantStatistiquesbyRegionAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "created_at",
        "region",
        "number_aidants",
        "number_aidants_is_active",
        "number_responsable",
        "number_aidants_without_totp",
        "number_aidant_can_create_mandat",
        "number_aidant_with_login",
        "number_aidant_who_have_created_mandat",
    )

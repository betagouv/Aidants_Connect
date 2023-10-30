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


class ReboardingAidantStatistiquesAdmin(VisibleToAdminMetier, ModelAdmin):
    list_display = (
        "created_at",
        "aidant",
        "connexions_before_reboarding",
        "connexions_j30_after",
        "connexions_j90_after",
        "created_mandats_before_reboarding",
        "created_mandats_j30_after",
        "created_mandats_j90_after",
        "demarches_before_reboarding",
        "demarches_j30_after",
        "demarches_j90_after",
        "usagers_before_reboarding",
        "usagers_j30_after",
        "usagers_j90_after",
        "warning_date",
        "reboarding_session_date",
    )

    readonly_fields = ("aidant",)
    list_filter = ("reboarding_session_date",)

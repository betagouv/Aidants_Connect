import operator
from functools import reduce

from django.contrib.admin import SimpleListFilter
from django.db.models import CharField, Q
from django.db.models.functions import Length

from admin_honeypot.admin import LoginAttemptAdmin as HoneypotLoginAttemptAdmin
from admin_honeypot.models import LoginAttempt as HoneypotLoginAttempt
from django_celery_beat.admin import ClockedScheduleAdmin, PeriodicTaskAdmin
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from django_otp.admin import OTPAdminSite
from magicauth.models import MagicToken

from aidants_connect.common.lookups import IsNullOrBlank
from aidants_connect_common.models import Department, Region

admin_site = OTPAdminSite(OTPAdminSite.name)
admin_site.login_template = "aidants_connect_web/admin/login.html"

admin_site.register(HoneypotLoginAttempt, HoneypotLoginAttemptAdmin)

CharField.register_lookup(Length)
CharField.register_lookup(IsNullOrBlank)


class VisibleToAdminMetier:
    """A mixin to make a model registered in the Admin visible to Admin Métier.
    Admin Métier corresponds to the traditional django `is_staff`
    """

    def has_module_permission(self, request):
        return request.user.is_staff or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


class VisibleToTechAdmin:
    """A mixin to make a model registered in the Admin visible to Tech Admins.
    ATAC is modelised by is_superuser
    """

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


class RegionFilter(SimpleListFilter):
    title = "Région"

    parameter_name = "region"
    filter_parameter_name = "zipcode"

    def lookups(self, request, model_admin):
        return [(r.insee_code, r.name) for r in Region.objects.all()] + [
            ("other", "Autre")
        ]

    def queryset(self, request, queryset):
        region_pk = self.value()

        if not region_pk:
            return

        if region_pk == "other":
            return queryset.filter(**{self.filter_parameter_name: 0})

        region = Region.objects.get(pk=region_pk)
        qgroup = reduce(
            operator.or_,
            (
                Q(
                    **{
                        f"{self.filter_parameter_name}__startswith": d.zipcode  # noqa: E501
                    }
                )
                for d in Department.objects.filter(region=region).all()
            ),
        )
        return queryset.filter(qgroup)


class DepartmentFilter(SimpleListFilter):
    title = "Département"

    parameter_name = "department"
    filter_parameter_name = "zipcode"

    @classmethod
    def generate_filter_list(cls, region=None):
        if not region:
            return [
                (d.insee_code, f"{d.name} ({d.zipcode})")
                for d in Department.objects.all().order_by("name")
            ] + [("other", "Autre")]
        return [
            (
                dept.insee_code,
                f"{dept.name} ({dept.zipcode})",
            )
            for dept in Department.objects.filter(region=region).order_by("name")
        ]

    def lookups(self, request, model_admin):
        region = None
        region_pk = request.GET.get("region", "other")
        if region_pk != "other":
            region = Region.objects.get(pk=region_pk)
        return self.generate_filter_list(region=region)

    def queryset(self, request, queryset):
        department_value = self.value()
        if not department_value:
            return
        if department_value == "other":
            return queryset.filter(
                Q(**{f"{self.filter_parameter_name}__isnull_or_blank": True})
                | Q(**{f"{self.filter_parameter_name}__length__lt": 5})
            )
        return queryset.filter(
            **{f"{self.filter_parameter_name}__startswith": department_value}
        )


# Also register the Django Celery Beat models
admin_site.register(PeriodicTask, PeriodicTaskAdmin)
admin_site.register(IntervalSchedule)
admin_site.register(CrontabSchedule)
admin_site.register(SolarSchedule)
admin_site.register(ClockedSchedule, ClockedScheduleAdmin)
admin_site.register(MagicToken)

import operator
from functools import reduce

from django.contrib.admin import SimpleListFilter
from django.db.models import Q

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

from aidants_connect_web.models import (
    DatavizDepartment,
    DatavizDepartmentsToRegion,
    DatavizRegion,
)

admin_site = OTPAdminSite(OTPAdminSite.name)
admin_site.login_template = "aidants_connect_web/admin/login.html"

admin_site.register(HoneypotLoginAttempt, HoneypotLoginAttemptAdmin)


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
        return [(r.id, r.name) for r in DatavizRegion.objects.all()] + [
            ("other", "Autre")
        ]

    def queryset(self, request, queryset):
        region_id = self.value()

        if not region_id:
            return

        if region_id == "other":
            return queryset.filter(**{self.filter_parameter_name: 0})

        region = DatavizRegion.objects.get(id=region_id)
        d2r = DatavizDepartmentsToRegion.objects.filter(region=region)
        qgroup = reduce(
            operator.or_,
            (
                Q(
                    **{
                        f"{self.filter_parameter_name}__startswith": d.department.normalize_zipcode()  # noqa: E501
                    }
                )
                for d in d2r.all()
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
                (d.normalize_zipcode(), f"{d.dep_name} ({d.normalize_zipcode()})")
                for d in DatavizDepartment.objects.all().order_by("dep_name")
            ] + [("other", "Autre")]
        return [
            (
                d2r.department.normalize_zipcode(),
                f"{d2r.department.dep_name} ({d2r.department.normalize_zipcode()})",
            )
            for d2r in DatavizDepartmentsToRegion.objects.filter(
                region=region
            ).order_by("department__dep_name")
        ]

    def lookups(self, request, model_admin):
        region = None
        region_id = request.GET.get("region", "other")
        if region_id != "other":
            region = DatavizRegion.objects.get(id=region_id)
        return self.generate_filter_list(region=region)

    def queryset(self, request, queryset):
        department_value = self.value()
        if not department_value:
            return
        if department_value == "other":
            return queryset.filter(**{f"{self.filter_parameter_name}": 0})
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

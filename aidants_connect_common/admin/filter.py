import operator
from functools import reduce

from django.contrib.admin import SimpleListFilter
from django.db.models import Count, F, Q, QuerySet

from aidants_connect_common.models import Department, Formation, Region


class RegionFilter(SimpleListFilter):
    template = "admin/filter-select.html"
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
    template = "admin/filter-select.html"
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


class FormationRegionFilter(RegionFilter):
    filter_parameter_name = "organisation__region"

    def queryset(self, request, queryset):
        region_pk = self.value()

        if not region_pk:
            return
        if region_pk == "other":
            return queryset.filter(**{self.filter_parameter_name: 0})

        region = Region.objects.get(pk=region_pk)
        return queryset.filter(organisation__region=region)


class FormationFillingFilter(SimpleListFilter):
    title = "Remplissage de la formation"

    parameter_name = "formation_filling"

    def lookups(self, request, model_admin):
        return ("empty", "Vide"), ("not_empty", "Avec inscrits"), ("full", "Pleine")

    def queryset(self, request, queryset: QuerySet[Formation]):
        match self.value():
            case "empty":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count=0
                )
            case "not_empty":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count__gt=0, attendants_count__lt=F("max_attendants")
                )
            case "full":
                return queryset.annotate(attendants_count=Count("attendants")).filter(
                    attendants_count=F("max_attendants")
                )
            case _:
                return queryset

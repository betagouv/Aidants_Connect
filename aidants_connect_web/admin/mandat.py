import logging
from collections.abc import Collection

from django.contrib import messages
from django.contrib.admin import ModelAdmin, TabularInline
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from aidants_connect.admin import VisibleToTechAdmin
from aidants_connect_common.admin import DepartmentFilter, RegionFilter
from aidants_connect_web.models import Autorisation, Mandat, Organisation

logger = logging.getLogger()


class MandatAutorisationInline(VisibleToTechAdmin, TabularInline):
    model = Autorisation
    fields = ("demarche", "revocation_date")
    readonly_fields = fields
    extra = 0
    max_num = 0


class MandatRegionFilter(RegionFilter):
    filter_parameter_name = "organisation__zipcode"


class MandatDepartmentFilter(DepartmentFilter):
    filter_parameter_name = "organisation__zipcode"


class MandatAdmin(VisibleToTechAdmin, ModelAdmin):
    list_display = (
        "id",
        "usager",
        "organisation",
        "creation_date",
        "expiration_date",
        "admin_is_active",
        "is_remote",
    )
    list_filter = (MandatRegionFilter, MandatDepartmentFilter)
    search_fields = ("usager__given_name", "usager__family_name", "organisation__name")

    fields = (
        "usager",
        "organisation",
        "duree_keyword",
        "creation_date",
        "expiration_date",
        "admin_is_active",
        "is_remote",
    )

    readonly_fields = fields
    raw_id_fields = ("organisation",)

    inlines = (MandatAutorisationInline,)

    actions = ("move_to_another_organisation",)

    def move_to_another_organisation(self, _, queryset):
        ids = ",".join(
            str(pk) for pk in queryset.order_by("pk").values_list("pk", flat=True)
        )
        return HttpResponseRedirect(
            f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}?ids={ids}"
        )

    move_to_another_organisation.short_description = (
        "Transférer le mandat vers une autre organisation"
    )

    def get_urls(self):
        return [
            path(
                "transfer/",
                self.admin_site.admin_view(self.mandate_transfer),
                name="aidants_connect_web_mandat_transfer",
            ),
            *super().get_urls(),
        ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if not (
            isinstance(obj, dict)
            and isinstance(obj.get("exclude_from_readonly_fields"), Collection)
        ):
            return readonly_fields

        return set(readonly_fields) - set(obj["exclude_from_readonly_fields"])

    def mandate_transfer(self, request):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__mandate_transfer_get(request)
        else:
            return self.__mandate_transfer_post(request)

    def __mandate_transfer_get(self, request):
        ids: str = request.GET.get("ids")
        if not ids:
            self.message_user(
                request,
                "Des mandats doivent être sélectionnés afin d’appliquer un transfert. "
                "Aucun élément n’a été transféré.",
                messages.ERROR,
            )

            return HttpResponseRedirect(
                reverse("otpadmin:aidants_connect_web_mandat_changelist")
            )

        include_fields = ["organisation"]
        mandates = Mandat.objects.filter(pk__in=ids.split(","))
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "form": self.get_form(
                request,
                obj={"exclude_from_readonly_fields": include_fields},
                fields=include_fields,
            ),
            "ids": ids,
            "mandates": mandates,
            "mandates_count": mandates.count(),
        }

        return render(request, "admin/transfert.html", context)

    def __mandate_transfer_post(self, request):
        try:
            ids = request.POST["ids"].split(",")
            organisation = Organisation.objects.get(pk=request.POST["organisation"])
            failure, failed_ids = Mandat.transfer_to_organisation(organisation, ids)

            mandates = Mandat.objects.filter(pk__in=failed_ids)
            if failure:
                context = {
                    **self.admin_site.each_context(request),
                    "media": self.media,
                    "mandates": mandates,
                    "mandates_count": mandates.count(),
                }

                return render(request, "admin/transfert_error.html", context)
        except Organisation.DoesNotExist:
            self.message_user(
                request,
                "L'organisation sélectionnée n'existe pas. "
                "Veuillez corriger votre requête",
                messages.ERROR,
            )

            return HttpResponseRedirect(
                f"{reverse('otpadmin:aidants_connect_web_mandat_transfer')}"
                f"?ids={request.POST['ids']}"
            )
        except Exception:
            logger.exception(
                "An error happened while trying to transfer mandates to "
                "another organisation"
            )

            self.message_user(
                request,
                "Les mandats n'ont pas pu être tansférés à cause d'une erreur.",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_mandat_changelist")
        )

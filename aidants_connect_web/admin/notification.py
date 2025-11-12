from django import forms
from django.contrib import messages as django_messages
from django.contrib.admin import ModelAdmin, helpers, register
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path, reverse

from aidants_connect.admin import VisibleToAdminMetier, admin_site
from aidants_connect_common.constants import TextChoicesEnum
from aidants_connect_web.models import Aidant, Notification


@register(Notification, site=admin_site)
class NotificationAdmin(VisibleToAdminMetier, ModelAdmin):
    date_hierarchy = "date"
    raw_id_fields = ("aidant",)
    list_display = ("type", "aidant", "date", "auto_ack_date", "was_ack")
    readonly_fields = ("was_ack",)
    change_list_template = "aidants_connect_web/admin/notification/change_list.html"
    mass_notify_exclude = ("aidant", "was_ack")

    def get_urls(self):
        return [
            path(
                "add-to-referents/",
                self.admin_site.admin_view(self.notify_all_referents),
                name="aidants_connect_web_notification_add_to_referents",
            ),
            *super().get_urls(),
        ]

    def notify_all_referents(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        fields = self.get_fields(request, None)
        for field in self.mass_notify_exclude:
            fields.remove(field)

        fieldsets = [(None, {"fields": ["aidant_class", *fields]})]

        class AidantClassChoices(TextChoicesEnum):
            ALL = "Tous les profils"
            REFERENTS = "Seulement les profils référents"
            AIDANTS = "Seulement les profils aidants"

        class ModelForm(self.get_form(request, None, change=False, fields=fields)):
            aidant_class = forms.ChoiceField(
                choices=AidantClassChoices.choices, label="Catégorie de profils"
            )

        if request.method == "POST":
            form = ModelForm(data=request.POST)

            if form.is_valid():
                aidant_filter_kwargs = {}
                match form.cleaned_data.pop("aidant_class"):
                    case AidantClassChoices.REFERENTS:
                        aidant_filter_kwargs["responsable_de__isnull"] = False
                    case AidantClassChoices.AIDANTS:
                        aidant_filter_kwargs["can_create_mandats"] = True
                try:
                    with transaction.atomic():
                        notifications = Notification.objects.bulk_create(
                            [
                                Notification(aidant_id=aidant_id, **form.cleaned_data)
                                for aidant_id in Aidant.objects.filter(
                                    **aidant_filter_kwargs
                                ).values_list("id", flat=True)
                            ]
                        )
                        from aidants_connect_web.tasks import (
                            send_email_on_new_notification_task,
                        )

                        for notification in notifications:
                            send_email_on_new_notification_task(notification)

                    notif_count = len(notifications)
                    term = "s" if notif_count > 1 else ""
                    django_messages.info(
                        request,
                        f"{notif_count} personne{term} ont été notifiée{term}",
                    )
                    return redirect(
                        reverse("otpadmin:aidants_connect_web_notification_changelist")
                    )
                except Exception as e:
                    django_messages.error(request, f"Il sʼest produit une erreur : {e}")
        else:
            form = ModelForm()

        admin_form = helpers.AdminForm(
            form,
            fieldsets,
            self.get_prepopulated_fields(request, None),
            self.get_readonly_fields(request, None),
            model_admin=self,
        )
        context = {
            **self.admin_site.each_context(request),
            "title": "Notifier en masse toute une classe de profils",
            "subtitle": None,
            "adminform": admin_form,
            "object_id": None,
            "original": None,
            "is_popup": False,
            "to_field": None,
            "media": self.media + admin_form.media,
            "inline_admin_formsets": [],
            "errors": helpers.AdminErrorList(form, []),
            "preserved_filters": self.get_preserved_filters(request),
            "show_save_and_add_another": False,
            "show_save_and_continue": False,
        }

        return self.render_change_form(
            request,
            context,
            add=True,
            change=False,
            obj=None,
            form_url=reverse(
                "otpadmin:aidants_connect_web_notification_add_to_referents"
            ),
        )

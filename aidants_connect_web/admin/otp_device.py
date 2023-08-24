import logging

from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from django_otp.plugins.otp_static.admin import StaticDeviceAdmin
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from import_export import resources
from import_export.admin import ImportMixin
from import_export.results import RowResult

from aidants_connect.admin import VisibleToAdminMetier
from aidants_connect_web.models import Aidant, CarteTOTP, Journal

logger = logging.getLogger()


def get_email_user_for_device(obj):
    try:
        return obj.user.email
    except Exception:
        pass
    try:
        return obj.aidant.email
    except Exception:
        pass
    return None


class StaticDeviceStaffAdmin(VisibleToAdminMetier, StaticDeviceAdmin):
    list_display = ("name", "user", get_email_user_for_device)
    search_fields = ("name", "user__username", "user__email")


class TOTPDeviceStaffAdmin(VisibleToAdminMetier, TOTPDeviceAdmin):
    search_fields = ("name", "user__username", "user__email")


class CarteTOTPResource(resources.ModelResource):
    class Meta:
        model = CarteTOTP
        import_id_fields = ("serial_number",)
        fields = ("serial_number", "seed")


class CarteTOTPAdmin(ImportMixin, VisibleToAdminMetier, ModelAdmin):
    def totp_devices_diagnostic(self, obj):
        devices = TOTPDevice.objects.filter(key=obj.seed)

        aidant_id = 0
        if obj.aidant is not None:
            aidant_id = obj.aidant.id

        if devices.count() == 0:
            if aidant_id > 0:
                return mark_safe(
                    "🚨 Aucun device ne correspond à cette carte. <br>"
                    "Pour régler le problème : cliquer sur le bouton "
                    "« Créer un TOTP Device manquant » en haut de cette page."
                )
            else:
                return "✅ Tout va bien !"

        if devices.count() == 1:
            device = devices.first()
            device_url = reverse(
                "otpadmin:otp_totp_totpdevice_change",
                kwargs={"object_id": device.id},
            )
            if aidant_id == 0:
                return mark_safe(
                    f"🚨 Cette carte devrait être associée à l’aidant {device.user} : "
                    f"saisir {device.user.id} dans le champ ci-dessus puis Enregistrer."
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )
            elif aidant_id != device.user.id:
                return mark_safe(
                    f"🚨 Cette carte est assignée à l'aidant {obj.aidant}, "
                    f"mais le device est assigné à {device.user}."
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )
            else:
                return mark_safe(
                    "✅ Tout va bien !"
                    f'<br><a href="{device_url}">Voir le device {device.name}</a>'
                )

        return (
            mark_safe(
                "<p>🚨 Il faudrait garder un seul TOTP Device parmi ceux-ci :</p>"
                '<table><tr><th scope="col">ID</th>'
                '<th scope="col">Nom</th>'
                '<th scope="col">Confirmé</th>'
                '<th scope="col">Aidant</th>'
                '<th scope="col">ID Aidant</th></tr>'
            )
            + format_html_join(
                "",
                (
                    '<tr><td>{}</td><td><a href="{}">{}</a></td><td>{}</td>'
                    "<td>{}</td><td>{}</td></tr>"
                ),
                (
                    (
                        d.id,
                        reverse(
                            "otpadmin:otp_totp_totpdevice_change",
                            kwargs={"object_id": d.id},
                        ),
                        d.name,
                        f"{'Oui' if d.confirmed else 'Non'}",
                        d.user,
                        f"{'🚨' if d.user.id != aidant_id else '✅'} {d.user.id}",
                    )
                    for d in devices
                ),
            )
            + mark_safe("</table>")
        )

    totp_devices_diagnostic.short_description = "Diagnostic Carte/TOTP Device"

    list_display = (
        "serial_number",
        "aidant",
        get_email_user_for_device,
        "is_functional",
    )
    list_filter = ("is_functional",)
    search_fields = ("serial_number", "aidant__email")
    raw_id_fields = ("aidant",)
    readonly_fields = ("totp_devices_diagnostic",)
    ordering = ("-created_at",)
    resource_classes = [CarteTOTPResource]
    import_template_name = "aidants_connect_web/admin/import_export/import.html"
    change_form_template = "aidants_connect_web/admin/carte_totp/change_form.html"

    def generate_log_entries(self, result, request):
        super().generate_log_entries(result, request)
        Journal.log_toitp_card_import(
            request.user,
            result.totals[RowResult.IMPORT_TYPE_NEW],
            result.totals[RowResult.IMPORT_TYPE_UPDATE],
        )

    def get_urls(self):
        return [
            path(
                "<path:object_id>/dissociate_from_aidant/",
                self.admin_site.admin_view(self.dissociate_from_aidant),
                name="aidants_connect_web_carte_totp_dissociate",
            ),
            path(
                "<path:object_id>/associate_to_aidant/",
                self.admin_site.admin_view(self.associate_to_aidant),
                name="aidants_connect_web_carte_totp_associate",
            ),
            *super().get_urls(),
        ]

    def associate_to_aidant(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__associate_to_aidant_get(request, object_id)
        else:
            return self.__associate_to_aidant_post(request, object_id)

    def dissociate_from_aidant(self, request, object_id):
        if request.method not in ["GET", "POST"]:
            return HttpResponseNotAllowed(["GET", "POST"])
        elif request.method == "GET":
            return self.__dissociate_from_aidant_get(request, object_id)
        else:
            return self.__dissociate_from_aidant_post(request, object_id)

    def __associate_to_aidant_get(self, request, object_id):
        object = CarteTOTP.objects.get(id=object_id)
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
            "form": self.get_form(request, fields=["aidant"], obj=object),
        }

        return render(
            request, "aidants_connect_web/admin/carte_totp/associate.html", context
        )

    def __associate_to_aidant_post(self, request, object_id):
        def redirect_to_list():
            return HttpResponseRedirect(
                reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
            )

        def redirect_to_object(object_id):
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_cartetotp_change",
                    kwargs={"object_id": object_id},
                )
            )

        def redirect_to_try_again(object_id):
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_carte_totp_associate",
                    kwargs={"object_id": object_id},
                )
            )

        if request.POST["aidant"].isnumeric():
            target_aidant_id = int(request.POST["aidant"])
        else:
            self.message_user(
                request, "L'identifiant de l'aidant est obligatoire.", messages.ERROR
            )
            return redirect_to_try_again(object_id)
        carte = CarteTOTP.objects.get(id=object_id)

        try:
            # Check if we are trying to associate the card with another aidant: BAD
            if carte.aidant is not None:
                if target_aidant_id != carte.aidant.id:
                    self.message_user(
                        request,
                        f"La carte {carte} est déjà associée à un autre aidant.",
                        messages.ERROR,
                    )
                    return redirect_to_list()

            # link card with aidant
            target_aidant = Aidant.objects.get(id=target_aidant_id)
            if target_aidant.has_a_carte_totp and carte.aidant != target_aidant:
                self.message_user(
                    request,
                    f"L’aidant {target_aidant} a déjà une carte TOTP. "
                    "Vous ne pouvez pas le lier à celle-ci en plus.",
                    messages.ERROR,
                )
                return redirect_to_try_again(object_id)
            carte.aidant = target_aidant
            carte.save()

            # check if totp devices need to be created
            totp_devices = TOTPDevice.objects.filter(user=target_aidant, key=carte.seed)
            if totp_devices.count() > 0:
                self.message_user(
                    request, "Tout s'est bien passé. Le TOTP Device existait déjà."
                )
                return redirect_to_object(object_id)
            else:
                # No Device exists: crate the TOTP Device and save everything
                carte.get_or_create_totp_device(confirmed=True)
                Journal.log_card_association(
                    request.user, target_aidant, carte.serial_number
                )
                self.message_user(
                    request,
                    f"Tout s'est bien passé. La carte {carte} a été associée à "
                    f"{target_aidant} et un TOTP Device a été créé.",
                )
                return redirect_to_list()

        except Aidant.DoesNotExist:
            self.message_user(
                request,
                f"Aucun aidant n’existe avec l'ID {target_aidant_id}. "
                "Veuillez corriger votre saisie.",
                messages.ERROR,
            )
            return redirect_to_try_again(object_id)
        except Exception as e:
            logger.exception(
                "An error occured while trying to associate an aidant"
                "with a new TOTP."
            )
            self.message_user(
                request,
                f"Quelque chose s’est mal passé durant l'opération. {e}",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
        )

    def __dissociate_from_aidant_get(self, request, object_id):
        object = CarteTOTP.objects.get(id=object_id)
        context = {
            **self.admin_site.each_context(request),
            "media": self.media,
            "object_id": object_id,
            "object": object,
        }

        return render(
            request, "aidants_connect_web/admin/carte_totp/dissociate.html", context
        )

    def __dissociate_from_aidant_post(self, request, object_id):
        try:
            object = CarteTOTP.objects.get(id=object_id)
            aidant = object.aidant
            if aidant is None:
                self.message_user(
                    request,
                    f"Aucun aidant n’est associé à la carte {object.serial_number}.",
                    messages.ERROR,
                )
                return HttpResponseRedirect(
                    reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
                )

            totp_devices = TOTPDevice.objects.filter(user=aidant, key=object.seed)
            for d in totp_devices:
                d.delete()
            object.aidant = None
            object.save()

            Journal.log_card_dissociation(
                request.user, aidant, object.serial_number, "Admin action"
            )

            self.message_user(request, "Tout s'est bien passé.")
            return HttpResponseRedirect(
                reverse(
                    "otpadmin:aidants_connect_web_cartetotp_change",
                    kwargs={"object_id": object_id},
                )
            )
        except Exception:
            logger.exception(
                "An error occured while trying to dissociate an aidant"
                "from their carte TOTP"
            )

            self.message_user(
                request,
                "Quelque chose s’est mal passé durant l'opération.",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("otpadmin:aidants_connect_web_cartetotp_changelist")
        )

from django.core.exceptions import MultipleObjectsReturned
from django.db.models import QuerySet
from django.forms import ChoiceField
from django.http import HttpRequest

from django_otp.plugins.otp_static.lib import add_static_token
from django_otp.plugins.otp_static.models import StaticToken
from import_export import resources
from import_export.admin import ConfirmImportForm, ImportForm
from import_export.fields import Field
from import_export.results import RowResult

from aidants_connect_web.admin import AidantAdmin
from aidants_connect_web.models import Aidant, Organisation


class AidantSandboxResource(resources.ModelResource):
    username = Field(attribute="username", column_name="email")

    class Meta:
        model = Aidant
        import_id_fields = ("username",)
        fields = ("username", "last_name", "first_name")

    def before_save_instance(self, instance: Aidant, using_transactions, dry_run):
        instance.email = instance.username
        instance.organisation = self.orga
        if not instance.first_name and not instance.last_name:
            instance.last_name = instance.email

    def before_import_row(self, row, row_number=None, **kwargs):
        row["email"] = row["email"].strip().lower()
        if row["organisation__data_pass_id"]:
            orga, _ = Organisation.objects.get_or_create(
                data_pass_id=row["organisation__data_pass_id"],
                defaults={
                    "name": row["organisation__name"],
                    "siret": row["organisation__siret"],
                    "address": row["organisation__address"],
                    "city": row["organisation__city"],
                    "zipcode": row["organisation__zipcode"],
                },
            )
        else:
            try:
                orga, _ = Organisation.objects.get_or_create(
                    name=row["organisation__name"],
                    siret=row["organisation__siret"],
                    address=row["organisation__address"],
                    city=row["organisation__city"],
                    zipcode=row["organisation__zipcode"],
                )
            except MultipleObjectsReturned:
                orga = Organisation.objects.filter(
                    name=row["organisation__name"],
                    siret=row["organisation__siret"],
                    address=row["organisation__address"],
                    city=row["organisation__city"],
                    zipcode=row["organisation__zipcode"],
                )[0]
        if row["Data pass Id Orga Responsable"]:
            respo_orgas = []
            data_pass_ids = row["Data pass Id Orga Responsable"].split("|")
            for str_one_id in data_pass_ids:
                if str_one_id and str_one_id.isdigit():
                    one_id = int(str_one_id)
                    orgas = Organisation.objects.filter(data_pass_id=one_id)
                    if orgas.exists():
                        respo_orgas.append(orgas.first())

            self.respo_orgas = respo_orgas

        self.orga = orga

    def after_save_instance(self, instance, using_transactions, dry_run):
        try:
            for one_orga in self.respo_orgas:
                instance.responsable_de.add(one_orga)
        except Exception:
            pass

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        if row_result.import_type != RowResult.IMPORT_TYPE_NEW:
            return
        add_static_token(row["email"], 123456)


class AidantImportForm(ImportForm):
    import_choices = ChoiceField(
        label="Type d'import",
        choices=(
            ("IMPORT_FOR_SANDBOX", "Importer des aidants dans la sandbox"),
            ("AJOUT_AIDANT", "Importer des aidants classiquement"),
        ),
    )


class ConfirmAidantImportForm(ConfirmImportForm):
    import_choices = ChoiceField(
        label="Type d'import",
        choices=(
            ("IMPORT_FOR_SANDBOX", "Importer des aidants dans la sandbox"),
            ("AJOUT_AIDANT", "Importer des aidants classiquement"),
        ),
    )


def get_import_resource_kwargs(self, request, form, *args, **kwargs):
    cleaned_data = getattr(form, "cleaned_data", False)
    if (
        isinstance(form, ConfirmAidantImportForm)
        or isinstance(form, AidantImportForm)
        and cleaned_data
    ):
        self.import_choices = cleaned_data["import_choices"]
    return kwargs


def get_import_resource_classes(self):
    import_choices = getattr(self, "import_choices", False)
    if import_choices and import_choices == "IMPORT_FOR_SANDBOX":
        return [AidantSandboxResource]
    return self.get_resource_classes()


def get_import_form(self):
    return AidantImportForm


def get_confirm_import_form(self):
    return ConfirmAidantImportForm


def add_static_token_for_aidants(self, request: HttpRequest, queryset: QuerySet):
    for aidant in queryset:
        if not StaticToken.objects.filter(device__user=aidant).exists():
            add_static_token(aidant.username, "123456")


AidantAdmin.add_static_token_for_aidants = add_static_token_for_aidants
AidantAdmin.add_static_token_for_aidants.short_description = "Ajouter des token infinis"
AidantAdmin.actions.append("add_static_token_for_aidants")
AidantAdmin.get_confirm_import_form = get_confirm_import_form
AidantAdmin.get_import_form = get_import_form
AidantAdmin.get_import_resource_kwargs = get_import_resource_kwargs
AidantAdmin.get_import_resource_classes = get_import_resource_classes

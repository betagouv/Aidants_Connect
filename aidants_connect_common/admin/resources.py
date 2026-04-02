from import_export.fields import Field
from import_export.resources import ModelResource
from import_export.widgets import ForeignKeyWidget

from aidants_connect_common.models import (
    Commune,
    Department,
    Formation,
    FormationAttendant,
)

from .widget import ZRRBooleanWidget


class FormationAttendantResource(ModelResource):
    first_name = Field(attribute="attendant__first_name", column_name="PRENOM")
    last_name = Field(attribute="attendant__last_name", column_name="NOM")
    email = Field(attribute="attendant__email", column_name="EMAIL")
    structure = Field(
        attribute="attendant__organisation__name", column_name="STRUCTURE"
    )
    id_grist = Field(attribute="id_grist", column_name="ID GRIST")
    id = Field(attribute="id", column_name="ID")
    formation = Field(column_name="FORMATION")
    state = Field(column_name="ETAT")

    class Meta:
        model = FormationAttendant
        fields = (
            "first_name",
            "last_name",
            "email",
            "structure",
            "formation",
            "state",
            "id_grist",
            "id",
        )

    def dehydrate_state(self, f_attendant):
        return FormationAttendant.State(f_attendant.state).label

    def dehydrate_formation(self, f_attendant):
        return str(f_attendant.formation)


class FormationResource(ModelResource):
    name = Field(column_name="NOM")
    publish = Field(column_name="Publie sur le site, disponible à l'inscription")
    start_datetime = Field(attribute="start_datetime", column_name="DATEDEBUT")
    end_datetime = Field(attribute="end_datetime", column_name="DATEFIN")
    status = Field(column_name="En présentiel/à distance")
    state = Field(column_name="ETAT")
    duration = Field(attribute="duration", column_name="DUREE")
    place = Field(attribute="place", column_name="LIEU")
    type = Field(attribute="type__label", column_name="TYPE")
    organisation = Field(attribute="organisation__name", column_name="ORGANISATION")
    description = Field(attribute="description", column_name="DESCRIPTION")
    id_grist = Field(attribute="id_grist", column_name="ID GRIST")
    id = Field(attribute="id", column_name="ID")
    number_apprenant = Field(column_name="Nombre d'apprenants")

    class Meta:
        model = Formation
        fields = (
            "name",
            "publish",
            "place",
            "start_datetime",
            "end_datetime",
            "status",
            "state",
            "duration",
            "organisation",
            "id_grist",
            "id",
            "number_apprenant",
            "type",
            "description",
        )

    def dehydrate_publish(self, formation):
        if formation.publish_or_not:
            return "Oui"
        return "Non"

    def dehydrate_name(self, formation):
        return str(formation)

    def dehydrate_number_apprenant(self, formation):
        return formation.number_of_attendants

    def dehydrate_status(self, formation):
        return Formation.Status(formation.status).label

    def dehydrate_state(self, formation):
        return Formation.State(formation.state).label


class CommuneResource(ModelResource):
    """
    Documentation for the imported CSV file is available at
    https://www.insee.fr/fr/information/6800685
    """

    insee_code = Field(attribute="insee_code", column_name="COM")
    name = Field(attribute="name", column_name="LIBELLE")
    department = Field(
        attribute="department",
        column_name="DEP",
        widget=ForeignKeyWidget(Department, field="insee_code"),
    )

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if row["TYPECOM"] != "COM":
            # Only import communes not communes associées or communes délégues
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    @classmethod
    def get_display_name(cls):
        return "Communes"

    class Meta:
        model = Commune
        fields = ("insee_code", "name", "department")
        import_id_fields = ("insee_code",)
        # There are 37_000+ communes which would take too much time to import
        # if not using bulk import.
        use_bulk = True
        skip_unchanged = True


class ZRRResource(ModelResource):
    insee_code = Field(attribute="insee_code", column_name="CODGEO")
    zrr = Field(attribute="zrr", column_name="ZRR_SIMP", widget=ZRRBooleanWidget())

    def __init__(self, commune_zrr_classification, **kwargs):
        super().__init__(**kwargs)
        self.fields["zrr"].widget.commune_zrr_classification = (
            commune_zrr_classification
        )

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not original.insee_code:
            # Prevent creating instances from ZRR file
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    @classmethod
    def get_display_name(cls):
        return "Zones de Revitalisation Rurale"

    class Meta:
        model = Commune
        fields = ("insee_code", "zrr")
        import_id_fields = ("insee_code",)
        # There are 37_000+ communes which would take too much time to import
        # if not using bulk import.
        use_bulk = True
        skip_unchanged = True

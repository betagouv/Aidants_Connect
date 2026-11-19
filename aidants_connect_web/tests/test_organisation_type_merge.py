import csv
import io
import tempfile

from django.core.management import call_command
from django.test import TestCase, tag

from aidants_connect_common.constants import RequestOriginConstants
from aidants_connect_habilitation.tests.factories import OrganisationRequestFactory
from aidants_connect_web.models import OrganisationType
from aidants_connect_web.organisation_type_merge import (
    apply_organisation_type_merge,
    parse_merge_mapping_from_csv,
    preview_organisation_type_merge,
    write_organisation_types_csv,
)
from aidants_connect_web.tests.factories import (
    OrganisationFactory,
    OrganisationTypeFactory,
)


@tag("commands")
class OrganisationTypeMergeTests(TestCase):
    def test_export_csv_contains_audit_columns(self):
        source_type = OrganisationTypeFactory(name="Type source")
        target_type = OrganisationType.objects.get(
            pk=RequestOriginConstants.ASSOCIATIONS.value
        )
        OrganisationFactory(type=source_type)
        OrganisationRequestFactory(type_id=source_type.id)

        output = io.StringIO()
        write_organisation_types_csv(output)

        rows = list(csv.DictReader(io.StringIO(output.getvalue())))
        exported_source = next(row for row in rows if row["id"] == str(source_type.id))

        self.assertEqual(exported_source["name"], "Type source")
        self.assertEqual(exported_source["nb_organisations"], "1")
        self.assertEqual(exported_source["nb_organisation_requests"], "1")
        self.assertEqual(exported_source["is_canonical"], "no")
        self.assertEqual(exported_source["target_id"], "")
        self.assertTrue(
            any(
                row["id"] == str(target_type.id) and row["is_canonical"] == "yes"
                for row in rows
            )
        )

    def test_parse_mapping_ignores_empty_target_id(self):
        csv_content = "id,name,target_id\n579,Type custom,13\n580,Autre custom,\n"
        mapping = parse_merge_mapping_from_csv(io.StringIO(csv_content))

        self.assertEqual(mapping, {579: 13})

    def test_apply_merge_moves_references_and_deletes_orphans(self):
        source_type = OrganisationTypeFactory(name="Type custom")
        target_type = OrganisationType.objects.get(
            pk=RequestOriginConstants.ASSOCIATIONS.value
        )
        organisation = OrganisationFactory(type=source_type)
        organisation_request = OrganisationRequestFactory(type_id=source_type.id)

        previews = preview_organisation_type_merge({source_type.id: target_type.id})
        self.assertEqual(previews[0].nb_organisations, 1)
        self.assertEqual(previews[0].nb_organisation_requests, 1)

        result = apply_organisation_type_merge({source_type.id: target_type.id})

        organisation.refresh_from_db()
        organisation_request.refresh_from_db()
        self.assertEqual(organisation.type_id, target_type.id)
        self.assertEqual(organisation_request.type_id, target_type.id)
        self.assertFalse(OrganisationType.objects.filter(pk=source_type.id).exists())
        self.assertIn(source_type.id, result.deleted_orphan_type_ids)

    def test_merge_command_dry_run_does_not_update_database(self):
        source_type = OrganisationTypeFactory(name="Type custom")
        target_type = OrganisationType.objects.get(
            pk=RequestOriginConstants.ASSOCIATIONS.value
        )
        organisation = OrganisationFactory(type=source_type)

        with tempfile.NamedTemporaryFile(
            "w+", newline="", encoding="utf-8"
        ) as csv_file:
            csv_file.write("id,name,target_id\n")
            csv_file.write(f"{source_type.id},Type custom,{target_type.id}\n")
            csv_file.flush()

            call_command("merge_organisation_types", csv_file.name)

        organisation.refresh_from_db()
        self.assertEqual(organisation.type_id, source_type.id)
        self.assertTrue(OrganisationType.objects.filter(pk=source_type.id).exists())

    def test_merge_command_apply_updates_database(self):
        source_type = OrganisationTypeFactory(name="Type custom")
        target_type = OrganisationType.objects.get(
            pk=RequestOriginConstants.ASSOCIATIONS.value
        )
        organisation = OrganisationFactory(type=source_type)

        with tempfile.NamedTemporaryFile(
            "w+", newline="", encoding="utf-8"
        ) as csv_file:
            csv_file.write("id,name,target_id\n")
            csv_file.write(f"{source_type.id},Type custom,{target_type.id}\n")
            csv_file.flush()

            call_command("merge_organisation_types", csv_file.name, "--apply")

        organisation.refresh_from_db()
        self.assertEqual(organisation.type_id, target_type.id)
        self.assertFalse(OrganisationType.objects.filter(pk=source_type.id).exists())

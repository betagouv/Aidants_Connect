from django.db import migrations

# Legacy organisation types removed from RequestOriginConstants in
# dc5ac400 ("New Choices for Organisation Type", 2024-11-18).
LEGACY_ORGANISATION_TYPE_MERGE = {
    4: 30,  # Secrétariats de mairie → Municipalités
    7: 8,  # Autre guichet de SP de proximité → Guichet opérateur de SP
    9: 13,  # Autres associations → Associations
    11: 12,  # Indépendant → Autre
    # TODO: 10 Structure médico-sociale (CSAPA, CHU, CMS) ?
}


def merge_legacy_organisation_types(apps, schema_editor):
    Organisation = apps.get_model("aidants_connect_web", "Organisation")
    OrganisationType = apps.get_model("aidants_connect_web", "OrganisationType")
    OrganisationRequest = apps.get_model(
        "aidants_connect_habilitation", "OrganisationRequest"
    )
    canonical_type_ids = {
        1,
        2,
        3,
        5,
        6,
        8,
        12,
        13,
        20,
        29,
        30,
        32,
        35,
        55,
        60,
        91,
        94,
        144,
        202,
        238,
        242,
        247,
        255,
        358,
        393,
        459,
        557,
        577,
        578,
    }

    for old_type_id, new_type_id in LEGACY_ORGANISATION_TYPE_MERGE.items():
        Organisation.objects.filter(type_id=old_type_id).update(type_id=new_type_id)
        OrganisationRequest.objects.filter(type_id=old_type_id).update(
            type_id=new_type_id
        )

    used_type_ids = set(
        Organisation.objects.exclude(type_id=None).values_list("type_id", flat=True)
    ) | set(
        OrganisationRequest.objects.exclude(type_id=None).values_list(
            "type_id", flat=True
        )
    )

    OrganisationType.objects.exclude(id__in=used_type_ids).exclude(
        id__in=canonical_type_ids
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0092_habilitationrequest_pix_score"),
        (
            "aidants_connect_habilitation",
            "0037_alter_organisationrequest_avg_nb_demarches_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            merge_legacy_organisation_types,
            migrations.RunPython.noop,
        ),
    ]

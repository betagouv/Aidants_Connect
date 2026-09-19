from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from io import TextIOBase

from django.db.models import Count

from aidants_connect_common.constants import RequestOriginConstants
from aidants_connect_habilitation.models import OrganisationRequest
from aidants_connect_web.models import Organisation, OrganisationType

CANONICAL_ORGANISATION_TYPE_IDS = {choice.value for choice in RequestOriginConstants}

EXPORT_FIELDNAMES = (
    "id",
    "name",
    "nb_organisations",
    "nb_organisation_requests",
    "is_canonical",
    "target_id",
)


@dataclass(frozen=True)
class OrganisationTypeAuditRow:
    id: int
    name: str
    nb_organisations: int
    nb_organisation_requests: int
    is_canonical: bool


@dataclass(frozen=True)
class OrganisationTypeMergePreview:
    source_id: int
    source_name: str
    target_id: int
    target_name: str
    nb_organisations: int
    nb_organisation_requests: int


@dataclass(frozen=True)
class ApplyOrganisationTypeMergeResult:
    previews: tuple[OrganisationTypeMergePreview, ...]
    deleted_orphan_type_ids: tuple[int, ...]


def get_organisation_type_audit_rows() -> list[OrganisationTypeAuditRow]:
    rows = []
    organisation_types = (
        OrganisationType.objects.annotate(
            nb_organisations=Count("organisation", distinct=True),
            nb_organisation_requests=Count("organisationrequest", distinct=True),
        )
        .order_by("name", "id")
        .values(
            "id",
            "name",
            "nb_organisations",
            "nb_organisation_requests",
        )
    )

    for organisation_type in organisation_types:
        rows.append(
            OrganisationTypeAuditRow(
                id=organisation_type["id"],
                name=organisation_type["name"],
                nb_organisations=organisation_type["nb_organisations"],
                nb_organisation_requests=organisation_type["nb_organisation_requests"],
                is_canonical=organisation_type["id"] in CANONICAL_ORGANISATION_TYPE_IDS,
            )
        )

    return rows


def write_organisation_types_csv(output: TextIOBase) -> None:
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDNAMES)
    writer.writeheader()

    for row in get_organisation_type_audit_rows():
        writer.writerow(
            {
                "id": row.id,
                "name": row.name,
                "nb_organisations": row.nb_organisations,
                "nb_organisation_requests": row.nb_organisation_requests,
                "is_canonical": "yes" if row.is_canonical else "no",
                "target_id": "",
            }
        )


def parse_merge_mapping_from_csv(input_file: TextIOBase) -> dict[int, int]:
    reader = csv.DictReader(input_file)
    if not reader.fieldnames:
        raise ValueError("Le fichier CSV est vide ou ne contient pas d'en-tête.")

    mapping: dict[int, int] = {}

    for line_number, row in enumerate(reader, start=2):
        source_id = _read_csv_id(row, ("id", "source_id"), line_number)
        target_id = _read_csv_id(row, ("target_id",), line_number, required=False)

        if target_id is None:
            continue

        if source_id == target_id:
            continue

        if source_id in mapping and mapping[source_id] != target_id:
            raise ValueError(
                f"Ligne {line_number} : le type {source_id} a plusieurs cibles "
                f"({mapping[source_id]} et {target_id})."
            )

        mapping[source_id] = target_id

    return mapping


def preview_organisation_type_merge(
    mapping: dict[int, int],
) -> list[OrganisationTypeMergePreview]:
    previews = []

    for source_id, target_id in sorted(mapping.items()):
        try:
            source_type = OrganisationType.objects.get(pk=source_id)
        except OrganisationType.DoesNotExist as exc:
            raise ValueError(f"Type source introuvable : id={source_id}.") from exc

        try:
            target_type = OrganisationType.objects.get(pk=target_id)
        except OrganisationType.DoesNotExist as exc:
            raise ValueError(
                f"Type cible introuvable : id={target_id} (source id={source_id})."
            ) from exc

        previews.append(
            OrganisationTypeMergePreview(
                source_id=source_id,
                source_name=source_type.name,
                target_id=target_id,
                target_name=target_type.name,
                nb_organisations=Organisation.objects.filter(type_id=source_id).count(),
                nb_organisation_requests=_count_organisation_requests(source_id),
            )
        )

    return previews


def apply_organisation_type_merge(
    mapping: dict[int, int],
    *,
    delete_orphans: bool = True,
) -> ApplyOrganisationTypeMergeResult:
    previews = preview_organisation_type_merge(mapping)

    for preview in previews:
        Organisation.objects.filter(type_id=preview.source_id).update(
            type_id=preview.target_id
        )
        _update_organisation_requests(preview.source_id, preview.target_id)

    deleted_orphan_type_ids: tuple[int, ...] = ()
    if delete_orphans:
        deleted_orphan_type_ids = delete_unreferenced_organisation_types()

    return ApplyOrganisationTypeMergeResult(
        previews=tuple(previews),
        deleted_orphan_type_ids=deleted_orphan_type_ids,
    )


def delete_unreferenced_organisation_types() -> tuple[int, ...]:
    used_type_ids = (
        set(
            Organisation.objects.exclude(type_id=None).values_list("type_id", flat=True)
        )
        | _used_organisation_request_type_ids()
    )

    orphan_type_ids = tuple(
        OrganisationType.objects.exclude(id__in=used_type_ids)
        .exclude(id__in=CANONICAL_ORGANISATION_TYPE_IDS)
        .values_list("id", flat=True)
    )
    OrganisationType.objects.filter(id__in=orphan_type_ids).delete()
    return orphan_type_ids


def _read_csv_id(
    row: dict[str, str | None],
    field_names: Iterable[str],
    line_number: int,
    *,
    required: bool = True,
) -> int | None:
    value = None
    for field_name in field_names:
        if row.get(field_name) not in (None, ""):
            value = row[field_name]
            break

    if value in (None, ""):
        if required:
            raise ValueError(
                f"Ligne {line_number} : colonne obligatoire manquante "
                f"({', '.join(field_names)})."
            )
        return None

    try:
        return int(str(value).strip())
    except ValueError as exc:
        raise ValueError(
            f"Ligne {line_number} : identifiant invalide ({value!r})."
        ) from exc


def _count_organisation_requests(type_id: int) -> int:
    return OrganisationRequest.objects.filter(type_id=type_id).count()


def _update_organisation_requests(source_id: int, target_id: int) -> None:
    OrganisationRequest.objects.filter(type_id=source_id).update(type_id=target_id)


def _used_organisation_request_type_ids() -> set[int]:
    return set(
        OrganisationRequest.objects.exclude(type_id=None).values_list(
            "type_id", flat=True
        )
    )


def iter_merge_summary_lines(
    previews: list[OrganisationTypeMergePreview],
    *,
    deleted_orphan_type_ids: tuple[int, ...] = (),
) -> Iterator[str]:
    if not previews:
        yield "Aucune fusion à appliquer."
        return

    for preview in previews:
        yield (
            f"- {preview.source_id} ({preview.source_name!r}) "
            f"→ {preview.target_id} ({preview.target_name!r}) : "
            f"{preview.nb_organisations} organisation(s), "
            f"{preview.nb_organisation_requests} demande(s)"
        )

    if deleted_orphan_type_ids:
        yield (
            f"Types orphelins supprimés ({len(deleted_orphan_type_ids)}) : "
            f"{', '.join(str(type_id) for type_id in deleted_orphan_type_ids)}"
        )

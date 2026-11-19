from django.core.management.base import BaseCommand, CommandError

from aidants_connect_web.organisation_type_merge import (
    apply_organisation_type_merge,
    iter_merge_summary_lines,
    parse_merge_mapping_from_csv,
    preview_organisation_type_merge,
)


class Command(BaseCommand):
    help = (
        "Fusionne des types de structure à partir d'un CSV exporté "
        "(colonnes id/source_id et target_id)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "mapping_file",
            help="Fichier CSV contenant les colonnes id et target_id.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Applique les fusions (par défaut : dry-run).",
        )
        parser.add_argument(
            "--no-delete-orphans",
            action="store_true",
            help="Ne supprime pas les types sans référence après fusion.",
        )

    def handle(self, *args, **options):
        mapping_file = options["mapping_file"]
        apply_changes = options["apply"]
        delete_orphans = not options["no_delete_orphans"]

        try:
            with open(mapping_file, newline="", encoding="utf-8") as input_file:
                mapping = parse_merge_mapping_from_csv(input_file)
        except OSError as exc:
            raise CommandError(
                f"Impossible de lire le fichier {mapping_file!r}."
            ) from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not mapping:
            self.stdout.write("Aucune ligne avec target_id à traiter.")
            return

        try:
            previews = preview_organisation_type_merge(mapping)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        mode = "APPLICATION" if apply_changes else "DRY-RUN"
        self.stdout.write(f"Mode : {mode}")
        for line in iter_merge_summary_lines(previews):
            self.stdout.write(line)

        if not apply_changes:
            self.stdout.write(
                "Aucune modification effectuée. Relancez avec --apply pour exécuter."
            )
            return

        try:
            result = apply_organisation_type_merge(
                mapping,
                delete_orphans=delete_orphans,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if delete_orphans and result.deleted_orphan_type_ids:
            deleted_ids = ", ".join(
                str(type_id) for type_id in result.deleted_orphan_type_ids
            )
            self.stdout.write(
                self.style.SUCCESS(f"Types orphelins supprimés : {deleted_ids}")
            )

        self.stdout.write(self.style.SUCCESS("Fusions appliquées."))

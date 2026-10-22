import sys

from django.core.management.base import BaseCommand, CommandError

from aidants_connect_web.organisation_type_merge import write_organisation_types_csv


class Command(BaseCommand):
    help = (
        "Exporte les types de structure dans un CSV pour préparer un remapping "
        "(colonne target_id à compléter avant import)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "output",
            nargs="?",
            default="-",
            help="Fichier CSV de sortie (défaut : stdout, utiliser '-' explicitement).",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        if output_path in ("-", ""):
            write_organisation_types_csv(sys.stdout)
            return

        try:
            with open(output_path, "w", newline="", encoding="utf-8") as output_file:
                write_organisation_types_csv(output_file)
        except OSError as exc:
            raise CommandError(
                f"Impossible d'écrire le fichier {output_path!r}."
            ) from exc

        self.stdout.write(self.style.SUCCESS(f"Export terminé : {output_path}"))

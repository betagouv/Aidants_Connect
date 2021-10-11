import os
import sys
from typing import Tuple, Optional

from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError

from aidants_connect_web.models import Organisation, Aidant

ORGANISATION_NAME_ARG = "--organisation-name"
ORGANISATION_NAME_DEST = "organisation_name"
ORGANISATION_NAME_ENV = "DJANGO_SUPERUSER_ORGANISATION_NAME"
ORGANISATION_ID_ARG = "--organisation"
ORGANISATION_ID_ENV = "DJANGO_SUPERUSER_ORGANISATION"

ERROR_MSG = (
    f"Either {ORGANISATION_NAME_ARG} option (alternatively the {ORGANISATION_NAME_ENV} "
    f"enviroment variable) or the {ORGANISATION_ID_ARG} option (alternatively the "
    f"{ORGANISATION_ID_ENV} environement variable) should be set"
)


class Command(createsuperuser.Command):
    def __init__(self, *args, **kwargs):
        self.options = {}
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            ORGANISATION_NAME_ARG,
            dest=ORGANISATION_NAME_DEST,
            help=(
                "The name of the organisation that should be created for this user. "
                "Alternatively, you can set this field by using the "
                f"{ORGANISATION_NAME_ENV} environment variable "
                f"(either this option or {ORGANISATION_ID_ARG} should be set)."
            ),
        )

    def handle(self, *args, **options):
        self.options = options

        organisation = options["organisation"] or os.environ.get(ORGANISATION_ID_ENV)
        organisation_name = options[ORGANISATION_NAME_DEST] or os.environ.get(
            ORGANISATION_NAME_ENV
        )

        if organisation is not None and organisation_name is not None:
            raise CommandError(f"{ERROR_MSG} but not both at the same time.")

        if options["interactive"]:
            return super().handle(*args, **options)

        try:
            if organisation is None and organisation_name is None:
                raise CommandError(f"{ERROR_MSG}.")

            if organisation_name is not None:
                organisation = Organisation.objects.create(name=organisation_name).pk

            options["organisation"] = organisation
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)

        return super().handle(*args, **options)

    def get_input_data(self, field, message, default=None):
        if not field == Aidant._meta.get_field("organisation"):
            return super().get_input_data(field, message, default)

        organisation_name = self.options[ORGANISATION_NAME_DEST] or os.environ.get(
            ORGANISATION_NAME_ENV
        )

        if organisation_name is None:
            organisation_id, organisation_name = self._get_input_organisation()

            if organisation_id is not None:
                return organisation_id

        return Organisation.objects.create(name=organisation_name).pk

    def _get_input_organisation(self) -> Tuple[Optional[int], Optional[str]]:
        organisation_id = None
        organisation_name = None
        choice = ""

        while choice not in ("1", "2"):
            choice = input(
                "You first need to reference an organisation for the user you're about "
                "to create. You can either:\n"
                "\t[1]: create a new one\n"
                "\t[2]: provide the id of an already existing one\n"
                "Choose either 1 or 2: "
            ).strip()

        while organisation_id is None and organisation_name is None:
            if choice == "1":
                organisation_name = input(
                    "Please enter the name of the new organisation you want to create: "
                ).strip()
                organisation_name = None if not organisation_name else organisation_name
            else:
                organisation_id = input(
                    "Please enter the id of the already existing organisation you want "
                    "the user to be associated with: "
                ).strip()
                try:
                    organisation_id = int(organisation_id)
                except ValueError:
                    organisation_id = None

        return organisation_id, organisation_name

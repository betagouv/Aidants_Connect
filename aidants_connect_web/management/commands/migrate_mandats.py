from datetime import timedelta

from django.core.management.base import BaseCommand

from aidants_connect_web.models import Autorisation, Mandat, Usager


class Command(BaseCommand):

    help = "Converts the current mandats data to the new model"

    def handle(self, *args, **options):

        self.stdout.write("Migrating data to new Mandat model...")

        # TODO: Convert all "create_mandat_print" journal entries to the new
        # "create_attestation" wording.

        all_usagers = Usager.objects.order_by('creation_date')

        # We loop through all our `usagers`...
        for usager in all_usagers:

            self.stdout.write("  Processing Usager #%d" % usager.id)

            autos = usager.autorisations.order_by('creation_date')
            num_autos = autos.count()

            orga_ids = set([auto.aidant.organisation.id for auto in autos])
            num_orgas = len(orga_ids)

            self.stdout.write(
                "    -> %d Autorisation(s), with %d Organisation(s)" % (
                    num_autos, num_orgas
                )
            )

            # Then, for each `usager`, we loop through all the `organisations`
            # they have signed a `mandat` with...
            for orga_id in orga_ids:

                orga_autos = autos.filter(aidant__organisation__pk=orga_id)
                num_orga_autos = orga_autos.count()
                num_linked_orga_autos = 0

                self.stdout.write(
                    "      -> Creating Mandat(s) with Organisation #%d..." % (
                        orga_id,
                    )
                )

                # We need to go on as long as all the `autorisations`
                # are not properly linked to a `mandat`.
                while num_linked_orga_autos < num_orga_autos:

                    # We focus on the first unlinked `autorisation`.
                    first_unlinked_auto = orga_autos[num_linked_orga_autos]

                    # We create a `mandat` based on this `autorisation`'s data.
                    new_mandat = Mandat.objects.create(
                        organisation=Organisation.objects.get(pk=org_id),
                        usager=usager,
                        creation_date=first_unlinked_auto.creation_date,
                        expiration_date=first_unlinked_auto.expiration_date,
                        is_remote=first_unlinked_auto.is_remote,
                    )

                    # TODO: (Try to) set the `duree_keyword` attribute on the
                    # `mandat`. That means making an "educated guesses" on the
                    # originally selected duration of the `mandat` based on the
                    # expiration date and the history we can gather through
                    # journal entries.

                    self.stdout.write("        -> Created Mandat #%d" % (
                        new_mandat.id,
                    ))

                    # We link to this new `mandat` all the `autorisations` that
                    # were created at "roughly the same time" (within one
                    # minute) as the current one.
                    creation_date = new_mandat.creation_date
                    creation_threshold = creation_date + timedelta(seconds=60)

                    current_auto = first_unlinked_auto

                    while current_auto.creation_date < creation_threshold:

                        current_auto.mandat = new_mandat
                        current_auto.save()

                        self.stdout.write(
                            "          -> Linked Autorisation #%d (%s)" % (
                                current_auto.id, current_auto.demarche
                            )
                        )

                        num_linked_orga_autos += 1
                        current_auto = orga_autos[num_linked_orga_autos]

        self.stdout.write("All done.")

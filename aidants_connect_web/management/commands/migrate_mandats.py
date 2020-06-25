# flake8: noqa

from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

from aidants_connect_web.models import (
    Autorisation,
    AutorisationDureeKeywords,
    Journal,
    Mandat,
    Organisation,
    Usager,
)


class Command(BaseCommand):

    help = "Migrate the current mandats to the new data model"

    def _compute_duree_keyword(self, autorisation):

        ETAT_URGENCE_2020_LAST_DAYS = (
            datetime.strptime("23/05/2020 23:59:59 +0100", "%d/%m/%Y %H:%M:%S %z"),  # the first one
            settings.ETAT_URGENCE_2020_LAST_DAY,
        )
        if autorisation.expiration_date in ETAT_URGENCE_2020_LAST_DAYS:
            return AutorisationDureeKeywords.EUS_03_20.value

        duration = autorisation.expiration_date - autorisation.creation_date
        ONE_DAY = 60 * 60 * 24  # in seconds
        APPROXIMATELY_ONE_DAY = ONE_DAY + (ONE_DAY * 5 / 100)  # 5% leeway

        if duration.total_seconds() < APPROXIMATELY_ONE_DAY:
            duree_keyword = AutorisationDureeKeywords.SHORT
        else:
            duree_keyword = AutorisationDureeKeywords.LONG

        return duree_keyword.value

    def handle(self, *args, **options):

        self.stdout.write("Migrating data to new Mandat model...")

        # First, we convert all "create_mandat_print" journal entries
        # to the new "create_attestation" wording.
        Journal.objects.filter(
            action='create_mandat_print'
        ).update(
            action='create_attestation'
        )

        # Also, for some reason(?), it appears that a wrong date was applied
        # to a lot of `autorisations` expiring at the end of the state of
        # emergency (which is, as Björk will tell you, where I want to be.)
        Autorisation.objects.filter(
            expiration_date=settings.ETAT_URGENCE_2020_LAST_DAY - timedelta(days=1)
        ).update(
            expiration_date=settings.ETAT_URGENCE_2020_LAST_DAY
        )

        # We can now loop through all our `usagers`...
        for usager in Usager.objects.order_by('creation_date'):

            self.stdout.write("\n  Processing Usager #%d" % usager.id)

            autos = usager.autorisations.order_by('creation_date')

            num_autos = autos.count()

            orga_ids = set([auto.aidant.organisation.id for auto in autos])
            num_orgas = len(orga_ids)

            self.stdout.write("    -> %d Autorisation(s), with %d Organisation(s)" % (
                num_autos, num_orgas
            ))

            # Then, for each `usager`, we loop through all the `organisations`
            # they have signed a `mandat` with...
            for orga_id in orga_ids:

                # This is wildly unoptimized, but it hardly matters
                # given our current data volume.
                orga = Organisation.objects.get(pk=orga_id)
                orga_name = orga.name

                orga_autos = autos.filter(aidant__organisation__pk=orga_id).order_by('creation_date')
                num_orga_autos = orga_autos.count()
                num_linked_orga_autos = 0

                self.stdout.write("      -> Creating Mandat(s) with Organisation \"%s\" (#%d)..." % (
                    orga_name, orga_id
                ))

                # We need to go on as long as all the `autorisations` are not
                # properly linked to a `mandat`.

                previous_mandat = None

                # Empirical hack: we force the queryset evaluation now.
                # If this is not done now, experience shows that there will be duplicates in it.
                # I'm not sure why, but it's past 7pm on a Friday night so it'll have to do.
                # This is probably because otherwise that would mean _slicing an unevaluated queryset_
                # which seems a bit... er... undeterministic?
                # See: https://docs.djangoproject.com/en/dev/ref/models/querysets/#when-querysets-are-evaluated
                orga_autos = list(orga_autos)

                while num_linked_orga_autos < num_orga_autos:

                    # We focus on the first unlinked `autorisation`.
                    first_unlinked_auto = orga_autos[num_linked_orga_autos]

                    # We create a `mandat` based on this `autorisation`'s data.
                    new_mandat = Mandat.objects.create(
                        organisation=Organisation.objects.get(pk=orga_id),
                        usager=usager,
                        creation_date=first_unlinked_auto.creation_date,
                        expiration_date=first_unlinked_auto.expiration_date,
                        is_remote=first_unlinked_auto.is_remote,
                        duree_keyword=self._compute_duree_keyword(
                            first_unlinked_auto
                        )
                    )

                    self.stdout.write("        -> Created Mandat #%d (%s)" % (
                        new_mandat.id, new_mandat.duree_keyword
                    ))

                    # We link to this new `mandat` all the `autorisations` that were created
                    # at "roughly the same time" (within one hour) as the current one.
                    creation_date = new_mandat.creation_date
                    creation_threshold = creation_date + timedelta(hours=1)

                    current_auto = first_unlinked_auto

                    while current_auto.creation_date < creation_threshold:

                        current_auto.mandat = new_mandat
                        current_auto.save()

                        self.stdout.write("          -> Linked Autorisation #%d (%s)" % (
                            current_auto.id, current_auto.demarche
                        ))
                        self.stdout.write("             from: %s" % current_auto.creation_date.strftime('%c'))
                        self.stdout.write("               to: %s" % current_auto.expiration_date.strftime('%c'))
                        num_linked_orga_autos += 1

                        try:
                            current_auto = orga_autos[num_linked_orga_autos]
                        except IndexError:
                            break

                    previous_mandat = new_mandat

        # A little sanity check just to be sure...
        unlinked_autos = Autorisation.objects.filter(mandat__isnull=True)
        num_unlinked_autos = unlinked_autos.count()
        if num_unlinked_autos > 0:
            self.stdout.write("WARNING: %d Autorisations remain unlinked to any Mandat!" % num_unlinked_autos)
        else:
            self.stdout.write("All done! :)")

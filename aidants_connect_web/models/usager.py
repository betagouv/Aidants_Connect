from __future__ import annotations

import logging
from datetime import timedelta

from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField

from .journal import Journal
from .utils import delete_mandats_and_clean_journal

logger = logging.getLogger()


class UsagerQuerySet(models.QuerySet):
    def active(self):
        return (
            self.filter(mandats__expiration_date__gt=timezone.now())
            .filter(mandats__autorisations__revocation_date__isnull=True)
            .distinct()
        )

    def visible_by(self, aidant):
        """
        :param aidant:
        :return: a new QuerySet instance only filtering in the usagers who have
        an autorisation with this aidant's organisation.
        """
        return self.filter(mandats__organisation=aidant.organisation).distinct()


class Usager(models.Model):
    GENDER_FEMALE = "female"
    GENDER_MALE = "male"
    GENDER_CHOICES = (
        (GENDER_FEMALE, "Femme"),
        (GENDER_MALE, "Homme"),
    )
    BIRTHCOUNTRY_FRANCE = "99100"
    EMAIL_NOT_PROVIDED = "noemailprovided@aidantconnect.beta.gouv.fr"

    given_name = models.CharField("Prénom", max_length=255, blank=False)
    family_name = models.CharField("Nom", max_length=255, blank=False)
    preferred_username = models.CharField(max_length=255, blank=True, null=True)

    gender = models.CharField(
        "Genre",
        max_length=6,
        choices=GENDER_CHOICES,
        default=GENDER_FEMALE,
    )

    birthdate = models.DateField("Date de naissance", blank=False)
    birthplace = models.CharField(
        "Lieu de naissance", max_length=5, blank=True, null=True
    )
    birthcountry = models.CharField(
        "Pays de naissance",
        max_length=5,
        default=BIRTHCOUNTRY_FRANCE,
    )

    sub = models.TextField(blank=False, unique=True)
    email = models.EmailField(blank=False, default=EMAIL_NOT_PROVIDED)
    creation_date = models.DateTimeField("Date de création", default=timezone.now)

    phone = PhoneNumberField(blank=True)

    objects = UsagerQuerySet.as_manager()

    class Meta:
        ordering = ["family_name", "given_name"]

    @property
    def search_terms(self):
        search_term = [self.family_name, self.given_name]
        if self.preferred_username:
            search_term.append(self.preferred_username)

        return search_term

    @property
    def renew_mandate_url(self):
        return reverse("renew_mandat", kwargs={"usager_id": self.id})

    def __str__(self):
        return f"{self.given_name} {self.family_name}"

    def get_full_name(self):
        return str(self)

    def normalize_birthplace(self):
        if not self.birthplace:
            return None

        normalized_birthplace = self.birthplace.zfill(5)
        if normalized_birthplace != self.birthplace:
            self.birthplace = normalized_birthplace
            self.save(update_fields=["birthplace"])

        return self.birthplace

    def clean_journal_entries_and_delete_mandats(self, request=None):
        today = timezone.now()
        str_today = today.strftime("%d/%m/%Y à %Hh%M")
        delete_mandats_and_clean_journal(self, str_today)

        entries = Journal.objects.filter(usager=self)

        usager_str_add_inf = (
            f"Add by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif à l'usager supprimé {self.family_name} "
            f"{self.given_name}  {self.preferred_username} "
            f"{self.email} le {str_today}"
        )
        entries.update(
            usager=None,
            additional_information=Concat(
                "additional_information", Value(usager_str_add_inf)
            ),
        )
        return True

    def has_all_mandats_revoked_or_expired_over_a_year(self):
        for mandat in self.mandats.all():
            if (
                not mandat.was_explicitly_revoked
                and timezone.now() < mandat.expiration_date + timedelta(days=365)
            ):
                return False
        return True

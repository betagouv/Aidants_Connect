from __future__ import annotations

import logging

from django.db.models import Value
from django.db.models.functions import Concat

from .journal import Journal

logger = logging.getLogger()


def delete_mandats_and_clean_journal(item, str_today):
    for mandat in item.mandats.all():
        entries = Journal.objects.filter(mandat=mandat)
        mandat_str_add_inf = (
            f"Added by clean_journal_entries_and_delete_mandats :"
            f"\n Relatif au mandat supprimé {mandat} le {str_today}"
        )
        entries.update(
            mandat=None,
            additional_information=Concat(
                "additional_information", Value(mandat_str_add_inf)
            ),
        )
        mandat.delete()

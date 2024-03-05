from __future__ import annotations

import logging
import re
from textwrap import dedent

from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat

import pgtrigger

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


class PGTriggerExtendedFunc(pgtrigger.Func):
    """Temporary until https://github.com/Opus10/django-pgtrigger/pull/150/ is merged"""

    def __init__(
        self, func, additionnal_models: dict[str, type[models.Model]] | None = None
    ):
        super().__init__(dedent(re.sub(r"[ \t\r\f\v]+\n", "\n", func)).strip())
        self.additionnal_models = additionnal_models or {}

    def render(self, model: models.Model) -> str:
        fields = pgtrigger.utils.AttrDict(
            {field.name: field for field in model._meta.fields}
        )
        columns = pgtrigger.utils.AttrDict(
            {field.name: field.column for field in model._meta.fields}
        )
        format_parameters = {"meta": model._meta, "fields": fields, "columns": columns}
        for prefix, additionnal_model in self.additionnal_models.items():
            format_parameters.update(
                {
                    f"{prefix}_meta": additionnal_model._meta,
                    f"{prefix}_fields": pgtrigger.utils.AttrDict(
                        {field.name: field for field in additionnal_model._meta.fields}
                    ),
                    f"{prefix}_columns": pgtrigger.utils.AttrDict(
                        {
                            field.name: field.column
                            for field in additionnal_model._meta.fields
                        }
                    ),
                }
            )
        return self.func.format(**format_parameters)

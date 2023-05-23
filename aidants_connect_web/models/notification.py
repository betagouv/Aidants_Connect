from __future__ import annotations

import logging

from django.db import models
from django.db.models import Q

from aidants_connect_web.constants import NotificationType

from .aidant import Aidant

logger = logging.getLogger()


class Notification(models.Model):
    type = models.CharField(choices=NotificationType.choices)
    aidant = models.ForeignKey(
        Aidant, on_delete=models.CASCADE, related_name="notifications"
    )
    date = models.DateField(auto_now_add=True)
    must_ack = models.BooleanField("Doit être acquité pour disparaître", default=True)
    auto_ack_date = models.DateField("Échéance", null=True, default=None)
    was_ack = models.BooleanField("A été acquité", null=True, default=False)

    def mark_read(self):
        self.was_ack = True
        self.save()

    def mark_unread(self):
        self.was_ack = False
        self.save()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    # Must be aknowlegeable if it has to be aknowleged
                    (Q(must_ack=False) ^ Q(was_ack__isnull=False))
                    # Can't both have no expiration date and be not acknoledgeable
                    & (Q(auto_ack_date__isnull=False) | Q(was_ack__isnull=False))
                ),
                name="must_ack_conditions",
            )
        ]

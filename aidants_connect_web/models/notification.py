from __future__ import annotations

import logging
from typing import Self

from django.db import models
from django.db.models import Q
from django.utils import timezone

from aidants_connect_common.models import MarkdownContentMixin
from aidants_connect_web.constants import NotificationType

from .aidant import Aidant

logger = logging.getLogger()


class NotificationQuerySet(models.QuerySet):
    def get_displayable_for_user(self, aidant: Aidant) -> Self:
        return self.filter(
            (
                (Q(must_ack=True) & Q(was_ack=False))
                | Q(auto_ack_date__gt=timezone.now())
            ),
            aidant=aidant,
        )


class Notification(MarkdownContentMixin):
    NotificationType = NotificationType

    type = models.CharField(choices=NotificationType.choices)
    aidant = models.ForeignKey(
        Aidant, on_delete=models.CASCADE, related_name="notifications"
    )
    date = models.DateField(auto_now_add=True)
    must_ack = models.BooleanField("Doit être acquité pour disparaître", default=True)
    auto_ack_date = models.DateField("Échéance", blank=True, null=True, default=None)
    was_ack = models.BooleanField("A été acquité", default=False)

    objects = NotificationQuerySet.as_manager()

    @property
    def type_label(self):
        return NotificationType(self.type).label

    def __str__(self):
        return f"Notification {self.get_type_display()} pour {self.aidant}"

    def mark_read(self):
        self.was_ack = True
        self.save(update_fields={"was_ack"})

    def mark_unread(self):
        self.was_ack = False
        self.save(update_fields={"was_ack"})

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    # Can't be manually acknowledged if manual ack is disabled
                    ~(Q(must_ack=False) & Q(was_ack=True))
                    # Can't both have no expiration date and be not acknoledgeable
                    & (Q(auto_ack_date__isnull=False) ^ Q(must_ack=True))
                ),
                name="must_ack_conditions",
            )
        ]

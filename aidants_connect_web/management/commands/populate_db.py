from ...models import Demarche
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


def create_demarches():
    demarches = [
        {"id": 0, "title": "Autre", "weight": -1},
        {"id": 1, "title": "Ma déclaration de revenus", "weight": 100},
        {"id": 2, "title": "Un renouvellement de carte grise", "weight": 80},
    ]
    for demarche in demarches:
        obj, created = Demarche.objects.update_or_create(
            id=int(demarche["id"]),
            defaults={"title": demarche["title"], "weight": demarche["weight"]},
        )


class Command(BaseCommand):
    help = "Populate database with initial demarches"

    def handle(self, *args, **kwargs):
        create_demarches()

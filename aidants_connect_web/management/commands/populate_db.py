from ...models import Demarche
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


def create_demarches():
    demarches = [
        {"id": 0, "title": "Autre", "weight": -1},
        {"id": 1, "title": "Déclarer mes revenus fiscaux", "weight": 100},
        {"id": 2, "title": "Déclarer un changement d’adresse", "weight": 80},
        {"id": 3, "title": "M’inscrire sur les listes électorales", "weight": 80},
        {
            "id": 4,
            "title": "Renouveler mon passeport / ma carte nationale d’identité",
            "weight": 80,
        },
        {
            "id": 5,
            "title": "Faire une démarche concernant mon permis / ma carte grise",
            "weight": 80,
        },
        {
            "id": 6,
            "title": "Suivre ma demande de Revenu de Solidarité Active (RSA)",
            "weight": 80,
        },
        {"id": 7, "title": "Faire une demande de carte de séjour", "weight": 80},
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

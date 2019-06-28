from ...models import Demarche, DemarcheCategory
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


def create_categories():
    categories = [
        {"id": 0, "title": "Logement", "weight": 100},
        {"id": 1, "title": "Transport", "weight": 90},
        {"id": 2, "title": "Santé", "weight": 80},
        {"id": 3, "title": "Handicap", "weight": 70},
        {"id": 4, "title": "Aides sociales", "weight": 60},
        {"id": 5, "title": "Famille", "weight": 50},
        {"id": 6, "title": "Papiers-Citoyenneté", "weight": 40},
        {"id": 7, "title": "Travail", "weight": 30},
        {"id": 8, "title": "Élections", "weight": 20},
        {"id": 9, "title": "Impôts", "weight": 10},
    ]
    for category in categories:
        obj, created = DemarcheCategory.objects.update_or_create(
            id=int(category["id"]),
            defaults={"title": category["title"], "weight": category["weight"]},
        )


def create_demarches():
    demarches = [
        {
            "id": 0,
            "title": "Signaler un changement d’adresse",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 1,
            "title": "Demander une allocation logement",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 2,
            "title": "Demander une aide au paiement des factures",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 3,
            "title": "Demander une aide pour la rénovation énergétique de mon logement",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 4,
            "title": "Hébergement social",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 5,
            "title": "Ehpad",
            "category": DemarcheCategory.objects.get(id=0),
            "weight": 0,
        },
        {
            "id": 6,
            "title": "Carte grise",
            "category": DemarcheCategory.objects.get(id=1),
            "weight": 0,
        },
        {
            "id": 7,
            "title": "Permis de conduire",
            "category": DemarcheCategory.objects.get(id=1),
            "weight": 0,
        },
        {
            "id": 8,
            "title": "Infractions routières",
            "category": DemarcheCategory.objects.get(id=1),
            "weight": 0,
        },
        {
            "id": 9,
            "title": "Affiliation ou remboursement sécurité sociale",
            "category": DemarcheCategory.objects.get(id=2),
            "weight": 0,
        },
        {
            "id": 10,
            "title": "Hospitalisation",
            "category": DemarcheCategory.objects.get(id=2),
            "weight": 0,
        },
        {
            "id": 11,
            "title": "Soins à domicile",
            "category": DemarcheCategory.objects.get(id=2),
            "weight": 0,
        },
        {
            "id": 12,
            "title": "Invalidité temporaire",
            "category": DemarcheCategory.objects.get(id=2),
            "weight": 0,
        },
        {
            "id": 13,
            "title": "Pension d’invalidité",
            "category": DemarcheCategory.objects.get(id=2),
            "weight": 0,
        },
        {
            "id": 14,
            "title": "Allocations (AAH, AEEH, PCH)",
            "category": DemarcheCategory.objects.get(id=3),
            "weight": 0,
        },
        {
            "id": 15,
            "title": "Couverture maladie universelle complémentaire (CMU-C)",
            "category": DemarcheCategory.objects.get(id=3),
            "weight": 0,
        },
        {
            "id": 16,
            "title": "Aide au paiement d’une complémentaire santé (ACS)",
            "category": DemarcheCategory.objects.get(id=3),
            "weight": 0,
        },
        {
            "id": 17,
            "title": "Revenu de solidarité active (RSA)",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 18,
            "title": "Allocation personnalisée d’autonomie (APA)",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 19,
            "title": "Allocation de solidarité aux personnes âgées (ASPA)",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 20,
            "title": "Allocation supplémentaire d’invalidité (ASI)",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 21,
            "title": "Allocation de solidarité spécifique (ASS)",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 22,
            "title": "Prime d’activité",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 23,
            "title": "Chèque énergie",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 24,
            "title": "Allocation familiale",
            "category": DemarcheCategory.objects.get(id=4),
            "weight": 0,
        },
        {
            "id": 25,
            "title": "Naissance",
            "category": DemarcheCategory.objects.get(id=5),
            "weight": 0,
        },
        {
            "id": 26,
            "title": "Adoption",
            "category": DemarcheCategory.objects.get(id=5),
            "weight": 0,
        },
        {
            "id": 27,
            "title": "PACS",
            "category": DemarcheCategory.objects.get(id=5),
            "weight": 0,
        },
        {
            "id": 28,
            "title": "Mariage",
            "category": DemarcheCategory.objects.get(id=5),
            "weight": 0,
        },
        {
            "id": 29,
            "title": "Divorce",
            "category": DemarcheCategory.objects.get(id=5),
            "weight": 0,
        },
        {
            "id": 30,
            "title": "Carte d’identité",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 31,
            "title": "Passeport",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 32,
            "title": "Certificat, copie, légalisation de document",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 33,
            "title": "Livret de famille",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 34,
            "title": "Changement de nom ou prénom",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 35,
            "title": "Changement de sexe",
            "category": DemarcheCategory.objects.get(id=6),
            "weight": 0,
        },
        {
            "id": 36,
            "title": "S’inscrire sur les listes électorales",
            "category": DemarcheCategory.objects.get(id=7),
            "weight": 0,
        },
        {
            "id": 37,
            "title": "Déclaration de revenus",
            "category": DemarcheCategory.objects.get(id=8),
            "weight": 0,
        },
        {
            "id": 38,
            "title": "Impôts professionnels",
            "category": DemarcheCategory.objects.get(id=8),
            "weight": 0,
        },
        {
            "id": 39,
            "title": "Taxe d’habitation",
            "category": DemarcheCategory.objects.get(id=8),
            "weight": 0,
        },
    ]
    for demarche in demarches:
        obj, created = Demarche.objects.update_or_create(
            id=int(demarche["id"]),
            defaults={
                "title": demarche["title"],
                "category": demarche["category"],
                "weight": demarche["weight"],
            },
        )


class Command(BaseCommand):
    help = "Populate database with initial demarches"

    def handle(self, *args, **kwargs):
        create_categories()
        create_demarches()

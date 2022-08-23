from json import loads as json_loads
from pathlib import Path

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

import aidants_connect_common
from aidants_connect_common.apps import AidantsConnectCommonConfig


@receiver(post_migrate)
def populate_departments_and_tables(app_config: AppConfig, **_):
    if app_config.name == AidantsConnectCommonConfig.name:
        Region = app_config.get_model("Region")
        Department = app_config.get_model("Department")

        fixture = (
            Path(aidants_connect_common.__file__).parent
            / "fixtures"
            / "departements_region.json"
        )

        with open(fixture) as f:
            json = json_loads(f.read())
            regions = json["regions"]
            departments = json["departments"]

            for region in regions:
                Region.objects.get_or_create(
                    insee_code=region["inseeCode"],
                    defaults={"name": region["name"]},
                )

            for department in departments:
                Department.objects.get_or_create(
                    insee_code=department["inseeCode"],
                    defaults={
                        "name": department["name"],
                        "zipcode": department["zipcode"],
                        "region": Region.objects.get(name=department["region"]),
                    },
                )

from typing import Any

from django.db import models
from django.db.models import CASCADE


class Region(models.Model):
    insee_code = models.CharField(
        "Code INSEE", max_length=2, unique=True, primary_key=True
    )
    name = models.CharField("Nom de région", max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Région"


class Department(models.Model):
    insee_code = models.CharField(
        "Code INSEE", max_length=3, unique=True, primary_key=True
    )
    zipcode = models.CharField("Code Postal", max_length=5)
    name = models.CharField("Nom du département", max_length=50, unique=True)
    region = models.ForeignKey(Region, on_delete=CASCADE, related_name="department")

    def __str__(self):
        return self.name

    @staticmethod
    def extract_dept_zipcode(code: Any):
        code = str(code).upper()
        if code.startswith("2A") or code.startswith("2B"):
            return "20"
        elif code.startswith("97"):
            return code[:3]

        return code[:2]

    class Meta:
        verbose_name = "Département"

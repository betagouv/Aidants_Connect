def __2024_02_26_bulk_populate_conseiller_numerique():
    from aidants_connect_web.models import Aidant

    FILE_PATH = ""
    with open(FILE_PATH, "r") as f:
        Aidant.objects.filter(email__in=f.read().splitlines()).update(
            conseiller_numerique=True
        )

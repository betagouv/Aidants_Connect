from celery import shared_task

from .synchro_grist import get_connexion_model_from_grist


@shared_task
def get_connexion_mode_from_grist_task():
    get_connexion_model_from_grist()

import logging

from django.template.defaultfilters import pluralize

from celery import shared_task

from aidants_connect_web.models import Connection


logger = logging.getLogger()


@shared_task
def delete_expired_connections():

    logger.info("Deleting expired connections...")

    expired_connections = Connection.objects.expired()
    deleted_connections_count, _ = expired_connections.delete()

    if deleted_connections_count > 0:
        logger.info(
            f"Successfully deleted {deleted_connections_count} "
            f"connection{pluralize(deleted_connections_count)}!"
        )
    else:
        logger.info("No connection to delete.")

    return deleted_connections_count

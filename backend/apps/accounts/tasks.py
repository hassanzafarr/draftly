import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def purge_storage_files(self, names):
    """Delete stored files left behind by an account erasure.

    Missing files count as deleted. Retries only the names that failed.
    """
    from django.core.files.storage import default_storage

    failed = []
    for name in names:
        try:
            default_storage.delete(name)
        except Exception:
            logger.exception("Could not delete stored file during erasure purge")
            failed.append(name)

    if failed:
        raise self.retry(args=[failed])
    logger.info("Purged %d stored files", len(names))
    return len(names)

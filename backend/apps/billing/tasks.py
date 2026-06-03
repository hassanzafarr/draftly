import datetime
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

STRIPE_EVENT_RETENTION_DAYS = 30


@shared_task
def prune_stripe_events():
    """Delete StripeEvent rows older than STRIPE_EVENT_RETENTION_DAYS.

    Stripe only retries webhooks for ~3 days, so rows beyond 30 days serve no
    idempotency purpose and grow the table unboundedly.
    """
    from .models import StripeEvent

    cutoff = timezone.now() - datetime.timedelta(days=STRIPE_EVENT_RETENTION_DAYS)
    deleted, _ = StripeEvent.objects.filter(received_at__lt=cutoff).delete()
    logger.info("Pruned %d StripeEvent rows older than %d days", deleted, STRIPE_EVENT_RETENTION_DAYS)
    return deleted

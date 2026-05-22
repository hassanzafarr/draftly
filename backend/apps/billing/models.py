from django.db import models


class StripeEvent(models.Model):
    """Idempotency record for Stripe webhook events.

    Stripe retries deliveries on non-2xx responses, so the same event can arrive
    multiple times. We insert the event id before processing; a duplicate insert
    raises IntegrityError and we skip handling.
    """

    event_id = models.CharField(max_length=255, primary_key=True)
    event_type = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["received_at"])]

    def __str__(self):
        return f"{self.event_type}:{self.event_id}"

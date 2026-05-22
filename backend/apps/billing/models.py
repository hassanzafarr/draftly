from django.db import models


class CreditPurchase(models.Model):
    """Audit trail for credit pack purchases. Balance is stored on Organization.credit_balance."""
    org = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="credit_purchases",
    )
    credits_purchased = models.PositiveIntegerField()
    credits_remaining = models.PositiveIntegerField()
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default="")
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.org} — {self.credits_purchased} credits ({self.purchased_at:%Y-%m-%d})"

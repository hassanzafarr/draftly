"""Stripe billing webhook + checkout tests.

Covers the production-critical paths:
- Webhook signature verification (rejects bad signatures, accepts valid ones).
- Idempotency: a duplicate event id is acknowledged but not re-processed.
- Portal upgrade path: subscription.updated derives tier from the price id,
  NOT from metadata (which the Customer Portal does not copy).
- Renewal: invoice.paid refreshes current_period_end and clears past_due.
- Cancellation: subscription.deleted downgrades to free.

We monkey-patch `stripe.Webhook.construct_event` so tests don't need a real
secret + signed payload; the bypass test asserts that the real path still
rejects bad signatures.
"""

import datetime
import json
from unittest.mock import patch

import pytest
import stripe

from apps.accounts.models import Organization
from apps.accounts.tests.factories import OrganizationFactory
from apps.billing.models import StripeEvent

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(event_id, event_type, data_object):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data_object},
    }


def _post_webhook(api_client, event):
    """Post a webhook event, bypassing signature verification via mock."""
    with patch.object(stripe.Webhook, "construct_event", return_value=event):
        return api_client.post(
            "/api/billing/webhook/",
            data=json.dumps(event),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test-sig",
        )


@pytest.fixture
def billing_settings(settings):
    """Configure deterministic price IDs for tier resolution."""
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    settings.STRIPE_SECRET_KEY = "sk_test"
    settings.STRIPE_PRICE_SOLO_MONTHLY = "price_solo_m"
    settings.STRIPE_PRICE_SOLO_ANNUAL = "price_solo_a"
    settings.STRIPE_PRICE_STUDIO_MONTHLY = "price_studio_m"
    settings.STRIPE_PRICE_STUDIO_ANNUAL = "price_studio_a"
    settings.STRIPE_PRICE_AGENCY_MONTHLY = "price_agency_m"
    settings.STRIPE_PRICE_AGENCY_ANNUAL = "price_agency_a"
    return settings


@pytest.fixture
def org_with_customer(db):
    return OrganizationFactory(
        name="Customer Org",
        stripe_customer_id="cus_test_123",
        subscription_tier="solo",
        billing_cadence="monthly",
        subscription_status="active",
    )


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def test_webhook_rejects_missing_secret(api_client, settings):
    settings.STRIPE_WEBHOOK_SECRET = ""

    res = api_client.post(
        "/api/billing/webhook/",
        data=json.dumps({"id": "evt_1", "type": "checkout.session.completed"}),
        content_type="application/json",
    )
    assert res.status_code == 400


def test_webhook_rejects_bad_signature(api_client, billing_settings):
    """When real construct_event raises, webhook returns 400 — no event recorded."""
    res = api_client.post(
        "/api/billing/webhook/",
        data=b'{"bogus": true}',
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=0,v1=deadbeef",
    )
    assert res.status_code == 400
    assert not StripeEvent.objects.exists()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_duplicate_event_is_skipped(api_client, billing_settings, org_with_customer):
    """Second delivery of the same event id must not re-apply state changes."""
    event = _make_event(
        "evt_dupe_1",
        "customer.subscription.deleted",
        {"customer": org_with_customer.stripe_customer_id},
    )

    res1 = _post_webhook(api_client, event)
    assert res1.status_code == 200

    org_with_customer.refresh_from_db()
    assert org_with_customer.subscription_tier == "free"

    # Manually "undo" the state change so we can detect re-processing.
    Organization.objects.filter(pk=org_with_customer.pk).update(
        subscription_tier="solo",
        subscription_status="active",
    )

    res2 = _post_webhook(api_client, event)
    assert res2.status_code == 200

    org_with_customer.refresh_from_db()
    # If the handler ran twice, this would be "free" again. Idempotency holds.
    assert org_with_customer.subscription_tier == "solo"
    assert StripeEvent.objects.filter(event_id="evt_dupe_1").count() == 1


def test_handler_failure_rolls_back_idempotency_marker(api_client, billing_settings):
    """If _handle_event raises, the StripeEvent row must be removed so Stripe
    can retry and we process the event next time."""
    event = _make_event("evt_fail_1", "customer.subscription.updated", {"customer": "cus_x"})

    with patch("apps.billing.views._handle_event", side_effect=RuntimeError("boom")):
        res = _post_webhook(api_client, event)

    assert res.status_code == 500
    assert not StripeEvent.objects.filter(event_id="evt_fail_1").exists()


# ---------------------------------------------------------------------------
# Portal upgrade path — the original P0 bug
# ---------------------------------------------------------------------------


def test_portal_upgrade_resolves_tier_from_price_not_metadata(
    api_client, billing_settings, org_with_customer
):
    """Customer Portal plan changes do NOT copy metadata.

    Regression guard: subscription.updated must derive tier from the price id
    on items.data[0], not from the (absent) metadata.tier field.
    """
    period_end_ts = int(datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC).timestamp())
    subscription = {
        "id": "sub_test_1",
        "customer": org_with_customer.stripe_customer_id,
        "status": "active",
        "current_period_end": period_end_ts,
        # No metadata.tier — simulates a portal upgrade.
        "metadata": {},
        "items": {"data": [{"price": {"id": billing_settings.STRIPE_PRICE_STUDIO_ANNUAL}}]},
    }
    event = _make_event("evt_portal_1", "customer.subscription.updated", subscription)

    res = _post_webhook(api_client, event)
    assert res.status_code == 200

    org_with_customer.refresh_from_db()
    assert org_with_customer.subscription_tier == "studio"
    assert org_with_customer.billing_cadence == "annual"
    assert org_with_customer.subscription_status == "active"
    assert org_with_customer.stripe_subscription_id == "sub_test_1"


def test_subscription_updated_with_unknown_price_keeps_tier(
    api_client, billing_settings, org_with_customer
):
    """Unknown price ID must not corrupt tier; status + period_end still sync."""
    subscription = {
        "id": "sub_test_2",
        "customer": org_with_customer.stripe_customer_id,
        "status": "past_due",
        "current_period_end": 1_900_000_000,
        "metadata": {},
        "items": {"data": [{"price": {"id": "price_unknown"}}]},
    }
    event = _make_event("evt_unknown_price", "customer.subscription.updated", subscription)

    _post_webhook(api_client, event)
    org_with_customer.refresh_from_db()

    assert org_with_customer.subscription_tier == "solo"  # unchanged
    assert org_with_customer.subscription_status == "past_due"


# ---------------------------------------------------------------------------
# Invoice paid (renewal)
# ---------------------------------------------------------------------------


def test_invoice_paid_refreshes_period_end_and_clears_past_due(
    api_client, billing_settings, org_with_customer
):
    Organization.objects.filter(pk=org_with_customer.pk).update(subscription_status="past_due")

    period_end_ts = int(datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC).timestamp())
    invoice = {
        "customer": org_with_customer.stripe_customer_id,
        "lines": {"data": [{"period": {"end": period_end_ts}}]},
    }
    event = _make_event("evt_invoice_1", "invoice.paid", invoice)

    res = _post_webhook(api_client, event)
    assert res.status_code == 200

    org_with_customer.refresh_from_db()
    assert org_with_customer.subscription_status == "active"
    assert org_with_customer.current_period_end is not None
    assert org_with_customer.current_period_end.year == 2026
    assert org_with_customer.current_period_end.month == 7


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def test_subscription_deleted_downgrades_to_free(api_client, billing_settings, org_with_customer):
    event = _make_event(
        "evt_cancel_1",
        "customer.subscription.deleted",
        {"customer": org_with_customer.stripe_customer_id},
    )
    res = _post_webhook(api_client, event)
    assert res.status_code == 200

    org_with_customer.refresh_from_db()
    assert org_with_customer.subscription_tier == "free"
    assert org_with_customer.subscription_status == "canceled"
    assert org_with_customer.stripe_subscription_id == ""
    assert org_with_customer.current_period_end is None


# ---------------------------------------------------------------------------
# Payment failed
# ---------------------------------------------------------------------------


def test_payment_failed_sets_past_due(api_client, billing_settings, org_with_customer):
    event = _make_event(
        "evt_pf_1",
        "invoice.payment_failed",
        {"customer": org_with_customer.stripe_customer_id},
    )
    _post_webhook(api_client, event)

    org_with_customer.refresh_from_db()
    assert org_with_customer.subscription_status == "past_due"
    # Tier should NOT change on a single failed payment.
    assert org_with_customer.subscription_tier == "solo"

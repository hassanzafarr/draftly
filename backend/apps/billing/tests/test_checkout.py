"""Checkout + portal endpoint tests.

We mock the Stripe SDK calls (the live API requires network + real keys).
Coverage focuses on:
- Tier/cadence validation.
- Customer is created lazily and cached on the Organization.
- The created Checkout Session uses the price id corresponding to (tier, cadence).
- Portal is rejected when org has no stripe_customer_id.
"""

from unittest.mock import MagicMock, patch

import pytest
import stripe

pytestmark = pytest.mark.django_db


@pytest.fixture
def billing_settings(settings):
    settings.STRIPE_SECRET_KEY = "sk_test"
    settings.STRIPE_PRICE_SOLO_MONTHLY = "price_solo_m"
    settings.STRIPE_PRICE_SOLO_ANNUAL = "price_solo_a"
    settings.STRIPE_PRICE_STUDIO_MONTHLY = "price_studio_m"
    settings.STRIPE_PRICE_STUDIO_ANNUAL = "price_studio_a"
    settings.STRIPE_PRICE_AGENCY_MONTHLY = "price_agency_m"
    settings.STRIPE_PRICE_AGENCY_ANNUAL = "price_agency_a"
    settings.FRONTEND_URL = "https://app.example.com"
    return settings


def test_checkout_rejects_invalid_tier(auth_client, billing_settings):
    res = auth_client.post(
        "/api/billing/checkout/",
        {"tier": "enterprise", "billing_cadence": "monthly"},
        format="json",
    )
    assert res.status_code == 400


def test_checkout_rejects_invalid_cadence(auth_client, billing_settings):
    res = auth_client.post(
        "/api/billing/checkout/",
        {"tier": "solo", "billing_cadence": "weekly"},
        format="json",
    )
    assert res.status_code == 400


def test_checkout_503_when_price_not_configured(auth_client, settings):
    settings.STRIPE_SECRET_KEY = "sk_test"
    settings.STRIPE_PRICE_SOLO_MONTHLY = ""  # explicitly unset

    res = auth_client.post(
        "/api/billing/checkout/",
        {"tier": "solo", "billing_cadence": "monthly"},
        format="json",
    )
    assert res.status_code == 503


def test_checkout_creates_customer_and_session_with_correct_price(auth_client, billing_settings):
    fake_customer = MagicMock(id="cus_new_1")
    fake_session = MagicMock(url="https://stripe.test/checkout/abc")

    with (
        patch.object(stripe.Customer, "create", return_value=fake_customer) as mock_cust,
        patch.object(stripe.checkout.Session, "create", return_value=fake_session) as mock_sess,
    ):
        res = auth_client.post(
            "/api/billing/checkout/",
            {"tier": "studio", "billing_cadence": "annual"},
            format="json",
        )

    assert res.status_code == 200
    assert res.json()["url"] == "https://stripe.test/checkout/abc"
    mock_cust.assert_called_once()
    # Customer.create receives the user's email (so it shows up in Stripe dashboard).
    assert mock_cust.call_args.kwargs["email"] == auth_client.user.email

    # Session created with the *annual* studio price id.
    call_kwargs = mock_sess.call_args.kwargs
    assert call_kwargs["customer"] == "cus_new_1"
    assert call_kwargs["line_items"][0]["price"] == billing_settings.STRIPE_PRICE_STUDIO_ANNUAL
    assert call_kwargs["success_url"].startswith("https://app.example.com/pricing")
    assert call_kwargs["metadata"]["tier"] == "studio"
    assert call_kwargs["metadata"]["billing_cadence"] == "annual"

    auth_client.user.org.refresh_from_db()
    assert auth_client.user.org.stripe_customer_id == "cus_new_1"


def test_checkout_reuses_existing_customer(auth_client, billing_settings):
    auth_client.user.org.stripe_customer_id = "cus_existing"
    auth_client.user.org.save(update_fields=["stripe_customer_id"])

    fake_session = MagicMock(url="https://stripe.test/checkout/zzz")

    with (
        patch.object(stripe.Customer, "create") as mock_cust,
        patch.object(stripe.checkout.Session, "create", return_value=fake_session) as mock_sess,
    ):
        res = auth_client.post(
            "/api/billing/checkout/",
            {"tier": "solo", "billing_cadence": "monthly"},
            format="json",
        )

    assert res.status_code == 200
    mock_cust.assert_not_called()
    assert mock_sess.call_args.kwargs["customer"] == "cus_existing"


def test_portal_rejects_org_without_customer(auth_client, billing_settings):
    res = auth_client.post("/api/billing/portal/")
    assert res.status_code == 400


def test_portal_creates_session_for_existing_customer(auth_client, billing_settings):
    auth_client.user.org.stripe_customer_id = "cus_portal_1"
    auth_client.user.org.save(update_fields=["stripe_customer_id"])

    fake = MagicMock(url="https://stripe.test/portal/xyz")
    with patch.object(stripe.billing_portal.Session, "create", return_value=fake) as mock_portal:
        res = auth_client.post("/api/billing/portal/")

    assert res.status_code == 200
    assert res.json()["url"] == "https://stripe.test/portal/xyz"
    call_kwargs = mock_portal.call_args.kwargs
    assert call_kwargs["customer"] == "cus_portal_1"
    assert call_kwargs["return_url"] == "https://app.example.com/settings"


def test_subscription_status_returns_org_state(auth_client, billing_settings, settings):
    settings.STRIPE_PUBLISHABLE_KEY = "pk_test_xyz"
    res = auth_client.get("/api/billing/subscription/")
    assert res.status_code == 200
    body = res.json()
    assert body["subscription_tier"] == auth_client.user.org.subscription_tier
    assert body["stripe_publishable_key"] == "pk_test_xyz"

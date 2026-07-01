import datetime
import logging

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from apps.core.permissions import IsOrgMember
from apps.core.throttling import BillingCheckoutThrottle

logger = logging.getLogger(__name__)

TIER_PRICE_MAP = {
    "solo": {
        "monthly": "STRIPE_PRICE_SOLO_MONTHLY",
        "annual": "STRIPE_PRICE_SOLO_ANNUAL",
    },
    "studio": {
        "monthly": "STRIPE_PRICE_STUDIO_MONTHLY",
        "annual": "STRIPE_PRICE_STUDIO_ANNUAL",
    },
    "agency": {
        "monthly": "STRIPE_PRICE_AGENCY_MONTHLY",
        "annual": "STRIPE_PRICE_AGENCY_ANNUAL",
    },
}

VALID_CADENCES = {"monthly", "annual"}


def _price_to_tier_map():
    """Build {price_id: (tier, cadence)} from current settings.

    Built lazily so test overrides and env reloads take effect. Empty price IDs
    are skipped so a misconfigured tier doesn't shadow others.
    """
    mapping = {}
    for tier, cadences in TIER_PRICE_MAP.items():
        for cadence, setting_name in cadences.items():
            price_id = getattr(settings, setting_name, "")
            if price_id:
                mapping[price_id] = (tier, cadence)
    return mapping


def _resolve_tier_from_subscription(subscription):
    """Given a Stripe subscription object, return (tier, cadence) or (None, None).

    Uses the price ID on the first line item — this is the source of truth
    after a Customer Portal plan change, since portal upgrades do NOT carry
    the metadata we set at checkout.
    """
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return None, None
    price_id = items[0].get("price", {}).get("id")
    if not price_id:
        return None, None
    return _price_to_tier_map().get(price_id, (None, None))


def _configure_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if settings.STRIPE_API_VERSION:
        stripe.api_version = settings.STRIPE_API_VERSION


def _get_or_create_stripe_customer(org, email=""):
    """Return the Stripe customer ID for an org, creating one lazily if needed."""
    if org.stripe_customer_id:
        return org.stripe_customer_id

    customer = stripe.Customer.create(
        name=org.name,
        email=email or None,
        metadata={"org_id": str(org.id)},
    )
    org.stripe_customer_id = customer.id
    org.save(update_fields=["stripe_customer_id"])
    return customer.id


@api_view(["POST"])
@permission_classes([IsOrgMember])
@throttle_classes([BillingCheckoutThrottle])
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for a subscription upgrade.
    Body: {"tier": "solo" | "studio" | "agency", "billing_cadence": "monthly" | "annual"}
    Returns: {"url": "<stripe_checkout_url>"}
    """
    tier = request.data.get("tier", "").lower()
    billing_cadence = (
        request.data.get("billing_cadence")
        or request.data.get("cadence")
        or request.data.get("billing")
        or "monthly"
    ).lower()

    if tier not in TIER_PRICE_MAP:
        return Response(
            {"detail": "Invalid tier. Must be 'solo', 'studio', or 'agency'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if billing_cadence not in VALID_CADENCES:
        return Response(
            {"detail": "Invalid billing cadence. Must be 'monthly' or 'annual'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    price_setting = TIER_PRICE_MAP[tier][billing_cadence]
    price_id = getattr(settings, price_setting, "")
    if not price_id:
        return Response(
            {"detail": "Billing not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    _configure_stripe()
    org = request.user.org

    try:
        customer_id = _get_or_create_stripe_customer(org, email=request.user.email)
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/pricing?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/pricing?canceled=true",
            automatic_tax={"enabled": True},
            billing_address_collection="required",
            customer_update={"address": "auto"},
            consent_collection={
                "terms_of_service": "required",
            },
            custom_text={
                "terms_of_service_acceptance": {
                    "message": (
                        f"I agree to the [Terms of Service]({settings.FRONTEND_URL}/terms) "
                        f"and [Privacy Policy]({settings.FRONTEND_URL}/privacy)."
                    ),
                },
            },
            metadata={
                "org_id": str(org.id),
                "tier": tier,
                "billing_cadence": billing_cadence,
            },
            subscription_data={
                "metadata": {
                    "org_id": str(org.id),
                    "tier": tier,
                    "billing_cadence": billing_cadence,
                }
            },
        )
        return Response({"url": session.url})
    except stripe.StripeError as exc:
        logger.error("Stripe checkout error for org %s: %s", org.id, exc)
        return Response({"detail": "Payment service error."}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["POST"])
@permission_classes([IsOrgMember])
@throttle_classes([BillingCheckoutThrottle])
def create_portal_session(request):
    """
    Create a Stripe Customer Portal session (manage/cancel subscription).
    Returns: {"url": "<stripe_portal_url>"}
    """
    _configure_stripe()
    org = request.user.org

    if not org.stripe_customer_id:
        return Response(
            {"detail": "No active subscription found."}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/settings",
        )
        return Response({"url": session.url})
    except stripe.StripeError as exc:
        logger.error("Stripe portal error for org %s: %s", org.id, exc)
        return Response({"detail": "Payment service error."}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
@permission_classes([IsOrgMember])
def subscription_status(request):
    """Return current billing state for the org."""
    org = request.user.org
    return Response(
        {
            "subscription_tier": org.subscription_tier,
            "subscription_status": org.subscription_status,
            "current_period_end": org.current_period_end,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        }
    )


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook handler. Verifies signature and syncs billing state to Organization.

    Idempotency: each event id is recorded in StripeEvent before processing; a
    duplicate delivery short-circuits with 200 OK without re-applying state.
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    _configure_stripe()

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        return HttpResponse(status=400)
    except Exception as exc:
        logger.error("Stripe webhook parse error: %s", exc)
        return HttpResponse(status=400)

    # construct_event returns a StripeObject, but the handlers below use dict
    # methods (.get, subscripting) throughout — normalize to a plain dict.
    event = event.to_dict()

    from .models import StripeEvent

    event_id = event.get("id", "")
    event_type = event.get("type", "")

    if not event_id:
        logger.warning("Stripe webhook missing event id")
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            StripeEvent.objects.create(event_id=event_id, event_type=event_type)
    except IntegrityError:
        logger.info("Duplicate Stripe event %s skipped", event_id)
        return HttpResponse(status=200)

    try:
        _handle_event(event)
    except Exception as exc:
        # Roll back the StripeEvent marker so Stripe retries deliver again.
        StripeEvent.objects.filter(event_id=event_id).delete()
        logger.exception("Stripe webhook handler failed for %s: %s", event_id, exc)
        return HttpResponse(status=500)

    return HttpResponse(status=200)


def _handle_event(event):
    from apps.accounts.models import Organization

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _on_checkout_completed(data, Organization)

    elif event_type == "customer.subscription.updated":
        _on_subscription_updated(data, Organization)

    elif event_type == "customer.subscription.deleted":
        _on_subscription_deleted(data, Organization)

    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        _on_invoice_paid(data, Organization)

    elif event_type == "invoice.payment_failed":
        _on_payment_failed(data, Organization)

    else:
        logger.debug("Unhandled Stripe event: %s", event_type)


def _ts_to_dt(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC)


def _on_checkout_completed(session, Organization):
    if session.get("mode") != "subscription":
        return

    org_id = session.get("metadata", {}).get("org_id")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not org_id:
        logger.warning("checkout.session.completed missing org_id in metadata")
        return

    # Fetch the subscription so tier comes from the price (single source of truth).
    tier = session.get("metadata", {}).get("tier")
    billing_cadence = session.get("metadata", {}).get("billing_cadence") or "monthly"

    if subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id).to_dict()
            resolved_tier, resolved_cadence = _resolve_tier_from_subscription(sub)
            if resolved_tier:
                tier = resolved_tier
            if resolved_cadence:
                billing_cadence = resolved_cadence
        except stripe.StripeError as exc:
            logger.warning("Could not retrieve subscription %s: %s", subscription_id, exc)

    if tier not in TIER_PRICE_MAP or billing_cadence not in VALID_CADENCES:
        logger.warning(
            "checkout.session.completed could not resolve tier/cadence for org %s", org_id
        )
        return

    fields = {
        "subscription_tier": tier,
        "billing_cadence": billing_cadence,
        "stripe_subscription_id": subscription_id or "",
        "subscription_status": "active",
    }
    if customer_id:
        fields["stripe_customer_id"] = customer_id

    updated = Organization.objects.filter(id=org_id).update(**fields)
    if updated:
        logger.info("Activated %s/%s subscription for org %s", tier, billing_cadence, org_id)


def _on_subscription_updated(subscription, Organization):
    """Handle subscription state changes — including Customer Portal plan changes,
    which do NOT carry our metadata. Tier is resolved from the price id on the
    first line item, which is always present."""
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    tier, billing_cadence = _resolve_tier_from_subscription(subscription)
    sub_status = subscription.get("status", "")
    period_end_dt = _ts_to_dt(subscription.get("current_period_end"))

    fields = {
        "subscription_status": sub_status,
        "current_period_end": period_end_dt,
        "stripe_subscription_id": subscription.get("id") or "",
    }
    if tier in TIER_PRICE_MAP:
        fields["subscription_tier"] = tier
    if billing_cadence in VALID_CADENCES:
        fields["billing_cadence"] = billing_cadence

    updated = Organization.objects.filter(stripe_customer_id=customer_id).update(**fields)
    if updated:
        logger.info(
            "Updated subscription for customer %s: tier=%s status=%s",
            customer_id,
            tier,
            sub_status,
        )
    else:
        logger.warning("subscription.updated for unknown customer %s", customer_id)


def _on_subscription_deleted(subscription, Organization):
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    Organization.objects.filter(stripe_customer_id=customer_id).update(
        subscription_tier="free",
        billing_cadence="monthly",
        stripe_subscription_id="",
        subscription_status="canceled",
        current_period_end=None,
    )
    logger.info("Subscription canceled for customer %s — downgraded to free", customer_id)


def _on_invoice_paid(invoice, Organization):
    """Renewal payment — refresh period_end and clear any past_due flag."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    period_end = invoice.get("lines", {}).get("data", [{}])[-1].get("period", {}).get("end")
    period_end_dt = _ts_to_dt(period_end)

    fields = {"subscription_status": "active"}
    if period_end_dt:
        fields["current_period_end"] = period_end_dt

    updated = Organization.objects.filter(stripe_customer_id=customer_id).update(**fields)
    if updated:
        logger.info("Invoice paid for customer %s; period_end=%s", customer_id, period_end_dt)


def _on_payment_failed(invoice, Organization):
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    Organization.objects.filter(stripe_customer_id=customer_id).update(
        subscription_status="past_due",
    )
    logger.warning("Payment failed for customer %s", customer_id)

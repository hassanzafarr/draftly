import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.core.permissions import IsOrgMember

logger = logging.getLogger(__name__)

TIER_PRICE_MAP = {
    "growth": "STRIPE_PRICE_GROWTH",
    "agency": "STRIPE_PRICE_AGENCY",
}


def _get_or_create_stripe_customer(org):
    """Return the Stripe customer ID for an org, creating one lazily if needed."""
    if org.stripe_customer_id:
        return org.stripe_customer_id

    customer = stripe.Customer.create(
        name=org.name,
        metadata={"org_id": str(org.id)},
    )
    org.stripe_customer_id = customer.id
    org.save(update_fields=["stripe_customer_id"])
    return customer.id


@api_view(["POST"])
@permission_classes([IsOrgMember])
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for a subscription upgrade.
    Body: {"tier": "growth" | "agency"}
    Returns: {"url": "<stripe_checkout_url>"}
    """
    tier = request.data.get("tier", "").lower()
    price_setting = TIER_PRICE_MAP.get(tier)
    if not price_setting:
        return Response({"detail": "Invalid tier. Must be 'growth' or 'agency'."}, status=status.HTTP_400_BAD_REQUEST)

    price_id = getattr(settings, price_setting, "")
    if not price_id:
        return Response({"detail": "Billing not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    org = request.user.org

    try:
        customer_id = _get_or_create_stripe_customer(org)
        frontend_origin = request.build_absolute_uri("/").rstrip("/").replace(
            request.get_host(), _get_frontend_origin()
        )
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{_get_frontend_origin()}/pricing?success=true",
            cancel_url=f"{_get_frontend_origin()}/pricing?canceled=true",
            metadata={"org_id": str(org.id), "tier": tier},
            subscription_data={"metadata": {"org_id": str(org.id), "tier": tier}},
        )
        return Response({"url": session.url})
    except stripe.StripeError as exc:
        logger.error("Stripe checkout error for org %s: %s", org.id, exc)
        return Response({"detail": "Payment service error."}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["POST"])
@permission_classes([IsOrgMember])
def create_portal_session(request):
    """
    Create a Stripe Customer Portal session (manage/cancel subscription).
    Returns: {"url": "<stripe_portal_url>"}
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    org = request.user.org

    if not org.stripe_customer_id:
        return Response({"detail": "No active subscription found."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=f"{_get_frontend_origin()}/settings",
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
    return Response({
        "subscription_tier": org.subscription_tier,
        "subscription_status": org.subscription_status,
        "current_period_end": org.current_period_end,
        "credit_balance": org.credit_balance,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    })


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook handler. Verifies signature and syncs billing state to Organization.
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    stripe.api_key = settings.STRIPE_SECRET_KEY

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

    _handle_event(event)
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

    elif event_type == "invoice.payment_failed":
        _on_payment_failed(data, Organization)

    else:
        logger.debug("Unhandled Stripe event: %s", event_type)


def _on_checkout_completed(session, Organization):
    if session.get("mode") != "subscription":
        return

    org_id = session.get("metadata", {}).get("org_id")
    tier = session.get("metadata", {}).get("tier")
    subscription_id = session.get("subscription")

    if not org_id or not tier:
        logger.warning("checkout.session.completed missing org_id or tier in metadata")
        return

    updated = Organization.objects.filter(id=org_id).update(
        subscription_tier=tier,
        stripe_subscription_id=subscription_id or "",
        subscription_status="active",
    )
    if updated:
        logger.info("Activated %s subscription for org %s", tier, org_id)


def _on_subscription_updated(subscription, Organization):
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    tier = subscription.get("metadata", {}).get("tier")
    sub_status = subscription.get("status", "")
    period_end = subscription.get("current_period_end")

    import datetime
    period_end_dt = (
        datetime.datetime.fromtimestamp(period_end, tz=datetime.timezone.utc)
        if period_end else None
    )

    fields = {
        "subscription_status": sub_status,
        "current_period_end": period_end_dt,
    }
    if tier:
        fields["subscription_tier"] = tier

    updated = Organization.objects.filter(stripe_customer_id=customer_id).update(**fields)
    if updated:
        logger.info("Updated subscription for customer %s: status=%s", customer_id, sub_status)


def _on_subscription_deleted(subscription, Organization):
    customer_id = subscription.get("customer")
    if not customer_id:
        return

    Organization.objects.filter(stripe_customer_id=customer_id).update(
        subscription_tier="starter",
        stripe_subscription_id="",
        subscription_status="canceled",
        current_period_end=None,
    )
    logger.info("Subscription canceled for customer %s — downgraded to starter", customer_id)


def _on_payment_failed(invoice, Organization):
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    Organization.objects.filter(stripe_customer_id=customer_id).update(
        subscription_status="past_due",
    )
    logger.warning("Payment failed for customer %s", customer_id)


def _get_frontend_origin():
    from django.conf import settings as s
    cors_origins = getattr(s, "CORS_ALLOWED_ORIGINS", "")
    if isinstance(cors_origins, (list, tuple)) and cors_origins:
        return cors_origins[0].rstrip("/")
    if isinstance(cors_origins, str) and cors_origins:
        return cors_origins.split(",")[0].strip().rstrip("/")
    return "http://localhost:5173"

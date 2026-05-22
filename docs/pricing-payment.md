# Draftly Pricing And Payment Integration Tracker

Last reviewed: 2026-05-22

## Current Product Decision

Draftly is subscription-only for now.

Users can subscribe to `solo`, `studio`, or `agency`. There are no proposal packs, top-up credits, or one-time overage purchases in the current product.

When an organization reaches its monthly proposal quota, proposal generation is blocked until the organization upgrades to a higher subscription tier or the monthly quota resets.

## Current Goal

Implement a reliable subscription payment flow:

1. Users can subscribe to Solo, Studio, or Agency through Stripe Checkout.
2. Stripe webhooks update the organization's subscription tier and billing cadence.
3. Stripe Customer Portal lets subscribed users manage or cancel billing.
4. Monthly proposal quotas are enforced by subscription tier.
5. Billing state is visible enough for support and customer-facing settings.

## What Is Done

- Pricing tiers exist on `Organization`: `free`, `solo`, `studio`, `agency`.
- Tier quotas are defined in `backend/apps/accounts/models.py`.
- New signups default to `free`.
- `billing_cadence` exists on `Organization`.
- Stripe customer/subscription fields exist on `Organization`:
  - `stripe_customer_id`
  - `stripe_subscription_id`
  - `subscription_status`
  - `current_period_end`
- `apps.billing` is registered in Django settings.
- Billing URLs are mounted at `/api/billing/`.
- Stripe dependency is listed in `backend/requirements.txt`.
- Subscription checkout endpoint exists:
  - `POST /api/billing/checkout/`
  - accepts `tier: solo | studio | agency`
  - accepts `billing_cadence: monthly | annual`
- Stripe Customer Portal endpoint exists:
  - `POST /api/billing/portal/`
- Stripe webhook endpoint exists:
  - `POST /api/billing/webhook/`
- Webhook handling updates org subscription state for:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`
- Cancelled subscriptions downgrade to `free`.
- Stripe price env vars match the active tiers:
  - `STRIPE_PRICE_SOLO_MONTHLY`
  - `STRIPE_PRICE_SOLO_ANNUAL`
  - `STRIPE_PRICE_STUDIO_MONTHLY`
  - `STRIPE_PRICE_STUDIO_ANNUAL`
  - `STRIPE_PRICE_AGENCY_MONTHLY`
  - `STRIPE_PRICE_AGENCY_ANNUAL`
- Migration chain is linear:
  - `accounts.0002_pricing_model_v1`
  - `accounts.0003_billing_fields`
- Pricing page monthly/annual state crash was fixed.
- Pricing page posts subscription checkout payloads to `/billing/checkout/`.
- Proposal pack UI and backend pack/credit logic were removed.

## Verified

- `python manage.py check` passed after installing `stripe`.
- `python manage.py makemigrations --check --dry-run` reports no model changes.
- `npm.cmd run build` passes.

Note: `showmigrations` could not be fully verified in the sandbox because the configured Supabase database connection was blocked by network permissions.

## Still Missing Or Broken

### 1. Serializer Does Not Expose All Billing Fields

`OrganizationSerializer` should expose safe billing fields needed by Settings:

- `subscription_status`
- `current_period_end`

Do not expose sensitive Stripe IDs unless an admin/debug UI needs them.

### 2. Settings Page Billing State Needs Final Polish

The Settings page has a Manage Billing action, but it should be verified end to end:

- Free users see an Upgrade button.
- Subscribed users see Manage Billing.
- Portal return lands back on Settings.
- Fresh org data is fetched after checkout or portal return.

### 3. Stripe Webhook Idempotency Is Missing

Stripe may send the same webhook more than once.

Missing:

- Stored Stripe event IDs.
- A unique guard so each Stripe event is processed once.

Recommended fix:

- Add a `StripeEvent` or `BillingEvent` model with unique `stripe_event_id`.
- Process each event inside a database transaction.

### 4. Subscription Lifecycle Is Basic

Current webhook handling covers activation, update, cancellation, and payment failure.

Still needed:

- Decide behavior for `past_due`.
- Decide whether canceled subscriptions downgrade immediately or at period end.
- Support `checkout.session.async_payment_succeeded` if async payment methods are enabled.
- Support annual/monthly plan switching through Stripe Portal or custom checkout.
- Store `current_period_end` from checkout/subscription events consistently.

### 5. Monthly Quota Counting Is Still Broad

Monthly proposal usage currently counts all proposals created this month.

Problem:

- Failed proposals can count against the monthly quota.
- Generating/in-progress proposals count immediately.

Recommended rule:

- Count successful generated proposals only, or explicitly track quota-consuming attempts.
- Align this with the product rule: failed generations should not consume quota.

### 6. Provider Cost Tracking Is Missing

`GenerationEvent` tracks provider and latency, but not cost.

Recommended fields:

- `input_tokens`
- `output_tokens`
- `cost_cents`
- `billing_source`, such as `free_quota` or `subscription_quota`

### 7. Stripe Products Must Be Created

Before real checkout works, create Stripe Products/Prices for:

- Solo monthly
- Solo annual
- Studio monthly
- Studio annual
- Agency monthly
- Agency annual

Then set the matching env vars in production and local development.

## Suggested Next Implementation Order

1. Re-run Django and frontend checks after pack removal.
2. Expose safe billing fields in `OrganizationSerializer`.
3. Verify Settings billing buttons and imports.
4. Add Stripe event idempotency.
5. Fix monthly quota counting so failed generations do not consume quota.
6. Add provider cost tracking fields.
7. Run full local and staging Stripe test flow.

## Stripe Test Checklist

- Free user can open pricing page without crash.
- Free user selecting Solo monthly redirects to Stripe Checkout.
- Successful Solo monthly checkout updates org:
  - `subscription_tier = solo`
  - `billing_cadence = monthly`
  - `subscription_status = active`
- Studio annual checkout updates org:
  - `subscription_tier = studio`
  - `billing_cadence = annual`
- Cancelled subscription downgrades org to:
  - `subscription_tier = free`
  - `billing_cadence = monthly`
  - `subscription_status = canceled`
- Payment failure marks `subscription_status = past_due`.
- Duplicate Stripe webhook does not reprocess the same event.
- Failed proposal generation does not consume monthly quota.
- Monthly quota blocks at the configured tier limit.

# Draftly Pricing And Payment Integration Tracker

Last reviewed: 2026-05-22

## Current Goal

Implement a reliable monetization flow:

1. Users can subscribe to Solo, Studio, or Agency through Stripe Checkout.
2. Stripe webhooks update the organization's subscription tier and billing cadence.
3. Users can buy proposal packs after their monthly proposal quota is exhausted.
4. Proposal generation consumes monthly quota first, then purchased pack credits.
5. Billing, quota, credits, and provider cost tracking are visible enough for support and margin review.

## What Is Done

- Pricing tiers exist on `Organization`: `free`, `solo`, `studio`, `agency`.
- Tier quotas are defined in `backend/apps/accounts/models.py`.
- New signups default to `free` through the model default.
- `billing_cadence` exists on `Organization`.
- Stripe customer/subscription fields exist on `Organization`:
  - `stripe_customer_id`
  - `stripe_subscription_id`
  - `subscription_status`
  - `current_period_end`
- `credit_balance` exists on `Organization`.
- `apps.billing` is registered in Django settings.
- Billing URLs are mounted at `/api/billing/`.
- Stripe dependency is listed in `backend/requirements.txt`.
- Local Stripe Python package was installed for development checks.
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
- Cancelled subscriptions now downgrade to `free`, not old `starter`.
- Stripe price env vars now match the active tiers:
  - `STRIPE_PRICE_SOLO_MONTHLY`
  - `STRIPE_PRICE_SOLO_ANNUAL`
  - `STRIPE_PRICE_STUDIO_MONTHLY`
  - `STRIPE_PRICE_STUDIO_ANNUAL`
  - `STRIPE_PRICE_AGENCY_MONTHLY`
  - `STRIPE_PRICE_AGENCY_ANNUAL`
- Migration conflict was cleaned up:
  - `accounts.0002_pricing_model_v1`
  - `accounts.0003_billing_fields`
  - `billing.0001_initial` depends on `accounts.0003_billing_fields`
- Pricing page monthly/annual state crash was fixed.
- Pricing page now posts subscription checkout payloads to `/billing/checkout/`.

## Verified

- `python manage.py check` passes after installing `stripe`.
- `python manage.py makemigrations --check --dry-run` reports no model changes.
- `npm.cmd run build` passes.

Note: `showmigrations` could not be fully verified in the sandbox because the configured Supabase database connection was blocked by network permissions.

## Still Missing Or Broken

### 1. Pack Purchases Are Not Implemented

The UI shows proposal packs, but they are display-only.

Missing:

- Backend endpoint to create one-time Stripe Checkout or PaymentIntent for packs.
- Pack Stripe price env vars.
- Webhook handler for successful pack purchases.
- Logic to increment the org pack balance after payment.
- Idempotency protection so duplicate Stripe webhook delivery does not add credits twice.
- Frontend buttons for buying Boost, Plus, and Power packs.

Recommended pack env vars:

```env
STRIPE_PRICE_PACK_BOOST=price_...
STRIPE_PRICE_PACK_PLUS=price_...
STRIPE_PRICE_PACK_POWER=price_...
```

### 2. Two Balance Fields Are Competing

There are currently two concepts:

- `proposal_pack_balance`
- `credit_balance`

Permission checks use `proposal_pack_balance`, but successful generation deducts `credit_balance`.

This must be unified before pack billing is reliable.

Recommended decision:

- Keep one field named `proposal_pack_balance` for the current pricing model.
- Remove or stop using `credit_balance`, unless the product is moving to a general credit system.
- Rename `CreditPurchase` fields from `credits_*` to `proposals_*` if packs stay proposal-based.

### 3. Pack Consumption Is Not Safe Yet

Current generation flow calculates whether a credit is needed before creating the proposal. The actual deduction happens later in Celery after successful generation.

Risks:

- Multiple concurrent generations can start with the same remaining pack balance.
- Failed generations still create `Proposal` rows, which can affect monthly quota counts.
- If the task succeeds but credit deduction silently updates zero rows, the generation still completes.

Recommended fix:

- Introduce a small usage ledger or reservation model.
- Reserve pack credit before dispatching Celery when monthly quota is exhausted.
- Finalize the reservation on success.
- Release/refund it on failure.

### 4. Monthly Quota Counting Is Too Broad

Monthly proposal usage currently counts all proposals created this month.

Problem:

- Failed proposals can count against the monthly quota.
- Generating/in-progress proposals count immediately.

Recommended rule:

- Count successful generated proposals only, or explicitly track quota-consuming attempts.
- Align this with the product rule: failed generations should not consume quota.

### 5. Serializer Does Not Expose All Billing Fields

`OrganizationSerializer` does not currently expose:

- `credit_balance`
- `subscription_status`
- `current_period_end`
- `stripe_subscription_id`

Frontend Settings tries to read some of these fields from `user.org`.

Recommended fix:

- Expose safe read-only billing fields:
  - `subscription_status`
  - `current_period_end`
  - chosen pack balance field
- Do not expose sensitive Stripe IDs unless needed for admin/debug UI.

### 6. Settings Page Has Runtime Risk

`Settings.jsx` references billing icons that need to be confirmed as imported:

- `CreditCard`
- `ExternalLink`
- `Coins`

The production build may pass while unresolved globals still crash when the relevant JSX branch renders.

Recommended fix:

- Import these icons from `lucide-react`.
- Load fresh org/billing data after checkout success or portal return.

### 7. Stripe Webhook Idempotency Is Missing

Stripe may send the same webhook more than once.

Missing:

- Stored Stripe event IDs.
- Unique payment intent/session/subscription event handling.
- Guard against duplicate pack credit increments.

Recommended fix:

- Add a `StripeEvent` or `BillingEvent` model with unique `stripe_event_id`.
- Process each event once inside a database transaction.

### 8. Subscription Lifecycle Is Too Basic

Current webhook handling covers basic activation, update, cancellation, and payment failure.

Still needed:

- Decide behavior for `past_due`.
- Decide whether canceled subscriptions downgrade immediately or at period end.
- Support `checkout.session.async_payment_succeeded` if using async payment methods.
- Support annual/monthly plan switching through Stripe Portal or custom checkout.
- Store `current_period_end` from checkout/subscription events consistently.

### 9. Provider Cost Tracking Is Missing

`GenerationEvent` tracks provider and latency, but not cost.

Missing:

- input token count
- output token count
- estimated provider cost
- whether monthly quota or pack balance was consumed

Recommended fields:

- `input_tokens`
- `output_tokens`
- `cost_cents`
- `consumed_pack`
- `billing_source` with values like `monthly_quota`, `pack`, `free_quota`

### 10. Stripe Products Must Be Created

Before real checkout works, create Stripe Products/Prices for:

- Solo monthly
- Solo annual
- Studio monthly
- Studio annual
- Agency monthly
- Agency annual
- Boost pack
- Plus pack
- Power pack

Then set the matching env vars in production and local development.

## Suggested Next Implementation Order

1. Unify `proposal_pack_balance` vs `credit_balance`.
2. Expose billing/pack fields in `OrganizationSerializer`.
3. Fix `Settings.jsx` missing billing icon imports and billing display.
4. Add Stripe event idempotency model.
5. Implement pack checkout endpoint.
6. Add pack webhook handling and balance increment.
7. Replace current pack deduction with transaction-safe reservation/finalization.
8. Fix quota counting so failed generations do not consume quota.
9. Add generation cost tracking fields.
10. Run full local and staging Stripe test flow.

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
- Pack purchase increments chosen pack balance exactly once.
- Duplicate Stripe webhook does not duplicate credits.
- Failed proposal generation does not consume monthly quota or pack balance.
- Concurrent over-quota generation cannot overspend pack balance.


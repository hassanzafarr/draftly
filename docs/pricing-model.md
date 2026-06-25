# Draftly Pricing Model

Last reviewed: 2026-05-22

## Current Decision

Draftly uses a subscription-only pricing model for now.

There are no proposal packs, usage top-ups, or one-time overage purchases in the current product. When an organization reaches its monthly proposal quota, generation is blocked until the monthly quota resets or the organization upgrades to a higher tier.

## Tiers

| Tier | Monthly | Annual | Proposals/mo | Docs | Seats | Badge |
| --- | --- | --- | --- | --- | --- | --- |
| Free | $0 | - | 3 | 10 | 1 | - |
| Solo | $12 | $115/yr | 25 | 25 | 1 | - |
| Studio | $49 | $470/yr | 150 | 250 | 5 | Most Popular |
| Agency | $149 | $1,430/yr | 750 | Unlimited | 10 | Best Value |

Annual pricing uses a 20% discount.

## Billing

Stripe handles monthly and annual subscriptions through Checkout and the Customer Portal.

Required Stripe price environment variables:

```env
STRIPE_PRICE_SOLO_MONTHLY=price_...
STRIPE_PRICE_SOLO_ANNUAL=price_...
STRIPE_PRICE_STUDIO_MONTHLY=price_...
STRIPE_PRICE_STUDIO_ANNUAL=price_...
STRIPE_PRICE_AGENCY_MONTHLY=price_...
STRIPE_PRICE_AGENCY_ANNUAL=price_...
```

## Backend Rules

- New organizations default to `free`.
- `billing_cadence` defaults to `monthly`.
- Monthly quota resets by month boundary in UTC.
- `OrgProposalQuotaPermission` blocks generation when monthly proposal quota is reached.
- `OrgDocQuotaPermission` blocks uploads when document quota is reached.
- Failed-generation quota accounting still needs a final decision and implementation.

## Open Items

- Expose safe billing fields in `OrganizationSerializer`.
- Add Stripe webhook idempotency.
- Decide exact downgrade timing for canceled subscriptions.
- Decide `past_due` access behavior.
- Add provider cost tracking to `GenerationEvent`.
- Verify the full Stripe Checkout and Portal flow in test mode.

# Draftly Pricing Model — CFO Recommendation

## Context

Draftly has working multi-tenant infrastructure with 3 hardcoded tiers (`starter`/`growth`/`agency`) enforced by DRF quota permissions, but **zero monetization**: no Stripe, no payment flow, no cost tracking. Tiers are set manually by an admin.

The user (acting CFO) wants to lock in a v1 pricing model now so:

1. The frontend Settings/Pricing page can display real prices.
2. Backend tier definitions match the go-to-market plan.
3. A Stripe integration (future) can be wired against a stable schema.

**Constraints locked with user:**

- Market: **Global / USD pricing**.
- ICP: **Freelancers + solo consultants** (low-ACV, high-volume).
- Model: **Freemium + paid tiers** (free trial drives signups).
- Costs: **Estimate from typical RAG SaaS economics** (no internal numbers yet).

---

## Unit Economics (estimated)

Per-proposal cost stack (conservative, list-price APIs):

| Component | Calls | Tokens / units | Cost |
| --- | --- | --- | --- |
| RFP query embedding (Google text-embedding-004) | 1 | ~2k tokens | ~$0.0001 |
| Cohere rerank (top-20 → top-K) | 1 | 20 docs | ~$0.002 |
| Claude Haiku 4.5 generation (primary) | 1 | ~8k in / ~4k out | ~$0.025 |
| Gemini 2.5 Flash (fallback share ~20%) | 0.2 | ~8k in / ~4k out | ~$0.003 |
| Postgres/pgvector + Redis + Celery worker amortized | — | — | ~$0.005 |
| **Per-proposal COGS** | | | **~$0.035** |

Document ingestion (one-time per doc): ~$0.0005 (embedding 50 chunks). Negligible vs. proposal cost.

**Margin target**: ≥85% gross margin on paid tiers (industry standard for AI SaaS). At $0.035 COGS, breakeven volume sets floor.

---

## Recommended Tier Structure (4 tiers: Free + 3 paid)

| Tier | Price (USD) | Proposals/mo | Docs (KB) | Seats | Target user |
| --- | --- | --- | --- | --- | --- |
| **Free** | $0 | 3 | 10 | 1 | Trial / solo freelancer testing fit |
| **Solo** | **$29/mo** | 25 | 50 | 1 | Active freelancer, 1-2 bids/week |
| **Studio** | **$79/mo** | 100 | 200 | 3 | Boutique consultancy, small team |
| **Agency** | **$199/mo** | 500 | unlimited | 10 | Mid-market firm, bid-heavy |

**Overages** (paid tiers only): handled via purchasable credit packs (see section below). Soft cap (warn at 80%, don't block) on Solo+; hard cap on Free. 1 credit = 1 proposal generation.

**Billing cadence**: monthly only in v1. Defer annual plans until we have churn data (~3-6 months post-launch) to size the discount correctly.

**Free signup**: email verification only, no credit card. Rate-limit signups by IP + email fingerprint to mitigate throwaway abuse.

**Pricing page**: public marketing page with full comparison table (SEO + transparency). Standard for self-serve at this price band.

---

## Credit Packs

Credits are one-time purchasable top-ups for paid tier users who exhaust their monthly quota. 1 credit = 1 proposal generation. Credits are consumed only after the monthly allocation runs out.

### Credit Pack Pricing

| Pack | Credits | Price | Per Credit | Gross Margin |
| --- | --- | --- | --- | --- |
| **Starter** | 10 | $12 | $1.20 | ~97% |
| **Value** | 30 | $30 | $1.00 | ~97% |
| **Power** | 100 | $85 | $0.85 | ~96% |

All packs clear the 85% margin floor. Bulk discount tops out at ~29% off the Starter rate — enough to incentivize larger purchases without cannibalizing monthly plan upgrades.

### Credit Pack Rules

- **Availability**: Solo+ only. Free tier is hard-blocked from purchasing credits — hitting the cap should convert, not extend.
- **Consumption order**: Monthly quota is spent first; credits only activate once the monthly balance hits zero.
- **No expiry**: Credits persist on the org account indefinitely. No monthly reset, no cliffs.
- **Org-scoped**: Credits are shared across all seats in the org (Studio/Agency). No per-seat credit tracking in v1.
- **No fractions**: 1 proposal always costs exactly 1 credit. Partial usage (e.g. failed generation) does not consume a credit.
- **Stackable**: Multiple packs can be purchased and balances accumulate.
- **No refunds on credits**: Consistent with SaaS norms — communicate this on the purchase screen.

### Credit Pack Margin Math

| Pack | Revenue | COGS (credits × $0.035) | Gross Margin |
| --- | --- | --- | --- |
| Starter (10) | $12 | $0.35 | 97.1% |
| Value (30) | $30 | $1.05 | 96.5% |
| Power (100) | $85 | $3.50 | 95.9% |

All packs comfortably exceed the 85% floor target.

### Why This Structure

- **$1.20/credit Starter** anchors just below the psychological $1.50 overage rate from v0. Feels like a deal for small top-ups.
- **$1.00/credit Value** is the sweet spot — round-number pricing, meaningful discount, most likely to convert.
- **$0.85/credit Power** rewards high-volume users and reduces churn risk at the Agency level without competing with the $199 plan itself ($199 gives 500 proposals at $0.40/proposal effective — still much cheaper than credit packs).
- **3 pack sizes**: mirrors the tier structure. More than 3 creates comparison fatigue at checkout.

---

## Margin Math (Subscription Tiers)

| Tier | Price | COGS @ 100% util | Gross margin |
| --- | --- | --- | --- |
| Free | $0 | $0.105 (3 proposals) | -$0.11 (CAC cost, capped low) |
| Solo | $29 | $0.875 (25) | **97%** |
| Studio | $79 | $3.50 (100) | **96%** |
| Agency | $199 | $17.50 (500) | **91%** |

All paid tiers clear the 85% margin floor with headroom for support, infra growth, and Stripe fees (~3%).

---

## Feature Differentiation Beyond Quotas

Quotas alone are weak differentiation. Layer feature gates:

- **Free**: Draftly watermark on PDF export, no DOCX export, no custom tone, 1 KB category only. No credit pack purchases.
- **Solo**: All export formats, all 3 KB categories, standard support. Credit pack purchases enabled.
- **Studio**: Team seats (3), shared KB, template library access, priority queue. Credit packs shared across seats.
- **Agency**: 10 seats, SSO (future), API access (future), custom branding on exports, dedicated support, SLA. Credit packs shared across all seats.

This lets you upsell on capability, not just volume — critical when ICP is solo (volume sells less than features).

---

## Why This Structure

1. **Free tier @ 3 proposals**: enough to feel the value loop end-to-end (upload KB → submit RFP → get draft → edit → export) without giving away the keys. 3 is the magic number — 1-2 feels stingy, 5+ kills conversion.
2. **$29 Solo anchor**: matches Jasper/Copy.ai/Notion AI psychological band for solo creators. Below the $50 friction threshold for personal credit cards.
3. **$79 Studio**: 2.7× Solo — captures freelancers leveling up to small teams without forcing the Agency jump.
4. **$199 Agency**: 2.5× Studio. Under $200 is still self-serve; above $200 typically needs sales-assist. Good ceiling for v1.
5. **3 paid tiers** (not 2, not 4): industry research (Price Intelligently) shows 3 paid tiers maximize conversion. 4+ paid creates choice paralysis; 2 leaves money on the table.
6. **Credit packs as overages**: cleaner UX than per-proposal billing — users buy in bulk, see a balance, and understand the cost upfront. Reduces surprise charges and support tickets.

---

## Payment Service

**Stripe** is the chosen payment provider. It handles both subscriptions (monthly tier billing) and one-time payments (credit pack purchases via Payment Intents).

### Stripe vs Paddle

| | Stripe | Paddle |
| --- | --- | --- |
| Fees | 2.9% + $0.30 | 5% + $0.50 |
| Tax handling | Manual / Stripe Tax add-on | Automatic (Merchant of Record) |
| Credit packs (one-time) | Native | Native |
| Subscriptions | Native | Native |
| Django ecosystem | Excellent (`dj-stripe`) | Weaker |
| Already in docs | Yes | No |

**Why Stripe:** ICP is US-first freelancers, margins are 91–97% so the fee difference is trivial, and `dj-stripe` gives a ready-made Django integration that maps cleanly to the `Organization` model. Revisit Paddle only if EU VAT compliance becomes a pain point post-launch — Paddle acts as Merchant of Record and handles tax automatically, which matters for EU customers.

---

## Implementation Touchpoints

When approved, changes land in:

- [backend/apps/accounts/models.py](../backend/apps/accounts/models.py) — extend `Tier.TextChoices` to add `FREE`, `SOLO`, `STUDIO`; update `QUOTA` dict. Add `seat_limit`, `monthly_price_usd`, and `credit_balance` fields on `Organization`.
- [backend/apps/core/permissions.py](../backend/apps/core/permissions.py) — `OrgProposalQuotaPermission` needs to check `credit_balance` as a secondary allowance after monthly quota is exhausted.
- [frontend/src/pages/Settings.jsx](../frontend/src/pages/Settings.jsx) — `TIER_CONFIG` dict (lines 12-31) needs price strings, new tier entries, feature lists, and credit balance display.
- **New**: pricing page (`frontend/src/pages/Pricing.jsx`) — public-facing comparison table including credit pack options.
- **New**: `CreditPack` model (`apps/billing/models.py`) — tracks pack purchases: `org`, `credits_purchased`, `credits_remaining`, `purchased_at`, `stripe_payment_intent_id`.
- **New**: GenerationEvent → add `input_tokens`, `output_tokens`, `cost_cents`, `consumed_credit` (bool) fields so overage billing + margin tracking work.
- **Future**: Stripe integration (`apps/billing/`) — checkout for both subscriptions and one-time credit pack purchases, webhooks, subscription state sync to `Org.tier`.

## Migration Strategy

Currently only 2 users in the system — no real legacy concern. Plan:

- Both users get manually flipped to `Agency` tier so they keep working without disruption.
- Old `starter` / `growth` SKUs deleted from `Tier.TextChoices` along with their QUOTA entries.
- `credit_balance` defaults to 0 for all existing orgs.
- No grandfathering logic, no time-boxed migration, no legacy SKU clutter. Clean schema from day 1.

---

## Verification (when implemented)

- [ ] Settings page shows 4 tiers with USD prices.
- [ ] New user signup defaults to `free` tier.
- [ ] Hitting Free tier cap (3 proposals) returns 403 from POST `/api/proposals/`.
- [ ] Soft-cap warning toast fires on Solo when 80%+ of monthly quota used.
- [ ] Free tier users see credit pack section as disabled/locked in Settings.
- [ ] Solo+ users can purchase a credit pack; `Organization.credit_balance` increments correctly.
- [ ] Credit balance is consumed only after monthly quota reaches zero.
- [ ] Failed proposal generation does not deduct a credit.
- [ ] Credit balance persists across the monthly reset (not zeroed on the 1st).
- [ ] GenerationEvent records `cost_cents` and `consumed_credit` per proposal; admin dashboard surfaces gross margin per tier per month.
- [ ] Stripe test checkout end-to-end: select Solo → pay → org tier flips to `solo` → quota refreshes.
- [ ] Stripe one-time checkout: buy Value pack → `credit_balance` increases by 30.

---

## Decisions Locked

- Market: Global / USD
- ICP: Freelancers + solo consultants (primary)
- Model: Freemium + 3 paid tiers + purchasable credit packs
- Free signup: email verify, no credit card
- Billing: monthly only in v1 (annual deferred)
- Pricing page: public marketing page
- Credits: Solo+ only, no expiry, org-scoped, 3 pack sizes
- Migration: 2 existing users → flip to Agency; drop old tiers

## Still Open (defer until post-launch)

- Refund policy (suggest: 14-day money-back on first paid month; no refunds on credit packs)
- Annual plans + discount sizing (revisit at 3-month mark)
- Enterprise/custom tier above Agency (only build when first lead asks)
- Per-seat add-ons vs. seats-included-in-tier
- Credit gifting / promo codes (useful for onboarding campaigns)

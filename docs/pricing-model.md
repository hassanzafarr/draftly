# Draftly Pricing Model — CFO Recommendation

## Context

Draftly has working multi-tenant infrastructure with hardcoded tiers (`starter`/`growth`/`agency`) enforced by DRF quota permissions, but **zero monetization**: no Stripe, no payment flow, no cost tracking. Tiers are set manually by an admin.

The user (acting CFO) has locked a v1 pricing model so:

1. The frontend Pricing/Settings page can display real prices.
2. Backend tier definitions match the go-to-market plan.
3. A Stripe integration (future) can be wired against a stable schema.

**Constraints locked with user:**

- Market: **Global / USD pricing**
- ICP: **Mixed — freelancers + small agencies** (both bands served by single ladder)
- Model: **Freemium + 3 paid tiers + purchasable proposal packs**
- Free signup: email verify, no credit card
- Billing: **Monthly + annual (20% off)** — both available v1
- Pricing page: public marketing page with monthly/annual toggle
- Credit/proposal display: **proposals only** in UI (no abstract credit layer)
- Backend tracking: **proposal counter, no credit abstraction**
- Seats: **hard cap per tier** (no per-seat add-ons in v1)
- Migration: existing 2 users flip to `agency`; drop old SKUs

---

## Unit Economics

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

**Margin floor**: 85% gross margin on paid tiers (industry standard for AI SaaS).

---

## Tier Structure (Free + 3 paid)

| Tier | Monthly | Annual (20% off) | Proposals/mo | Docs (KB) | Seats | Badge |
| --- | --- | --- | --- | --- | --- | --- |
| **Free** | $0 | — | 3 | 10 | 1 | — |
| **Solo** | $19 | $182/yr ($15.20/mo) | 25 | 25 | 1 | — |
| **Studio** | $89 | $854/yr ($71.20/mo) | 150 | 250 | 5 | Most Popular |
| **Agency** | $249 | $2,390/yr ($199.20/mo) | 750 | unlimited | 10 | Best Value |

**Annual discount**: flat 20% off across all paid tiers. Stripe handles proration on upgrade/downgrade.

**No rollover**: monthly quota resets 1st UTC. Proposal packs (overage) persist indefinitely.

**Soft cap** (paid tiers): warn at 80% utilization, don't block. **Hard cap** on Free (must upgrade).

---

## Margin Math (Subscription)

| Tier | Monthly Revenue | COGS @ 100% util | Gross Margin |
| --- | --- | --- | --- |
| Free | $0 | $0.105 (3 proposals) | -$0.11 (CAC, capped low) |
| Solo | $19 | $0.875 (25) | **95%** |
| Studio | $89 | $5.25 (150) | **94%** |
| Agency | $249 | $26.25 (750) | **89%** |

Annual pricing (20% off) margin:

| Tier | Effective $/mo | Margin |
| --- | --- | --- |
| Solo | $15.20 | 94% |
| Studio | $71.20 | 93% |
| Agency | $199.20 | 87% |

All paid tiers clear the 85% floor on both monthly and annual. Stripe fees (~3%) leave plenty of headroom.

---

## Proposal Packs (Overage)

Proposal packs are one-time top-ups for paid tier users who exhaust their monthly quota. 1 proposal generation = 1 pack credit. Pack credits are consumed only after the monthly allocation runs out.

### Pack Pricing

| Pack | Proposals | Price | Per Proposal | Gross Margin |
| --- | --- | --- | --- | --- |
| **Boost** | 10 | $12 | $1.20 | ~97% |
| **Plus** | 30 | $30 | $1.00 | ~97% |
| **Power** | 100 | $85 | $0.85 | ~96% |

All packs clear the 85% margin floor.

### Pack Rules

- **Availability**: Solo+ only. Free tier is hard-blocked from purchasing packs — hitting the cap should convert, not extend.
- **Consumption order**: Monthly quota is spent first; pack balance only activates once the monthly balance hits zero.
- **No expiry**: Pack balance persists on the org indefinitely. No monthly reset, no cliffs.
- **Org-scoped**: Pack balance is shared across all seats in the org. No per-seat tracking in v1.
- **No fractions**: 1 proposal always costs exactly 1 pack credit. Failed generations do not consume.
- **Stackable**: Multiple packs can be purchased; balances accumulate.
- **No refunds on packs**: Consistent with SaaS norms — communicate this on the purchase screen.

### Why This Structure

- **$1.20 Boost** anchors below the psychological $1.50 overage rate. Small top-up feel.
- **$1.00 Plus** sweet spot — round-number, meaningful discount, most likely to convert.
- **$0.85 Power** rewards heavy users without competing with the $249 Agency plan (which effectively costs $0.33/proposal at 750/mo).
- **3 pack sizes**: mirrors the tier structure. More than 3 creates comparison fatigue at checkout.

---

## Feature Differentiation Beyond Quotas

Quotas alone are weak differentiation. Feature gates per tier:

- **Free**: Draftly watermark on PDF export, no DOCX export, no custom tone, 1 KB category only. No pack purchases.
- **Solo**: All export formats, all 3 KB categories, standard support. Pack purchases enabled.
- **Studio**: 5 seats, shared KB, template library access, priority queue, packs shared across seats. **Most Popular** badge.
- **Agency**: 10 seats, SSO (future), API access (future), custom branding on exports, dedicated support, SLA, packs shared. **Best Value** badge.

Upsell on capability + volume — critical when ICP is mixed (freelancer cares about price, agency cares about seats + features).

---

## Why This Structure

1. **Free @ 3 proposals**: enough to feel the value loop end-to-end (upload KB → submit RFP → get draft → edit → export). 3 is the magic number — 1-2 feels stingy, 5+ kills conversion.
2. **$19 Solo entry**: under personal-card friction threshold (~$25). Beats Jasper/Copy.ai band ($29) — wins price-sensitive freelancer impulse signups.
3. **$89 Studio**: 4.7× Solo jump justified by 5× seats + 6× proposals + team features. Sweet spot for small consultancies.
4. **$249 Agency**: 2.8× Studio. Under $250 still self-serve; above typically needs sales-assist. Good ceiling for v1.
5. **3 paid tiers** (Free + Solo + Studio + Agency): industry research (Price Intelligently) shows 3 paid tiers maximize conversion. 4+ paid creates choice paralysis.
6. **Annual @ 20% off**: industry-standard discount. Drives cash upfront, reduces churn. Flat across tiers for clean UI signal.
7. **Proposal packs as overages**: cleaner UX than per-proposal metered billing — users buy in bulk, see a balance, understand cost upfront. Reduces surprise charges and support tickets.

---

## Pricing Page UI

Match competitor convention (e.g. Higgsfield, Jasper):

```
[Monthly / Yearly]  toggle

┌──────────┐  ┌──────────┐  ┌────────────────┐  ┌─────────────┐
│   Free   │  │   Solo   │  │     Studio     │  │   Agency    │
│   $0     │  │  $19/mo  │  │    $89/mo      │  │  $249/mo    │
│          │  │   -20%   │  │     -20%       │  │    -20%     │
│          │  │          │  │  MOST POPULAR  │  │ BEST VALUE  │
│ 3 prop   │  │ 25 prop  │  │   150 prop     │  │  750 prop   │
│ 10 docs  │  │ 25 docs  │  │   250 docs     │  │   unlim     │
│ 1 seat   │  │ 1 seat   │  │   5 seats      │  │  10 seats   │
│ [Start]  │  │ [Start]  │  │   [Start]      │  │  [Start]    │
└──────────┘  └──────────┘  └────────────────┘  └─────────────┘
```

All 4 tiers always visible (no Individual/Teams toggle — mixed ICP is served by full ladder).

Monthly/Yearly toggle flips price + shows -20% badge on Yearly side.

---

## Payment Service

**Stripe** is the chosen payment provider. It handles subscriptions (monthly + annual tier billing) and one-time payments (proposal pack purchases via Payment Intents).

### Stripe vs Paddle

| | Stripe | Paddle |
| --- | --- | --- |
| Fees | 2.9% + $0.30 | 5% + $0.50 |
| Tax handling | Manual / Stripe Tax add-on | Automatic (Merchant of Record) |
| One-time payments | Native | Native |
| Subscriptions | Native | Native |
| Django ecosystem | Excellent (`dj-stripe`) | Weaker |

**Why Stripe:** ICP is US-first, margins are 89–95% so fee difference is trivial, and `dj-stripe` maps cleanly to the `Organization` model. Revisit Paddle only if EU VAT compliance becomes a pain point post-launch.

---

## Implementation Touchpoints

When approved, changes land in:

- [backend/apps/accounts/models.py](../backend/apps/accounts/models.py) — replace `Tier.TextChoices` with `FREE`, `SOLO`, `STUDIO`, `AGENCY`; update `QUOTA` dict. Add fields: `seat_limit`, `monthly_price_usd`, `annual_price_usd`, `billing_cadence` (monthly/annual), `proposal_pack_balance`.
- [backend/apps/core/permissions.py](../backend/apps/core/permissions.py) — `OrgProposalQuotaPermission` checks `proposal_pack_balance` as secondary allowance after monthly quota exhausted. Add `OrgSeatLimitPermission` for invite endpoints (future).
- [frontend/src/pages/Settings.jsx](../frontend/src/pages/Settings.jsx) — `TIER_CONFIG` dict needs updated tier entries, price strings (monthly + annual), feature lists, pack balance display.
- **New**: pricing page (`frontend/src/pages/Pricing.jsx`) — public-facing 4-tier comparison with monthly/yearly toggle, pack options below.
- **New**: `ProposalPack` model (`apps/billing/models.py`) — tracks pack purchases: `org`, `proposals_purchased`, `proposals_remaining`, `purchased_at`, `stripe_payment_intent_id`.
- **New**: `GenerationEvent` → add `input_tokens`, `output_tokens`, `cost_cents`, `consumed_pack` (bool) fields so overage billing + margin tracking work.
- **Future**: Stripe integration (`apps/billing/`) — checkout for subscriptions (monthly + annual price IDs per tier) and one-time pack purchases, webhooks, subscription state sync to `Org.tier` + `Org.billing_cadence`.

---

## Migration Strategy

Only 2 users in the system — no legacy concern.

- Both users manually flipped to `agency` tier so they keep working without disruption.
- Old `starter` / `growth` SKUs deleted from `Tier.TextChoices` along with their QUOTA entries.
- `proposal_pack_balance` defaults to 0 for all existing orgs.
- `billing_cadence` defaults to `monthly`.
- No grandfathering logic, no time-boxed migration, no legacy SKU clutter. Clean schema from day 1.

---

## Verification (when implemented)

- [ ] Pricing page shows 4 tiers with USD prices.
- [ ] Monthly/Yearly toggle flips price + -20% badge correctly.
- [ ] Studio shows "Most Popular" ribbon; Agency shows "Best Value" ribbon.
- [ ] New user signup defaults to `free` tier, `billing_cadence=monthly`.
- [ ] Hitting Free tier cap (3 proposals) returns 403 from POST `/api/proposals/`.
- [ ] Soft-cap warning toast fires on Solo+ when 80%+ of monthly quota used.
- [ ] Free tier users see pack section as disabled/locked in Settings.
- [ ] Solo+ users can purchase a pack; `Organization.proposal_pack_balance` increments correctly.
- [ ] Pack balance is consumed only after monthly quota reaches zero.
- [ ] Failed proposal generation does not deduct from quota or pack balance.
- [ ] Pack balance persists across the monthly reset (not zeroed on the 1st).
- [ ] Annual subscription bills correct amount (e.g. Solo annual = $182 upfront).
- [ ] GenerationEvent records `cost_cents` and `consumed_pack` per proposal; admin dashboard surfaces gross margin per tier per month.
- [ ] Stripe test checkout end-to-end: select Solo monthly → pay → org tier flips to `solo`, cadence `monthly`, quota refreshes.
- [ ] Stripe test checkout: select Studio annual → pay → org tier `studio`, cadence `annual`, $854 charged.
- [ ] Stripe one-time checkout: buy Plus pack → `proposal_pack_balance` increases by 30.
- [ ] Seat invite endpoint (future) blocks at tier seat limit (1/1/5/10).

---

## Decisions Locked

- Market: Global / USD
- ICP: Mixed (freelancers + small agencies)
- Model: Freemium + 3 paid tiers + proposal packs
- Free signup: email verify, no credit card
- Billing: Monthly + annual (20% off)
- Pricing page: public marketing page, all 4 tiers visible, monthly/yearly toggle
- UI: proposals displayed (no credit abstraction)
- Backend: proposal counter only, no internal credits
- Packs: Solo+ only, no expiry, org-scoped, 3 pack sizes (Boost/Plus/Power)
- Seats: hard cap per tier (no per-seat add-ons)
- Badges: Studio = Most Popular, Agency = Best Value
- Migration: existing 2 users → flip to Agency; drop old tiers

## Still Open (defer until post-launch)

- Refund policy (suggest: 14-day money-back on first paid month; no refunds on packs; annual prorated on cancel)
- Enterprise/custom tier above Agency (only build when first lead asks)
- Per-seat add-ons vs. seats-included-in-tier
- Pack gifting / promo codes (useful for onboarding campaigns)
- Auto-recharge on pack balance (currently manual only)
- API access pricing (Agency-only feature, future)

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
|---|---|---|---|
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
|---|---|---|---|---|---|
| **Free** | $0 | 3 | 10 | 1 | Trial / solo freelancer testing fit |
| **Solo** | **$29/mo** | 25 | 50 | 1 | Active freelancer, 1-2 bids/week |
| **Studio** | **$79/mo** | 100 | 200 | 3 | Boutique consultancy, small team |
| **Agency** | **$199/mo** | 500 | unlimited | 10 | Mid-market firm, bid-heavy |

**Overages** (paid tiers only): $1.50 per extra proposal above monthly cap. Soft cap (warn, don't block) on Solo+; hard cap on Free.

**Billing cadence**: monthly only in v1. Defer annual plans until we have churn data (~3-6 months post-launch) to size the discount correctly.

**Free signup**: email verification only, no credit card. Rate-limit signups by IP + email fingerprint to mitigate throwaway abuse.

**Pricing page**: public marketing page with full comparison table (SEO + transparency). Standard for self-serve at this price band.

---

## Margin Math

| Tier | Price | COGS @ 100% util | Gross margin |
|---|---|---|---|
| Free | $0 | $0.105 (3 proposals) | -$0.11 (CAC cost, capped low) |
| Solo | $29 | $0.875 (25) | **97%** |
| Studio | $79 | $3.50 (100) | **96%** |
| Agency | $199 | $17.50 (500) | **91%** |

All paid tiers clear the 85% margin floor with headroom for support, infra growth, and Stripe fees (~3%).

---

## Feature Differentiation Beyond Quotas

Quotas alone are weak differentiation. Layer feature gates:

- **Free**: Draftly watermark on PDF export, no DOCX export, no custom tone, 1 KB category only.
- **Solo**: All export formats, all 3 KB categories, standard support.
- **Studio**: Team seats (3), shared KB, template library access, priority queue.
- **Agency**: 10 seats, SSO (future), API access (future), custom branding on exports, dedicated support, SLA.

This lets you upsell on capability, not just volume — critical when ICP is solo (volume sells less than features).

---

## Why This Structure

1. **Free tier @ 3 proposals**: enough to feel the value loop end-to-end (upload KB → submit RFP → get draft → edit → export) without giving away the keys. 3 is the magic number — 1-2 feels stingy, 5+ kills conversion.
2. **$29 Solo anchor**: matches Jasper/Copy.ai/Notion AI psychological band for solo creators. Below the $50 friction threshold for personal credit cards.
3. **$79 Studio**: 2.7× Solo — captures freelancers leveling up to small teams without forcing the Agency jump.
4. **$199 Agency**: 2.5× Studio. Under $200 is still self-serve; above $200 typically needs sales-assist. Good ceiling for v1.
5. **3 paid tiers** (not 2, not 4): industry research (Price Intelligently) shows 3 paid tiers maximize conversion. 4+ paid creates choice paralysis; 2 leaves money on the table.

---

## Implementation Touchpoints

When approved, changes land in:

- [backend/apps/accounts/models.py](../backend/apps/accounts/models.py) — extend `Tier.TextChoices` to add `FREE`, `SOLO`, `STUDIO`; update `QUOTA` dict. Add `seat_limit` + `monthly_price_usd` fields or keep config-only.
- [backend/apps/core/permissions.py](../backend/apps/core/permissions.py) — `OrgDocQuotaPermission` + `OrgProposalQuotaPermission` already enforce per-tier; just pick up new QUOTA values.
- [frontend/src/pages/Settings.jsx](../frontend/src/pages/Settings.jsx) — `TIER_CONFIG` dict (lines 12-31) needs price strings, new tier entries, feature lists.
- **New**: pricing page (`frontend/src/pages/Pricing.jsx`) — public-facing comparison table.
- **New**: GenerationEvent → add `input_tokens`, `output_tokens`, `cost_cents` fields so overage billing + margin tracking work.
- **Future**: Stripe integration (`apps/billing/`) — checkout, webhooks, subscription state sync to Org.tier.

## Migration Strategy

Currently only 2 users in the system — no real legacy concern. Plan:
- Both users get manually flipped to `Agency` tier so they keep working without disruption.
- Old `starter` / `growth` SKUs deleted from `Tier.TextChoices` along with their QUOTA entries.
- No grandfathering logic, no time-boxed migration, no legacy SKU clutter. Clean schema from day 1.

---

## Verification (when implemented)

- [ ] Settings page shows 4 tiers with USD prices.
- [ ] New user signup defaults to `free` tier.
- [ ] Hitting Free tier cap (3 proposals) returns 403 from POST `/api/proposals/`.
- [ ] Soft-cap warning toast fires on Solo when 80%+ of monthly quota used.
- [ ] GenerationEvent records cost_cents per proposal; admin dashboard surfaces gross margin per tier per month.
- [ ] Stripe test checkout end-to-end: select Solo → pay → org tier flips to `solo` → quota refreshes.

---

## Decisions Locked

- Market: Global / USD
- ICP: Freelancers + solo consultants (primary)
- Model: Freemium + 3 paid tiers
- Free signup: email verify, no credit card
- Billing: monthly only in v1 (annual deferred)
- Pricing page: public marketing page
- Migration: 2 existing users → flip to Agency; drop old tiers

## Still Open (defer until post-launch)

- Refund policy (suggest: 14-day money-back on first paid month)
- Annual plans + discount sizing (revisit at 3-month mark)
- Enterprise/custom tier above Agency (only build when first lead asks)
- Per-seat add-ons vs. seats-included-in-tier

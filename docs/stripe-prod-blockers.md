# Stripe — Remaining Production Blockers

Status as of 2026-05-23. P0/P1 webhook + checkout fixes already shipped (price→tier reverse-lookup, `StripeEvent` idempotency, `invoice.paid` handler, `FRONTEND_URL`, pinned API version, 17 tests passing). The items below must be resolved before charging real customers.

---

## P0 — must fix before any prod traffic

### 1. Run + verify the new migration in prod
- File: `backend/apps/billing/migrations/0001_initial.py` (creates `StripeEvent` table).
- Action: `python manage.py migrate billing` on Railway before the new code is live, or webhook idempotency will crash with `relation "billing_stripeevent" does not exist`.
- Risk: every webhook returns 500 → Stripe retries → duplicate charges processed once code is patched.

### 2. Configure Stripe webhook endpoint in the Stripe dashboard
- URL: `https://<api-host>/api/billing/webhook/`
- Events to enable (exact list):
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.paid` (or `invoice.payment_succeeded` — handler accepts both)
  - `invoice.payment_failed`
- Copy the signing secret → set `STRIPE_WEBHOOK_SECRET` in Railway env.
- Without this, the handler returns 400 on every delivery (`STRIPE_WEBHOOK_SECRET is not configured`).

### 3. Create Products + Prices in Stripe live mode
- Currently only test-mode `price_...` IDs may be configured.
- Create 6 prices (Solo M/A, Studio M/A, Agency M/A) matching the amounts in `Organization.QUOTA`.
- Set `STRIPE_PRICE_*_MONTHLY` + `STRIPE_PRICE_*_ANNUAL` env vars to the **live-mode** IDs.
- Use live `STRIPE_SECRET_KEY` (`sk_live_...`) and `STRIPE_PUBLISHABLE_KEY` (`pk_live_...`).
- Mismatch between mode of secret key and price IDs → `No such price` errors at checkout.

### 4. Set `FRONTEND_URL` in Railway env to the production SPA origin
- Example: `FRONTEND_URL=https://draftly.software`
- Default fallback is `http://localhost:5173` — checkout success/cancel + portal return would redirect users to localhost.

### 5. End-to-end live test in Stripe test mode before flipping to live
- `stripe listen --forward-to http://localhost:8000/api/billing/webhook/`
- Walk through: signup → upgrade Solo monthly → portal upgrade to Studio annual → cancel → resubscribe.
- Confirm DB tier/cadence/period_end correct at each step.
- Confirm test-card decline path → `subscription_status == "past_due"`.

---

## P1 — fix before announcing or scaling

### 6. Re-bind quota check to subscription period, not calendar month
- File: [backend/apps/core/permissions.py:30-37](backend/apps/core/permissions.py#L30-L37).
- Current: counts proposals where `created_at >= month_start` (UTC 1st-of-month).
- Problem: user upgrades mid-month, their old usage carries against the new bigger quota — fine. But if they signed up mid-month, they get a partial month for full price. Worse, annual subscribers reset every UTC 1st even though they paid for 12 months.
- Fix: use `Organization.current_period_end` (or its start) as the window. Reset proposal count at each Stripe billing period.

### 7. Failed-payment recovery flow
- Currently `invoice.payment_failed` → `subscription_status = "past_due"` and nothing happens. No email, no in-app banner, no grace-period logic, no auto-cancel.
- Decide policy: Stripe Smart Retries handle ~3 retries over ~3 weeks, then `customer.subscription.deleted` fires (already handled). Need a frontend banner: "Payment failed — update card" reading `subscription_status`.
- Quotas keep enforcing the paid tier during `past_due` — verify whether that's intended (we currently bill for value not delivered).

### 8. Tier downgrade behavior is undefined
- Stripe Portal allows immediate downgrade. With our code: `subscription.updated` fires with the new (cheaper) price → tier flips immediately → user may exceed new tier's quotas instantly.
- Decide: downgrade at period end (set `cancel_at_period_end` + schedule the change) vs. immediate-with-credit. Document the choice + implement.

### 9. Disable subscription deletion via Portal
- Stripe Portal default lets users cancel directly. Confirm whether to allow self-serve cancel or require a contact-support flow. Configure under Stripe Dashboard → Billing → Customer Portal.
- If self-serve cancel is allowed, confirm `customer.subscription.deleted` handler does the right thing (downgrade to free — already implemented).

### 10. Webhook retry alerting
- `StripeEvent` table grows unbounded. After 30 days, prune via a Celery beat job (or add a partial index + manual cleanup).
- Stripe will retry a failing webhook for ~3 days. Add a Sentry alert on the `500` log path in [backend/apps/billing/views.py:222-225](backend/apps/billing/views.py#L222-L225) so we notice handler bugs before retries exhaust.

---

## P2 — operational hygiene

### 11. Stripe Tax / EU VAT
- Required for any sale into the EU (~5% of typical SaaS revenue).
- Action: enable Stripe Tax in dashboard → set `automatic_tax: {"enabled": True}` on `checkout.Session.create()` call in [backend/apps/billing/views.py:120-138](backend/apps/billing/views.py#L120-L138).
- Set tax registrations for any state/country we collect from.

### 12. Promo codes / trial periods
- No coupon support in checkout call. If marketing wants a launch promo, add `allow_promotion_codes=True` to the Session.create kwargs.
- No trial period configured on the Price objects. Decide and configure in Stripe Dashboard if desired.

### 13. Proposal-pack one-time purchases
- `Organization` model removed `proposal_pack_balance` in the recent pricing revamp (commit `fe1fe4d`). Pricing docs still mention Boost/Plus/Power packs.
- Reconcile: either re-add the field + a `payment_intent` flow + handler for `payment_intent.succeeded`, or remove the packs from marketing copy.

### 14. Customer email sync on user email change
- `Customer.create()` now passes `request.user.email`. If the user later changes email via `/auth/profile/`, the Stripe Customer is not updated. Stripe receipts go to the old address.
- Add a post-save signal on `User.email` change → `stripe.Customer.modify(org.stripe_customer_id, email=new)`.

### 15. Multi-seat billing for Studio/Agency tiers
- Tiers advertise "5 seats" / "10 seats" but billing is flat-rate per org. If the product grows into per-seat pricing later, the price IDs and `quantity` in `line_items` need rework.
- Document the current "seats = soft cap on User.objects.filter(org=...).count()" rule somewhere visible.

### 16. PCI scope confirmation
- Stripe Checkout + Portal keep us in PCI scope SAQ-A (lowest). Confirm no card data ever touches our servers (current code is clean — verify no future regression introduces Elements or direct PaymentIntent UI without re-evaluation).

### 17. Backup webhook delivery
- Stripe will retry failed webhooks for ~3 days, but a multi-day outage of our API loses events permanently. Stripe Workbench → Event Log can replay manually. Document the replay runbook so on-call knows where to look.

---

## Pre-launch checklist (condensed)

- [ ] Migration applied: `billing.0001_initial`
- [ ] Live Stripe keys in Railway: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`
- [ ] Live price IDs set (6 vars)
- [ ] `STRIPE_WEBHOOK_SECRET` set from dashboard endpoint
- [ ] `FRONTEND_URL` set to prod origin
- [ ] `STRIPE_API_VERSION` set (default `2024-11-20.acacia` ok)
- [ ] Stripe webhook endpoint configured with the 5 event types
- [ ] Stripe Tax enabled if selling into EU
- [ ] Customer Portal configured (cancel policy, upgrade rules)
- [ ] End-to-end test in Stripe test mode (signup → upgrade → portal change → cancel → resub → failed-payment)
- [ ] Sentry alert on billing webhook 500
- [ ] Quota window aligned with billing period (P1 #6)
- [ ] Past-due frontend banner in Settings (P1 #7)

---

## Reference

- [backend/apps/billing/views.py](backend/apps/billing/views.py) — webhook + checkout
- [backend/apps/billing/models.py](backend/apps/billing/models.py) — `StripeEvent`
- [backend/apps/billing/tests/](backend/apps/billing/tests/) — 17 tests, all green
- [docs/pricing-model.md](docs/pricing-model.md) — tier + quota spec

# Stripe — Remaining Production Blockers

Status as of 2026-05-23; **updated 2026-07-01**. P0/P1 webhook + checkout fixes already shipped (price→tier reverse-lookup, `StripeEvent` idempotency, `invoice.paid` handler, `FRONTEND_URL`, pinned API version, 17 tests passing). The items below must be resolved before charging real customers.

> **Deploy note (2026-07-01):** Backend runs on **Azure Container Apps** (`draftly-api`, habitforge-rg, francecentral), not Railway. All "set X in Railway env" instructions below mean **set the env var on the `draftly-api` Container App**. Migrations run via the container, not `railway run`.

### ✅ Completed since 2026-05-23

- **#6 Quota window bound to billing period** — [permissions.py:60-77](backend/apps/core/permissions.py#L60-L77) resolves period start from `current_period_end` + cadence for paid tiers; calendar-month fallback for free.
- **#7 Past-due frontend banner** — [AppShell.jsx:15-24](frontend/src/components/AppShell.jsx#L15-L24) renders "Payment failed — update payment method" when `subscription_status === "past_due"`. (Grace-period/auto-cancel policy still per #7 below.)
- **#10 (part) StripeEvent pruning** — daily beat job `prune-stripe-events-daily` at 03:00 UTC ([celery.py:14](backend/config/celery.py#L14), [billing/tasks.py:13](backend/apps/billing/tasks.py#L13)). Sentry alert on the 500 path still open.
- **#11 Stripe Tax** — `automatic_tax={"enabled": True}` live at [billing/views.py:135](backend/apps/billing/views.py#L135). Still need tax registrations set in dashboard.
- **#14 Customer email sync** — [accounts/views.py:174](backend/apps/accounts/views.py#L174) calls `stripe.Customer.modify(...)` on email change.
- **Bonus (not in original doc):** ToS/Privacy consent collection at checkout ([billing/views.py:136-146](backend/apps/billing/views.py#L136-L146)).

Still open: all P0 ops items, #8 downgrade policy, #9 portal cancel config, #10 Sentry 500 alert, #12 promo codes, #13 proposal packs, #15 seats, #16 PCI verify, #17 replay runbook.

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

### 6. Re-bind quota check to subscription period, not calendar month ✅ DONE (2026-07-01)
- File: [backend/apps/core/permissions.py:60-77](backend/apps/core/permissions.py#L60-L77).
- Shipped: `_billing_period_start(period_end, cadence)` derives the window start from `Organization.current_period_end`; paid tiers reset per Stripe billing period, free tier keeps UTC 1st-of-month fallback.

### 7. Failed-payment recovery flow — ⚠️ PARTIAL (banner done 2026-07-01)
- Done: in-app banner in [AppShell.jsx:15-24](frontend/src/components/AppShell.jsx#L15-L24) reads `subscription_status === "past_due"` → "Payment failed — update payment method".
- Still open: no dunning email; relying on Stripe Smart Retries (~3 retries/~3 weeks) then `customer.subscription.deleted` (already handled). Decide grace-period/auto-cancel policy.
- Still open: quotas keep enforcing the paid tier during `past_due` — confirm intended (currently bill for value not delivered).

### 8. Tier downgrade behavior is undefined
- Stripe Portal allows immediate downgrade. With our code: `subscription.updated` fires with the new (cheaper) price → tier flips immediately → user may exceed new tier's quotas instantly.
- Decide: downgrade at period end (set `cancel_at_period_end` + schedule the change) vs. immediate-with-credit. Document the choice + implement.

### 9. Disable subscription deletion via Portal
- Stripe Portal default lets users cancel directly. Confirm whether to allow self-serve cancel or require a contact-support flow. Configure under Stripe Dashboard → Billing → Customer Portal.
- If self-serve cancel is allowed, confirm `customer.subscription.deleted` handler does the right thing (downgrade to free — already implemented).

### 10. Webhook retry alerting — ⚠️ PARTIAL (prune done 2026-07-01)
- Done: `prune-stripe-events-daily` beat job deletes `StripeEvent` rows older than `STRIPE_EVENT_RETENTION_DAYS` (default 30) at 03:00 UTC ([celery.py:12-18](backend/config/celery.py#L12-L18), [billing/tasks.py:13-25](backend/apps/billing/tasks.py#L13-L25)).
- Still open: Stripe retries a failing webhook for ~3 days. Add a Sentry alert on the `500` log path in [backend/apps/billing/views.py:254-258](backend/apps/billing/views.py#L254-L258) so we notice handler bugs before retries exhaust.

---

## P2 — operational hygiene

### 11. Stripe Tax / EU VAT — ⚠️ PARTIAL (code done 2026-07-01)
- Done: `automatic_tax={"enabled": True}` on the checkout session ([backend/apps/billing/views.py:135](backend/apps/billing/views.py#L135)).
- Still open: enable Stripe Tax in the dashboard and set tax registrations for any state/country we collect from.

### 12. Promo codes / trial periods
- No coupon support in checkout call. If marketing wants a launch promo, add `allow_promotion_codes=True` to the Session.create kwargs.
- No trial period configured on the Price objects. Decide and configure in Stripe Dashboard if desired.

### 13. Proposal-pack one-time purchases
- `Organization` model removed `proposal_pack_balance` in the recent pricing revamp (commit `fe1fe4d`). Pricing docs still mention Boost/Plus/Power packs.
- Reconcile: either re-add the field + a `payment_intent` flow + handler for `payment_intent.succeeded`, or remove the packs from marketing copy.

### 14. Customer email sync on user email change ✅ DONE (2026-07-01)
- Shipped: email update path calls `stripe.Customer.modify(org.stripe_customer_id, email=email)` ([backend/apps/accounts/views.py:174](backend/apps/accounts/views.py#L174)).

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
- [ ] Stripe Tax enabled in dashboard + registrations (code done — P2 #11)
- [ ] Customer Portal configured (cancel policy, upgrade rules)
- [ ] End-to-end test in Stripe test mode (signup → upgrade → portal change → cancel → resub → failed-payment)
- [ ] Sentry alert on billing webhook 500
- [x] Quota window aligned with billing period (P1 #6) — 2026-07-01
- [x] Past-due frontend banner (P1 #7, in AppShell) — 2026-07-01
- [x] StripeEvent pruning beat job (P1 #10) — 2026-07-01
- [x] Customer email sync on email change (P2 #14) — 2026-07-01

---

## Reference

- [backend/apps/billing/views.py](backend/apps/billing/views.py) — webhook + checkout
- [backend/apps/billing/models.py](backend/apps/billing/models.py) — `StripeEvent`
- [backend/apps/billing/tests/](backend/apps/billing/tests/) — 17 tests, all green
- [docs/pricing-model.md](docs/pricing-model.md) — tier + quota spec

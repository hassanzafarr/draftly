#!/usr/bin/env python
"""Create Stripe Products + Prices for Draftly tiers and print the env vars.

Stripe Price objects are immutable — you cannot edit an amount. To change a
price you create a NEW Price (and a Product to hang it on, if missing) and point
the app's STRIPE_PRICE_* env vars at the new IDs. This script does exactly that.

Safety:
  - Refuses to run against a live key (sk_live_) unless you pass --live.
  - Idempotent: each Price is tagged with a lookup_key; a re-run reuses the
    existing Price with that key instead of creating a duplicate.

Usage:
    export STRIPE_SECRET_KEY=sk_test_...          # test mode first
    python backend/scripts/create_stripe_prices.py
    # then, only after verifying in the Stripe test dashboard:
    export STRIPE_SECRET_KEY=sk_live_...
    python backend/scripts/create_stripe_prices.py --live

The amounts below MUST match Organization.QUOTA in
backend/apps/accounts/models.py. Keep them in sync.
"""

import argparse
import os
import sys

import stripe

# tier -> (display name, monthly USD, annual-total USD). Mirrors QUOTA.
TIERS = {
    "solo": ("Draftly Solo", 12, 115),
    "studio": ("Draftly Studio", 49, 470),
    "agency": ("Draftly Agency", 149, 1430),
}

# (cadence, stripe interval, env-var suffix)
CADENCES = [
    ("monthly", "month", "MONTHLY"),
    ("annual", "year", "ANNUAL"),
]


def _find_price_by_lookup_key(lookup_key: str):
    resp = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1)
    return resp.data[0] if resp.data else None


def _find_product_by_name(name: str):
    # Stripe has no exact-name lookup; scan active products (small N for us).
    for product in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if product.name == name:
            return product
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow running against a live (sk_live_) key. Default refuses.",
    )
    args = parser.parse_args()

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        print("ERROR: STRIPE_SECRET_KEY is not set.", file=sys.stderr)
        return 1
    if key.startswith("sk_live_") and not args.live:
        print(
            "ERROR: refusing to run against a LIVE key without --live. "
            "Run in test mode first (sk_test_...).",
            file=sys.stderr,
        )
        return 1

    stripe.api_key = key
    mode = "LIVE" if key.startswith("sk_live_") else "TEST"
    print(f"# Stripe mode: {mode}\n")

    env_lines: list[str] = []

    for tier, (product_name, monthly_usd, annual_usd) in TIERS.items():
        product = _find_product_by_name(product_name)
        if product is None:
            product = stripe.Product.create(name=product_name)
            print(f"# created product {product.id} ({product_name})")
        else:
            print(f"# reuse product {product.id} ({product_name})")

        amounts = {"monthly": monthly_usd, "annual": annual_usd}
        for cadence, interval, suffix in CADENCES:
            lookup_key = f"draftly_{tier}_{cadence}"
            price = _find_price_by_lookup_key(lookup_key)
            if price is None:
                price = stripe.Price.create(
                    product=product.id,
                    unit_amount=amounts[cadence] * 100,  # USD -> cents
                    currency="usd",
                    recurring={"interval": interval},
                    lookup_key=lookup_key,
                    nickname=f"{product_name} ({cadence})",
                )
                print(f"# created price {price.id} ({lookup_key}, ${amounts[cadence]})")
            else:
                print(f"# reuse price {price.id} ({lookup_key})")
            env_lines.append(f"STRIPE_PRICE_{tier.upper()}_{suffix}={price.id}")

    print("\n# --- paste into Railway/Azure env (and .env for local) ---")
    print("\n".join(env_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Zap, Sparkles, Crown, Star, Clock, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import useAuthStore from "../store/auth";
import api from "../api/client";

const PLANS = {
  monthly: [
    {
      id: "free",
      name: "Free",
      price: 0,
      priceLabel: "$0",
      period: "/ month",
      tagline: "Try Draftly end-to-end",
      icon: Zap,
      iconColor: "text-cyan-400",
      highlight: false,
      badge: null,
      cta: "Get started",
      ctaDisabled: false,
      features: [
        "3 proposals / month",
        "10 documents",
        "1 seat",
        "PDF export (watermark)",
        "1 KB category",
      ],
    },
    {
      id: "solo",
      name: "Solo",
      price: 12,
      priceLabel: "$12",
      period: "/ month",
      tagline: "For active freelancers",
      icon: Sparkles,
      iconColor: "text-violet-400",
      highlight: true,
      badge: "Most Popular",
      cta: "Upgrade to Solo",
      ctaDisabled: false,
      features: [
        "25 proposals / month",
        "25 documents",
        "1 seat",
        "PDF & DOCX export",
        "All 3 KB categories",
      ],
    },
    {
      id: "studio",
      name: "Studio",
      price: 49,
      priceLabel: "$49",
      period: "/ month",
      tagline: "Small teams and boutique consultancies",
      icon: Star,
      iconColor: "text-fuchsia-400",
      highlight: false,
      badge: null,
      cta: "Upgrade to Studio",
      ctaDisabled: false,
      features: [
        "150 proposals / month",
        "250 documents",
        "5 seats",
        "Shared knowledge base",
        "Template library",
        "Priority generation queue",
      ],
    },
    {
      id: "agency",
      name: "Agency",
      price: 149,
      priceLabel: "$149",
      period: "/ month",
      tagline: "Bid-heavy agencies",
      icon: Crown,
      iconColor: "text-amber-400",
      highlight: false,
      badge: "Best Value",
      cta: "Upgrade to Agency",
      ctaDisabled: false,
      features: [
        "750 proposals / month",
        "Unlimited documents",
        "10 seats",
        "Custom export branding",
        "SSO (coming soon)",
        "API access (coming soon)",
        "Dedicated support + SLA",
      ],
    },
  ],
  annual: [
    {
      id: "free",
      name: "Free",
      price: 0,
      priceLabel: "$0",
      period: "/ month",
      tagline: "Try Draftly end-to-end",
      icon: Zap,
      iconColor: "text-cyan-400",
      highlight: false,
      badge: null,
      cta: "Get started",
      ctaDisabled: false,
      features: [
        "3 proposals / month",
        "10 documents",
        "1 seat",
        "PDF export (watermark)",
        "1 KB category",
      ],
    },
    {
      id: "solo",
      name: "Solo",
      price: 9.6,
      priceLabel: "$9.60",
      originalPrice: "$12",
      period: "/ month",
      annualNote: "billed $115 / year",
      tagline: "For active freelancers",
      icon: Sparkles,
      iconColor: "text-violet-400",
      highlight: true,
      badge: "Most Popular",
      cta: "Upgrade to Solo",
      ctaDisabled: false,
      features: [
        "25 proposals / month",
        "25 documents",
        "1 seat",
        "PDF & DOCX export",
        "All 3 KB categories",
      ],
    },
    {
      id: "studio",
      name: "Studio",
      price: 39.2,
      priceLabel: "$39.20",
      originalPrice: "$49",
      period: "/ month",
      annualNote: "billed $470 / year",
      tagline: "Small teams and boutique consultancies",
      icon: Star,
      iconColor: "text-fuchsia-400",
      highlight: false,
      badge: null,
      cta: "Upgrade to Studio",
      ctaDisabled: false,
      features: [
        "150 proposals / month",
        "250 documents",
        "5 seats",
        "Shared knowledge base",
        "Template library",
        "Priority generation queue",
      ],
    },
    {
      id: "agency",
      name: "Agency",
      price: 119.2,
      priceLabel: "$119.20",
      originalPrice: "$149",
      period: "/ month",
      annualNote: "billed $1,430 / year",
      tagline: "Bid-heavy agencies",
      icon: Crown,
      iconColor: "text-amber-400",
      highlight: false,
      badge: "Best Value",
      cta: "Upgrade to Agency",
      ctaDisabled: false,
      features: [
        "750 proposals / month",
        "Unlimited documents",
        "10 seats",
        "Custom export branding",
        "SSO (coming soon)",
        "API access (coming soon)",
        "Dedicated support + SLA",
      ],
    },
  ],
};

export default function Pricing() {
  const [billing, setBilling] = useState("monthly");
  const [upgrading, setUpgrading] = useState(null);
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const currentTier = user?.org?.subscription_tier ?? "free";
  const plans = PLANS[billing];

  const handleUpgrade = async (tier) => {
    if (tier === "free") {
      navigate("/");
      return;
    }

    setUpgrading(tier);
    try {
      const { data } = await api.post("/billing/checkout/", {
        tier,
        billing_cadence: billing,
      });
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not start checkout.");
      setUpgrading(null);
    }
  };

  return (
    <div className="min-h-screen px-6 py-12">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-10 text-center"
        >
          <h1 className="mb-3 text-3xl font-bold tracking-tight text-foreground">
            Simple, transparent pricing
          </h1>
          <p className="text-base text-muted-foreground">
            Choose the plan that fits your team. Upgrade or downgrade at any time.
          </p>

          {/* Billing toggle */}
          <div className="mt-6 inline-flex items-center gap-1 rounded-full border border-hairline bg-surface p-1">
            {["monthly", "annual"].map((b) => (
              <button
                key={b}
                onClick={() => setBilling(b)}
                className={`relative flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
                  billing === b
                    ? "bg-violet text-white shadow"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {b === "annual" && (
                  <span
                    className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                      billing === b
                        ? "bg-white/20 text-white"
                        : "bg-emerald-500/20 text-emerald-400"
                    }`}
                  >
                    −20%
                  </span>
                )}
                {b.charAt(0).toUpperCase() + b.slice(1)}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan, i) => {
            const Icon = plan.icon;
            const isCurrent = plan.id === currentTier;
            const isLoading = upgrading === plan.id;

            return (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`relative flex flex-col rounded-2xl border p-6 transition-all ${
                  plan.highlight
                    ? "border-violet/60 bg-gradient-to-b from-violet/10 via-surface to-surface shadow-lg shadow-violet/10"
                    : "border-hairline bg-surface hover:border-violet/30"
                }`}
              >
                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-3 py-0.5 text-xs font-semibold text-white shadow ${
                        plan.highlight ? "bg-violet" : "bg-amber-500"
                      }`}
                    >
                      <Clock className="h-3 w-3" />
                      {plan.badge}
                    </span>
                  </div>
                )}

                {/* Plan name & icon */}
                <div className="mb-4 flex items-center gap-2">
                  <span className={`rounded-lg bg-surface-2 p-1.5 ${plan.iconColor}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="text-base font-semibold text-foreground">{plan.name}</span>
                </div>

                {/* Price */}
                <div className="mb-1 flex items-end gap-1">
                  <span className="text-4xl font-bold text-foreground">{plan.priceLabel}</span>
                  <span className="mb-1 text-sm text-muted-foreground">{plan.period}</span>
                </div>
                <p className="mb-5 text-sm text-muted-foreground">{plan.tagline}</p>

                {/* CTA button */}
                {isCurrent ? (
                  <div className="mb-5 flex h-10 items-center justify-center rounded-xl border border-hairline text-sm text-muted-foreground">
                    Your current plan
                  </div>
                ) : (
                  <button
                    onClick={() => handleUpgrade(plan.id)}
                    disabled={!!upgrading}
                    className={`mb-5 flex h-10 w-full items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-60 ${
                      plan.highlight
                        ? "bg-violet text-white shadow hover:bg-violet/90 active:scale-[0.98]"
                        : "bg-surface-2 text-foreground hover:bg-surface active:scale-[0.98]"
                    }`}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Redirecting…
                      </>
                    ) : (
                      plan.cta
                    )}
                  </button>
                )}

                <hr className="mb-5 border-hairline" />

                {/* Features */}
                <ul className="flex flex-col gap-2.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      {f}
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </div>

        {/* Footer note */}
        <p className="mt-8 text-center text-xs text-muted-foreground">
          All plans include SSL encryption and GDPR-compliant data handling. Payments are securely
          processed by Stripe.
        </p>
      </div>
    </div>
  );
}

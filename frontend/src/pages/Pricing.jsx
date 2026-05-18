import { useState } from "react";
import { motion } from "framer-motion";
import { Check, Zap, Sparkles, Crown, Clock } from "lucide-react";
import { useNavigate } from "react-router-dom";
import useAuthStore from "../store/auth";

const PLANS = {
  monthly: [
    {
      id: "starter",
      name: "Starter",
      price: 0,
      priceLabel: "$0",
      period: "/ month",
      tagline: "Get started with AI proposals",
      icon: Zap,
      iconColor: "text-cyan-400",
      highlight: false,
      badge: null,
      cta: "Current plan",
      ctaDisabled: true,
      features: [
        "50 processed documents",
        "5 proposals / month",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Basic analytics",
      ],
    },
    {
      id: "growth",
      name: "Growth",
      price: 29,
      priceLabel: "$29",
      period: "/ month",
      tagline: "Scale your proposal workflow",
      icon: Sparkles,
      iconColor: "text-violet-400",
      highlight: true,
      badge: "Most Popular",
      cta: "Upgrade to Growth",
      ctaDisabled: false,
      features: [
        "200 processed documents",
        "25 proposals / month",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Advanced analytics",
        "Priority generation queue",
        "Custom tone & style",
      ],
    },
    {
      id: "agency",
      name: "Agency",
      price: 99,
      priceLabel: "$99",
      period: "/ month",
      tagline: "Unlimited power for agencies",
      icon: Crown,
      iconColor: "text-amber-400",
      highlight: false,
      badge: null,
      cta: "Upgrade to Agency",
      ctaDisabled: false,
      features: [
        "Unlimited documents",
        "Unlimited proposals",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Full analytics suite",
        "Priority generation queue",
        "Custom tone & style",
        "Team member management",
        "Dedicated support",
      ],
    },
  ],
  annual: [
    {
      id: "starter",
      name: "Starter",
      price: 0,
      priceLabel: "$0",
      period: "/ month",
      tagline: "Get started with AI proposals",
      icon: Zap,
      iconColor: "text-cyan-400",
      highlight: false,
      badge: null,
      cta: "Current plan",
      ctaDisabled: true,
      features: [
        "50 processed documents",
        "5 proposals / month",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Basic analytics",
      ],
    },
    {
      id: "growth",
      name: "Growth",
      price: 23,
      priceLabel: "$23",
      originalPrice: "$29",
      period: "/ month",
      annualNote: "billed $276 / year",
      tagline: "Scale your proposal workflow",
      icon: Sparkles,
      iconColor: "text-violet-400",
      highlight: true,
      badge: "Most Popular",
      cta: "Upgrade to Growth",
      ctaDisabled: false,
      features: [
        "200 processed documents",
        "25 proposals / month",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Advanced analytics",
        "Priority generation queue",
        "Custom tone & style",
      ],
    },
    {
      id: "agency",
      name: "Agency",
      price: 79,
      priceLabel: "$79",
      originalPrice: "$99",
      period: "/ month",
      annualNote: "billed $948 / year",
      tagline: "Unlimited power for agencies",
      icon: Crown,
      iconColor: "text-amber-400",
      highlight: false,
      badge: null,
      cta: "Upgrade to Agency",
      ctaDisabled: false,
      features: [
        "Unlimited documents",
        "Unlimited proposals",
        "PDF & DOCX export",
        "10-section AI drafts",
        "Full analytics suite",
        "Priority generation queue",
        "Custom tone & style",
        "Team member management",
        "Dedicated support",
      ],
    },
  ],
};

export default function Pricing() {
  const [billing, setBilling] = useState("monthly");
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const currentTier = user?.org?.tier ?? "starter";
  const plans = PLANS[billing];

  return (
    <div className="min-h-screen px-6 py-12">
      <div className="mx-auto max-w-5xl">
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
          <div className="mt-6 inline-flex items-center gap-1 rounded-full border border-hairline bg-surface-1 p-1">
            {["monthly", "annual"].map((b) => (
              <button
                key={b}
                onClick={() => setBilling(b)}
                className={`relative flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
                  billing === b
                    ? "bg-white text-gray-900 shadow dark:bg-surface-3 dark:text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {b === "annual" && (
                  <span className="rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400">
                    −20%
                  </span>
                )}
                {b.charAt(0).toUpperCase() + b.slice(1)}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {plans.map((plan, i) => {
            const Icon = plan.icon;
            const isCurrent = plan.id === currentTier;
            return (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
                className={`relative flex flex-col rounded-2xl border p-6 transition-all ${
                  plan.highlight
                    ? "border-violet/60 bg-gradient-to-b from-violet/10 via-surface-1 to-surface-1 shadow-lg shadow-violet/10"
                    : "border-hairline bg-surface-1 hover:border-violet/30"
                }`}
              >
                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 rounded-full bg-violet px-3 py-0.5 text-xs font-semibold text-white shadow">
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
                  {plan.originalPrice && (
                    <span className="mb-1 text-lg text-muted-foreground line-through">
                      {plan.originalPrice}
                    </span>
                  )}
                  <span className="text-4xl font-bold text-foreground">{plan.priceLabel}</span>
                  <span className="mb-1 text-sm text-muted-foreground">{plan.period}</span>
                </div>
                {plan.annualNote && (
                  <p className="mb-3 text-xs text-muted-foreground">{plan.annualNote}</p>
                )}
                <p className="mb-5 text-sm text-muted-foreground">{plan.tagline}</p>

                {/* CTA button */}
                {isCurrent ? (
                  <div className="mb-5 flex h-10 items-center justify-center rounded-xl border border-hairline text-sm text-muted-foreground">
                    Your current plan
                  </div>
                ) : (
                  <button
                    disabled={plan.ctaDisabled}
                    onClick={() => navigate("/settings")}
                    className={`mb-5 h-10 w-full rounded-xl text-sm font-semibold transition-all ${
                      plan.highlight
                        ? "bg-violet text-white shadow hover:bg-violet/90 active:scale-[0.98]"
                        : "bg-surface-3 text-foreground hover:bg-surface-2 active:scale-[0.98]"
                    }`}
                  >
                    {plan.cta}
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
          All plans include SSL encryption and GDPR-compliant data handling. Tiers are currently set manually — no payment required during beta.
        </p>
      </div>
    </div>
  );
}

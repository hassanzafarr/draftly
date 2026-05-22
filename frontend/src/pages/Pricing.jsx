import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Check, Zap, Sparkles, Crown, Loader2 } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "react-hot-toast";
import useAuthStore from "../store/auth";
import api from "../api/client";

const PLANS = [
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
    cta: "Your current plan",
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
];

export default function Pricing() {
  const [upgrading, setUpgrading] = useState(null);
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const currentTier = user?.org?.subscription_tier ?? "starter";

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("success") === "true") {
      toast.success("Subscription activated! Your plan will update shortly.");
      navigate("/pricing", { replace: true });
    } else if (params.get("canceled") === "true") {
      toast("Checkout canceled — no charge was made.", { icon: "ℹ️" });
      navigate("/pricing", { replace: true });
    }
  }, [location.search]);

  const handleUpgrade = async (planId) => {
    if (upgrading) return;
    setUpgrading(planId);
    try {
      const { data } = await api.post("/billing/checkout/", { tier: planId });
      window.location.href = data.url;
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not start checkout. Please try again.";
      toast.error(msg);
      setUpgrading(null);
    }
  };

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

          {/* Billing toggle — annual coming soon */}
          <div className="mt-6 inline-flex items-center gap-1 rounded-full border border-hairline bg-surface-1 p-1">
            <button className="relative flex items-center gap-1.5 rounded-full bg-surface-3 px-4 py-1.5 text-sm font-medium text-foreground shadow">
              Monthly
            </button>
            <button
              disabled
              className="relative flex cursor-not-allowed items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium text-muted-foreground opacity-60"
              title="Annual billing coming soon"
            >
              <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                Soon
              </span>
              Annual
            </button>
          </div>
        </motion.div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {PLANS.map((plan, i) => {
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
                    ? "border-violet/60 bg-gradient-to-b from-violet/10 via-surface-1 to-surface-1 shadow-lg shadow-violet/10"
                    : "border-hairline bg-surface-1 hover:border-violet/30"
                }`}
              >
                {/* Badge */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 rounded-full bg-violet px-3 py-0.5 text-xs font-semibold text-white shadow">
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
                        : "bg-surface-3 text-foreground hover:bg-surface-2 active:scale-[0.98]"
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
          All plans include SSL encryption and GDPR-compliant data handling. Payments are securely processed by Stripe.
        </p>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, ArrowRight, Loader2, ArrowLeft } from "lucide-react";
import { AuthShell } from "../components/AuthShell";
import api from "../api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError("Please enter a valid email.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/password-reset/", { email: email.trim() });
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Forgot your password?"
      subtitle={
        sent
          ? "Check your inbox for a reset link."
          : "Enter your email and we'll send you a reset link."
      }
      footer={
        <Link
          to="/login"
          className="inline-flex items-center gap-1 font-medium text-foreground transition hover:text-violet"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to sign in
        </Link>
      }
    >
      {sent ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-hairline bg-surface-2 px-4 py-5 text-center text-sm text-muted-foreground"
        >
          If <span className="font-medium text-foreground">{email}</span> is
          registered, a reset link is on its way. Check your spam folder if you
          don&apos;t see it.
        </motion.div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="group relative block">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition group-focus-within:text-foreground">
              <Mail className="h-4 w-4" />
            </span>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="h-11 w-full rounded-xl border border-hairline bg-surface-2 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground/70 transition focus:border-violet/50 focus:outline-none focus:ring-2 focus:ring-violet/30"
            />
          </label>

          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          <motion.button
            type="submit"
            disabled={loading}
            whileTap={{ scale: 0.98 }}
            className="group relative flex h-11 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-violet to-magenta text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition disabled:opacity-70"
          >
            <span
              aria-hidden
              className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full"
            />
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Sending…
              </>
            ) : (
              <>
                Send reset link
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </>
            )}
          </motion.button>
        </form>
      )}
    </AuthShell>
  );
}

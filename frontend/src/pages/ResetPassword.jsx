import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Eye, EyeOff, ArrowRight, Loader2, ArrowLeft } from "lucide-react";
import { toast } from "react-hot-toast";
import { AuthShell } from "../components/AuthShell";
import api from "../api/client";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const uid = searchParams.get("uid") || "";
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const invalidLink = !uid || !token;

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/password-reset/confirm/", { uid, token, new_password: password });
      toast.success("Password reset! Please sign in.");
      navigate("/login");
    } catch (err) {
      const msg = err.response?.data?.detail || "Reset failed. The link may have expired.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Set new password"
      subtitle={
        invalidLink
          ? "This reset link is missing required parameters."
          : "Choose a strong password for your account."
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
      {invalidLink ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-4 text-center text-sm text-destructive">
          Invalid or incomplete reset link. Please request a new one.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="group relative block">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition group-focus-within:text-foreground">
              <Lock className="h-4 w-4" />
            </span>
            <input
              type={show ? "text" : "password"}
              placeholder="Min. 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className="h-11 w-full rounded-xl border border-hairline bg-surface-2 pl-10 pr-10 text-sm text-foreground placeholder:text-muted-foreground/70 transition focus:border-violet/50 focus:outline-none focus:ring-2 focus:ring-violet/30"
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition hover:text-foreground"
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
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
                Resetting…
              </>
            ) : (
              <>
                Reset password
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </>
            )}
          </motion.button>
        </form>
      )}
    </AuthShell>
  );
}

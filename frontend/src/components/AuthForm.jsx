import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, Loader2, Mail, Lock, Building2, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../api/client";
import useAuthStore from "../store/auth";

export function AuthForm({ mode }) {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (mode === "signup" && orgName.trim().length < 2) {
      setError("Please enter your agency / company name.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError("Please enter a valid email.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      if (mode === "signup") {
        await api.post("/auth/register/", {
          org_name: orgName.trim(),
          email: email.trim(),
          password,
        });
        await login(email.trim(), password);
        toast.success("Welcome! Your workspace is ready.");
      } else {
        await login(email.trim(), password);
      }
      navigate("/");
    } catch (err) {
      const data = err.response?.data;
      const msg =
        data?.email?.[0] ||
        data?.org_name?.[0] ||
        data?.password?.[0] ||
        data?.detail ||
        (mode === "signup" ? "Registration failed." : "Invalid email or password.");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <AnimatePresence mode="popLayout">
        {mode === "signup" && (
          <motion.div
            key="orgName"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
          >
            <Field
              icon={<Building2 className="h-4 w-4" />}
              type="text"
              placeholder="Agency / Company name"
              value={orgName}
              onChange={setOrgName}
              autoComplete="organization"
            />
          </motion.div>
        )}
      </AnimatePresence>

      <Field
        icon={<Mail className="h-4 w-4" />}
        type="email"
        placeholder="you@company.com"
        value={email}
        onChange={setEmail}
        autoComplete="email"
      />

      <Field
        icon={<Lock className="h-4 w-4" />}
        type={show ? "text" : "password"}
        placeholder={mode === "signup" ? "Min. 8 characters" : "Password"}
        value={password}
        onChange={setPassword}
        autoComplete={mode === "signup" ? "new-password" : "current-password"}
        trailing={
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="text-muted-foreground transition hover:text-foreground"
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        }
      />

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
            {mode === "login" ? "Signing in…" : "Creating account…"}
          </>
        ) : (
          <>
            {mode === "login" ? "Sign in" : "Create account"}
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </>
        )}
      </motion.button>

      {mode === "signup" && (
        <p className="text-center text-[11px] text-muted-foreground">
          By creating an account you agree to our Terms &amp; Privacy Policy.
        </p>
      )}
    </form>
  );
}

function Field({ icon, trailing, value, onChange, ...props }) {
  return (
    <label className="group relative block">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition group-focus-within:text-foreground">
        {icon}
      </span>
      <input
        {...props}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 w-full rounded-xl border border-hairline bg-surface-2 pl-10 pr-10 text-sm text-foreground placeholder:text-muted-foreground/70 transition focus:border-violet/50 focus:outline-none focus:ring-2 focus:ring-violet/30"
      />
      {trailing && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2">{trailing}</span>
      )}
    </label>
  );
}

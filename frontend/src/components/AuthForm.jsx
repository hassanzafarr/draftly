import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, Loader2, Mail, Lock, Building2, ArrowRight } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import { useGoogleLogin } from "@react-oauth/google";
import api from "../api/client";
import useAuthStore from "../store/auth";

export function AuthForm({ mode }) {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const googleLogin = useAuthStore((s) => s.googleLogin);
  const googleComplete = useAuthStore((s) => s.googleComplete);

  // Email/password form state
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Google two-step state
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleStep, setGoogleStep] = useState(null); // null | "org_name"
  const [googleCredential, setGoogleCredential] = useState(null);
  const [googleDisplayName, setGoogleDisplayName] = useState("");
  const [googleOrgName, setGoogleOrgName] = useState("");

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

  const openGooglePopup = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setError(null);
      try {
        const { data } = await api.post("/auth/google/", {
          credential: tokenResponse.access_token,
        });

        if (data.status === "new_user") {
          setGoogleCredential(tokenResponse.access_token);
          setGoogleDisplayName(data.display_name || "");
          setGoogleStep("org_name");
        } else {
          localStorage.setItem("access_token", data.access);
          localStorage.setItem("refresh_token", data.refresh);
          useAuthStore.setState({ user: data.user });
          navigate("/");
        }
      } catch (err) {
        const msg =
          err.response?.data?.detail ||
          "Google sign-in failed. Please try again.";
        setError(msg);
      } finally {
        setGoogleLoading(false);
      }
    },
    onError: () => {
      setGoogleLoading(false);
      setError("Google sign-in was cancelled or failed. Please try again.");
    },
    flow: "implicit",
  });

  async function handleGoogleOrgSubmit(e) {
    e.preventDefault();
    setError(null);
    if (googleOrgName.trim().length < 2) {
      setError("Please enter your organisation name (at least 2 characters).");
      return;
    }
    setGoogleLoading(true);
    try {
      await googleComplete(googleCredential, googleOrgName.trim());
      toast.success("Welcome! Your workspace is ready.");
      navigate("/");
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        "Could not complete sign-up. Please try again.";
      setError(msg);
    } finally {
      setGoogleLoading(false);
    }
  }

  // Step 2: org name collection for new Google users
  if (googleStep === "org_name") {
    return (
      <form onSubmit={handleGoogleOrgSubmit} className="space-y-4">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            Welcome{googleDisplayName ? `, ${googleDisplayName}` : ""}! One last step — give your workspace a name.
          </p>
        </div>

        <Field
          icon={<Building2 className="h-4 w-4" />}
          type="text"
          placeholder="Agency / Company name"
          value={googleOrgName}
          onChange={setGoogleOrgName}
          autoComplete="organization"
          autoFocus
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
          disabled={googleLoading}
          whileTap={{ scale: 0.98 }}
          className="group relative flex h-11 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-violet to-magenta text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition disabled:opacity-70"
        >
          <span
            aria-hidden
            className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full"
          />
          {googleLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating workspace…
            </>
          ) : (
            <>
              Create workspace
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </>
          )}
        </motion.button>

        <button
          type="button"
          onClick={() => { setGoogleStep(null); setError(null); }}
          className="w-full text-center text-xs text-muted-foreground transition hover:text-foreground"
        >
          ← Go back
        </button>
      </form>
    );
  }

  // Default: email/password form + Google button
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

      {mode === "login" && (
        <div className="text-right">
          <Link
            to="/forgot-password"
            className="text-xs text-muted-foreground transition hover:text-foreground"
          >
            Forgot password?
          </Link>
        </div>
      )}

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

      {/* OR divider */}
      <div className="relative my-1">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-hairline" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-surface-1 px-3 text-xs text-muted-foreground">or</span>
        </div>
      </div>

      {/* Google sign-in button */}
      <motion.button
        type="button"
        disabled={googleLoading}
        whileTap={{ scale: 0.98 }}
        onClick={() => { setGoogleLoading(true); openGooglePopup(); }}
        className="flex h-11 w-full items-center justify-center gap-3 rounded-xl border border-hairline bg-surface-2 text-sm font-medium text-foreground transition hover:bg-surface-3 disabled:opacity-70"
      >
        {googleLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <GoogleIcon />
        )}
        {googleLoading
          ? "Connecting…"
          : mode === "login"
          ? "Continue with Google"
          : "Sign up with Google"}
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

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
      <path
        d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
        fill="#EA4335"
      />
    </svg>
  );
}

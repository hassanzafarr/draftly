import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, XCircle, Users, ArrowRight, Lock } from "lucide-react";
import { toast } from "react-hot-toast";
import { AuthShell } from "../components/AuthShell";
import api from "../api/client";
import useAuthStore from "../store/auth";

export default function AcceptInvite() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fetchMe = useAuthStore((s) => s.fetchMe);
  const token = searchParams.get("token") || "";

  const [state, setState] = useState("loading"); // loading | ready | invalid
  const [invite, setInvite] = useState(null);
  const [message, setMessage] = useState("");

  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setMessage("Invalid invitation link. Please check the link in your email.");
      setState("invalid");
      return;
    }
    api
      .get(`/auth/invites/${token}/`)
      .then((res) => {
        setInvite(res.data);
        setState("ready");
      })
      .catch((err) => {
        setMessage(err.response?.data?.detail || "This invitation is invalid or has expired.");
        setState("invalid");
      });
  }, [token]);

  const handleAccept = async (e) => {
    e.preventDefault();
    if (password !== confirmPw) {
      toast.error("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (!termsAccepted) {
      toast.error("Please accept the Terms of Service.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/auth/invites/accept/", {
        token,
        password,
        terms_accepted: termsAccepted,
      });
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      await fetchMe();
      toast.success(`Welcome to ${invite.org_name}!`);
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not accept the invitation.");
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Join your team"
      subtitle={
        state === "ready"
          ? `You've been invited to ${invite.org_name}`
          : state === "loading"
            ? "Checking your invitation…"
            : "Something went wrong."
      }
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-foreground transition hover:text-violet">
            Sign in
          </Link>
        </>
      }
    >
      <motion.div key={state} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
        {state === "loading" && (
          <div className="flex justify-center py-6">
            <Loader2 className="h-10 w-10 animate-spin text-violet" />
          </div>
        )}

        {state === "invalid" && (
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <XCircle className="h-10 w-10 text-destructive" />
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {message}
            </p>
          </div>
        )}

        {state === "ready" && (
          <form onSubmit={handleAccept} className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl border border-violet/30 bg-violet/10 px-4 py-3">
              <Users className="h-5 w-5 shrink-0 text-violet" />
              <div className="min-w-0 text-left text-sm">
                <p className="truncate font-medium text-foreground">{invite.org_name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {invite.email} · {invite.role}
                  {invite.invited_by ? ` · invited by ${invite.invited_by}` : ""}
                </p>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-left text-xs font-medium text-muted-foreground">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters"
                className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-left text-xs font-medium text-muted-foreground">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
                placeholder="Re-enter password"
                className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
              />
            </div>

            <label className="flex items-start gap-2 text-left text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 accent-[var(--violet)]"
              />
              <span>
                I agree to the{" "}
                <Link to="/terms" className="text-foreground underline hover:text-violet">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link to="/privacy" className="text-foreground underline hover:text-violet">
                  Privacy Policy
                </Link>
                .
              </span>
            </label>

            <button
              type="submit"
              disabled={submitting || !password || !confirmPw}
              className="group relative flex h-11 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-violet to-magenta text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition disabled:opacity-50"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Lock className="h-4 w-4" />
              )}
              Accept invitation
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </button>
          </form>
        )}
      </motion.div>
    </AuthShell>
  );
}

import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, ArrowRight } from "lucide-react";
import { AuthShell } from "../components/AuthShell";
import api from "../api/client";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const uid = searchParams.get("uid") || "";
  const token = searchParams.get("token") || "";

  const [state, setState] = useState("loading"); // loading | success | error | invalid
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!uid || !token) {
      setState("invalid");
      return;
    }

    api
      .post("/auth/verify-email/", { uid, token })
      .then((res) => {
        setMessage(res.data?.detail || "Email verified.");
        setState("success");
      })
      .catch((err) => {
        setMessage(err.response?.data?.detail || "Verification failed. The link may have expired.");
        setState(err.response?.status === 400 ? "error" : "error");
      });
  }, [uid, token]);

  return (
    <AuthShell
      title="Email verification"
      subtitle={
        state === "loading"
          ? "Verifying your email address…"
          : state === "success"
            ? "Your account is ready."
            : "Something went wrong."
      }
      footer={
        state !== "loading" && (
          <Link
            to="/login"
            className="inline-flex items-center gap-1 font-medium text-foreground transition hover:text-violet"
          >
            Go to sign in
            <ArrowRight className="h-3 w-3" />
          </Link>
        )
      }
    >
      <motion.div
        key={state}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-4 py-2 text-center"
      >
        {state === "loading" && <Loader2 className="h-10 w-10 animate-spin text-violet" />}

        {state === "success" && (
          <>
            <CheckCircle2 className="h-10 w-10 text-emerald-500" />
            <p className="text-sm text-foreground">{message}</p>
            <Link
              to="/login"
              className="group relative flex h-11 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-violet to-magenta text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition"
            >
              <span
                aria-hidden
                className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full"
              />
              Sign in
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
          </>
        )}

        {(state === "error" || state === "invalid") && (
          <>
            <XCircle className="h-10 w-10 text-destructive" />
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {state === "invalid"
                ? "Invalid verification link. Please check the link in your email."
                : message}
            </p>
          </>
        )}
      </motion.div>
    </AuthShell>
  );
}

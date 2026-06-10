import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { createPortal } from "react-dom";
import { Cookie } from "lucide-react";
import { Link } from "react-router-dom";
import { initSentry } from "../instrument";

const CONSENT_KEY = "draftly-cookie-consent";

export default function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(CONSENT_KEY);
    if (stored === "accepted") {
      initSentry();
    } else if (!stored) {
      setVisible(true);
    }
    // "essential" — Sentry stays off, no banner
  }, []);

  function accept() {
    localStorage.setItem(CONSENT_KEY, "accepted");
    initSentry();
    setVisible(false);
  }

  function essential() {
    localStorage.setItem(CONSENT_KEY, "essential");
    setVisible(false);
  }

  return createPortal(
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: "spring", stiffness: 320, damping: 30 }}
          className="fixed bottom-0 left-0 right-0 z-[200] p-4"
        >
          <div
            className="glass-strong relative mx-auto flex max-w-2xl flex-col gap-3 overflow-hidden rounded-2xl border border-hairline p-5 sm:flex-row sm:items-center sm:justify-between"
            style={{ boxShadow: "var(--shadow-panel)" }}
          >
            <div
              className="absolute inset-x-0 top-0 h-[2px]"
              style={{ background: "linear-gradient(90deg, var(--violet), var(--cyan))" }}
            />
            <div className="flex items-start gap-3">
              <Cookie className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "var(--violet)" }} />
              <p className="text-sm text-muted-foreground">
                We use essential cookies for authentication and optional analytics cookies for error
                tracking.{" "}
                <Link
                  to="/privacy"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  Learn more
                </Link>
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                onClick={essential}
                className="rounded-xl border border-hairline bg-surface/60 px-4 py-2 text-sm font-medium text-foreground transition hover:bg-surface-2/80"
              >
                Essential Only
              </button>
              <button
                onClick={accept}
                className="rounded-xl px-4 py-2 text-sm font-semibold text-white transition"
                style={{
                  background: "linear-gradient(135deg, var(--violet), var(--magenta))",
                  boxShadow: "var(--shadow-glow-violet)",
                }}
              >
                Accept All
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}

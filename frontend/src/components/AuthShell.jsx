
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}) {
  return (
    <div className="relative min-h-dvh overflow-hidden">
      <div className="app-backdrop" />
      <div className="stars pointer-events-none absolute inset-0 opacity-40" />

      {/* animated orbs */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -top-32 -left-32 h-[420px] w-[420px] rounded-full"
        style={{ background: "radial-gradient(closest-side, oklch(0.62 0.25 295 / 0.35), transparent 70%)" }}
        animate={{ x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -bottom-32 -right-32 h-[460px] w-[460px] rounded-full"
        style={{ background: "radial-gradient(closest-side, oklch(0.78 0.18 200 / 0.3), transparent 70%)" }}
        animate={{ x: [0, -30, 0], y: [0, -40, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute top-1/3 left-1/2 h-[340px] w-[340px] -translate-x-1/2 rounded-full"
        style={{ background: "radial-gradient(closest-side, oklch(0.7 0.27 340 / 0.22), transparent 70%)" }}
        animate={{ scale: [1, 1.15, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative z-10 flex min-h-dvh items-center justify-center px-4 py-10">
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-[440px]"
        >
          <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
            <span className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-magenta">
              <span
                className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet to-magenta opacity-70 blur-md"
                aria-hidden
              />
              <Sparkles className="relative h-5 w-5 text-white" />
            </span>
            <span className="font-display text-xl font-semibold tracking-tight text-foreground">
              PropoAI
            </span>
          </Link>

          <div
            className="relative overflow-hidden rounded-2xl border border-hairline p-8 backdrop-blur-xl"
            style={{
              background: "var(--surface)",
              boxShadow: "var(--shadow-panel)",
            }}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-x-0 -top-px h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent, oklch(0.78 0.18 200 / 0.6), oklch(0.62 0.25 295 / 0.6), transparent)",
              }}
            />

            <div className="mb-6 text-center">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">
                {title}
              </h1>
              <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
            </div>

            {children}
          </div>

          <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>
        </motion.div>
      </div>
    </div>
  );
}

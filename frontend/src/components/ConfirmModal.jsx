import { useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2, Info, X } from "lucide-react";
import { createPortal } from "react-dom";

/**
 * Reusable confirmation modal with beautiful glassmorphism design.
 *
 * @param {boolean}  open           - Whether the modal is visible
 * @param {function} onClose        - Called when user cancels / clicks outside
 * @param {function} onConfirm      - Called when user confirms
 * @param {string}   title          - Modal heading (e.g. "Delete Proposal")
 * @param {string}   description    - Body text explaining the action
 * @param {string}   confirmText    - Label for the confirm button (default "Confirm")
 * @param {string}   cancelText     - Label for the cancel button  (default "Cancel")
 * @param {"destructive"|"default"} variant - Color scheme
 * @param {React.ReactNode} icon    - Optional custom icon override
 * @param {boolean}  loading        - If true, disables buttons and shows spinner
 */
export default function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title = "Are you sure?",
  description = "This action cannot be undone.",
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "destructive",
  icon,
  loading = false,
}) {
  const overlayRef = useRef(null);
  const confirmBtnRef = useRef(null);

  // Close on Escape
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Escape" && !loading) onClose();
    },
    [onClose, loading],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      // Focus confirm button for accessibility
      setTimeout(() => confirmBtnRef.current?.focus(), 80);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleKeyDown]);

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const isDestructive = variant === "destructive";

  const DefaultIcon = isDestructive ? Trash2 : Info;
  const resolvedIcon = icon ?? <DefaultIcon className="h-6 w-6" />;

  const modal = (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={overlayRef}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => {
            if (e.target === overlayRef.current && !loading) onClose();
          }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          style={{ background: "oklch(0 0 0 / 0.55)", backdropFilter: "blur(6px)" }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 16 }}
            transition={{ type: "spring", stiffness: 380, damping: 28 }}
            className="relative w-full max-w-[420px] overflow-hidden rounded-2xl"
            style={{
              background: "linear-gradient(180deg, var(--glass-strong-top), var(--glass-strong-bottom))",
              backdropFilter: "blur(22px) saturate(150%)",
              border: "1px solid var(--hairline-strong)",
              boxShadow: "var(--shadow-panel)",
            }}
          >
            {/* Decorative gradient bar at top */}
            <div
              className="absolute inset-x-0 top-0 h-[2px]"
              style={{
                background: isDestructive
                  ? "linear-gradient(90deg, var(--destructive), var(--amber))"
                  : "linear-gradient(90deg, var(--violet), var(--cyan))",
              }}
            />

            {/* Close button */}
            <button
              onClick={onClose}
              disabled={loading}
              className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition hover:bg-surface-2/80 hover:text-foreground disabled:opacity-40"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="px-6 pb-6 pt-7">
              {/* Icon */}
              <div className="flex justify-center">
                <motion.div
                  initial={{ scale: 0, rotate: -20 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20, delay: 0.08 }}
                  className="flex h-14 w-14 items-center justify-center rounded-2xl"
                  style={{
                    background: isDestructive
                      ? "color-mix(in oklab, var(--destructive) 18%, transparent)"
                      : "color-mix(in oklab, var(--violet) 18%, transparent)",
                    boxShadow: isDestructive
                      ? "0 0 30px -6px var(--destructive)"
                      : "0 0 30px -6px var(--violet)",
                    color: isDestructive ? "var(--destructive)" : "var(--violet)",
                  }}
                >
                  {resolvedIcon}
                </motion.div>
              </div>

              {/* Title */}
              <h2 className="mt-5 text-center font-display text-lg font-bold tracking-tight text-foreground">
                {title}
              </h2>

              {/* Description */}
              <p className="mx-auto mt-2 max-w-[320px] text-center text-sm leading-relaxed text-muted-foreground">
                {description}
              </p>

              {/* Actions */}
              <div className="mt-7 flex items-center gap-3">
                <button
                  onClick={onClose}
                  disabled={loading}
                  className="flex-1 rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm font-medium text-foreground transition hover:border-foreground/20 hover:bg-surface-2/80 disabled:opacity-40"
                >
                  {cancelText}
                </button>

                <button
                  ref={confirmBtnRef}
                  onClick={onConfirm}
                  disabled={loading}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition disabled:opacity-60"
                  style={{
                    background: isDestructive
                      ? "linear-gradient(135deg, var(--destructive), color-mix(in oklab, var(--destructive) 75%, var(--amber)))"
                      : "linear-gradient(135deg, var(--violet), var(--magenta))",
                    boxShadow: isDestructive
                      ? "0 0 24px -4px var(--destructive)"
                      : "var(--shadow-glow-violet)",
                  }}
                >
                  {loading && (
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                      className="inline-block h-4 w-4 rounded-full border-2 border-white/30 border-t-white"
                    />
                  )}
                  {confirmText}
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return createPortal(modal, document.body);
}

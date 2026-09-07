import { useState, useEffect, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  X,
  Brain,
  FileText,
  Zap,
  CheckCircle2,
  Download,
  Database,
  ChevronRight,
  Check,
  Wand2,
} from "lucide-react";

export const DEMO_TOUR_STORAGE_KEY = "draftly_demo_tour_seen";

const SLIDES = [
  {
    id: "welcome",
    badge: "Demo Sandbox • Guided Tour",
    badgeColor: "violet",
    title: "Turn Complex RFPs into Winning Proposals",
    subtitle: "Welcome to Draftly — your AI-powered proposal co-pilot.",
    description:
      "You are in a fully functional demo sandbox. Draftly connects your organization's domain knowledge, past proposals, and case studies to Claude and Gemini to draft structured, bespoke proposals in seconds instead of days.",
    highlights: [
      "Pre-seeded with real-world enterprise documents",
      "AI grounds every response in verified corporate context",
      "Daily proposal credits available to test generation",
    ],
    previewType: "pipeline",
  },
  {
    id: "knowledge-base",
    badge: "Step 2 of 5 • Ground Truth",
    badgeColor: "cyan",
    title: "Knowledge Base & Semantic RAG",
    subtitle: "Say goodbye to hallucinated proposals.",
    description:
      "Draftly automatically parses, chunks, and embeds your organization's past winning proposals, case studies, and compliance sheets into a high-speed pgvector database. When a new RFP arrives, we semantically match the most relevant proof points.",
    highlights: [
      "Curated demo documents pre-indexed & ready to search",
      "Automatic chunking with 768-dim vector embeddings",
      "Cohere reranking for ultra-high precision citation",
    ],
    previewType: "knowledge",
  },
  {
    id: "generator",
    badge: "Step 3 of 5 • The Generator",
    badgeColor: "magenta",
    title: "1-Click AI Proposal Generation",
    subtitle: "From client requirements to full draft in 60 seconds.",
    description:
      "Paste your client's RFP prompt, pick from industry templates (IT Services, Web App, SOW, Consulting), and dial in your desired tone (Persuasive, Technical, Formal) and depth (Concise to Comprehensive). Watch the live ticker compose your proposal in real time.",
    highlights: [
      "Multi-template support with dynamic section schemas",
      "Adjustable voice, tone, and paragraph depth controls",
      "Live transparent AI generation stage tracking",
    ],
    previewType: "generator",
  },
  {
    id: "editor",
    badge: "Step 4 of 5 • Structured Output",
    badgeColor: "emerald",
    title: "10-Section Structured Proposal Editor",
    subtitle: "Complete, compliant, and ready for your team's polish.",
    description:
      "Draftly produces an exhaustive 10-section response — including Executive Summary, Technical Architecture, Methodology, Pricing, and Team Credentials. Edit inline with TipTap or trigger targeted section regenerations with one click.",
    highlights: [
      "Complete 10-section industry-standard layout",
      "TipTap rich-text editor with instant formatting",
      "Per-section AI rewrite and tone adjustment tools",
    ],
    previewType: "editor",
  },
  {
    id: "export",
    badge: "Step 5 of 5 • Finish & Win",
    badgeColor: "amber",
    title: "Branded PDF Export & Next Steps",
    subtitle: "Export ready-to-sign proposals and track your pipeline.",
    description:
      "Export high-resolution branded PDFs with a single click. When you're ready to upload your organization's proprietary documents and invite your teammates, sign up for your dedicated workspace.",
    highlights: [
      "One-click professional PDF export with custom styling",
      "Built-in proposal win-rate and turnaround analytics",
      "Seamless upgrade to upload your own private documents",
    ],
    previewType: "export",
  },
];

export function DemoOnboardingModal({ open, onClose, onAction }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const modalRef = useRef(null);

  const slide = SLIDES[currentSlide];
  const isFirst = currentSlide === 0;
  const isLast = currentSlide === SLIDES.length - 1;

  const handleNext = useCallback(() => {
    if (!isLast) {
      setCurrentSlide((prev) => prev + 1);
    } else {
      localStorage.setItem(DEMO_TOUR_STORAGE_KEY, "true");
      onClose();
    }
  }, [isLast, onClose]);

  const handlePrev = useCallback(() => {
    if (!isFirst) {
      setCurrentSlide((prev) => prev - 1);
    }
  }, [isFirst]);

  const handleDismiss = useCallback(() => {
    localStorage.setItem(DEMO_TOUR_STORAGE_KEY, "true");
    onClose();
  }, [onClose]);

  const handleStartGenerating = useCallback(() => {
    localStorage.setItem(DEMO_TOUR_STORAGE_KEY, "true");
    onClose();
    if (onAction) {
      onAction("generate");
    }
  }, [onClose, onAction]);

  // Reset to first slide when reopened
  useEffect(() => {
    if (open) {
      setCurrentSlide(0);
    }
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e) {
      if (e.key === "Escape") {
        handleDismiss();
      } else if (e.key === "ArrowRight") {
        handleNext();
      } else if (e.key === "ArrowLeft") {
        handlePrev();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, handleDismiss, handleNext, handlePrev]);

  // Lock body scroll
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

  if (typeof document === "undefined") return null;

  const getBadgeClasses = (color) => {
    switch (color) {
      case "cyan":
        return "bg-cyan/15 text-cyan ring-1 ring-cyan/40";
      case "magenta":
        return "bg-magenta/15 text-magenta ring-1 ring-magenta/40";
      case "emerald":
        return "bg-emerald/15 text-emerald ring-1 ring-emerald/40";
      case "amber":
        return "bg-amber/15 text-amber ring-1 ring-amber/40";
      default:
        return "bg-violet/15 text-violet ring-1 ring-violet/40";
    }
  };

  const modal = (
    <AnimatePresence>
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="demo-tour-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
        >
          {/* Backdrop with dark blur and vignette */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={handleDismiss}
            className="absolute inset-0 bg-background/85 backdrop-blur-xl"
          />

          {/* Glowing ambient radial halos */}
          <div className="pointer-events-none absolute -top-40 -left-40 h-96 w-96 rounded-full bg-violet/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-cyan/20 blur-3xl" />

          {/* Modal Container */}
          <motion.div
            ref={modalRef}
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 12 }}
            transition={{ type: "spring", damping: 26, stiffness: 320 }}
            className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-hairline bg-surface/95 shadow-2xl backdrop-blur-2xl"
            style={{
              boxShadow: "var(--shadow-panel)",
            }}
          >
            {/* Top Bar: Progress & Close */}
            <div className="flex items-center justify-between border-b border-hairline px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet/15 text-violet ring-1 ring-violet/30">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
                    Draftly Demo Tutorial
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    Step {currentSlide + 1} of {SLIDES.length}
                  </span>
                </div>
              </div>

              {/* Progress dots */}
              <div className="hidden items-center gap-2 sm:flex">
                {SLIDES.map((s, idx) => (
                  <button
                    key={s.id}
                    onClick={() => setCurrentSlide(idx)}
                    aria-label={`Go to slide ${idx + 1}: ${s.title}`}
                    className={`h-2 rounded-full transition-all duration-300 ${
                      idx === currentSlide
                        ? "w-7 bg-violet shadow-sm shadow-violet/50"
                        : "w-2 bg-hairline hover:bg-muted-foreground/50"
                    }`}
                  />
                ))}
              </div>

              {/* Close Button */}
              <button
                onClick={handleDismiss}
                aria-label="Close tutorial"
                className="flex h-8 w-8 items-center justify-center rounded-xl border border-hairline text-muted-foreground transition hover:border-hairline hover:bg-surface-2 hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Top Progress Line */}
            <div className="h-0.5 w-full bg-hairline">
              <motion.div
                className="h-full bg-gradient-to-r from-violet via-cyan to-magenta"
                initial={false}
                animate={{ width: `${((currentSlide + 1) / SLIDES.length) * 100}%` }}
                transition={{ ease: "easeInOut", duration: 0.3 }}
              />
            </div>

            {/* Slide Body */}
            <div className="p-6 sm:p-8">
              <AnimatePresence mode="wait">
                <motion.div
                  key={slide.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.24, ease: "easeOut" }}
                  className="grid grid-cols-1 gap-8 md:grid-cols-12 md:items-center"
                >
                  {/* Left Column: Text & Features */}
                  <div className="flex flex-col md:col-span-6 lg:col-span-7">
                    <div className="mb-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${getBadgeClasses(
                          slide.badgeColor
                        )}`}
                      >
                        <Zap className="h-3 w-3" />
                        {slide.badge}
                      </span>
                    </div>

                    <h2
                      id="demo-tour-title"
                      className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
                    >
                      {slide.title}
                    </h2>
                    <p className="mt-1 text-sm font-medium text-cyan">{slide.subtitle}</p>

                    <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                      {slide.description}
                    </p>

                    {/* Bullet Points */}
                    <div className="mt-6 space-y-2.5">
                      {slide.highlights.map((highlight, i) => (
                        <div key={i} className="flex items-start gap-2.5 text-xs text-foreground">
                          <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-violet/20 text-violet">
                            <Check className="h-2.5 w-2.5 stroke-[3]" />
                          </span>
                          <span>{highlight}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Right Column: Visual Mockup Widget */}
                  <div className="flex items-center justify-center md:col-span-6 lg:col-span-5">
                    <div className="w-full max-w-sm rounded-2xl border border-hairline bg-surface-2/70 p-4 shadow-xl ring-1 ring-hairline backdrop-blur-md">
                      <SlideVisualPreview type={slide.previewType} />
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Bottom Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline bg-surface-2/40 px-6 py-4 sm:px-8">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDismiss}
                  className="text-xs font-medium text-muted-foreground transition hover:text-foreground"
                >
                  Skip tutorial
                </button>
                <span className="text-muted-foreground/30">•</span>
                <span className="text-xs text-muted-foreground">
                  Press{" "}
                  <kbd className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-foreground ring-1 ring-hairline">
                    Esc
                  </kbd>{" "}
                  to exit
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {!isFirst && (
                  <button
                    onClick={handlePrev}
                    className="flex items-center gap-1.5 rounded-xl border border-hairline bg-surface px-3.5 py-2 text-xs font-medium text-foreground transition hover:bg-surface-2 active:scale-95"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    Back
                  </button>
                )}

                {!isLast ? (
                  <button
                    onClick={handleNext}
                    className="flex items-center gap-2 rounded-xl bg-violet px-4 py-2 text-xs font-medium text-white shadow-md shadow-violet/30 transition hover:bg-violet/90 active:scale-95"
                  >
                    Next
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={handleStartGenerating}
                    className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-violet/30 transition hover:opacity-95 active:scale-95"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Start Exploring Demo
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );

  return createPortal(modal, document.body);
}

/**
 * Custom Visual Mockups for each slide illustrating Draftly features.
 */
function SlideVisualPreview({ type }) {
  switch (type) {
    case "pipeline":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono text-[11px] uppercase tracking-wider text-violet">
              RAG Pipeline
            </span>
            <span className="rounded-full bg-emerald/15 px-2 py-0.5 text-[10px] font-medium text-emerald ring-1 ring-emerald/30">
              Active Sandbox
            </span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-3 rounded-xl border border-hairline bg-surface/80 p-2.5 text-xs">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet/20 text-violet">
                <FileText className="h-4 w-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">RFP Requirements</span>
                <span className="text-[10px] text-muted-foreground">Fintech Redesign RFP</span>
              </div>
            </div>

            <div className="flex justify-center text-muted-foreground">
              <ChevronRight className="h-4 w-4 rotate-90 text-violet" />
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-cyan/30 bg-cyan/10 p-2.5 text-xs ring-1 ring-cyan/20">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan/20 text-cyan">
                <Database className="h-4 w-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">pgvector Semantic Match</span>
                <span className="text-[10px] text-cyan">3 Relevant Docs Embedded</span>
              </div>
            </div>

            <div className="flex justify-center text-muted-foreground">
              <ChevronRight className="h-4 w-4 rotate-90 text-magenta" />
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-magenta/30 bg-magenta/10 p-2.5 text-xs ring-1 ring-magenta/20">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-magenta/20 text-magenta">
                <Wand2 className="h-4 w-4" />
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">10-Section AI Draft</span>
                <span className="text-[10px] text-magenta">Tailored Proposal Generated</span>
              </div>
            </div>
          </div>
        </div>
      );

    case "knowledge":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono text-[11px] uppercase tracking-wider text-cyan">
              Pre-Indexed Assets
            </span>
            <span className="rounded-full bg-cyan/15 px-2 py-0.5 text-[10px] font-medium text-cyan ring-1 ring-cyan/30">
              pgvector Ready
            </span>
          </div>

          <div className="space-y-2">
            {[
              {
                title: "Fintech Platform Case Study.pdf",
                chunks: "14 chunks",
                match: "98% match",
                color: "text-emerald",
              },
              {
                title: "Enterprise Cloud Capabilities.docx",
                chunks: "22 chunks",
                match: "94% match",
                color: "text-cyan",
              },
              {
                title: "Security & SOC2 Compliance.pdf",
                chunks: "9 chunks",
                match: "91% match",
                color: "text-violet",
              },
            ].map((doc, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-hairline bg-surface/80 p-2.5 text-xs transition hover:border-cyan/40"
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Brain className="h-4 w-4 shrink-0 text-cyan" />
                  <span className="truncate font-medium text-foreground">{doc.title}</span>
                </div>
                <span className={`shrink-0 font-mono text-[10px] font-medium ${doc.color}`}>
                  {doc.match}
                </span>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-hairline bg-surface/60 p-2 text-center text-[10px] text-muted-foreground">
            🔒 In demo mode, documents are read-only. Create your own org to upload custom docs.
          </div>
        </div>
      );

    case "generator":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono text-[11px] uppercase tracking-wider text-magenta">
              Smart Controls
            </span>
            <span className="rounded-full bg-magenta/15 px-2 py-0.5 text-[10px] font-medium text-magenta ring-1 ring-magenta/30">
              Live Preview
            </span>
          </div>

          <div className="space-y-2 rounded-xl border border-hairline bg-surface/90 p-3">
            <div className="flex items-center justify-between border-b border-hairline pb-2 text-[11px]">
              <span className="text-muted-foreground">Template:</span>
              <span className="font-medium text-foreground">IT Services & Cloud</span>
            </div>

            <div className="flex items-center justify-between border-b border-hairline pb-2 text-[11px]">
              <span className="text-muted-foreground">Tone:</span>
              <span className="rounded bg-violet/20 px-1.5 py-0.5 font-medium text-violet">
                Persuasive
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Depth:</span>
              <span className="font-medium text-foreground">Standard (2 paras)</span>
            </div>
          </div>

          <div className="rounded-xl border border-hairline bg-surface/50 p-2.5">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Live Stage Ticker
            </span>
            <div className="mt-1 flex items-center gap-2 text-xs font-medium text-cyan">
              <span className="h-2 w-2 animate-ping rounded-full bg-cyan" />
              <span>Drafting all 10 proposal sections…</span>
            </div>
          </div>
        </div>
      );

    case "editor":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono text-[11px] uppercase tracking-wider text-emerald">
              10-Section Outline
            </span>
            <span className="rounded-full bg-emerald/15 px-2 py-0.5 text-[10px] font-medium text-emerald ring-1 ring-emerald/30">
              Rich TipTap
            </span>
          </div>

          <div className="space-y-1.5">
            {[
              { num: "01", name: "Executive Summary", status: "Ready" },
              { num: "02", name: "Client Understanding", status: "Ready" },
              { num: "03", name: "Technical Architecture", status: "Ready" },
              { num: "04", name: "Methodology & Timeline", status: "Ready" },
              { num: "05", name: "Commercials & Pricing", status: "Ready" },
            ].map((sec, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-hairline bg-surface/70 px-2.5 py-1.5 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-muted-foreground">{sec.num}</span>
                  <span className="font-medium text-foreground">{sec.name}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3 w-3 text-emerald" />
                  <span className="text-[10px] text-emerald">{sec.status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-center gap-1.5 rounded-lg border border-violet/30 bg-violet/10 py-1.5 text-[11px] font-medium text-violet">
            <Sparkles className="h-3 w-3" />
            <span>Inline AI Section Rewriter Available</span>
          </div>
        </div>
      );

    case "export":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono text-[11px] uppercase tracking-wider text-amber">
              Ready to Win
            </span>
            <span className="rounded-full bg-amber/15 px-2 py-0.5 text-[10px] font-medium text-amber ring-1 ring-amber/30">
              Export Ready
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col rounded-xl border border-hairline bg-surface/90 p-2.5">
              <span className="text-[10px] text-muted-foreground">Win Rate</span>
              <span className="font-display text-lg font-bold text-foreground">67%</span>
              <span className="text-[9px] text-emerald">↑ +12% this quarter</span>
            </div>
            <div className="flex flex-col rounded-xl border border-hairline bg-surface/90 p-2.5">
              <span className="text-[10px] text-muted-foreground">Turnaround</span>
              <span className="font-display text-lg font-bold text-foreground">2.4 hrs</span>
              <span className="text-[9px] text-cyan">vs 3 days manual</span>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-emerald/30 bg-emerald/10 p-3 ring-1 ring-emerald/20">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald/20 text-emerald">
              <Download className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-foreground">1-Click PDF Export</span>
              <span className="text-[10px] text-muted-foreground">
                Formatted with your brand typography & tables
              </span>
            </div>
          </div>
        </div>
      );

    default:
      return null;
  }
}
export default DemoOnboardingModal;

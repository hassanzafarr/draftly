import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-hot-toast";
import {
  ArrowLeft, Save, Download, RefreshCw,
  Sparkles, Check, FileText, Loader2, AlertCircle, FileCheck2,
} from "lucide-react";
import jsPDF from "jspdf";
import api from "../api/client";

const SECTION_ORDER = [
  "executive_summary", "understanding_requirements", "proposed_solution",
  "relevant_experience", "team_qualifications", "project_timeline",
  "methodology", "pricing", "why_us", "appendix",
];

const SECTION_LABELS = {
  executive_summary: "Executive Summary",
  understanding_requirements: "Understanding of Requirements",
  proposed_solution: "Proposed Solution / Technical Approach",
  relevant_experience: "Relevant Experience & Case Studies",
  team_qualifications: "Team & Qualifications",
  project_timeline: "Project Timeline",
  methodology: "Methodology",
  pricing: "Pricing / Commercial Proposal",
  why_us: "Why Us",
  appendix: "Appendix / Supporting Materials",
};

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [proposal, setProposal] = useState(null);
  const [sections, setSections] = useState({});
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);
  const [regeneratingId, setRegeneratingId] = useState(null);
  const [activeId, setActiveId] = useState(SECTION_ORDER[0]);
  const sectionRefs = useRef({});
  const pollRef = useRef(null);

  const fetchProposal = useCallback(async () => {
    const { data } = await api.get(`/proposals/${id}/`);
    setProposal(data);
    if (data.sections) setSections(data.sections);
    return data;
  }, [id]);

  useEffect(() => {
    fetchProposal()
      .then((data) => {
        if (data.status === "generating") {
          pollRef.current = setInterval(async () => {
            const updated = await fetchProposal();
            if (updated.status !== "generating") clearInterval(pollRef.current);
          }, 3000);
        }
      })
      .catch(() => toast.error("Failed to load proposal."));
    return () => clearInterval(pollRef.current);
  }, [fetchProposal]);

  // Active section tracking on scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (!visible.length) return;
        const top = visible.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        const key = top.target.getAttribute("data-section-key");
        if (key) setActiveId(key);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: 0 },
    );
    Object.values(sectionRefs.current).forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, [proposal]);

  const handleSave = async (finalize = false) => {
    setSaving(true);
    try {
      await api.patch(`/proposals/${id}/`, {
        sections,
        ...(finalize ? { status: "final" } : {}),
      });
      setSavedAt(new Date().toLocaleTimeString());
      toast.success(finalize ? "Proposal finalized!" : "Changes saved.");
      if (finalize) fetchProposal();
    } catch {
      toast.error("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerate = async (sectionKey = null) => {
    const msg = sectionKey
      ? `Regenerate the "${SECTION_LABELS[sectionKey]}" section? This will replace its current content.`
      : "Regenerate the full proposal? All edits will be replaced.";
    if (!window.confirm(msg)) return;

    if (sectionKey) {
      setRegeneratingId(sectionKey);
    }

    try {
      const { data: newProposal } = await api.post(`/rfps/${proposal.rfp}/generate/`);
      toast.success("Regenerating — you'll be taken to the new draft.");
      navigate(`/proposals/${newProposal.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to regenerate.");
      setRegeneratingId(null);
    }
  };

  const handleDownloadPDF = () => {
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 48;
    const contentWidth = pageWidth - margin * 2;
    let y = margin;

    const ensureSpace = (needed) => {
      if (y + needed > pageHeight - margin) { doc.addPage(); y = margin; }
    };

    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.splitTextToSize(proposal.rfp_title || "Proposal", contentWidth).forEach((line) => {
      ensureSpace(26); doc.text(line, margin, y); y += 24;
    });

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(120);
    doc.text(
      `${proposal.status === "final" ? "Finalized" : "Draft"}  •  ${new Date().toLocaleDateString()}`,
      margin, y,
    );
    y += 24;
    doc.setTextColor(0);

    SECTION_ORDER.forEach((key) => {
      const body = (sections[key] || "").trim();
      if (!body) return;
      ensureSpace(40);
      doc.setFont("helvetica", "bold"); doc.setFontSize(13);
      doc.text(SECTION_LABELS[key], margin, y); y += 18;
      doc.setFont("helvetica", "normal"); doc.setFontSize(11);
      doc.splitTextToSize(body, contentWidth).forEach((line) => {
        ensureSpace(16); doc.text(line, margin, y); y += 15;
      });
      y += 12;
    });

    const safeTitle = (proposal.rfp_title || "proposal").replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    doc.save(`${safeTitle}.pdf`);
    toast.success("PDF downloaded.");
  };

  /* ── Loading ── */
  if (!proposal) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-violet" />
          <p className="text-sm">Loading proposal…</p>
        </div>
      </div>
    );
  }

  /* ── Still generating ── */
  if (proposal.status === "generating") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6">
        <div className="relative flex h-24 w-24 items-center justify-center">
          <span className="radial-pulse absolute h-24 w-24 rounded-full border border-violet/40" />
          <span className="radial-pulse absolute h-24 w-24 rounded-full border border-cyan/40" style={{ animationDelay: "0.8s" }} />
          <div className="relative z-10 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-violet to-magenta shadow-[var(--shadow-glow-violet)]">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
        </div>
        <div className="text-center">
          <p className="font-display text-lg font-semibold text-foreground">Generating your proposal…</p>
          <p className="mt-1 text-sm text-muted-foreground">This usually takes 30–60 seconds.</p>
        </div>
      </div>
    );
  }

  /* ── Failed ── */
  if (proposal.status === "failed") {
    return (
      <div className="flex h-screen items-center justify-center px-4">
        <div className="glass-strong w-full max-w-md rounded-2xl p-8 text-center">
          <AlertCircle className="mx-auto mb-3 h-10 w-10 text-destructive" />
          <p className="font-display font-semibold text-foreground">Generation failed</p>
          <p className="mt-1 text-sm text-muted-foreground">{proposal.error_message || "Something went wrong."}</p>
          <button
            onClick={() => handleRegenerate()}
            className="mx-auto mt-5 flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)]"
          >
            <RefreshCw className="h-4 w-4" /> Try again
          </button>
        </div>
      </div>
    );
  }

  /* ── Editor ── */
  return (
    <div className="grid min-h-dvh grid-cols-1 lg:grid-cols-[260px_1fr]">

      {/* Left section nav */}
      <aside className="sticky top-0 z-10 hidden h-dvh flex-col border-r border-hairline p-5 backdrop-blur-xl lg:flex" style={{ background: "var(--sidebar-bg)" }}>
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-xs text-muted-foreground transition hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to generator
        </button>

        <div className="mt-6 flex-1 overflow-y-auto">
          <p className="font-mono text-[10px] uppercase tracking-widest text-violet">Sections</p>
          <ul className="mt-3 space-y-1">
            {SECTION_ORDER.map((key, i) => {
              const active = activeId === key;
              return (
                <li key={key}>
                  <button
                    onClick={() => sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" })}
                    className={`group relative flex w-full items-start gap-2 rounded-lg px-2 py-2 text-left text-xs transition ${
                      active
                        ? "bg-violet/15 text-foreground"
                        : "text-muted-foreground hover:bg-surface-2/60 hover:text-foreground"
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="ed-sec-pill"
                        className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-gradient-to-b from-violet to-magenta"
                      />
                    )}
                    <span className="font-mono text-[10px] text-cyan">{String(i + 1).padStart(2, "0")}</span>
                    <span className="leading-snug">{SECTION_LABELS[key].split(" / ")[0]}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="mt-4 rounded-xl border border-hairline bg-surface-2/40 p-3 text-[11px] text-muted-foreground">
          <p className="font-medium text-foreground">Tip</p>
          <p className="mt-1">Hover any section to reveal regenerate &amp; edit controls.</p>
        </div>
      </aside>

      {/* Main editor area */}
      <div className="relative">

        {/* Sticky header */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-hairline px-6 py-4 backdrop-blur-xl" style={{ background: "oklch(0 0 0 / 0)" }}>
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-magenta">
              <FileText className="h-4 w-4 text-white" />
            </span>
            <div className="min-w-0">
              <p className="truncate font-display text-base font-semibold text-foreground">
                {proposal.rfp_title || "Untitled Proposal"}
              </p>
              <p className="flex items-center gap-2 text-[11px] text-muted-foreground">
                {proposal.status === "final" ? (
                  <span className="flex items-center gap-1 text-emerald">
                    <FileCheck2 className="h-3 w-3" /> Finalized
                  </span>
                ) : "Draft"}
                {savedAt && (
                  <span className="text-emerald">
                    <Check className="mr-0.5 inline h-3 w-3" />Saved {savedAt}
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => handleRegenerate()}
              className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-3 py-1.5 text-xs text-muted-foreground transition hover:border-violet/40 hover:text-foreground"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Regenerate
            </button>
            <button
              onClick={() => handleSave(false)}
              disabled={saving}
              className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-3 py-1.5 text-xs text-foreground transition hover:border-violet/40 disabled:opacity-50"
            >
              <Save className={`h-3.5 w-3.5 ${saving ? "animate-pulse" : ""}`} />
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              onClick={handleDownloadPDF}
              className="flex items-center gap-1.5 rounded-full bg-gradient-to-r from-violet to-magenta px-4 py-1.5 text-xs font-semibold text-white shadow-[var(--shadow-glow-violet)]"
            >
              <Download className="h-3.5 w-3.5" /> Export PDF
            </button>
            {proposal.status !== "final" && (
              <button
                onClick={() => handleSave(true)}
                disabled={saving}
                className="flex items-center gap-1.5 rounded-full border border-emerald/40 bg-emerald/10 px-3 py-1.5 text-xs font-semibold text-emerald transition hover:bg-emerald/20 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" /> Finalize
              </button>
            )}
          </div>
        </header>

        {/* Section cards */}
        <div className="mx-auto max-w-3xl px-6 py-10">
          <div className="space-y-6">
            {SECTION_ORDER.map((key, i) => (
              <motion.div
                key={key}
                data-section-key={key}
                ref={(el) => { sectionRefs.current[key] = el; }}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="group relative rounded-2xl border border-hairline bg-surface/40 p-5 backdrop-blur-md transition hover:border-violet/30"
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-cyan">{String(i + 1).padStart(2, "0")}</span>
                    <h3 className="font-display text-base font-semibold text-foreground">
                      {SECTION_LABELS[key]}
                    </h3>
                  </div>
                  <button
                    onClick={() => handleRegenerate(key)}
                    disabled={regeneratingId === key}
                    className="flex items-center gap-1 rounded-full border border-hairline bg-surface-2/60 px-2.5 py-1 text-[11px] text-foreground/85 opacity-0 transition hover:border-violet/40 group-hover:opacity-100 disabled:opacity-60"
                  >
                    {regeneratingId === key ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                    Regenerate
                  </button>
                </div>

                <div className="relative">
                  <AnimatePresence>
                    {regeneratingId === key && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-background/60 backdrop-blur-sm"
                      >
                        <div className="flex items-center gap-2 rounded-full border border-violet/40 bg-violet/15 px-3 py-1.5 text-xs text-violet">
                          <Sparkles className="h-3.5 w-3.5 animate-pulse" /> Regenerating…
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <textarea
                    value={sections[key] || ""}
                    onChange={(e) => setSections((s) => ({ ...s, [key]: e.target.value }))}
                    rows={Math.max(4, Math.ceil((sections[key] || "").length / 90))}
                    placeholder={`Write the ${SECTION_LABELS[key]} section…`}
                    className="block w-full resize-none rounded-lg bg-transparent text-sm leading-relaxed text-foreground/90 placeholder:text-muted-foreground/40 focus:outline-none"
                  />
                </div>
              </motion.div>
            ))}
          </div>

          {/* Bottom actions */}
          <div className="mt-10 flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-violet" />
              End of draft
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadPDF}
                className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-4 py-2 text-xs font-medium text-muted-foreground transition hover:border-cyan/40 hover:text-foreground"
              >
                <Download className="h-3.5 w-3.5" /> Export PDF
              </button>
              <button
                onClick={() => handleSave(false)}
                disabled={saving}
                className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-4 py-2 text-xs font-medium text-foreground transition hover:border-violet/40 disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                {saving ? "Saving…" : "Save Draft"}
              </button>
              {proposal.status !== "final" && (
                <button
                  onClick={() => handleSave(true)}
                  disabled={saving}
                  className="flex items-center gap-1.5 rounded-full bg-gradient-to-r from-violet to-magenta px-4 py-2 text-xs font-semibold text-white shadow-[var(--shadow-glow-violet)] disabled:opacity-50"
                >
                  <Check className="h-3.5 w-3.5" /> Finalize
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText, Search, Filter, ChevronRight, Plus, Sparkles,
  Clock, CheckCircle2, AlertCircle, Loader2, Trash2,
} from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../api/client";
import ConfirmModal from "../components/ConfirmModal";

const STATUS_CONFIG = {
  draft:      { label: "Draft",      color: "amber",   icon: Clock },
  final:      { label: "Finalized",  color: "emerald", icon: CheckCircle2 },
  generating: { label: "Generating", color: "violet",  icon: Loader2 },
  failed:     { label: "Failed",     color: "destructive", icon: AlertCircle },
};

const FILTER_OPTIONS = ["All", "Draft", "Final", "Generating", "Failed"];

export default function Proposals() {
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [deleteTarget, setDeleteTarget] = useState(null); // { id, title }
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.get("/proposals/")
      .then(({ data }) => setProposals(data.results || data))
      .catch(() => toast.error("Failed to load proposals."))
      .finally(() => setLoading(false));
  }, []);

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/proposals/${deleteTarget.id}/`);
      setProposals((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      toast.success("Proposal deleted.");
    } catch {
      toast.error("Failed to delete proposal.");
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const filtered = useMemo(() => {
    let result = proposals;
    if (filter !== "All") {
      result = result.filter((p) => p.status === filter.toLowerCase());
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          (p.rfp_title || "").toLowerCase().includes(q) ||
          (p.tone || "").toLowerCase().includes(q),
      );
    }
    return result;
  }, [proposals, filter, search]);

  const counts = useMemo(() => {
    const c = { All: proposals.length };
    FILTER_OPTIONS.slice(1).forEach((f) => {
      c[f] = proposals.filter((p) => p.status === f.toLowerCase()).length;
    });
    return c;
  }, [proposals]);

  return (
    <div className="px-6 py-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between gap-4"
        >
          <div className="flex items-center gap-4">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-magenta shadow-[var(--shadow-glow-violet)]">
              <FileText className="h-6 w-6 text-white" />
            </span>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Proposals
              </h1>
              <p className="text-sm text-muted-foreground">
                {proposals.length} proposal{proposals.length !== 1 ? "s" : ""} total
              </p>
            </div>
          </div>
          <Link
            to="/"
            className="flex items-center gap-2 rounded-full bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition hover:shadow-[var(--shadow-glow-magenta)]"
          >
            <Plus className="h-4 w-4" /> New Proposal
          </Link>
        </motion.header>

        {/* Search + Filters */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search proposals..."
              className="w-full rounded-xl border border-hairline bg-surface/60 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Filter className="h-3.5 w-3.5" /> Status:
            </span>
            {FILTER_OPTIONS.map((f) => {
              const isActive = filter === f;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`relative rounded-full border px-4 py-2 text-xs font-medium transition ${
                    isActive
                      ? "border-transparent text-white"
                      : "border-hairline bg-surface/40 text-foreground/80 hover:border-violet/40 hover:text-foreground"
                  }`}
                >
                  {isActive && (
                    <motion.span
                      layoutId="proposal-filter-pill"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-violet to-cyan shadow-[var(--shadow-glow-violet)]"
                    />
                  )}
                  <span className="relative">{f} ({counts[f] || 0})</span>
                </button>
              );
            })}
          </div>
        </motion.div>

        {/* Content */}
        {loading ? (
          <div className="mt-16 flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-violet" />
            <p className="text-sm text-muted-foreground">Loading proposals…</p>
          </div>
        ) : filtered.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-16 flex flex-col items-center gap-4"
          >
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-surface-2/60 ring-1 ring-hairline">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <p className="font-display text-lg font-semibold text-foreground">
              {search || filter !== "All" ? "No matching proposals" : "No proposals yet"}
            </p>
            <p className="text-sm text-muted-foreground">
              {search || filter !== "All"
                ? "Try adjusting your search or filter."
                : "Generate your first proposal from the Generator page."}
            </p>
            {!search && filter === "All" && (
              <Link
                to="/"
                className="mt-2 flex items-center gap-2 rounded-full bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)]"
              >
                <Sparkles className="h-4 w-4" /> Create First Proposal
              </Link>
            )}
          </motion.div>
        ) : (
          <div className="mt-6 space-y-3">
            <AnimatePresence mode="popLayout">
              {filtered.map((p, i) => {
                const cfg = STATUS_CONFIG[p.status] || STATUS_CONFIG.draft;
                const StatusIcon = cfg.icon;
                const wordCount = p.sections
                  ? Object.values(p.sections).reduce(
                      (sum, s) => sum + (s || "").split(/\s+/).filter(Boolean).length,
                      0,
                    )
                  : 0;

                return (
                  <motion.div
                    key={p.id}
                    layout
                    initial={{ opacity: 0, y: 12, scale: 1 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{
                      layout: { type: "spring", stiffness: 300, damping: 28 },
                      opacity: { delay: i * 0.03 },
                      y: { delay: i * 0.03, type: "spring", stiffness: 220, damping: 24 }
                    }}
                    className="group glass relative w-full overflow-hidden rounded-2xl p-5 transition hover:border-violet/30"
                  >
                    <Link
                      to={`/proposals/${p.id}`}
                      className="flex items-center justify-between gap-4"
                    >
                      <div className="flex min-w-0 items-center gap-4">
                        <span
                          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                          style={{
                            background: `color-mix(in oklab, var(--${cfg.color}) 22%, transparent)`,
                            boxShadow: `0 0 20px -8px var(--${cfg.color})`,
                          }}
                        >
                          <StatusIcon
                            className={`h-5 w-5 ${p.status === "generating" ? "animate-spin" : ""}`}
                            style={{ color: `var(--${cfg.color})` }}
                          />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-display text-base font-semibold text-foreground">
                            {p.rfp_title || "Untitled Proposal"}
                          </p>
                          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                            <span>{new Date(p.created_at).toLocaleDateString()}</span>
                            <span>·</span>
                            <span className="capitalize">{p.tone || "professional"}</span>
                            {wordCount > 0 && (
                              <>
                                <span>·</span>
                                <span>{wordCount.toLocaleString()} words</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setDeleteTarget({ id: p.id, title: p.rfp_title });
                          }}
                          className="flex h-8 w-8 items-center justify-center rounded-lg border border-hairline bg-surface/60 text-muted-foreground opacity-0 transition hover:border-destructive/40 hover:text-destructive group-hover:opacity-100"
                          title="Delete proposal"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                        <span
                          className="rounded-full px-3 py-1 text-xs font-medium"
                          style={{
                            background: `color-mix(in oklab, var(--${cfg.color}) 18%, transparent)`,
                            color: `var(--${cfg.color})`,
                          }}
                        >
                          {cfg.label}
                        </span>
                        <ChevronRight className="h-4 w-4 text-muted-foreground transition group-hover:text-foreground" />
                      </div>
                    </Link>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Proposal"
        description={`Are you sure you want to delete "${deleteTarget?.title || ""}"? This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        loading={deleting}
      />
    </div>
  );
}

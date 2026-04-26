import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Sparkles, Layers, ArrowRight, Filter } from "lucide-react";
import { templates, templateFilters } from "../lib/mock-data";

const accentMap = {
  violet:  { text: "text-violet",  bg: "bg-violet/15",  border: "border-violet/40",  glow: "var(--shadow-glow-violet)",  hex: "var(--violet)"  },
  cyan:    { text: "text-cyan",    bg: "bg-cyan/15",    border: "border-cyan/40",    glow: "var(--shadow-glow-cyan)",    hex: "var(--cyan)"    },
  magenta: { text: "text-magenta", bg: "bg-magenta/15", border: "border-magenta/40", glow: "var(--shadow-glow-magenta)", hex: "var(--magenta)" },
  emerald: { text: "text-emerald", bg: "bg-emerald/15", border: "border-emerald/40", glow: "0 0 40px -8px var(--emerald)", hex: "var(--emerald)" },
  amber:   { text: "text-amber",   bg: "bg-amber/15",   border: "border-amber/40",   glow: "0 0 40px -8px var(--amber)",   hex: "var(--amber)"   },
};

export default function Templates() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState("All");

  const filtered = templates.filter(
    (t) => filter === "All" || t.category === filter.toLowerCase(),
  );

  return (
    <div className="px-8 py-10">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-[var(--shadow-glow-violet)]">
            <FileText className="h-6 w-6 text-white" />
          </span>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Templates
            </h1>
            <p className="text-sm text-muted-foreground">
              Start with a pre-built template to accelerate your proposal creation
            </p>
          </div>
        </motion.header>

        {/* Filter row */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-8 flex items-center gap-3 overflow-x-auto pb-1"
        >
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Filter className="h-3.5 w-3.5" /> Filter:
          </span>
          {templateFilters.map((f) => {
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
                    layoutId="filter-pill"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-violet to-cyan shadow-[var(--shadow-glow-violet)]"
                  />
                )}
                <span className="relative">{f}</span>
              </button>
            );
          })}
        </motion.div>

        {/* Grid */}
        <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {filtered.map((t, i) => {
              const a = accentMap[t.accent];
              return (
                <motion.button
                  key={t.id}
                  layout
                  initial={{ opacity: 0, y: 16, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.96 }}
                  transition={{ delay: i * 0.05, type: "spring", stiffness: 220, damping: 24 }}
                  whileHover={{ y: -6 }}
                  onClick={() => navigate("/")}
                  className="group relative overflow-hidden rounded-2xl border border-hairline bg-surface/60 p-6 text-left backdrop-blur-md transition hover:border-violet/40"
                  style={{ minHeight: 340 }}
                >
                  {/* glow halo */}
                  <span
                    className="pointer-events-none absolute -top-16 -left-16 h-44 w-44 rounded-full opacity-30 blur-3xl transition group-hover:opacity-70"
                    style={{ background: a.hex }}
                  />
                  {/* category chip top-right */}
                  <span
                    className={`absolute right-5 top-5 rounded-full ${a.bg} ${a.text} border ${a.border} px-2.5 py-0.5 text-[10px] font-medium lowercase tracking-wide`}
                  >
                    {t.category}
                  </span>

                  {/* icon */}
                  <span
                    className={`relative flex h-12 w-12 items-center justify-center rounded-xl ${a.bg} border ${a.border}`}
                    style={{ boxShadow: a.glow }}
                  >
                    <Sparkles className={`h-5 w-5 ${a.text}`} />
                  </span>

                  <h3 className="mt-5 font-display text-lg font-semibold text-foreground transition group-hover:text-gradient">
                    {t.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t.snippet}</p>

                  <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                    <Layers className="h-3.5 w-3.5" />
                    {t.sectionsCount} sections included
                  </div>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {t.sections.map((s) => (
                      <span
                        key={s}
                        className="rounded-md border border-hairline bg-surface-2/60 px-2 py-1 text-[10px] text-foreground/80"
                      >
                        {s}
                      </span>
                    ))}
                    <span className="rounded-md border border-hairline bg-surface-2/60 px-2 py-1 text-[10px] text-muted-foreground">
                      +3
                    </span>
                  </div>

                  <div
                    className={`mt-5 flex items-center justify-center gap-2 rounded-xl border ${a.border} ${a.bg} py-2.5 text-xs font-medium ${a.text} transition group-hover:scale-[1.02]`}
                  >
                    Use Template <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                </motion.button>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

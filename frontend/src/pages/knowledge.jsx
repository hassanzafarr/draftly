import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "react-hot-toast";
import {
  UploadCloud, FileText, Brain, CheckCircle2, Loader2,
  Briefcase, Layers, Trash2, FolderOpen, Sparkles, AlertCircle,
} from "lucide-react";
import api from "../api/client";

const CATEGORIES = [
  { id: "Company Profile",  label: "Company Profile",  description: "Brand guidelines, about us, team bios", icon: Briefcase, hex: "var(--cyan)" },
  { id: "Past Proposals",   label: "Past Proposals",   description: "Previously submitted proposals",         icon: Layers,    hex: "var(--magenta)" },
  { id: "Case Studies",     label: "Case Studies",     description: "Success stories and project outcomes",   icon: Briefcase, hex: "var(--emerald)" },
];

function docToUiStatus(status) {
  if (status === "processed") return "Ready";
  if (status === "processing") return "Indexing";
  if (status === "failed") return "Failed";
  return "Processing";
}

export default function Knowledge() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [active, setActive] = useState("Company Profile");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const fetchDocs = useCallback(() => {
    api.get("/documents/")
      .then((r) => setDocs(r.data.results ?? r.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchDocs();
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, [fetchDocs]);

  const handleAdd = async (fileList) => {
    if (!fileList?.length) return;
    setUploading(true);
    const files = Array.from(fileList);
    await Promise.allSettled(
      files.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("title", file.name.replace(/\.[^/.]+$/, ""));
        try {
          await api.post("/documents/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        } catch (err) {
          toast.error(`Failed to upload "${file.name}".`);
        }
      }),
    );
    toast.success(`${files.length > 1 ? `${files.length} files` : "File"} uploaded — processing started.`);
    fetchDocs();
    setUploading(false);
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this document and all its indexed data?")) return;
    try {
      await api.delete(`/documents/${id}/`);
      setDocs((d) => d.filter((doc) => doc.id !== id));
      toast.success("Document deleted.");
    } catch {
      toast.error("Failed to delete document.");
    }
  };

  const totalIndexed = docs.filter((d) => d.status === "processed").length;

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
            <FolderOpen className="h-6 w-6 text-white" />
          </span>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Knowledge Base
            </h1>
            <p className="text-sm text-muted-foreground">
              Feed your company data to enhance AI-generated proposals
            </p>
          </div>
        </motion.header>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* LEFT — Upload + categories */}
          <div className="space-y-6">

            {/* Drop zone */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); handleAdd(e.dataTransfer.files); }}
              onClick={() => !uploading && inputRef.current?.click()}
              className={`group relative flex cursor-pointer flex-col items-center justify-center gap-3 overflow-hidden rounded-2xl border-2 border-dashed bg-surface/40 py-14 text-center backdrop-blur-md transition ${
                dragging
                  ? "scale-[1.01] border-violet bg-violet/10"
                  : "border-hairline hover:border-violet/40"
              } ${uploading ? "cursor-wait opacity-70" : ""}`}
            >
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => handleAdd(e.target.files)}
              />
              <motion.span
                whileHover={{ rotate: 6, scale: 1.05 }}
                className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-[var(--shadow-glow-violet)]"
              >
                {uploading
                  ? <Loader2 className="h-6 w-6 animate-spin text-white" />
                  : <UploadCloud className="h-6 w-6 text-white" />
                }
              </motion.span>
              <p className="text-base font-semibold text-foreground">
                {uploading ? "Uploading…" : "Drag and drop files"}
              </p>
              <p className="text-xs text-muted-foreground">
                {uploading
                  ? "Please wait"
                  : <>or click to browse · PDF, DOCX, TXT · adds to <span className="text-cyan">{active}</span></>
                }
              </p>
              {dragging && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="pointer-events-none absolute inset-0 rounded-2xl ring-2 ring-violet/60"
                />
              )}
            </motion.div>

            {/* Categories */}
            <div>
              <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                Knowledge Categories
              </p>
              <div className="space-y-2">
                {CATEGORIES.map((c, i) => {
                  const isActive = active === c.id;
                  const Icon = c.icon;
                  return (
                    <motion.button
                      key={c.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 + i * 0.07 }}
                      whileHover={{ x: 4 }}
                      onClick={() => setActive(c.id)}
                      className={`flex w-full items-center gap-3 rounded-2xl border bg-surface/60 p-4 text-left backdrop-blur-md transition ${
                        isActive
                          ? "border-violet/50 ring-1 ring-violet/40"
                          : "border-hairline hover:border-violet/30"
                      }`}
                    >
                      <span
                        className="flex h-11 w-11 items-center justify-center rounded-xl"
                        style={{
                          background: `color-mix(in oklab, ${c.hex} 22%, transparent)`,
                          boxShadow: isActive ? `0 0 30px -8px ${c.hex}` : undefined,
                        }}
                      >
                        <Icon className="h-5 w-5" style={{ color: c.hex }} />
                      </span>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-foreground">{c.label}</p>
                        <p className="text-xs text-muted-foreground">{c.description}</p>
                      </div>
                      {isActive && (
                        <motion.span
                          layoutId="cat-dot"
                          className="h-2 w-2 rounded-full bg-violet shadow-[0_0_10px_var(--violet)]"
                        />
                      )}
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* RIGHT — Brain hub + file list */}
          <div className="space-y-6">

            {/* AI brain visualisation */}
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="glass-strong relative flex h-[280px] flex-col items-center justify-center overflow-hidden rounded-2xl"
            >
              <div className="absolute inset-0 stars opacity-40" />
              <div className="absolute h-56 w-56 rounded-full bg-violet/15 blur-3xl" />
              <div className="absolute h-44 w-44 animate-spin rounded-full border border-dashed border-cyan/30 [animation-duration:18s]" />
              <div className="absolute h-32 w-32 animate-spin rounded-full border border-dashed border-magenta/40 [animation-direction:reverse] [animation-duration:12s]" />
              <span className="radial-pulse absolute h-20 w-20 rounded-full border border-violet/40" />
              <span className="radial-pulse absolute h-20 w-20 rounded-full border border-cyan/40" style={{ animationDelay: "1.2s" }} />

              {[...Array(4)].map((_, i) => {
                const positions = [{ x: -110, y: -40 }, { x: 100, y: -50 }, { x: -90, y: 60 }, { x: 105, y: 50 }];
                return (
                  <motion.span
                    key={i}
                    animate={{ x: [positions[i].x, positions[i].x * 0.6, positions[i].x], y: [positions[i].y, positions[i].y * 0.6, positions[i].y] }}
                    transition={{ duration: 4 + i, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute flex h-9 w-9 items-center justify-center rounded-lg border border-hairline bg-surface-2/80 shadow-panel backdrop-blur"
                  >
                    <FileText className="h-4 w-4" style={{ color: ["var(--cyan)", "var(--emerald)", "var(--magenta)", "var(--amber)"][i] }} />
                  </motion.span>
                );
              })}

              <div className="pulse-ring relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-violet to-cyan shadow-[var(--shadow-glow-violet)]">
                <Brain className="h-9 w-9 text-white" />
              </div>
              <motion.p
                key={totalIndexed}
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="relative z-10 mt-6 font-display text-3xl font-bold tabular-nums text-foreground"
              >
                {totalIndexed}
              </motion.p>
              <p className="relative z-10 text-xs text-muted-foreground">Documents Indexed</p>
            </motion.div>

            {/* File list */}
            <div className="glass rounded-2xl p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-violet" />
                  <p className="font-display text-sm font-semibold text-foreground">Uploaded Files</p>
                </div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  {docs.length} total
                </span>
              </div>

              <div className="space-y-2">
                {loading ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader2 className="h-5 w-5 animate-spin text-violet" />
                  </div>
                ) : (
                  <AnimatePresence mode="popLayout">
                    {docs.length === 0 ? (
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="px-3 py-10 text-center text-sm text-muted-foreground"
                      >
                        No files yet. Drop one to feed the brain.
                      </motion.p>
                    ) : (
                      docs.map((doc, i) => {
                        const uiStatus = docToUiStatus(doc.status);
                        return (
                          <motion.div
                            key={doc.id}
                            layout
                            initial={{ opacity: 0, x: -16 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 16 }}
                            transition={{ delay: i * 0.04, type: "spring", stiffness: 260, damping: 26 }}
                            className="group relative overflow-hidden rounded-xl border border-hairline bg-surface/60 p-3"
                          >
                            <div className="flex items-center gap-3">
                              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-magenta/10 ring-1 ring-magenta/40">
                                <FileText className="h-4 w-4 text-magenta" />
                              </span>
                              <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-medium text-foreground">{doc.title}</p>
                                <p className="font-mono text-[10px] text-muted-foreground">
                                  {doc.status === "failed" && doc.error_message
                                    ? doc.error_message
                                    : doc.status}
                                </p>
                              </div>
                              <StatusPill status={uiStatus} />
                              <button
                                onClick={() => handleDelete(doc.id)}
                                aria-label={`Delete ${doc.title}`}
                                className="text-muted-foreground transition hover:text-magenta"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                            {uiStatus !== "Ready" && uiStatus !== "Failed" && (
                              <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-surface-2">
                                <div className="shimmer h-full w-full" />
                              </div>
                            )}
                            {uiStatus === "Failed" && (
                              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-destructive">
                                <AlertCircle className="h-3 w-3" />
                                {doc.error_message || "Processing failed"}
                              </div>
                            )}
                          </motion.div>
                        );
                      })
                    )}
                  </AnimatePresence>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }) {
  if (status === "Ready") return (
    <span className="flex items-center gap-1 rounded-full border border-emerald/40 bg-emerald/10 px-2 py-0.5 text-[10px] font-medium text-emerald">
      <CheckCircle2 className="h-3 w-3" /> Ready
    </span>
  );
  if (status === "Indexing") return (
    <span className="flex items-center gap-1 rounded-full border border-amber/40 bg-amber/10 px-2 py-0.5 text-[10px] font-medium text-amber">
      <Sparkles className="h-3 w-3" /> Indexing
    </span>
  );
  if (status === "Failed") return (
    <span className="flex items-center gap-1 rounded-full border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-[10px] font-medium text-destructive">
      <AlertCircle className="h-3 w-3" /> Failed
    </span>
  );
  return (
    <span className="flex items-center gap-1 rounded-full border border-violet/40 bg-violet/10 px-2 py-0.5 text-[10px] font-medium text-violet">
      <Loader2 className="h-3 w-3 animate-spin" /> Processing
    </span>
  );
}

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
    Paperclip,
    Send,
    X,
    FileText,
    ChevronDown,
    Sparkles,
    ArrowRight,
    Plus,
    Wand2,
} from "lucide-react";
import { toast } from "react-hot-toast";
import { suggestionChips, coreFeatures, tones, sampleProposalSections } from "../lib/mock-data";
import useAuthStore from "../store/auth";
import api from "../api/client";

const thinkingSteps = [
    "Analyzing RFP intent…",
    "Reading uploaded files…",
    "Pulling from your knowledge base…",
    "Structuring proposal sections…",
    "Polishing tone & language…",
];

export function Generator() {
    const [phase, setPhase] = useState("idle");
    const [input, setInput] = useState("");
    const [files, setFiles] = useState([]);
    const [tone, setTone] = useState("Persuasive");
    const [toneOpen, setToneOpen] = useState(false);
    const [stepIdx, setStepIdx] = useState(0);
    const [progress, setProgress] = useState(0);
    const [isDragging, setIsDragging] = useState(false);
    const [proposalId, setProposalId] = useState(null);
    const fileRef = useRef(null);
    const pollRef = useRef(null);
    const navigate = useNavigate();
    const user = useAuthStore((s) => s.user);
    const displayName = user?.email?.split("@")[0] ?? "there";
    const initials = displayName.slice(0, 2).toUpperCase();

    function attach(list) {
        if (!list) return;
        const next = Array.from(list).map((f, i) => ({
            id: `${Date.now()}-${i}`,
            name: f.name,
            size: `${(f.size / 1024).toFixed(0)} KB`,
            file: f,
        }));
        setFiles((p) => [...p, ...next]);
    }

    function removeFile(id) {
        setFiles((p) => p.filter((f) => f.id !== id));
    }

    async function generate() {
        if (!input.trim() && files.length === 0) return;
        setPhase("thinking");
        setStepIdx(0);
        setProgress(0);
        setProposalId(null);

        try {
            const title = input.trim().slice(0, 80) || files[0]?.name?.replace(/\.[^/.]+$/, "") || "Untitled Proposal";
            let rfpPayload = { title, raw_text: input.trim() };
            let rfpConfig;
            if (files[0]?.file) {
                rfpPayload = new FormData();
                rfpPayload.append("title", title);
                rfpPayload.append("raw_text", input.trim());
                rfpPayload.append("file", files[0].file);
                rfpConfig = { headers: { "Content-Type": "multipart/form-data" } };
            }
            const { data: rfp } = await api.post("/rfps/", rfpPayload, rfpConfig);
            toast.success("RFP saved — generating proposal…");
            const { data: proposal } = await api.post(`/rfps/${rfp.id}/generate/`, { tone: tone.toLowerCase() });
            setProposalId(proposal.id);

            pollRef.current = setInterval(async () => {
                try {
                    const { data } = await api.get(`/proposals/${proposal.id}/`);
                    if (data.status === "draft") {
                        clearInterval(pollRef.current);
                        setProgress(100);
                        setTimeout(() => setPhase("result"), 350);
                    } else if (data.status === "failed") {
                        clearInterval(pollRef.current);
                        toast.error("Proposal generation failed. Please try again.");
                        reset();
                    }
                } catch {
                    clearInterval(pollRef.current);
                    toast.error("Lost connection while generating.");
                    reset();
                }
            }, 3000);
        } catch (err) {
            toast.error(err.response?.data?.detail || "Failed to create RFP.");
            reset();
        }
    }

    function reset() {
        clearInterval(pollRef.current);
        setPhase("idle");
        setInput("");
        setFiles([]);
        setProgress(0);
        setStepIdx(0);
        setProposalId(null);
    }

    useEffect(() => {
        if (phase !== "thinking") return;
        const stepTimer = setInterval(() => {
            setStepIdx((i) => Math.min(i + 1, thinkingSteps.length - 1));
        }, 700);
        // cap at 90% — real API drives the final jump to 100%
        const progTimer = setInterval(() => {
            setProgress((p) => {
                if (p >= 90) { clearInterval(progTimer); return 90; }
                return p + 2;
            });
        }, 70);
        return () => {
            clearInterval(stepTimer);
            clearInterval(progTimer);
        };
    }, [phase]);

    useEffect(() => () => clearInterval(pollRef.current), []);

    function openInEditor() {
        if (proposalId) navigate(`/proposals/${proposalId}`);
    }

    return (
        <div
            className="relative flex min-h-dvh flex-col"
            onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                attach(e.dataTransfer.files);
            }}
        >
            {/* Top bar */}
            <header className="flex items-center justify-between px-8 py-5">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="inline-flex h-2 w-2 rounded-full bg-cyan shadow-[0_0_10px_var(--cyan)]" />
                    <span className="font-mono uppercase tracking-widest">Session · live</span>
                </div>
                <div className="flex items-center gap-3">
                    {phase !== "idle" && (
                        <button
                            onClick={reset}
                            className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-3 py-1.5 text-xs text-foreground/85 backdrop-blur hover:border-violet/40"
                        >
                            <Plus className="h-3.5 w-3.5" /> New chat
                        </button>
                    )}
                    <span className="hidden text-sm text-muted-foreground sm:inline">{displayName}</span>
                    <div className="relative h-9 w-9 overflow-hidden rounded-full ring-1 ring-violet/50">
                        <span className="absolute inset-0 bg-gradient-to-br from-violet to-magenta" />
                        <span className="relative z-10 flex h-full w-full items-center justify-center text-xs font-semibold text-white">
                            {initials}
                        </span>
                    </div>
                </div>
            </header>

            {/* Scrollable content area — leaves room for fixed input */}
            <div className="flex flex-1 flex-col items-center px-6 pb-[280px]">
                <AnimatePresence mode="wait">
                    {phase === "idle" && (
                        <motion.div
                            key="hero"
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -12 }}
                            transition={{ duration: 0.5 }}
                            className="mt-8 w-full max-w-3xl text-center"
                        >
                            <p className="font-display text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
                                Welcome back, <span className="text-magenta-gradient">{displayName}</span>
                            </p>
                            <h1 className="mt-6 font-display text-3xl font-semibold tracking-tight text-balance sm:text-5xl">
                                What would you like to <span className="text-gradient">propose</span> today?
                            </h1>
                            <p className="mt-4 text-sm text-muted-foreground sm:text-base">
                                Describe your RFP or attach documents. PropoAI drafts a polished, on-brand proposal in seconds.
                            </p>

                            {/* Suggestion chips */}
                            <motion.div
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 }}
                                className="mx-auto mt-8 flex flex-wrap justify-center gap-2"
                            >
                                {suggestionChips.map((s, i) => (
                                    <motion.button
                                        key={s}
                                        whileHover={{ y: -2 }}
                                        onClick={() => setInput(s)}
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.25 + i * 0.05 }}
                                        className="glass group flex items-center gap-2 rounded-full px-4 py-2 text-xs text-foreground/85 transition hover:text-foreground"
                                    >
                                        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br from-violet/40 to-cyan/40 ring-1 ring-violet/40">
                                            <Sparkles className="h-3 w-3 text-cyan" />
                                        </span>
                                        {s}
                                    </motion.button>
                                ))}
                            </motion.div>

                            {/* Core Features */}
                            <div className="mx-auto mt-10 w-full max-w-4xl text-left">
                                <p className="mb-3 font-display text-sm font-medium text-foreground/90">Core Features</p>
                                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                                    {coreFeatures.map((f, i) => {
                                        const accents = [
                                            { ring: "ring-cyan/40", text: "text-cyan", color: "var(--cyan)" },
                                            { ring: "ring-violet/40", text: "text-violet", color: "var(--violet)" },
                                            { ring: "ring-magenta/40", text: "text-magenta", color: "var(--magenta)" },
                                        ][i % 3];
                                        return (
                                            <FeatureCard
                                                key={f.id}
                                                feature={f}
                                                accents={accents}
                                                index={i}
                                            />
                                        );
                                    })}
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {phase === "thinking" && (
                        <motion.div
                            key="thinking"
                            initial={{ opacity: 0, scale: 0.96 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0 }}
                            className="mt-6 w-full max-w-3xl"
                        >
                            <ThinkingStage files={files} step={thinkingSteps[stepIdx]} progress={progress} />
                        </motion.div>
                    )}

                    {phase === "result" && (
                        <motion.div
                            key="result"
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                            className="mt-8 w-full max-w-3xl"
                        >
                            <ResultCard
                                onOpen={openInEditor}
                                title={input.trim() || "A Phased Path to Outcome-Driven Delivery"}
                                tone={tone}
                            />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* FIXED bottom input */}
            <div className="pointer-events-none fixed bottom-0 left-[78px] right-0 z-30 px-6 pb-6">
                <div className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-48 bg-gradient-to-t from-background via-background/85 to-transparent" />
                <div className="pointer-events-auto mx-auto w-full max-w-4xl">
                    <div className={`input-ring relative shadow-panel transition ${isDragging ? "scale-[1.01]" : ""}`}>
                        <div className="relative rounded-[17px] p-4" style={{ background: "var(--input-bg)" }}>
                            {/* file chips */}
                            {files.length > 0 && (
                                <div className="mb-3 flex flex-wrap gap-2">
                                    <AnimatePresence>
                                        {files.map((f) => (
                                            <motion.div
                                                key={f.id}
                                                layout
                                                initial={{ opacity: 0, scale: 0.85, y: 4 }}
                                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                                exit={{ opacity: 0, scale: 0.85, y: -4 }}
                                                className="group flex items-center gap-2 rounded-full border border-violet/40 bg-violet/10 px-3 py-1.5 text-xs"
                                            >
                                                <FileText className="h-3.5 w-3.5 text-violet" />
                                                <span className="max-w-[180px] truncate text-foreground">{f.name}</span>
                                                <span className="text-muted-foreground">{f.size}</span>
                                                <button
                                                    aria-label={`Remove ${f.name}`}
                                                    onClick={() => removeFile(f.id)}
                                                    className="ml-1 text-muted-foreground hover:text-magenta"
                                                >
                                                    <X className="h-3.5 w-3.5" />
                                                </button>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>
                                </div>
                            )}

                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                rows={2}
                                placeholder="Describe the proposal you need… or drop a PDF/DOCX RFP here."
                                className="block w-full resize-none bg-transparent text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none sm:text-base"
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate();
                                }}
                                disabled={phase === "thinking"}
                            />

                            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-3">
                                <div className="flex items-center gap-2">
                                    <div className="relative">
                                        <button
                                            onClick={() => setToneOpen((v) => !v)}
                                            className="flex items-center gap-2 rounded-full border border-hairline bg-surface-2/60 px-3 py-1.5 text-xs text-foreground hover:border-violet/40"
                                        >
                                            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                                                Tone
                                            </span>
                                            <span className="font-medium">{tone}</span>
                                            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                                        </button>
                                        <AnimatePresence>
                                            {toneOpen && (
                                                <motion.ul
                                                    initial={{ opacity: 0, y: 6 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    exit={{ opacity: 0, y: 6 }}
                                                    className="glass-strong absolute bottom-full left-0 z-20 mb-2 w-44 overflow-hidden rounded-xl p-1 text-sm shadow-panel"
                                                >
                                                    {tones.map((t) => (
                                                        <li key={t}>
                                                            <button
                                                                onClick={() => {
                                                                    setTone(t);
                                                                    setToneOpen(false);
                                                                }}
                                                                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition hover:bg-violet/15 ${t === tone ? "text-cyan" : "text-foreground/85"
                                                                    }`}
                                                            >
                                                                {t}
                                                                {t === tone && (
                                                                    <span className="h-1.5 w-1.5 rounded-full bg-cyan shadow-[0_0_8px_var(--cyan)]" />
                                                                )}
                                                            </button>
                                                        </li>
                                                    ))}
                                                </motion.ul>
                                            )}
                                        </AnimatePresence>
                                    </div>

                                    <span className="hidden rounded-full border border-hairline bg-surface-2/60 px-3 py-1.5 text-xs text-muted-foreground sm:inline-flex">
                                        <span className="font-mono text-[10px] uppercase tracking-widest">Industry · Tech</span>
                                    </span>
                                </div>

                                <div className="flex items-center gap-2">
                                    <input
                                        ref={fileRef}
                                        type="file"
                                        multiple
                                        className="hidden"
                                        onChange={(e) => attach(e.target.files)}
                                    />
                                    <button
                                        onClick={() => fileRef.current?.click()}
                                        aria-label="Attach files"
                                        className="flex h-10 w-10 items-center justify-center rounded-full border border-magenta/40 bg-magenta/10 text-magenta transition hover:bg-magenta/20"
                                    >
                                        <Paperclip className="h-4 w-4" />
                                    </button>
                                    <motion.button
                                        whileTap={{ scale: 0.94 }}
                                        onClick={generate}
                                        disabled={phase === "thinking"}
                                        className="group relative flex items-center gap-2 overflow-hidden rounded-full bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] transition hover:shadow-[var(--shadow-glow-magenta)] disabled:opacity-60"
                                    >
                                        {phase === "thinking" ? (
                                            <>
                                                <Wand2 className="h-4 w-4 animate-pulse" /> Generating…
                                            </>
                                        ) : (
                                            <>
                                                <Send className="h-4 w-4" /> Generate
                                            </>
                                        )}
                                    </motion.button>
                                </div>
                            </div>
                        </div>
                        {isDragging && (
                            <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-[18px] bg-violet/10 text-sm font-medium text-violet">
                                Drop files to attach
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

/* ============ FEATURE CARD ============ */

function FeatureCard({ feature, accents, index }) {
    const ref = useRef(null);
    const [glow, setGlow] = useState({ x: 50, y: 50, active: false });

    function handleMove(e) {
        const rect = ref.current?.getBoundingClientRect();
        if (!rect) return;
        setGlow({
            x: ((e.clientX - rect.left) / rect.width) * 100,
            y: ((e.clientY - rect.top) / rect.height) * 100,
            active: true,
        });
    }

    return (
        <motion.div
            ref={ref}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + index * 0.08 }}
            whileHover={{ y: -4 }}
            onMouseMove={handleMove}
            onMouseLeave={() => setGlow((g) => ({ ...g, active: false }))}
            className={`glass group relative cursor-pointer overflow-hidden rounded-2xl p-4 ring-1 ${accents.ring}`}
        >
            <span
                className="pointer-events-none absolute inset-0 z-[1] rounded-2xl transition-opacity duration-300"
                style={{
                    opacity: glow.active ? 0.35 : 0,
                    background: `radial-gradient(140px circle at ${glow.x}% ${glow.y}%, ${accents.color}, transparent 70%)`,
                    mixBlendMode: "screen",
                }}
            />
            <div className="relative z-[2] flex items-center gap-3">
                <span
                    className={`flex h-9 w-9 items-center justify-center rounded-xl bg-surface-2 ring-1 ${accents.ring} ${accents.text}`}
                >
                    <Sparkles className="h-4 w-4" />
                </span>
                <div>
                    <p className="text-sm font-semibold text-foreground">{feature.title}</p>
                    <p className="text-xs text-muted-foreground">{feature.caption}</p>
                </div>
            </div>
        </motion.div>
    );
}

/* ============ THINKING STAGE ============ */

function ThinkingStage({
    files,
    step,
    progress,
}) {
    return (
        <div className="relative flex flex-col items-center">
            {/* Brain core with orbiting effects */}
            <div className="relative my-6 flex h-64 w-64 items-center justify-center">
                {/* glow halo */}
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-violet/30 via-cyan/20 to-magenta/30 blur-3xl" />
                {/* radial pulses */}
                <span className="radial-pulse absolute h-24 w-24 rounded-full border border-violet/40" />
                <span className="radial-pulse absolute h-24 w-24 rounded-full border border-cyan/40" style={{ animationDelay: "0.8s" }} />
                <span className="radial-pulse absolute h-24 w-24 rounded-full border border-magenta/40" style={{ animationDelay: "1.6s" }} />

                {/* orbits */}
                <div className="absolute inset-6 animate-spin rounded-full border border-dashed border-violet/40 [animation-duration:14s]" />
                <div className="absolute inset-12 animate-spin rounded-full border border-dashed border-cyan/40 [animation-direction:reverse] [animation-duration:10s]" />

                {/* particles */}
                {[...Array(8)].map((_, i) => {
                    const angle = (i / 8) * Math.PI * 2;
                    const r = 110;
                    return (
                        <motion.span
                            key={i}
                            initial={{ x: Math.cos(angle) * r, y: Math.sin(angle) * r, opacity: 0 }}
                            animate={{
                                x: [Math.cos(angle) * r, 0],
                                y: [Math.sin(angle) * r, 0],
                                opacity: [0, 1, 0],
                                scale: [1, 0.4],
                            }}
                            transition={{ duration: 1.6, delay: i * 0.2, repeat: Infinity, ease: "easeIn" }}
                            className="absolute h-1.5 w-1.5 rounded-full"
                            style={{
                                background: ["var(--violet)", "var(--cyan)", "var(--magenta)"][i % 3],
                                boxShadow: `0 0 12px ${["var(--violet)", "var(--cyan)", "var(--magenta)"][i % 3]}`,
                            }}
                        />
                    );
                })}

                {/* Files orbiting toward core */}
                {files.slice(0, 5).map((f, i) => {
                    const angle = (i / Math.max(files.length, 1)) * Math.PI * 2;
                    const radius = 130;
                    const x = Math.cos(angle) * radius;
                    const y = Math.sin(angle) * radius;
                    return (
                        <motion.div
                            key={f.id}
                            initial={{ x, y, opacity: 0, scale: 0.6 }}
                            animate={{
                                x: [x, x * 0.4, 0],
                                y: [y, y * 0.4, 0],
                                opacity: [0, 1, 0],
                                scale: [0.6, 1, 0.4],
                            }}
                            transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.3, ease: "easeInOut" }}
                            className="absolute flex items-center gap-1.5 rounded-md border border-cyan/40 bg-surface-2/80 px-2 py-1 text-[10px] text-cyan shadow-[var(--shadow-glow-cyan)]"
                        >
                            <FileText className="h-3 w-3" />
                            <span className="max-w-[80px] truncate">{f.name}</span>
                        </motion.div>
                    );
                })}

                {/* Core */}
                <div className="pulse-ring relative z-10 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-violet via-magenta to-cyan shadow-[var(--shadow-glow-violet)]">
                    <Sparkles className="h-8 w-8 text-white" />
                </div>
            </div>

            {/* Progress bar */}
            <div className="w-full max-w-md">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ ease: "linear" }}
                        className="h-full bg-gradient-to-r from-violet via-magenta to-cyan"
                    />
                </div>
                <div className="mt-2 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                        <span className="flex gap-1">
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan [animation-delay:0ms]" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet [animation-delay:150ms]" />
                            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-magenta [animation-delay:300ms]" />
                        </span>
                        <AnimatePresence mode="wait">
                            <motion.span
                                key={step}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -6 }}
                                transition={{ duration: 0.3 }}
                                className="font-mono text-[10px] uppercase tracking-widest text-foreground/80"
                            >
                                {step}
                            </motion.span>
                        </AnimatePresence>
                    </div>
                    <span className="font-mono tabular-nums text-muted-foreground">{progress}%</span>
                </div>
            </div>
        </div>
    );
}

/* ============ RESULT CARD ============ */

function ResultCard({ onOpen, title, tone }) {
    return (
        <div className="space-y-4 pb-8">
            <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-violet/20 ring-1 ring-violet/40">
                    <Sparkles className="h-3.5 w-3.5 text-violet" />
                </span>
                <span className="font-mono text-[11px] uppercase tracking-widest text-violet">
                    PropoAI · Draft ready
                </span>
                <span className="h-px flex-1 bg-gradient-to-r from-violet/40 to-transparent" />
            </div>

            <motion.button
                onClick={onOpen}
                whileHover={{ y: -4 }}
                whileTap={{ scale: 0.99 }}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-strong group relative w-full overflow-hidden rounded-2xl p-6 text-left shadow-panel transition hover:border-violet/40"
            >
                {/* shimmer band */}
                <span className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-violet to-transparent opacity-60" />
                <span className="pointer-events-none absolute -bottom-20 -right-20 h-48 w-48 rounded-full bg-violet/30 opacity-50 blur-3xl transition group-hover:opacity-80" />

                <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                        <p className="font-mono text-[10px] uppercase tracking-widest text-cyan">Proposal · {tone}</p>
                        <h2 className="mt-1.5 truncate font-display text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                            {title}
                        </h2>
                        <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                            {sampleProposalSections.length} sections drafted — Executive Summary, Scope, Timeline, Team, Investment, Next Steps. Click to open in editor.
                        </p>
                    </div>
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-magenta text-white shadow-[var(--shadow-glow-violet)] transition group-hover:scale-110">
                        <ArrowRight className="h-5 w-5" />
                    </span>
                </div>

                {/* mini section preview chips */}
                <div className="mt-5 flex flex-wrap gap-1.5">
                    {sampleProposalSections.map((s, i) => (
                        <motion.span
                            key={s.id}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 + i * 0.06 }}
                            className="rounded-md border border-hairline bg-surface-2/60 px-2 py-1 text-[10px] text-foreground/80"
                        >
                            {String(i + 1).padStart(2, "0")} · {s.title}
                        </motion.span>
                    ))}
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-hairline pt-4 text-xs">
                    <span className="text-muted-foreground">Open in editor to refine each section</span>
                    <span className="font-mono uppercase tracking-widest text-violet group-hover:text-magenta">
                        Open editor →
                    </span>
                </div>
            </motion.button>
        </div>
    );
}

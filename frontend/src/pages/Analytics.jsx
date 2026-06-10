import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import { FileText, TrendingUp, Clock, Zap, BarChart2, Loader2, AlertCircle } from "lucide-react";
import api from "../api/client";

function useCount(target, duration = 1400) {
  const [n, setN] = useState(0);
  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(target * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return n;
}

const colorMap = {
  violet: "var(--violet)",
  cyan: "var(--cyan)",
  emerald: "var(--emerald)",
  amber: "var(--amber)",
  magenta: "var(--magenta)",
  muted: "var(--muted-foreground)",
};

const toneColors = {
  professional: "violet",
  persuasive: "cyan",
  formal: "emerald",
  friendly: "magenta",
  technical: "amber",
};

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/analytics/stats/")
      .then(({ data: d }) => setData(d))
      .catch(() => setError("Failed to load analytics."))
      .finally(() => setLoading(false));
  }, []);

  // Animated values (use 0 as fallback while loading)
  const total = useCount(data?.total_proposals || 0);
  const success = useCount(data?.success_rate || 0);
  const avgResp = useCount((data?.avg_response_seconds || 0) * 10) / 10;
  const finalized = useCount(data?.final_count || 0);

  const stats = [
    {
      icon: FileText,
      label: "Total Proposals",
      value: Math.round(total).toString(),
      color: "cyan",
    },
    { icon: TrendingUp, label: "Success Rate", value: `${success.toFixed(0)}%`, color: "emerald" },
    { icon: Clock, label: "Avg Gen Time", value: `${avgResp.toFixed(1)}s`, color: "magenta" },
    { icon: Zap, label: "Finalized", value: Math.round(finalized).toString(), color: "amber" },
  ];

  // Prepare tone chart data
  const toneData = (data?.by_tone || []).map((t) => ({
    name: t.tone?.charAt(0).toUpperCase() + t.tone?.slice(1),
    value: t.count,
    color: toneColors[t.tone] || "violet",
  }));

  const monthlyPerformance = data?.monthly_performance || [];

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-violet" />
          <p className="text-sm text-muted-foreground">Loading analytics…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center px-4">
        <div className="glass-strong w-full max-w-md rounded-2xl p-8 text-center">
          <AlertCircle className="mx-auto mb-3 h-10 w-10 text-destructive" />
          <p className="font-display font-semibold text-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6 py-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-[var(--shadow-glow-violet)]">
            <BarChart2 className="h-6 w-6 text-white" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Analytics
            </h1>
            <p className="text-sm text-muted-foreground">
              Real-time insights from your proposal activity
            </p>
          </div>
        </motion.header>

        {/* Stat cards */}
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, type: "spring", stiffness: 220 }}
              whileHover={{ y: -4 }}
              className="glass relative overflow-hidden rounded-2xl p-4"
            >
              <span
                className="flex h-11 w-11 items-center justify-center rounded-xl"
                style={{
                  background: `color-mix(in oklab, ${colorMap[s.color]} 22%, transparent)`,
                  boxShadow: `0 0 30px -10px ${colorMap[s.color]}`,
                }}
              >
                <s.icon className="h-5 w-5" style={{ color: colorMap[s.color] }} />
              </span>
              <p className="mt-3 font-display text-2xl font-bold tabular-nums text-foreground">
                {s.value}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{s.label}</p>
              <span
                className="pointer-events-none absolute -bottom-12 -right-12 h-28 w-28 rounded-full opacity-30 blur-3xl"
                style={{ background: colorMap[s.color] }}
              />
            </motion.div>
          ))}
        </div>

        {/* Status Breakdown */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { label: "Drafts", count: data?.draft_count || 0, color: "amber" },
            { label: "Finalized", count: data?.final_count || 0, color: "emerald" },
            { label: "Generating", count: data?.generating_count || 0, color: "violet" },
            { label: "Failed", count: data?.failed_count || 0, color: "magenta" },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="flex items-center gap-3 rounded-xl border border-hairline bg-surface/60 px-4 py-3 backdrop-blur"
            >
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{
                  background: colorMap[item.color],
                  boxShadow: `0 0 10px ${colorMap[item.color]}`,
                }}
              />
              <div>
                <p className="font-display text-lg font-bold tabular-nums text-foreground">
                  {item.count}
                </p>
                <p className="text-[11px] text-muted-foreground">{item.label}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Charts grid */}
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Monthly performance */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass rounded-2xl p-6"
          >
            <p className="font-display text-base font-semibold text-foreground">
              Monthly Performance
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Proposals created vs. finalized over the last 12 months
            </p>
            {monthlyPerformance.length === 0 ? (
              <div className="mt-8 flex h-48 items-center justify-center text-sm text-muted-foreground">
                <p>Not enough data yet. Generate more proposals to see trends.</p>
              </div>
            ) : (
              <div className="mt-4 h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={monthlyPerformance}
                    margin={{ left: -20, right: 0, top: 8, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="g-drafted" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--violet)" stopOpacity={0.6} />
                        <stop offset="100%" stopColor="var(--violet)" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="g-won" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--emerald)" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="var(--emerald)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--hairline)" vertical={false} />
                    <XAxis
                      dataKey="month"
                      stroke="var(--muted-foreground)"
                      tickLine={false}
                      axisLine={false}
                      fontSize={11}
                    />
                    <YAxis
                      stroke="var(--muted-foreground)"
                      tickLine={false}
                      axisLine={false}
                      fontSize={11}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface)",
                        border: "1px solid var(--hairline)",
                        borderRadius: 12,
                        fontSize: 12,
                        color: "var(--foreground)",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="drafted"
                      stroke="var(--violet)"
                      strokeWidth={2.5}
                      fill="url(#g-drafted)"
                      animationDuration={1200}
                      name="Created"
                    />
                    <Area
                      type="monotone"
                      dataKey="won"
                      stroke="var(--emerald)"
                      strokeWidth={2.5}
                      fill="url(#g-won)"
                      animationDuration={1400}
                      name="Finalized"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </motion.div>

          {/* Proposals by Tone */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass rounded-2xl p-6"
          >
            <p className="font-display text-base font-semibold text-foreground">
              Proposals by Tone
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Distribution of writing tones across your proposals
            </p>
            {toneData.length === 0 ? (
              <div className="mt-8 flex h-48 items-center justify-center text-sm text-muted-foreground">
                <p>No tone data available yet.</p>
              </div>
            ) : (
              <div className="mt-4 grid grid-cols-1 items-center gap-6 lg:grid-cols-2">
                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={toneData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={45}
                        outerRadius={80}
                        paddingAngle={3}
                        stroke="none"
                        animationDuration={1200}
                      >
                        {toneData.map((c) => (
                          <Cell key={c.name} fill={colorMap[c.color] || colorMap.violet} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface)",
                          border: "1px solid var(--hairline)",
                          borderRadius: 12,
                          fontSize: 12,
                          color: "var(--foreground)",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2">
                  {toneData.map((c, i) => (
                    <motion.div
                      key={c.name}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + i * 0.08 }}
                      className="flex items-center justify-between rounded-xl border border-hairline bg-surface/60 px-4 py-3 backdrop-blur"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="h-2.5 w-2.5 rounded-full"
                          style={{
                            background: colorMap[c.color] || colorMap.violet,
                            boxShadow: `0 0 10px ${colorMap[c.color] || colorMap.violet}`,
                          }}
                        />
                        <span className="text-sm font-medium text-foreground">{c.name}</span>
                      </div>
                      <span className="font-display text-lg font-bold text-foreground tabular-nums">
                        {c.value}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </div>

        {/* Provider usage */}
        {(data?.providers || []).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="glass mt-5 rounded-2xl p-6"
          >
            <p className="font-display text-base font-semibold text-foreground">
              AI Provider Usage
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Which AI models are generating your proposals
            </p>
            <div className="mt-4 h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.providers} margin={{ left: -20, right: 0, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="var(--hairline)" vertical={false} />
                  <XAxis
                    dataKey="provider"
                    stroke="var(--muted-foreground)"
                    tickLine={false}
                    axisLine={false}
                    fontSize={11}
                    tickFormatter={(v) => v?.charAt(0).toUpperCase() + v?.slice(1)}
                  />
                  <YAxis
                    stroke="var(--muted-foreground)"
                    tickLine={false}
                    axisLine={false}
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--hairline)",
                      borderRadius: 12,
                      fontSize: 12,
                      color: "var(--foreground)",
                    }}
                  />
                  <Bar
                    dataKey="count"
                    fill="var(--violet)"
                    radius={[6, 6, 0, 0]}
                    animationDuration={1200}
                    name="Proposals"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

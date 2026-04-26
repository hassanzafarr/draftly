import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { FileText, TrendingUp, Clock, DollarSign, BarChart2 } from "lucide-react";
import {
  analyticsStats,
  monthlyPerformance,
  winRateTrend,
  proposalsByCategory,
} from "../lib/mock-data";

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

export default function Analytics() {
  const total = useCount(analyticsStats.totalProposals);
  const success = useCount(analyticsStats.successRate);
  const avg = useCount(analyticsStats.avgResponse * 10) / 10;
  const revenue = useCount(analyticsStats.revenueWon / 1000);

  const stats = [
    { icon: FileText, label: "Total Proposals", value: Math.round(total).toString(), color: "cyan" },
    { icon: TrendingUp, label: "Success Rate", value: `${success.toFixed(0)}%`, color: "emerald" },
    { icon: Clock, label: "Avg Response", value: `${avg.toFixed(1)} days`, color: "magenta" },
    { icon: DollarSign, label: "Revenue Won", value: `${Math.round(revenue)}K`, color: "amber" },
  ];

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
            <BarChart2 className="h-6 w-6 text-white" />
          </span>
          <div>
            <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Analytics
            </h1>
            <p className="text-sm text-muted-foreground">
              Track your proposal performance and insights
            </p>
          </div>
        </motion.header>

        {/* Stat cards */}
        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, type: "spring", stiffness: 220 }}
              whileHover={{ y: -4 }}
              className="glass relative overflow-hidden rounded-2xl p-5"
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
              <p className="mt-4 font-display text-3xl font-bold tabular-nums text-foreground">
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

        {/* Charts grid */}
        <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {/* Monthly performance */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass rounded-2xl p-6"
          >
            <p className="font-display text-base font-semibold text-foreground">Monthly Performance</p>
            <div className="mt-4 h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyPerformance} margin={{ left: -20, right: 0, top: 8, bottom: 0 }}>
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
                  <XAxis dataKey="month" stroke="var(--muted-foreground)" tickLine={false} axisLine={false} fontSize={11} />
                  <YAxis stroke="var(--muted-foreground)" tickLine={false} axisLine={false} fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--hairline)",
                      borderRadius: 12,
                      fontSize: 12,
                      color: "var(--foreground)",
                    }}
                  />
                  <Area type="monotone" dataKey="drafted" stroke="var(--violet)" strokeWidth={2.5} fill="url(#g-drafted)" animationDuration={1200} />
                  <Area type="monotone" dataKey="won" stroke="var(--emerald)" strokeWidth={2.5} fill="url(#g-won)" animationDuration={1400} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Win rate trend */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass rounded-2xl p-6"
          >
            <p className="font-display text-base font-semibold text-foreground">Win Rate Trend</p>
            <div className="mt-4 h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={winRateTrend} margin={{ left: -20, right: 0, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="var(--hairline)" vertical={false} />
                  <XAxis dataKey="month" stroke="var(--muted-foreground)" tickLine={false} axisLine={false} fontSize={11} />
                  <YAxis stroke="var(--muted-foreground)" tickLine={false} axisLine={false} fontSize={11} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--hairline)",
                      borderRadius: 12,
                      fontSize: 12,
                      color: "var(--foreground)",
                    }}
                    formatter={(v) => [`${v}%`, "Win rate"]}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="var(--violet)"
                    strokeWidth={3}
                    dot={{ fill: "var(--magenta)", r: 5, strokeWidth: 0 }}
                    activeDot={{ r: 7, fill: "var(--magenta)" }}
                    animationDuration={1400}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        {/* Proposals by category */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass mt-5 rounded-2xl p-6"
        >
          <p className="font-display text-base font-semibold text-foreground">Proposals by Category</p>
          <div className="mt-4 grid grid-cols-1 items-center gap-6 lg:grid-cols-2">
            {/* Donut */}
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={proposalsByCategory}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    stroke="none"
                    animationDuration={1200}
                  >
                    {proposalsByCategory.map((c) => (
                      <Cell key={c.name} fill={colorMap[c.color]} />
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

            {/* List */}
            <div className="space-y-2">
              {proposalsByCategory.map((c, i) => (
                <motion.div
                  key={c.name}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 + i * 0.08 }}
                  className="flex items-center justify-between rounded-xl border border-hairline bg-surface/60 px-4 py-3 backdrop-blur"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ background: colorMap[c.color], boxShadow: `0 0 10px ${colorMap[c.color]}` }}
                    />
                    <span className="text-sm font-medium text-foreground">{c.name}</span>
                  </div>
                  <div className="flex items-baseline gap-2 text-right">
                    <span className="font-display text-lg font-bold text-foreground tabular-nums">{c.value}</span>
                    <span className="font-mono text-xs text-muted-foreground">{c.percentage}%</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

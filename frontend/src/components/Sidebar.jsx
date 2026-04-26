import { Link, useLocation, useNavigate } from "react-router-dom";
import { Home, FileText, Brain, BarChart3, Settings, LogOut, Sparkles, Sun, Moon } from "lucide-react";
import { motion } from "framer-motion";
import { useTheme } from "./ThemeProvider";
import useAuthStore from "../store/auth";

const items = [
  { to: "/", label: "Generator", icon: Home },
  { to: "/templates", label: "Templates", icon: FileText },
  { to: "/knowledge", label: "Knowledge", icon: Brain },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Sidebar() {
  const { pathname } = useLocation();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside
      className="relative z-20 flex h-dvh w-[78px] shrink-0 flex-col items-center justify-between border-r border-hairline py-6 backdrop-blur-xl"
      style={{ background: "var(--sidebar-bg)" }}
    >
      <Link to="/" className="group relative flex h-11 w-11 items-center justify-center rounded-xl">
        <span className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet to-magenta opacity-90 blur-[10px] transition group-hover:opacity-100" />
        <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-magenta">
          <Sparkles className="h-5 w-5 text-white" />
        </span>
      </Link>

      <nav className="flex flex-col items-center gap-3">
        {items.map(({ to, label, icon: Icon }) => {
          const active = pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className="group relative flex h-11 w-11 items-center justify-center rounded-xl"
              aria-label={label}
            >
              {active && (
                <motion.span
                  layoutId="active-pill"
                  className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet/30 to-magenta/30 ring-1 ring-violet/60"
                  style={{ boxShadow: "var(--shadow-glow-violet)" }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span
                className={`relative flex h-11 w-11 items-center justify-center rounded-xl border transition ${
                  active
                    ? "border-violet/40 text-foreground"
                    : "border-hairline text-muted-foreground hover:border-violet/40 hover:text-foreground"
                }`}
              >
                <Icon className="h-[18px] w-[18px]" />
              </span>
              <span className="pointer-events-none absolute left-[58px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-md bg-surface-2 px-2 py-1 text-xs text-foreground opacity-0 shadow-lg ring-1 ring-hairline transition group-hover:opacity-100">
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col items-center gap-3">
        <button
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          className="group relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border border-hairline text-muted-foreground transition hover:border-violet/40 hover:text-foreground"
        >
          <motion.span
            key={theme}
            initial={{ rotate: -90, opacity: 0, scale: 0.6 }}
            animate={{ rotate: 0, opacity: 1, scale: 1 }}
            exit={{ rotate: 90, opacity: 0, scale: 0.6 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="flex items-center justify-center"
          >
            {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
          </motion.span>
          <span className="pointer-events-none absolute left-[52px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-md bg-surface-2 px-2 py-1 text-xs text-foreground opacity-0 shadow-lg ring-1 ring-hairline transition group-hover:opacity-100">
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </span>
        </button>
        <button
          aria-label="Settings"
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-hairline text-muted-foreground hover:text-foreground"
        >
          <Settings className="h-[18px] w-[18px]" />
        </button>
        <button
          aria-label="Sign out"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-hairline text-muted-foreground hover:text-magenta"
        >
          <LogOut className="h-[18px] w-[18px]" />
        </button>
      </div>
    </aside>
  );
}

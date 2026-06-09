import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Settings as SettingsIcon, User, Building2, Lock, Shield,
  Save, Loader2, CheckCircle2, Crown, Sparkles,
  Zap, Star, CreditCard, ExternalLink,
} from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../api/client";
import useAuthStore from "../store/auth";

const TIER_CONFIG = {
  free: {
    label: "Free",
    price: "$0 / month",
    color: "cyan",
    icon: Zap,
    features: ["3 proposals/mo", "10 documents", "1 seat"],
  },
  solo: {
    label: "Solo",
    price: "$19 / month",
    color: "violet",
    icon: Sparkles,
    features: ["25 proposals/mo", "25 documents", "1 seat"],
  },
  studio: {
    label: "Studio",
    price: "$89 / month",
    color: "magenta",
    icon: Star,
    features: ["150 proposals/mo", "250 documents", "5 seats"],
  },
  agency: {
    label: "Agency",
    price: "$249 / month",
    color: "amber",
    icon: Crown,
    features: ["750 proposals/mo", "Unlimited documents", "10 seats"],
  },
};

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "security", label: "Security", icon: Lock },
];

export default function Settings() {
  const { user, fetchMe } = useAuthStore();
  const [tab, setTab] = useState("profile");

  // Profile state
  const [email, setEmail] = useState(user?.email || "");
  const [savingProfile, setSavingProfile] = useState(false);

  // Org state
  const [orgName, setOrgName] = useState(user?.org?.name || "");
  const [savingOrg, setSavingOrg] = useState(false);

  // Password state
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  // Billing state
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setEmail(user.email || "");
      setOrgName(user.org?.name || "");
    }
  }, [user]);

  const handleSaveProfile = async () => {
    setSavingProfile(true);
    try {
      await api.patch("/auth/profile/", { email });
      await fetchMe();
      toast.success("Profile updated.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSaveOrg = async () => {
    setSavingOrg(true);
    try {
      await api.patch("/auth/org/", { name: orgName });
      await fetchMe();
      toast.success("Organization updated.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update organization.");
    } finally {
      setSavingOrg(false);
    }
  };

  const handleBillingPortal = async () => {
    setPortalLoading(true);
    try {
      const { data } = await api.post("/billing/portal/");
      window.location.href = data.url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not open billing portal.");
      setPortalLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPw !== confirmPw) {
      toast.error("Passwords do not match.");
      return;
    }
    if (newPw.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    setSavingPw(true);
    try {
      await api.post("/auth/password/", {
        current_password: currentPw,
        new_password: newPw,
      });
      toast.success("Password changed successfully.");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to change password.");
    } finally {
      setSavingPw(false);
    }
  };

  const tier = TIER_CONFIG[user?.org?.subscription_tier] || TIER_CONFIG.free;
  const TierIcon = tier.icon;
  const displayName = user?.email?.split("@")[0] ?? "User";
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <div className="px-6 py-6">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-magenta shadow-[var(--shadow-glow-violet)]">
            <SettingsIcon className="h-6 w-6 text-white" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Settings
            </h1>
            <p className="text-sm text-muted-foreground">
              Manage your profile, organization, and security
            </p>
          </div>
        </motion.header>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-6 flex items-center gap-2 border-b border-hairline pb-0"
        >
          {TABS.map(({ id, label, icon: Icon }) => {
            const isActive = tab === id;
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition ${
                  isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
                {isActive && (
                  <motion.span
                    layoutId="settings-tab"
                    className="absolute inset-x-0 -bottom-px h-0.5 bg-gradient-to-r from-violet to-magenta"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
              </button>
            );
          })}
        </motion.div>

        {/* Tab content */}
        <div className="mt-6">
          {/* Profile */}
          {tab === "profile" && (
            <motion.div
              key="profile"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Avatar + name */}
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-5">
                  <div className="relative h-16 w-16 overflow-hidden rounded-2xl ring-2 ring-violet/50">
                    {user?.avatar_url ? (
                      <img src={user.avatar_url} alt="Profile" className="h-full w-full object-cover" />
                    ) : (
                      <>
                        <span className="absolute inset-0 bg-gradient-to-br from-violet to-magenta" />
                        <span className="relative z-10 flex h-full w-full items-center justify-center text-xl font-bold text-white">
                          {initials}
                        </span>
                      </>
                    )}
                  </div>
                  <div>
                    <p className="font-display text-xl font-semibold text-foreground">{displayName}</p>
                    <p className="text-sm text-muted-foreground capitalize">{user?.role || "member"} · {user?.org?.name || "—"}</p>
                  </div>
                </div>
              </div>

              {/* Email */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">Email Address</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Your email is used for login and notifications
                </p>
                <div className="mt-4 flex gap-3">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="flex-1 rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                    placeholder="your@email.com"
                  />
                  <button
                    onClick={handleSaveProfile}
                    disabled={savingProfile || email === user?.email}
                    className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] disabled:opacity-50"
                  >
                    {savingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save
                  </button>
                </div>
              </div>

              {/* Account info */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">Account Details</h3>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Account ID</span>
                    <span className="font-mono text-xs text-foreground">{user?.id?.slice(0, 8)}…</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Role</span>
                    <span className="capitalize text-foreground">{user?.role}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Member since</span>
                    <span className="text-foreground">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Organization */}
          {tab === "organization" && (
            <motion.div
              key="organization"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              {/* Subscription tier */}
              <div className="glass relative overflow-hidden rounded-2xl p-6">
                <span
                  className="pointer-events-none absolute -top-16 -right-16 h-40 w-40 rounded-full opacity-30 blur-3xl"
                  style={{ background: `var(--${tier.color})` }}
                />
                <div className="relative">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span
                        className="flex h-11 w-11 items-center justify-center rounded-xl"
                        style={{
                          background: `color-mix(in oklab, var(--${tier.color}) 22%, transparent)`,
                          boxShadow: `0 0 30px -10px var(--${tier.color})`,
                        }}
                      >
                        <TierIcon className="h-5 w-5" style={{ color: `var(--${tier.color})` }} />
                      </span>
                      <div>
                        <p className="font-display text-lg font-bold text-foreground">{tier.label} Plan</p>
                        <p className="text-xs text-muted-foreground">{tier.price}</p>
                      </div>
                    </div>

                    {/* Billing action button */}
                    {user?.org?.subscription_tier === "free" ? (
                      <a
                        href="/pricing"
                        className="flex shrink-0 items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet to-magenta px-4 py-2 text-xs font-semibold text-white shadow-[var(--shadow-glow-violet)]"
                      >
                        <CreditCard className="h-3.5 w-3.5" />
                        Upgrade
                      </a>
                    ) : (
                      <button
                        onClick={handleBillingPortal}
                        disabled={portalLoading}
                        className="flex shrink-0 items-center gap-1.5 rounded-xl border border-hairline bg-surface/60 px-4 py-2 text-xs font-medium text-foreground hover:bg-surface-2 disabled:opacity-50"
                      >
                        {portalLoading ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ExternalLink className="h-3.5 w-3.5" />
                        )}
                        Manage billing
                      </button>
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {tier.features.map((f) => (
                      <span
                        key={f}
                        className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/40 px-3 py-1.5 text-xs text-foreground/80"
                      >
                        <CheckCircle2 className="h-3 w-3" style={{ color: `var(--${tier.color})` }} />
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Org name */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">Organization Name</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  This appears on your generated proposals
                </p>
                <div className="mt-4 flex gap-3">
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="flex-1 rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                    placeholder="Your Organization"
                  />
                  <button
                    onClick={handleSaveOrg}
                    disabled={savingOrg || orgName === user?.org?.name}
                    className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] disabled:opacity-50"
                  >
                    {savingOrg ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save
                  </button>
                </div>
              </div>

              {/* Usage */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">Usage & Quotas</h3>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Document quota</span>
                    <span className="text-foreground">{user?.org?.doc_quota?.toLocaleString() || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Proposal quota</span>
                    <span className="text-foreground">{user?.org?.proposal_quota?.toLocaleString() || "—"} / month</span>
                  </div>
                  {user?.org?.current_period_end && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Billing period ends</span>
                      <span className="text-foreground">{new Date(user.org.current_period_end).toLocaleDateString()}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Organization created</span>
                    <span className="text-foreground">{user?.org?.created_at ? new Date(user.org.created_at).toLocaleDateString() : "—"}</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Security */}
          {tab === "security" && (
            <motion.div
              key="security"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber/15 ring-1 ring-amber/40">
                    <Shield className="h-4 w-4 text-amber" />
                  </span>
                  <div>
                    <h3 className="font-display text-base font-semibold text-foreground">Password</h3>
                    <p className="text-xs text-muted-foreground">
                      {user?.has_password ? "Update your account password" : "Your account uses Google Sign-In"}
                    </p>
                  </div>
                </div>

                {user?.has_password ? (
                  <div className="mt-6 space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Current Password</label>
                      <input
                        type="password"
                        value={currentPw}
                        onChange={(e) => setCurrentPw(e.target.value)}
                        className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                        placeholder="••••••••"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">New Password</label>
                      <input
                        type="password"
                        value={newPw}
                        onChange={(e) => setNewPw(e.target.value)}
                        className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                        placeholder="Min 8 characters"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">Confirm New Password</label>
                      <input
                        type="password"
                        value={confirmPw}
                        onChange={(e) => setConfirmPw(e.target.value)}
                        className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                        placeholder="Re-enter new password"
                      />
                    </div>
                    <button
                      onClick={handleChangePassword}
                      disabled={savingPw || !currentPw || !newPw}
                      className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] disabled:opacity-50"
                    >
                      {savingPw ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
                      Change Password
                    </button>
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-muted-foreground">
                    You signed in with Google. Password-based login is disabled for this account.
                  </p>
                )}
              </div>

              {/* Session info */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">Session</h3>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Auth method</span>
                    <span className="text-foreground">
                      {user?.has_password ? "Email + Password" : "Google Sign-In"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Access token</span>
                    <span className="font-mono text-xs text-foreground">
                      {localStorage.getItem("access_token") ? "Active" : "None"}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Settings as SettingsIcon,
  User,
  Building2,
  Lock,
  Shield,
  Save,
  Loader2,
  CheckCircle2,
  Crown,
  Sparkles,
  Zap,
  Star,
  CreditCard,
  ExternalLink,
  Users,
  Send,
  Trash2,
  MailOpen,
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
    price: "$12 / month",
    color: "violet",
    icon: Sparkles,
    features: ["25 proposals/mo", "25 documents", "1 seat"],
  },
  studio: {
    label: "Studio",
    price: "$49 / month",
    color: "magenta",
    icon: Star,
    features: ["150 proposals/mo", "250 documents", "5 seats"],
  },
  agency: {
    label: "Agency",
    price: "$149 / month",
    color: "amber",
    icon: Crown,
    features: ["750 proposals/mo", "Unlimited documents", "10 seats"],
  },
};

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "team", label: "Team", icon: Users },
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
    fetchMe();
  }, []);

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
                      <img
                        src={user.avatar_url}
                        alt="Profile"
                        className="h-full w-full object-cover"
                      />
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
                    <p className="font-display text-xl font-semibold text-foreground">
                      {displayName}
                    </p>
                    <p className="text-sm text-muted-foreground capitalize">
                      {user?.role || "member"} · {user?.org?.name || "—"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Email */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">
                  Email Address
                </h3>
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
                    {savingProfile ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    Save
                  </button>
                </div>
              </div>

              {/* Account info */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">
                  Account Details
                </h3>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Account ID</span>
                    <span className="font-mono text-xs text-foreground">
                      {user?.id?.slice(0, 8)}…
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Role</span>
                    <span className="capitalize text-foreground">{user?.role}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Member since</span>
                    <span className="text-foreground">
                      {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
                    </span>
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
                        <p className="font-display text-lg font-bold text-foreground">
                          {tier.label} Plan
                        </p>
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
                        <CheckCircle2
                          className="h-3 w-3"
                          style={{ color: `var(--${tier.color})` }}
                        />
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Org name */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">
                  Organization Name
                </h3>
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
                    {savingOrg ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                    Save
                  </button>
                </div>
              </div>

              {/* Usage */}
              <div className="glass rounded-2xl p-6">
                <h3 className="font-display text-base font-semibold text-foreground">
                  Usage & Quotas
                </h3>
                <div className="mt-5 space-y-5">
                  {/* Proposals */}
                  {(() => {
                    const used = user?.org?.proposals_used ?? 0;
                    const quota = user?.org?.proposal_quota ?? 0;
                    if (!quota) return null;
                    const pct = Math.min(Math.round((used / quota) * 100), 100);
                    const atLimit = used >= quota;
                    const isWarning = !atLimit && pct >= 80;
                    return (
                      <div>
                        <div className="mb-1.5 flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Proposals this month</span>
                          <span
                            className={
                              atLimit ? "font-semibold text-destructive" : "text-foreground"
                            }
                          >
                            {used} / {quota}
                          </span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
                          <div
                            className={`h-full rounded-full transition-all ${
                              atLimit
                                ? "bg-destructive"
                                : isWarning
                                  ? "bg-amber"
                                  : "bg-gradient-to-r from-violet to-magenta"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {atLimit && (
                          <p className="mt-1.5 text-xs text-destructive">
                            Monthly proposal limit reached.{" "}
                            <a
                              href="/pricing"
                              className="underline underline-offset-2 hover:text-foreground"
                            >
                              Upgrade plan →
                            </a>
                          </p>
                        )}
                        {isWarning && (
                          <p className="mt-1.5 text-xs text-amber">
                            {quota - used} proposal{quota - used !== 1 ? "s" : ""} remaining this
                            month.
                          </p>
                        )}
                      </div>
                    );
                  })()}

                  {/* Documents */}
                  {(() => {
                    const used = user?.org?.docs_used ?? 0;
                    const quota = user?.org?.doc_quota ?? 0;
                    const unlimited = quota >= 999999;
                    if (unlimited) {
                      return (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Documents</span>
                          <span className="text-foreground">{used} / Unlimited</span>
                        </div>
                      );
                    }
                    if (!quota) return null;
                    const pct = Math.min(Math.round((used / quota) * 100), 100);
                    const atLimit = used >= quota;
                    const isWarning = !atLimit && pct >= 80;
                    return (
                      <div>
                        <div className="mb-1.5 flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Documents</span>
                          <span
                            className={
                              atLimit ? "font-semibold text-destructive" : "text-foreground"
                            }
                          >
                            {used} / {quota}
                          </span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
                          <div
                            className={`h-full rounded-full transition-all ${
                              atLimit
                                ? "bg-destructive"
                                : isWarning
                                  ? "bg-amber"
                                  : "bg-gradient-to-r from-violet to-magenta"
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {atLimit && (
                          <p className="mt-1.5 text-xs text-destructive">
                            Document limit reached.{" "}
                            <a
                              href="/pricing"
                              className="underline underline-offset-2 hover:text-foreground"
                            >
                              Upgrade plan →
                            </a>
                          </p>
                        )}
                        {isWarning && (
                          <p className="mt-1.5 text-xs text-amber">
                            {quota - used} document slot{quota - used !== 1 ? "s" : ""} remaining.
                          </p>
                        )}
                      </div>
                    );
                  })()}

                  {/* Misc */}
                  <div className="space-y-3 border-t border-hairline pt-4 text-sm">
                    {user?.org?.current_period_end && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Billing period ends</span>
                        <span className="text-foreground">
                          {new Date(user.org.current_period_end).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Organization created</span>
                      <span className="text-foreground">
                        {user?.org?.created_at
                          ? new Date(user.org.created_at).toLocaleDateString()
                          : "—"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Team */}
          {tab === "team" && <TeamTab user={user} />}

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
                    <h3 className="font-display text-base font-semibold text-foreground">
                      Password
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {user?.has_password
                        ? "Update your account password"
                        : "Your account uses Google Sign-In"}
                    </p>
                  </div>
                </div>

                {user?.has_password ? (
                  <div className="mt-6 space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        Current Password
                      </label>
                      <input
                        type="password"
                        value={currentPw}
                        onChange={(e) => setCurrentPw(e.target.value)}
                        className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                        placeholder="••••••••"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        New Password
                      </label>
                      <input
                        type="password"
                        value={newPw}
                        onChange={(e) => setNewPw(e.target.value)}
                        className="w-full rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
                        placeholder="Min 8 characters"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                        Confirm New Password
                      </label>
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
                      {savingPw ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Lock className="h-4 w-4" />
                      )}
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

function TeamTab({ user }) {
  const isAdmin = user?.role === "admin";

  const [members, setMembers] = useState([]);
  const [seats, setSeats] = useState({ used: 0, limit: 0 });
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [sending, setSending] = useState(false);

  const loadTeam = useCallback(async () => {
    try {
      const requests = [api.get("/auth/team/members/")];
      if (isAdmin) requests.push(api.get("/auth/team/invites/"));
      const [membersRes, invitesRes] = await Promise.all(requests);
      setMembers(membersRes.data.members);
      setSeats({ used: membersRes.data.seats_used, limit: membersRes.data.seat_limit });
      if (invitesRes) setInvites(invitesRes.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load team.");
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    loadTeam();
  }, [loadTeam]);

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setSending(true);
    try {
      await api.post("/auth/team/invites/", {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      toast.success(`Invitation sent to ${inviteEmail.trim()}.`);
      setInviteEmail("");
      setInviteRole("member");
      await loadTeam();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send the invitation.");
    } finally {
      setSending(false);
    }
  };

  const handleRevoke = async (invite) => {
    try {
      await api.delete(`/auth/team/invites/${invite.id}/`);
      toast.success(`Invitation to ${invite.email} revoked.`);
      await loadTeam();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not revoke the invitation.");
    }
  };

  const handleRemoveMember = async (member) => {
    if (!window.confirm(`Remove ${member.email} from the organization?`)) return;
    try {
      await api.delete(`/auth/team/members/${member.id}/`);
      toast.success(`${member.email} removed.`);
      await loadTeam();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not remove the member.");
    }
  };

  const seatsFull = seats.limit > 0 && seats.used >= seats.limit;

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-violet" />
      </div>
    );
  }

  return (
    <motion.div
      key="team"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Seats */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display text-base font-semibold text-foreground">Team</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Members and pending invitations count toward your seats
            </p>
          </div>
          <span
            className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
              seatsFull
                ? "border-amber/40 bg-amber/10 text-amber"
                : "border-hairline bg-surface/40 text-foreground/80"
            }`}
          >
            {seats.used} of {seats.limit} seat{seats.limit !== 1 ? "s" : ""} used
          </span>
        </div>

        {/* Invite form — admins only */}
        {isAdmin && (
          <form onSubmit={handleInvite} className="mt-5 flex flex-wrap gap-3">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="teammate@company.com"
              className="min-w-[220px] flex-1 rounded-xl border border-hairline bg-surface/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              aria-label="Role"
              className="rounded-xl border border-hairline bg-surface/60 px-3 py-2.5 text-sm text-foreground backdrop-blur focus:border-violet/40 focus:outline-none"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button
              type="submit"
              disabled={sending || !inviteEmail.trim() || seatsFull}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet to-magenta px-5 py-2.5 text-sm font-semibold text-white shadow-[var(--shadow-glow-violet)] disabled:opacity-50"
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Invite
            </button>
            {seatsFull && (
              <p className="w-full text-xs text-amber">
                All seats are in use. Upgrade your plan to invite more teammates.
              </p>
            )}
          </form>
        )}
      </div>

      {/* Members */}
      <div className="glass rounded-2xl p-6">
        <h3 className="font-display text-base font-semibold text-foreground">
          Members ({members.length})
        </h3>
        <ul className="mt-4 divide-y divide-hairline">
          {members.map((m) => {
            const name = m.email.split("@")[0];
            return (
              <li key={m.id} className="flex items-center gap-4 py-3">
                <div className="relative h-9 w-9 shrink-0 overflow-hidden rounded-full ring-1 ring-violet/40">
                  {m.avatar_url ? (
                    <img src={m.avatar_url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <>
                      <span className="absolute inset-0 bg-gradient-to-br from-violet to-magenta" />
                      <span className="relative z-10 flex h-full w-full items-center justify-center text-[11px] font-semibold text-white">
                        {name.slice(0, 2).toUpperCase()}
                      </span>
                    </>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-foreground">
                    {m.email}
                    {m.id === user?.id && (
                      <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Joined {new Date(m.created_at).toLocaleDateString()}
                    {!m.is_active && " · pending verification"}
                  </p>
                </div>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] capitalize ${
                    m.role === "admin"
                      ? "border-violet/40 bg-violet/10 text-violet"
                      : "border-hairline bg-surface/40 text-foreground/70"
                  }`}
                >
                  {m.role}
                </span>
                {isAdmin && m.id !== user?.id && (
                  <button
                    onClick={() => handleRemoveMember(m)}
                    aria-label={`Remove ${m.email}`}
                    className="rounded-lg p-2 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      {/* Pending invites — admins only */}
      {isAdmin && (
        <div className="glass rounded-2xl p-6">
          <h3 className="font-display text-base font-semibold text-foreground">
            Pending Invitations ({invites.length})
          </h3>
          {invites.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">No pending invitations.</p>
          ) : (
            <ul className="mt-4 divide-y divide-hairline">
              {invites.map((inv) => (
                <li key={inv.id} className="flex items-center gap-4 py-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-cyan/10 ring-1 ring-cyan/40">
                    <MailOpen className="h-4 w-4 text-cyan" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-foreground">{inv.email}</p>
                    <p className="text-xs text-muted-foreground">
                      Expires {new Date(inv.expires_at).toLocaleDateString()}
                      {inv.invited_by_email && ` · invited by ${inv.invited_by_email}`}
                    </p>
                  </div>
                  <span className="rounded-full border border-hairline bg-surface/40 px-2.5 py-0.5 text-[11px] capitalize text-foreground/70">
                    {inv.role}
                  </span>
                  <button
                    onClick={() => handleRevoke(inv)}
                    aria-label={`Revoke invitation to ${inv.email}`}
                    className="rounded-lg p-2 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </motion.div>
  );
}

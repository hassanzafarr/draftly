import { Link } from "react-router-dom";

// Keep in sync with the providers configured in backend/config/settings.py.
const SUB_PROCESSORS = [
  {
    name: "Anthropic",
    purpose: "Proposal generation (primary AI model)",
    data: "RFP text and relevant excerpts of your documents",
    location: "United States",
    privacyUrl: "https://www.anthropic.com/legal/privacy",
  },
  {
    name: "Google AI (Gemini API)",
    purpose: "Document embeddings; fallback proposal generation",
    data: "Document text, RFP text",
    location: "United States",
    privacyUrl: "https://policies.google.com/privacy",
  },
  {
    name: "Groq",
    purpose: "Fallback proposal generation",
    data: "RFP text and relevant document excerpts",
    location: "United States",
    privacyUrl: "https://groq.com/privacy-policy/",
  },
  {
    name: "Cohere",
    purpose: "Search result re-ranking",
    data: "RFP text and candidate document excerpts",
    location: "United States",
    privacyUrl: "https://cohere.com/privacy",
  },
  {
    name: "Supabase",
    purpose: "Database and file storage",
    data: "All account and content data",
    location: "EU (Ireland)",
    privacyUrl: "https://supabase.com/privacy",
  },
  {
    name: "Microsoft Azure",
    purpose: "Application hosting",
    data: "Data in transit while requests are processed",
    location: "EU (France)",
    privacyUrl: "https://privacy.microsoft.com/privacystatement",
  },
  {
    name: "Upstash",
    purpose: "Background job queue",
    data: "Job identifiers and file names (no document content)",
    location: "EU (Ireland)",
    privacyUrl: "https://upstash.com/trust/privacy.pdf",
  },
  {
    name: "Vercel",
    purpose: "Website hosting",
    data: "IP address, request metadata",
    location: "Global edge network",
    privacyUrl: "https://vercel.com/legal/privacy-policy",
  },
  {
    name: "Resend",
    purpose: "Transactional email",
    data: "Email address, email content",
    location: "United States",
    privacyUrl: "https://resend.com/legal/privacy-policy",
  },
  {
    name: "Stripe",
    purpose: "Payment processing",
    data: "Email, billing details (we never see card numbers)",
    location: "United States / EU",
    privacyUrl: "https://stripe.com/privacy",
  },
  {
    name: "Google Sign-In",
    purpose: "Optional sign-in with Google",
    data: "Email, Google account ID, avatar",
    location: "United States",
    privacyUrl: "https://policies.google.com/privacy",
  },
  {
    name: "Sentry",
    purpose: "Error monitoring (opt-in only)",
    data: "Error traces, browser type, IP address",
    location: "United States",
    privacyUrl: "https://sentry.io/privacy/",
  },
];

export default function Privacy() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="app-backdrop" />

      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-hairline bg-surface/60 backdrop-blur-xl">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
            <Link to="/" className="flex items-center gap-2.5">
              <span className="relative flex h-8 w-8 items-center justify-center rounded-lg">
                <span
                  className="absolute inset-0 rounded-lg opacity-60 blur-[8px]"
                  style={{ background: "linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4)" }}
                  aria-hidden
                />
                <img
                  src="/logo.png"
                  alt="Draftly"
                  className="relative h-7 w-7 object-contain drop-shadow-lg"
                />
              </span>
              <span className="font-display text-lg font-semibold tracking-tight text-foreground">
                Draftly
              </span>
            </Link>
            <nav className="flex items-center gap-4 text-sm text-muted-foreground">
              <Link to="/terms" className="transition hover:text-foreground">
                Terms of Service
              </Link>
              <Link
                to="/login"
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-foreground transition"
                style={{
                  background: "linear-gradient(135deg, var(--violet), var(--magenta))",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                Sign in →
              </Link>
            </nav>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto max-w-3xl px-6 py-14">
          <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">
            Privacy Policy
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Effective date: <strong className="text-foreground">28 October 2026</strong> · Last
            updated: <strong className="text-foreground">28 October 2026</strong>
          </p>

          <div className="mt-10 space-y-10 text-sm leading-relaxed text-muted-foreground">
            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                1. Introduction and Data Controller
              </h2>
              <p>
                The Draftly proposal generation platform at{" "}
                <strong className="text-foreground">draftly.software</strong> (the “Service”) is
                operated by <strong className="text-foreground">Hassan Zafar</strong> (“
                <strong className="text-foreground">Draftly</strong>”, “we”, “us”, or “our”), who is
                the data controller for the personal data described in this policy.
              </p>
              <p className="mt-3">
                This Privacy Policy explains what personal data we collect, why we collect it, how
                we use and protect it, and your rights. Questions? Contact us at{" "}
                <a
                  href="mailto:hassanzafar619@gmail.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  hassanzafar619@gmail.com
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                2. What Data We Collect
              </h2>
              <div className="space-y-3">
                <div>
                  <strong className="text-foreground">Account data</strong> — your email address and
                  organisation name, collected when you register.
                </div>
                <div>
                  <strong className="text-foreground">Profile data</strong> — avatar URL and Google
                  account ID, only if you sign in with Google.
                </div>
                <div>
                  <strong className="text-foreground">Content data</strong> — documents you upload,
                  RFP text you submit, and proposals generated on your behalf. This data is stored
                  to provide the core Service and is scoped to your organisation.
                </div>
                <div>
                  <strong className="text-foreground">Usage data</strong> — proposal creation
                  counts, document upload counts, and plan tier usage — collected in aggregate to
                  enforce quotas and produce your analytics dashboard.
                </div>
                <div>
                  <strong className="text-foreground">Technical data</strong> — IP address, browser
                  type, and error traces, collected <em>only</em> if you consent to analytics
                  cookies (Sentry error tracking). If you choose “Essential Only”, no technical data
                  is collected by us.
                </div>
                <div>
                  <strong className="text-foreground">Payment data</strong> — billing is handled
                  directly by{" "}
                  <a
                    href="https://stripe.com"
                    className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Stripe
                  </a>
                  . We never see or store your card number, CVC, or bank details. We store only
                  Stripe customer and subscription IDs to manage your plan.
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                3. How We Use Your Data
              </h2>
              <ul className="list-disc space-y-1.5 pl-4">
                <li>To create and manage your account and organisation.</li>
                <li>
                  To provide the proposal generation Service (RAG retrieval, AI generation, document
                  storage).
                </li>
                <li>
                  To send transactional emails — email verification, password reset, billing
                  receipts.
                </li>
                <li>To process subscription payments through Stripe.</li>
                <li>To enforce plan quotas (document and proposal limits).</li>
                <li>
                  To monitor errors and performance via Sentry —{" "}
                  <em>only with your explicit consent</em>.
                </li>
                <li>
                  To produce the analytics dashboard shown to your organisation (no data shared
                  externally).
                </li>
              </ul>
              <p className="mt-3">
                We do <strong className="text-foreground">not</strong> sell your data to third
                parties, use it for advertising, or train AI models on your documents.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                4. Cookie Policy
              </h2>
              <div className="space-y-3">
                <div>
                  <strong className="text-foreground">Essential storage (always active)</strong> —
                  JWT authentication tokens stored in your browser’s{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">localStorage</code>.
                  These are necessary for you to stay logged in. They are not advertising cookies
                  and do not track you across websites.
                </div>
                <div>
                  <strong className="text-foreground">Analytics cookies (opt-in only)</strong> — if
                  you click “Accept All” on the consent banner, we load Sentry, which may use
                  browser storage to correlate error sessions. Sentry is configured with text
                  masking and media blocking to minimise exposure of personal data. You can change
                  your preference at any time by clearing your browser’s{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">localStorage</code> key{" "}
                  <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">
                    draftly-cookie-consent
                  </code>{" "}
                  and reloading.
                </div>
                <div>
                  We use{" "}
                  <strong className="text-foreground">
                    no advertising, social-media, or third-party tracking cookies
                  </strong>
                  .
                </div>
              </div>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                5. Data Sharing
              </h2>
              <p>
                We share data only with the following sub-processors, and only what each one needs
                to perform its function:
              </p>
              <div className="mt-4 overflow-x-auto rounded-lg border border-hairline">
                <table className="w-full min-w-[520px] text-left text-xs">
                  <thead className="bg-surface-2 text-foreground">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Sub-processor</th>
                      <th className="px-3 py-2 font-semibold">Purpose</th>
                      <th className="px-3 py-2 font-semibold">Data shared</th>
                      <th className="px-3 py-2 font-semibold">Location</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline">
                    {SUB_PROCESSORS.map((p) => (
                      <tr key={p.name}>
                        <td className="px-3 py-2 align-top">
                          <a
                            href={p.privacyUrl}
                            className="font-medium text-foreground underline underline-offset-2 transition hover:opacity-70"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {p.name}
                          </a>
                        </td>
                        <td className="px-3 py-2 align-top">{p.purpose}</td>
                        <td className="px-3 py-2 align-top">{p.data}</td>
                        <td className="px-3 py-2 align-top">{p.location}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3">
                <strong className="text-foreground">International transfers.</strong> Your account
                data, documents and proposals are stored in the European Union. Some sub-processors
                (the AI providers, Stripe, Sentry, Vercel and Resend) may process data in the United
                States. These transfers rely on the safeguards those providers offer, such as the EU
                Standard Contractual Clauses or the EU–U.S. Data Privacy Framework.
              </p>
              <p className="mt-3">No data is sold to third parties.</p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                6. Data Retention
              </h2>
              <p>We retain your account and content data for as long as your account is active.</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  <strong className="text-foreground">Account deletion is immediate.</strong> When
                  you delete your account from{" "}
                  <strong className="text-foreground">Settings → Privacy</strong>, your personal
                  data is removed from our live systems right away. If you are the only member of
                  your organisation, its documents, RFPs, proposals and uploaded files are deleted
                  too; otherwise that content stays with your organisation without your name
                  attached.
                </li>
                <li>
                  <strong className="text-foreground">Backups</strong> — residual copies in our
                  database backups are overwritten within{" "}
                  <strong className="text-foreground">30 days</strong>.
                </li>
                <li>
                  <strong className="text-foreground">Billing records</strong> — invoices and
                  payment records held by Stripe are kept only as long as tax and accounting law
                  requires (up to <strong className="text-foreground">10 years</strong> under German
                  law).
                </li>
              </ul>
              <p className="mt-3">
                If you cannot access your account, request deletion by emailing{" "}
                <a
                  href="mailto:hassanzafar619@gmail.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  hassanzafar619@gmail.com
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                7. Your Rights
              </h2>
              <p>Depending on your location, you may have the following rights:</p>
              <ul className="mt-3 list-disc space-y-1.5 pl-4">
                <li>
                  <strong className="text-foreground">Access</strong> — request a copy of the
                  personal data we hold about you.
                </li>
                <li>
                  <strong className="text-foreground">Rectification</strong> — correct inaccurate or
                  incomplete data.
                </li>
                <li>
                  <strong className="text-foreground">Erasure</strong> — request deletion of your
                  data (“right to be forgotten”).
                </li>
                <li>
                  <strong className="text-foreground">Restriction</strong> — ask us to pause
                  processing your data.
                </li>
                <li>
                  <strong className="text-foreground">Portability</strong> — receive your data in a
                  machine-readable format.
                </li>
                <li>
                  <strong className="text-foreground">Objection</strong> — object to processing
                  based on legitimate interests.
                </li>
                <li>
                  <strong className="text-foreground">Withdraw consent</strong> — opt out of
                  analytics cookies at any time (see Cookie Policy above).
                </li>
              </ul>
              <p className="mt-3">
                You can exercise your rights of access, portability and erasure yourself: go to{" "}
                <strong className="text-foreground">Settings → Privacy</strong> to download a copy
                of your data (a ZIP containing machine-readable JSON plus your original files) or to
                delete your account. For any other request, contact{" "}
                <a
                  href="mailto:hassanzafar619@gmail.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  hassanzafar619@gmail.com
                </a>
                . We will respond within 30 days.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                8. Security
              </h2>
              <p>
                All traffic is encrypted with HTTPS (HSTS enforced). Every request is scoped to your
                organisation so one customer can never read another’s data. Passwords are hashed
                with PBKDF2, changing your password signs out every other session, and sign-in,
                registration and password-reset endpoints are rate-limited. No system is perfectly
                secure — if you discover a vulnerability, please report it to{" "}
                <a
                  href="mailto:hassanzafar619@gmail.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  hassanzafar619@gmail.com
                </a>
                .
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                9. Changes to This Policy
              </h2>
              <p>
                We may update this policy. Material changes will be communicated by email at least{" "}
                <strong className="text-foreground">30 days</strong> before they take effect.
                Continued use of the Service after that date constitutes acceptance of the updated
                policy.
              </p>
            </section>

            <section>
              <h2 className="mb-3 font-display text-lg font-semibold text-foreground">
                10. Contact
              </h2>
              <p>
                <strong className="text-foreground">Hassan Zafar</strong>, operating as Draftly
                <br />
                Fulda, Germany
                <br />
                Email:{" "}
                <a
                  href="mailto:hassanzafar619@gmail.com"
                  className="text-foreground underline underline-offset-2 transition hover:opacity-70"
                >
                  hassanzafar619@gmail.com
                </a>
              </p>
            </section>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-hairline py-8 text-center text-xs text-muted-foreground">
          <span>© 2026 Hassan Zafar. All rights reserved.</span>
          <span className="mx-3">·</span>
          <Link to="/terms" className="transition hover:text-foreground">
            Terms of Service
          </Link>
          <span className="mx-3">·</span>
          <Link to="/privacy" className="text-foreground">
            Privacy Policy
          </Link>
        </footer>
      </div>
    </div>
  );
}
